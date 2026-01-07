"""
Database initialization script for BRAC authentication system.
Creates initial global tenant "jeturing" and admin user "Pluton_JE".
"""

import secrets
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from api.database import SessionLocal, init_db
from api.models.user import User
from api.models.tenant import Tenant
from api.services.auth import AuthService
from core.rbac_config import Permission

logger = logging.getLogger(__name__)


def generate_deployment_key(length: int = 32) -> str:
    """Generate a secure random deployment key"""
    return secrets.token_urlsafe(length)


def init_default_roles(db: Session) -> dict:
    """
    Initialize default BRAC roles with permissions.
    Returns dict of role names to Role objects.
    """
    auth_service = AuthService(db)

    roles = {}

    # Viewer Role - Read-only access
    roles["viewer"] = auth_service.get_or_create_role(
        name="viewer",
        display_name="Viewer",
        description="Read-only access to cases, analyses, and reports",
        permissions=[Permission.READ.value],
        is_system=True,
    )

    # Analyst Role - Standard forensic analyst
    roles["analyst"] = auth_service.get_or_create_role(
        name="analyst",
        display_name="Analyst",
        description="Forensic analyst with execution permissions",
        permissions=[
            Permission.READ.value,
            Permission.WRITE.value,
            Permission.RUN_TOOLS.value,
            Permission.VIEW_LOGS.value,
        ],
        is_system=True,
    )

    # Senior Analyst Role - Advanced analyst with agent management
    roles["senior_analyst"] = auth_service.get_or_create_role(
        name="senior_analyst",
        display_name="Senior Analyst",
        description="Senior analyst with full forensic capabilities",
        permissions=[
            Permission.READ.value,
            Permission.WRITE.value,
            Permission.DELETE.value,
            Permission.RUN_TOOLS.value,
            Permission.MANAGE_AGENTS.value,
            Permission.VIEW_LOGS.value,
            Permission.EXPORT.value,
            Permission.PENTEST.value,
        ],
        is_system=True,
    )

    # Admin Role - Full system access
    roles["admin"] = auth_service.get_or_create_role(
        name="admin",
        display_name="Administrator",
        description="Full system administrator with all permissions",
        permissions=[
            Permission.READ.value,
            Permission.WRITE.value,
            Permission.DELETE.value,
            Permission.RUN_TOOLS.value,
            Permission.MANAGE_AGENTS.value,
            Permission.ADMIN.value,
            Permission.VIEW_LOGS.value,
            Permission.EXPORT.value,
            Permission.PENTEST.value,
        ],
        is_system=True,
    )

    logger.info("✅ Default roles initialized")
    return roles


def init_global_tenant(db: Session) -> Tenant:
    """
    Initialize the global "jeturing" tenant.
    This is the master tenant for system administration.
    """
    # Check if jeturing tenant already exists
    tenant = db.query(Tenant).filter(Tenant.name == "jeturing").first()

    if tenant:
        logger.info("✅ Global tenant 'jeturing' already exists")
        return tenant

    # Create jeturing tenant
    tenant = Tenant(
        tenant_id="jeturing",
        name="jeturing",
        subdomain="jeturing",
        schema_name="tenant_jeturing",
        config={
            "is_global": True,
            "description": "Global master tenant for system administration",
        },
        llm_model="full",
        enable_autonomous_agents=True,
        is_active=True,
        created_by="system",
        contact_email="admin@jeturing.local",
        max_cases=10000,
        max_storage_gb=1000,
        max_users=100,
        plan="enterprise",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    logger.info("✅ Global tenant 'jeturing' created")
    return tenant


def init_admin_user(db: Session, tenant: Tenant, roles: dict) -> tuple:
    """
    Initialize the Pluton_JE admin user with a dynamic deployment key.
    Returns (User, deployment_key) tuple.
    """
    auth_service = AuthService(db)

    # Check if Pluton_JE user already exists
    existing_user = db.query(User).filter(User.username == "Pluton_JE").first()

    if existing_user:
        logger.info("✅ Admin user 'Pluton_JE' already exists")
        return existing_user, None

    # Generate secure deployment key
    deployment_key = generate_deployment_key()

    # Create admin user
    user, error = auth_service.create_user(
        username="Pluton_JE",
        email="pluton@jeturing.local",
        password=deployment_key,
        full_name="Pluton JE - Global Administrator",
        is_global_admin=True,
        created_by="system",
    )

    if error:
        raise Exception(f"Failed to create admin user: {error}")

    # Assign admin role
    auth_service.assign_role(user, roles["admin"])

    # Associate user with jeturing tenant
    user.tenants.append(tenant)
    db.commit()

    logger.info("✅ Admin user 'Pluton_JE' created with deployment key")
    return user, deployment_key


def init_brac_system() -> dict:
    """
    Initialize the complete BRAC authentication system.

    Returns:
        dict with initialization results including deployment key
    """
    logger.info("🔧 Initializing BRAC authentication system...")

    # Initialize database tables
    init_db()

    # Create database session
    db = SessionLocal()

    try:
        # 1. Initialize default roles
        roles = init_default_roles(db)

        # 2. Create global jeturing tenant
        tenant = init_global_tenant(db)

        # 3. Create Pluton_JE admin user
        user, deployment_key = init_admin_user(db, tenant, roles)

        result = {
            "success": True,
            "tenant": {
                "id": str(tenant.id),
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
            },
            "admin_user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
            },
            "deployment_key": deployment_key,
            "roles_created": len(roles),
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info("✅ BRAC system initialization complete")
        return result

    except Exception as e:
        logger.error(f"❌ BRAC initialization failed: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    result = init_brac_system()

    print("\n" + "=" * 70)
    print("🔐 BRAC AUTHENTICATION SYSTEM INITIALIZED")
    print("=" * 70)
    print(f"\n📋 Global Tenant: {result['tenant']['name']}")
    print(f"   Tenant ID: {result['tenant']['tenant_id']}")
    print(f"\n👤 Admin User: {result['admin_user']['username']}")
    print(f"   Email: {result['admin_user']['email']}")

    if result["deployment_key"]:
        print("\n🔑 DEPLOYMENT KEY (save this - it won't be shown again):")
        print(f"   {result['deployment_key']}")
        print("\n⚠️  Use this key for first login with username: Pluton_JE")
    else:
        print("\n✅ Admin user already exists - no new deployment key generated")

    print(f"\n📊 Roles Created: {result['roles_created']}")
    print("   - viewer (read-only)")
    print("   - analyst (standard forensic)")
    print("   - senior_analyst (advanced)")
    print("   - admin (full access)")

    print(f"\n⏰ Initialized at: {result['timestamp']}")
    print("=" * 70 + "\n")
