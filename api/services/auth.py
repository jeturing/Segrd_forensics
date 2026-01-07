"""
Authentication Service for BRAC (Base Roles and Claims)
JWT-based authentication with multi-tenant support
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import jwt
from jwt import PyJWTError as JWTError
from sqlalchemy.orm import Session

from api.models.user import User, UserSession, UserAuditLog, Role
from api.config import settings

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days


class AuthService:
    """Authentication and authorization service"""

    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user with username and password.
        Returns (User, error_message) tuple.
        """
        # Find user by username or email
        user = (
            self.db.query(User)
            .filter((User.username == username) | (User.email == username))
            .first()
        )

        if not user:
            logger.warning(f"🚫 Login attempt for non-existent user: {username}")
            self._log_auth_event(
                None,
                "login_failed",
                "failure",
                {"reason": "user_not_found", "username": username},
                ip_address,
                user_agent,
            )
            return None, "Invalid username or password"

        # Check if account is locked
        if user.is_locked:
            if user.locked_until and datetime.utcnow() > user.locked_until:
                # Unlock account after lockout period
                user.is_locked = False
                user.locked_until = None
                user.failed_login_attempts = 0
                self.db.commit()
            else:
                logger.warning(f"🔒 Login attempt for locked account: {username}")
                self._log_auth_event(
                    user.id,
                    "login_failed",
                    "failure",
                    {"reason": "account_locked"},
                    ip_address,
                    user_agent,
                )
                return None, "Account is locked. Please try again later."

        # Check if account is active
        if not user.is_active:
            logger.warning(f"🚫 Login attempt for inactive account: {username}")
            self._log_auth_event(
                user.id,
                "login_failed",
                "failure",
                {"reason": "account_inactive"},
                ip_address,
                user_agent,
            )
            return None, "Account is not active. Contact administrator."

        # Verify password
        if not user.check_password(password):
            user.increment_failed_login()
            self.db.commit()

            logger.warning(
                f"🚫 Failed login attempt for {username} "
                f"({user.failed_login_attempts} attempts)"
            )
            self._log_auth_event(
                user.id,
                "login_failed",
                "failure",
                {"reason": "invalid_password", "attempts": user.failed_login_attempts},
                ip_address,
                user_agent,
            )
            return None, "Invalid username or password"

        # Successful authentication
        user.reset_failed_login()
        self.db.commit()

        logger.info(f"✅ Successful login for user: {username}")
        self._log_auth_event(
            user.id,
            "login_success",
            "success",
            {"username": username},
            ip_address,
            user_agent,
        )

        return user, None

    def create_access_token(
        self,
        user: User,
        tenant_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token for the user"""
        if expires_delta is None:
            expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.utcnow() + expires_delta

        # Build token payload with user claims
        to_encode = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_global_admin": user.is_global_admin,
            "tenant_id": tenant_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }

        # Add roles and permissions
        if tenant_id:
            roles = user.get_tenant_roles(tenant_id)
        else:
            roles = user.roles

        to_encode["roles"] = [role.name for role in roles]

        # Flatten permissions from all roles
        all_permissions = set()
        for role in roles:
            all_permissions.update(role.permissions)
        to_encode["permissions"] = list(all_permissions)

        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, user: User) -> str:
        """Create a JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "sub": str(user.id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        Returns payload if valid, None otherwise.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # Check token type
            token_type = payload.get("type", "access")
            if token_type not in ["access", "refresh"]:
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return None

            return payload

        except JWTError as e:
            logger.warning(f"⚠️ JWT verification failed: {e}")
            return None

    def create_session(
        self,
        user: User,
        session_token: str,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_hours: int = 24,
    ) -> UserSession:
        """Create a new user session"""
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def get_session(self, session_token: str) -> Optional[UserSession]:
        """Get a user session by token"""
        session = (
            self.db.query(UserSession)
            .filter(
                UserSession.session_token == session_token,
                UserSession.is_active,
            )
            .first()
        )

        if session and session.is_expired():
            session.is_active = False
            self.db.commit()
            return None

        return session

    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a user session"""
        session = (
            self.db.query(UserSession)
            .filter(UserSession.session_token == session_token)
            .first()
        )

        if session:
            session.is_active = False
            self.db.commit()
            return True

        return False

    def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        count = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active)
            .update({"is_active": False})
        )

        self.db.commit()
        return count

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_global_admin: bool = False,
        created_by: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Create a new user.
        Returns (User, error_message) tuple.
        """
        # Check if username already exists
        existing = (
            self.db.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )

        if existing:
            return None, "Username or email already exists"

        # Validate password strength
        if len(password) < 8:
            return None, "Password must be at least 8 characters long"

        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            is_global_admin=is_global_admin,
            is_active=True,
            is_verified=is_global_admin,  # Auto-verify admin users
            created_by=created_by,
        )

        user.set_password(password)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"✅ User created: {username} (admin={is_global_admin})")

        return user, None

    def assign_role(
        self, user: User, role: Role, tenant_id: Optional[str] = None
    ) -> bool:
        """Assign a role to a user, optionally scoped to a tenant"""
        # Check if user already has this role
        if role in user.roles:
            return False

        user.roles.append(role)
        self.db.commit()

        logger.info(f"✅ Role '{role.name}' assigned to user {user.username}")
        return True

    def remove_role(self, user: User, role: Role) -> bool:
        """Remove a role from a user"""
        if role not in user.roles:
            return False

        user.roles.remove(role)
        self.db.commit()

        logger.info(f"✅ Role '{role.name}' removed from user {user.username}")
        return True

    def get_or_create_role(
        self,
        name: str,
        display_name: str,
        permissions: list,
        description: Optional[str] = None,
        is_system: bool = False,
    ) -> Role:
        """Get existing role or create a new one"""
        role = self.db.query(Role).filter(Role.name == name).first()

        if role:
            return role

        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            permissions=permissions,
            is_system=is_system,
        )

        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        logger.info(f"✅ Role created: {name}")
        return role

    def _log_auth_event(
        self,
        user_id: Optional[str],
        event_type: str,
        status: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Log an authentication event to audit log"""
        log = UserAuditLog(
            user_id=user_id,
            event_type=event_type,
            action=event_type,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            tenant_id=tenant_id,
            details=details,
        )

        self.db.add(log)
        self.db.commit()


def get_current_user_from_token(token: str, db: Session) -> Optional[User]:
    """
    Get the current user from a JWT token.
    Used by route dependencies.
    """
    auth_service = AuthService(db)
    payload = auth_service.verify_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user
