"""
Authentication Routes - BRAC Login & User Management
Handles user authentication, registration, and session management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import logging

from sqlalchemy.orm import Session
from api.database import get_db
from api.services.auth import AuthService, get_current_user_from_token
from api.models.user import User, Role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


# ==================== REQUEST/RESPONSE MODELS ====================


class LoginRequest(BaseModel):
    """Login request model"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)  # Allow deployment keys
    tenant_id: Optional[str] = None  # Optional - auto-selected if user has only one


class LoginResponse(BaseModel):
    """Login response model"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict
    requires_tenant_selection: bool = False
    available_tenants: Optional[List[dict]] = None


class TenantSelectRequest(BaseModel):
    """Request to select tenant after initial auth"""
    
    username: str
    session_token: str  # Temporary token from first login step
    tenant_id: str


class RegisterRequest(BaseModel):
    """User registration model"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    invitation_code: Optional[str] = None  # For tenant invitation


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""

    current_password: str
    new_password: str = Field(..., min_length=8)


class CreateUserRequest(BaseModel):
    """Admin endpoint to create users"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    is_global_admin: bool = False
    roles: Optional[List[str]] = []


class AssignRoleRequest(BaseModel):
    """Assign role to user"""

    user_id: str
    role_name: str
    tenant_id: Optional[str] = None


# ==================== DEPENDENCIES ====================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials
    user = get_current_user_from_token(token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to require admin user"""
    if not current_user.is_global_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


# ==================== PUBLIC ENDPOINTS ====================


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.
    
    Flow:
    1. If user has only one tenant -> auto-select and return full tokens
    2. If user has multiple tenants and no tenant_id provided -> return tenant list for selection
    3. If user has multiple tenants and tenant_id provided -> use that tenant

    The access token is used for API requests (1 hour validity).
    The refresh token is used to obtain new access tokens (30 days validity).
    """
    auth_service = AuthService(db)

    # Get client info
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")

    # Authenticate
    user, error = auth_service.authenticate_user(
        request.username, request.password, ip_address=ip_address, user_agent=user_agent
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user's tenants
    user_tenants = user.tenants if user.tenants else []
    
    # Determine which tenant to use
    # Use tenant.id (UUID) for session, but tenant.tenant_id (slug) for tokens
    selected_tenant = None  # Will hold the actual Tenant object
    selected_tenant_slug = request.tenant_id  # The slug like "jeturing"
    
    if len(user_tenants) == 0:
        # User has no tenants - use default (jeturing) or none
        selected_tenant = None
        selected_tenant_slug = None
    elif len(user_tenants) == 1:
        # Only one tenant - auto-select
        selected_tenant = user_tenants[0]
        selected_tenant_slug = selected_tenant.tenant_id  # slug for JWT
    elif len(user_tenants) > 1 and not request.tenant_id:
        # Multiple tenants and none specified - require selection
        return LoginResponse(
            access_token="",
            refresh_token="",
            expires_in=0,
            user=user.to_dict(),
            requires_tenant_selection=True,
            available_tenants=[
                {
                    "id": str(t.id),
                    "tenant_id": t.tenant_id,
                    "name": t.name,
                    "subdomain": t.subdomain
                } for t in user_tenants
            ]
        )
    else:
        # Multiple tenants with specific one selected - find it
        for t in user_tenants:
            if t.tenant_id == request.tenant_id or str(t.id) == request.tenant_id:
                selected_tenant = t
                selected_tenant_slug = t.tenant_id
                break

    # Create tokens with selected tenant slug (for JWT payload)
    access_token = auth_service.create_access_token(user, tenant_id=selected_tenant_slug)
    refresh_token = auth_service.create_refresh_token(user)

    # Create session with tenant UUID (for database FK)
    auth_service.create_session(
        user,
        access_token,
        tenant_id=str(selected_tenant.id) if selected_tenant else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,  # 1 hour
        user=user.to_dict(),
        requires_tenant_selection=False,
        available_tenants=None,
    )


@router.post("/select-tenant", response_model=LoginResponse)
async def select_tenant(request: TenantSelectRequest, req: Request, db: Session = Depends(get_db)):
    """
    Complete login by selecting a tenant (for users with multiple tenants).
    Called after initial login returns requires_tenant_selection=True.
    """
    auth_service = AuthService(db)
    
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
    
    # Verify user has access to this tenant
    tenant_ids = [t.tenant_id for t in user.tenants]
    if request.tenant_id not in tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this tenant"
        )
    
    # Get client info
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    # Create tokens with selected tenant
    access_token = auth_service.create_access_token(user, tenant_id=request.tenant_id)
    refresh_token = auth_service.create_refresh_token(user)

    # Create session
    auth_service.create_session(
        user,
        access_token,
        tenant_id=request.tenant_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user=user.to_dict(),
        requires_tenant_selection=False,
        available_tenants=None,
    )


@router.post("/register", response_model=LoginResponse)
async def register(
    request: RegisterRequest, req: Request, db: Session = Depends(get_db)
):
    """
    Register a new user account.

    Note: New registrations are disabled by default in production.
    Use admin endpoints to create users.
    """
    # TODO: Check if registration is enabled
    # TODO: Validate invitation code if provided

    auth_service = AuthService(db)

    user, error = auth_service.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        is_global_admin=False,
    )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Auto-login after registration
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")

    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)

    auth_service.create_session(
        user, access_token, ip_address=ip_address, user_agent=user_agent
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        user=user.to_dict(),
    )


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using a valid refresh token.
    """
    auth_service = AuthService(db)

    # Verify refresh token
    payload = auth_service.verify_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get user
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    access_token = auth_service.create_access_token(user)

    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Logout current user and invalidate session.
    """
    token = credentials.credentials
    auth_service = AuthService(db)

    # Invalidate session
    success = auth_service.invalidate_session(token)

    return {"message": "Logged out successfully" if success else "Session not found"}


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return current_user.to_dict(include_sensitive=False)


@router.put("/me/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.
    """
    # Verify current password
    if not current_user.check_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Set new password
    current_user.set_password(request.new_password)
    db.commit()

    # Invalidate all existing sessions
    auth_service = AuthService(db)
    count = auth_service.invalidate_all_user_sessions(str(current_user.id))

    logger.info(
        f"✅ Password changed for user {current_user.username}, {count} sessions invalidated"
    )

    return {"message": "Password changed successfully", "sessions_invalidated": count}


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get all active sessions for current user.
    """
    from api.models.user import UserSession

    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id, UserSession.is_active)
        .all()
    )

    return {"sessions": [s.to_dict() for s in sessions]}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke a specific session.
    """
    from api.models.user import UserSession

    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == current_user.id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    session.is_active = False
    db.commit()

    return {"message": "Session revoked successfully"}


# ==================== ADMIN ENDPOINTS ====================


@router.post("/users", dependencies=[Depends(get_current_admin_user)])
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to create a new user.
    """
    auth_service = AuthService(db)

    user, error = auth_service.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        is_global_admin=request.is_global_admin,
        created_by=current_user.username,
    )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Assign roles if provided
    for role_name in request.roles:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            auth_service.assign_role(user, role)

    return {"message": "User created successfully", "user": user.to_dict()}


@router.get("/users", dependencies=[Depends(get_current_admin_user)])
async def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Admin endpoint to list all users.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()

    return {
        "users": [u.to_dict() for u in users],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/users/{user_id}", dependencies=[Depends(get_current_admin_user)])
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    Admin endpoint to get user details.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user.to_dict(include_sensitive=True)


@router.put("/users/{user_id}/activate", dependencies=[Depends(get_current_admin_user)])
async def activate_user(user_id: str, db: Session = Depends(get_db)):
    """
    Admin endpoint to activate a user account.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = True
    user.is_locked = False
    user.locked_until = None
    user.failed_login_attempts = 0
    db.commit()

    return {"message": "User activated successfully"}


@router.put(
    "/users/{user_id}/deactivate", dependencies=[Depends(get_current_admin_user)]
)
async def deactivate_user(user_id: str, db: Session = Depends(get_db)):
    """
    Admin endpoint to deactivate a user account.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = False
    db.commit()

    # Invalidate all sessions
    auth_service = AuthService(db)
    count = auth_service.invalidate_all_user_sessions(str(user.id))

    return {"message": "User deactivated successfully", "sessions_invalidated": count}


@router.post("/roles/assign", dependencies=[Depends(get_current_admin_user)])
async def assign_role_to_user(
    request: AssignRoleRequest, db: Session = Depends(get_db)
):
    """
    Admin endpoint to assign a role to a user.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    role = db.query(Role).filter(Role.name == request.role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    auth_service = AuthService(db)
    success = auth_service.assign_role(user, role, tenant_id=request.tenant_id)

    if not success:
        return {"message": "User already has this role"}

    return {"message": "Role assigned successfully"}


@router.get("/roles", dependencies=[Depends(get_current_admin_user)])
async def list_roles(db: Session = Depends(get_db)):
    """
    Admin endpoint to list all roles.
    """
    roles = db.query(Role).all()

    return {"roles": [r.to_dict() for r in roles]}
