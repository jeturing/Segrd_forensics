"""
Tenant Model for Multi-Tenancy Support
"""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text, Integer
from sqlalchemy.orm import relationship
import uuid

from api.database import Base, GUID


class Tenant(Base):
    """
    Tenant model for multi-tenancy isolation.
    Format: Jeturing_{GUID}
    """

    __tablename__ = "tenants"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(63), unique=True, nullable=False, index=True)

    # PostgreSQL schema for isolation
    schema_name = Column(String(63), unique=True, nullable=False)

    # Configuration
    config = Column(JSON, default=dict)

    # LLM Configuration
    llm_model = Column(String(50), default="basic")  # basic, medium, full
    llm_config = Column(JSON, default=dict)

    # Autonomous Agents
    enable_autonomous_agents = Column(Boolean, default=True)
    agent_config = Column(JSON, default=dict)

    # Status
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    # Contact
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Limits
    max_cases = Column(Integer, default=1000)
    max_storage_gb = Column(Integer, default=100)
    max_users = Column(Integer, default=50)

    # Billing (optional)
    plan = Column(String(50), default="enterprise")
    billing_email = Column(String(255), nullable=True)

    # Relationships
    users = relationship("User", secondary="user_tenants", back_populates="tenants")

    def __repr__(self):
        return f"<Tenant {self.tenant_id} ({self.name})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "name": self.name,
            "subdomain": self.subdomain,
            "schema_name": self.schema_name,
            "config": self.config,
            "llm_model": self.llm_model,
            "llm_config": self.llm_config,
            "enable_autonomous_agents": self.enable_autonomous_agents,
            "agent_config": self.agent_config,
            "is_active": self.is_active,
            "is_suspended": self.is_suspended,
            "suspension_reason": self.suspension_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "max_cases": self.max_cases,
            "max_storage_gb": self.max_storage_gb,
            "max_users": self.max_users,
            "plan": self.plan,
            "billing_email": self.billing_email,
        }

    @staticmethod
    def generate_tenant_id() -> str:
        """Generate tenant ID in format: Jeturing_{GUID}"""
        return f"Jeturing_{uuid.uuid4()}"

    @staticmethod
    def generate_schema_name(subdomain: str) -> str:
        """Generate PostgreSQL schema name from subdomain"""
        # Ensure schema name is valid (alphanumeric + underscore)
        schema = subdomain.lower().replace("-", "_")
        return f"tenant_{schema}"
