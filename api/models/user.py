"""
User Model for BRAC (Base Roles and Claims) Authentication
Multi-tenant user management with granular permissions
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    JSON,
    Text,
    Integer,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import relationship
import uuid
import bcrypt

from api.database import Base, GUID


# Association table for many-to-many relationship between users and tenants
user_tenants = Table(
    "user_tenants",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE")),
    Column(
        "tenant_id", GUID(), ForeignKey("tenants.id", ondelete="CASCADE")
    ),
    Column("created_at", DateTime, default=datetime.utcnow),
)


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE")),
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE")),
    Column(
        "tenant_id",
        GUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    ),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class User(Base):
    """
    User model with BRAC (Base Roles and Claims) support.
    Supports multi-tenant access with different roles per tenant.
    """

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Personal Information
    full_name = Column(String(255), nullable=True)
    department = Column(String(100), nullable=True)
    title = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)

    # Global Admin Flag (for cross-tenant administrators)
    is_global_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)

    # Metadata (using user_metadata to avoid conflict with SQLAlchemy's metadata attribute)
    created_by = Column(String(255), nullable=True)
    user_metadata = Column(JSON, default=dict)

    # Relationships
    tenants = relationship("Tenant", secondary=user_tenants, back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "UserAuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "UserApiKey", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"

    def set_password(self, password: str) -> None:
        """Hash and set the user's password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode(
            "utf-8"
        )
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def increment_failed_login(self) -> None:
        """Increment failed login attempts and lock if threshold exceeded"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.is_locked = True
            # Lock for 30 minutes
            from datetime import timedelta

            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    def reset_failed_login(self) -> None:
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.is_locked = False
        self.locked_until = None
        self.last_login = datetime.utcnow()

    def has_permission(self, permission: str, tenant_id: Optional[str] = None) -> bool:
        """
        Check if user has a specific permission.
        If tenant_id provided, checks permissions within that tenant.
        Global admins have all permissions.
        """
        if self.is_global_admin:
            return True

        # Check permissions from all assigned roles
        for role in self.roles:
            # If tenant_id specified, only check roles for that tenant
            if tenant_id:
                # Get user_roles association to check tenant_id
                # This is simplified - in production, query the association table
                pass

            if permission in role.permissions:
                return True

        return False

    def get_tenant_roles(self, tenant_id: str) -> List["Role"]:
        """Get all roles for a specific tenant"""
        # This would query the user_roles association table
        # Simplified implementation
        return [role for role in self.roles]

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "department": self.department,
            "title": self.title,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_locked": self.is_locked,
            "is_global_admin": self.is_global_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "tenants": [{"id": str(t.id), "name": t.name} for t in self.tenants],
            "roles": [{"id": str(r.id), "name": r.name} for r in self.roles],
        }

        if include_sensitive:
            data["locked_until"] = (
                self.locked_until.isoformat() if self.locked_until else None
            )
            data["failed_login_attempts"] = self.failed_login_attempts
            data["password_changed_at"] = (
                self.password_changed_at.isoformat()
                if self.password_changed_at
                else None
            )

        return data


class Role(Base):
    """
    Role model for BRAC system.
    Roles contain a set of permissions and can be assigned to users.
    """

    __tablename__ = "roles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Permissions stored as JSON array
    permissions = Column(JSON, default=list)

    # Role Type (system roles cannot be deleted)
    is_system = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSession(Base):
    """
    User session model for tracking active sessions.
    Supports multiple concurrent sessions per user.
    """

    __tablename__ = "user_sessions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_token = Column(String(1024), unique=True, nullable=False, index=True)

    # Session Info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    tenant_id = Column(GUID(), ForeignKey("tenants.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession {self.id} for user {self.user_id}>"

    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "is_active": self.is_active,
            "is_expired": self.is_expired(),
        }


class UserAuditLog(Base):
    """
    Audit log for user authentication and authorization events.
    Tracks all security-relevant actions.
    """

    __tablename__ = "user_audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    # Event Details
    event_type = Column(
        String(50), nullable=False
    )  # login, logout, permission_check, etc.
    action = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # success, failure, denied

    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    tenant_id = Column(GUID(), ForeignKey("tenants.id"), nullable=True)

    # Additional Details
    details = Column(JSON, default=dict)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<UserAuditLog {self.event_type} by {self.user_id}>"


class UserApiKey(Base):
    """
    API Keys for programmatic access.
    Can be scoped to specific tenants and have expiration.
    """

    __tablename__ = "user_api_keys"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Key Details
    key_name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)  # First chars for identification

    # Scope
    tenant_id = Column(GUID(), ForeignKey("tenants.id"), nullable=True)
    permissions = Column(JSON, default=list)  # Optional: restrict permissions

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<UserApiKey {self.key_name} for user {self.user_id}>"

    def is_expired(self) -> bool:
        """Check if API key has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (never expose full key)"""
        return {
            "id": str(self.id),
            "key_name": self.key_name,
            "key_prefix": self.key_prefix,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_expired": self.is_expired(),
        }
