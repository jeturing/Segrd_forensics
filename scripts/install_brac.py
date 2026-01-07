#!/usr/bin/env python3
"""
Interactive installer for MCP Kali Forensics with BRAC authentication.
This script initializes the database, creates the global tenant 'jeturing',
and creates the admin user 'Pluton_JE' with a dynamic deployment key.
"""
import sys
import os
import logging
from pathlib import Path
from importlib.util import find_spec

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print installation banner"""
    print("\n" + "=" * 70)
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  __  __  ____ ____    _  __    _ _   _____                    ║")
    print("║ |  \\/  |/ ___|  _ \\  | |/ /_ _| (_) |  ___|__  _ __ ___      ║")
    print("║ | |\\/| | |   | |_) | | ' / _` | | | | |_ / _ \\| '__/ _ \\     ║")
    print("║ | |  | | |___|  __/  | . \\ (_| | | | |  _| (_) | | |  __/    ║")
    print("║ |_|  |_|\\____|_|     |_|\\_\\__,_|_|_| |_|  \\___/|_|  \\___|    ║")
    print("║                                                                ║")
    print("║         BRAC Authentication System Installer v4.5              ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("=" * 70 + "\n")


def check_database_type():
    """
    Auto-detect database type (SQLite or PostgreSQL).
    Returns: 'sqlite' or 'postgresql'
    """
    from api.config import settings

    db_url = settings.DATABASE_URL

    if db_url.startswith("sqlite"):
        return "sqlite"
    elif db_url.startswith("postgresql"):
        return "postgresql"
    else:
        logger.warning("Unknown database type, defaulting to SQLite")
        return "sqlite"


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("📋 Checking prerequisites...\n")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✅ Python version: {}.{}".format(*sys.version_info[:2]))

    # Check required directories
    logs_dir = Path(project_root) / "logs"
    evidence_dir = Path(project_root) / "evidence"

    logs_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print("✅ Required directories created")

    # Check database type
    db_type = check_database_type()
    print(f"✅ Database type: {db_type}")

    # Check required packages
    try:
        # Check if packages are available
        packages_ok = all(
            [
                find_spec("fastapi"),
                find_spec("sqlalchemy"),
                find_spec("jwt"),
                find_spec("bcrypt"),
            ]
        )
        if not packages_ok:
            raise ImportError("Some required packages are missing")

        print("✅ Required packages installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("\n💡 Run: pip install -r requirements.txt")
        return False

    print()
    return True


def initialize_database():
    """Initialize the database schema"""
    print("🔧 Initializing database schema...")

    try:
        from api.database import init_db

        init_db()
        print("✅ Database schema initialized\n")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"❌ Database initialization failed: {e}\n")
        return False


def initialize_brac():
    """Initialize BRAC authentication system"""
    print("🔐 Initializing BRAC authentication system...")
    print("   - Creating default roles")
    print("   - Creating global tenant 'jeturing'")
    print("   - Creating admin user 'Pluton_JE'\n")

    try:
        from api.services.init_brac import init_brac_system

        result = init_brac_system()

        if not result["success"]:
            print("❌ BRAC initialization failed\n")
            return False, None

        print("=" * 70)
        print("🎉 BRAC AUTHENTICATION SYSTEM INITIALIZED SUCCESSFULLY!")
        print("=" * 70)

        print(f"\n📋 Global Tenant: {result['tenant']['name']}")
        print(f"   Tenant ID: {result['tenant']['tenant_id']}")

        print(f"\n👤 Admin User: {result['admin_user']['username']}")
        print(f"   Email: {result['admin_user']['email']}")

        deployment_key = result.get("deployment_key")
        if deployment_key:
            print("\n🔑 DEPLOYMENT KEY (SAVE THIS - WON'T BE SHOWN AGAIN):")
            print(f"\n   {deployment_key}\n")
            print("⚠️  Use this key for first login:")
            print(f"   Username: {result['admin_user']['username']}")
            print(f"   Password: {deployment_key}")
            print("\n💡 You can change this password after first login")
        else:
            print("\n✅ Admin user already exists - no new deployment key generated")

        print(f"\n📊 Roles Created: {result['roles_created']}")
        print("   - viewer (read-only)")
        print("   - analyst (standard forensic)")
        print("   - senior_analyst (advanced)")
        print("   - admin (full access)")

        print(f"\n⏰ Initialized at: {result['timestamp']}")
        print("=" * 70 + "\n")

        return True, deployment_key

    except Exception as e:
        logger.error(f"Failed to initialize BRAC: {e}", exc_info=True)
        print(f"❌ BRAC initialization failed: {e}\n")
        return False, None


def save_deployment_key(key: str):
    """Save deployment key to a secure file"""
    if not key:
        return

    key_file = Path(project_root) / ".deployment_key"

    try:
        with open(key_file, "w") as f:
            f.write(key)

        # Set restrictive permissions (Unix only)
        if os.name != "nt":  # Not Windows
            os.chmod(key_file, 0o600)

        print(f"💾 Deployment key saved to: {key_file}")
        print("   (Secure file with restricted permissions)\n")

    except Exception as e:
        logger.error(f"Failed to save deployment key: {e}")
        print(f"⚠️  Could not save deployment key to file: {e}\n")


def update_env_file():
    """Update or create .env file with JWT secret"""
    env_file = Path(project_root) / ".env"
    env_example = Path(project_root) / ".env.example"

    # If .env doesn't exist, copy from .env.example
    if not env_file.exists() and env_example.exists():
        import shutil

        shutil.copy(env_example, env_file)
        print("✅ Created .env file from .env.example")

    # Generate JWT secret if not present
    try:
        import secrets

        if env_file.exists():
            with open(env_file, "r") as f:
                content = f.read()

            if "JWT_SECRET_KEY" not in content or "your-jwt-secret-key" in content:
                jwt_secret = secrets.token_urlsafe(32)

                # Replace or add JWT_SECRET_KEY
                if "JWT_SECRET_KEY" in content:
                    lines = content.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("JWT_SECRET_KEY"):
                            new_lines.append(f"JWT_SECRET_KEY={jwt_secret}")
                        else:
                            new_lines.append(line)
                    content = "\n".join(new_lines)
                else:
                    content += f"\nJWT_SECRET_KEY={jwt_secret}\n"

                with open(env_file, "w") as f:
                    f.write(content)

                print("✅ Generated and saved JWT secret key\n")

    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        print(f"⚠️  Could not update .env file: {e}\n")


def main():
    """Main installation flow"""
    print_banner()

    # Welcome message
    print("Welcome to the MCP Kali Forensics installer!")
    print("This will set up BRAC authentication with multi-tenant support.\n")

    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please fix the issues and try again.\n")
        return 1

    # Ask for confirmation
    print("📌 This installer will:")
    print("   1. Initialize the database schema")
    print("   2. Create default BRAC roles")
    print("   3. Create global tenant 'jeturing'")
    print("   4. Create admin user 'Pluton_JE' with a random deployment key")
    print("   5. Configure environment variables\n")

    response = input("Continue with installation? (y/n): ").strip().lower()
    if response != "y":
        print("\n❌ Installation cancelled.\n")
        return 0

    print()

    # Initialize database
    if not initialize_database():
        return 1

    # Update .env file
    update_env_file()

    # Initialize BRAC
    success, deployment_key = initialize_brac()
    if not success:
        return 1

    # Save deployment key
    if deployment_key:
        save_deployment_key(deployment_key)

    # Final instructions
    print("=" * 70)
    print("🎉 INSTALLATION COMPLETE!")
    print("=" * 70)
    print("\n📚 Next steps:")
    print("   1. Start the server: uvicorn api.main:app --reload")
    print("   2. Login at: http://localhost:8000/api/auth/login")
    print("   3. Use username 'Pluton_JE' with the deployment key above")
    print("   4. Change your password after first login")
    print("\n📖 Documentation: /docs")
    print("🔍 API Explorer: http://localhost:8000/docs")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Installation cancelled by user.\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Installation failed: {e}", exc_info=True)
        print(f"\n❌ Installation failed: {e}\n")
        sys.exit(1)
