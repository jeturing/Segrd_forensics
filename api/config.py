"""
Configuración de variables de entorno y settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración del MCP"""
    
    # Aplicación
    APP_NAME: str = "mcp-kali-forensics"
    APP_VERSION: str = "4.7.0"
    DEBUG: bool = False
    DEMO_DATA_ENABLED: bool = False  # Deshabilitar datos demo por defecto; usar env DEMO_DATA_ENABLED=true para habilitar fallback
    
    # API
    API_KEY: str
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # JWT Authentication (v4.6)
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"  # CAMBIAR EN PRODUCCIÓN
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # RBAC (Role-Based Access Control) v4.6
    RBAC_ENABLED: bool = True  # Activado por defecto en v4.6
    RBAC_DEFAULT_ROLE: str = "viewer"  # Rol más restrictivo por defecto

    # HexStrike AI (Red Team v4.6)
    HEXSTRIKE_ENABLED: bool = False
    HEXSTRIKE_BASE_URL: str = "http://hexstrike-ai:8888"
    HEXSTRIKE_API_KEY: Optional[str] = None
    HEXSTRIKE_TIMEOUT: int = 60
    
    # Jeturing CORE
    JETURING_CORE_ENABLED: bool = True
    JETURING_CORE_URL: str = "https://core.jeturing.local"
    JETURING_CORE_API_KEY: str
    
    # Microsoft 365
    M365_TENANT_ID: Optional[str] = None
    M365_CLIENT_ID: Optional[str] = None
    M365_CLIENT_SECRET: Optional[str] = None
    
    # Tailscale
    TAILSCALE_ENABLED: bool = False
    TAILSCALE_AUTH_KEY: Optional[str] = None
    
    # HIBP API
    HIBP_API_KEY: Optional[str] = None
    HIBP_ENABLED: bool = False
    
    # Dehashed API
    DEHASHED_API_KEY: Optional[str] = None
    DEHASHED_ENABLED: bool = False
    
    # =============================================================================
    # Threat Intelligence & OSINT APIs
    # =============================================================================
    
    # Shodan
    SHODAN_API_KEY: Optional[str] = None
    
    # Censys
    CENSYS_API_ID: Optional[str] = None
    CENSYS_API_SECRET: Optional[str] = None
    
    # FullContact
    FULLCONTACT_API_KEY: Optional[str] = None
    
    # Hunter.io
    HUNTER_API_KEY: Optional[str] = None
    
    # SecurityTrails
    SECURITYTRAILS_API_KEY: Optional[str] = None
    
    # FraudGuard
    FRAUDGUARD_USER: Optional[str] = None
    FRAUDGUARD_PASS: Optional[str] = None
    
    # Honeypot Checker
    HONEYPOT_API_KEY: Optional[str] = None
    
    # Malware Patrol
    MALWAREPATROL_API_KEY: Optional[str] = None
    
    # Intelligence X
    INTELX_API_KEY: Optional[str] = None
    
    # IBM X-Force Exchange
    XFORCE_API_KEY: Optional[str] = None
    XFORCE_API_SECRET: Optional[str] = None
    
    # VirusTotal
    VT_API_KEY: Optional[str] = None
    VT_API_KEY_BACKUP: Optional[str] = None
    
    # Hybrid Analysis
    HYBRID_ANALYSIS_KEY: Optional[str] = None
    HYBRID_ANALYSIS_SECRET: Optional[str] = None
    
    # AbuseIPDB
    ABUSEIPDB_API_KEY: Optional[str] = None
    
    # OTX AlienVault
    OTX_API_KEY: Optional[str] = None
    
    # URLScan.io
    URLSCAN_API_KEY: Optional[str] = None
    
    # Google Services
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # reCAPTCHA
    RECAPTCHA_SITE_KEY: Optional[str] = None
    RECAPTCHA_SECRET_KEY: Optional[str] = None
    
    # Unsplash
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    UNSPLASH_SECRET_KEY: Optional[str] = None
    
    # ============================================================================
    # MINIO OBJECT STORAGE (Multi-tenant Evidence)
    # ============================================================================
    MINIO_ENABLED: bool = True
    MINIO_ENDPOINT: str = "10.10.10.5:9000"
    MINIO_ACCESS_KEY: str = "Jeturing"
    MINIO_SECRET_KEY: str = "Prd-11lkm41231jn123j1n2l3"
    MINIO_BUCKET: str = "forensics-evidence"
    MINIO_SECURE: bool = False
    MINIO_CONSOLE_URL: str = "http://10.10.10.5:9001"
    
    # Paths (Native Kali/WSL - sin Docker)
    # Usa ./tools dentro del proyecto (no /opt) para evitar problemas de permisos
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    TOOLS_DIR: Path = PROJECT_ROOT / "tools"
    EVIDENCE_DIR: Path = PROJECT_ROOT / "evidence"  # ./evidence en el proyecto
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    # Audit logging configuration
    AUDIT_LOG_TO_DB: bool = False  # If False, audit events are written to rotating files only
    AUDIT_LOG_FILE_NAME: str = "audit.log"
    AUDIT_LOG_ROTATION_WHEN: str = "midnight"
    AUDIT_LOG_BACKUP_COUNT: int = 14
    
    # Database (PostgreSQL por defecto, SQLite legacy removido)
    DATABASE_URL: str = "postgresql://forensics:change-me-please@postgres:5432/forensics"
    # DB mode: 'postgresql' (default) or 'postgrest' (use PostgREST endpoint)
    DB_MODE: str = "postgresql"
    POSTGREST_URL: Optional[str] = None

    # PostgreSQL (base de datos principal)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "forensics"
    POSTGRES_USER: str = "forensics"
    POSTGRES_PASSWORD: str = "change-me-please"
    
    # ============================================================================
    # HERRAMIENTAS INSTALADAS - CATEGORÍA BÁSICO
    # ============================================================================
    SPARROW_PATH: Optional[Path] = None
    HAWK_PATH: Optional[Path] = None
    O365_EXTRACTOR_PATH: Optional[Path] = None
    
    # ============================================================================
    # HERRAMIENTAS INSTALADAS - CATEGORÍA RECONOCIMIENTO
    # ============================================================================
    AZUREHOUND_PATH: Optional[Path] = None
    ROADTOOLS_PATH: Optional[Path] = None
    AADINTERNALS_PATH: Optional[Path] = None
    
    # ============================================================================
    # HERRAMIENTAS INSTALADAS - CATEGORÍA AUDITORÍA
    # ============================================================================
    MONKEY365_PATH: Optional[Path] = None
    MAESTER_PATH: Optional[Path] = None
    PNP_POWERSHELL_PATH: Optional[Path] = None
    
    # ============================================================================
    # HERRAMIENTAS INSTALADAS - CATEGORÍA FORENSE
    # ============================================================================
    LOKI_PATH: Optional[Path] = None
    YARA_RULES_PATH: Optional[Path] = None
    CLOUD_KATANA_PATH: Optional[Path] = None
    
    # ============================================================================
    # LLM STUDIO INTEGRATION (v4.3)
    # ============================================================================
    LLM_PROVIDER: str = "llm_studio"  # llm_studio, phi4_local, offline
    LLM_STUDIO_URL: str = "http://100.101.115.5:2714/v1/completions"
    LLM_STUDIO_API_KEY: Optional[str] = None
    LLM_STUDIO_MODEL: str = "phi-4"
    LLM_STUDIO_TIMEOUT: int = 40
    PHI4_LOCAL_ENABLED: bool = True
    OFFLINE_LLM_ENABLED: bool = True
    
    # ============================================================================
    # STRIPE BILLING (v4.6)
    # ============================================================================
    STRIPE_ENABLED: bool = False
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_ENVIRONMENT: str = "test"  # test, live
    
    # ============================================================================
    # SMTP EMAIL (v4.6.1)
    # ============================================================================
    SMTP_HOST: str = "mail5010.site4now.net"
    SMTP_PORT: int = 465
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SSL: bool = True
    SMTP_FROM_EMAIL: str = "no-reply@sajet.us"
    SMTP_CONTACT_TO: str = "sales@jeturing.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variables VITE_* del frontend

settings = Settings()

# Crear directorios si no existen (permisos de usuario local)
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Accessor con caché para evitar re-instanciar Settings
@lru_cache()
def get_settings() -> Settings:
    return settings

# Auto-detectar tools en la carpeta ./tools
def _discover_tools():
    """Detecta automáticamente los tools instalados en ./tools"""
    tools_map = {}
    
    if settings.TOOLS_DIR.exists():
        for tool_dir in settings.TOOLS_DIR.iterdir():
            if tool_dir.is_dir():
                tool_name = tool_dir.name
                tools_map[tool_name] = tool_dir
                
                # ============================================================================
                # CATEGORÍA: BÁSICO
                # ============================================================================
                if tool_name.lower() == "sparrow":
                    settings.SPARROW_PATH = tool_dir / "Sparrow.ps1"
                elif tool_name.lower() == "hawk":
                    settings.HAWK_PATH = tool_dir / "hawk.ps1"
                elif tool_name.lower() == "o365-extractor":
                    settings.O365_EXTRACTOR_PATH = tool_dir
                
                # ============================================================================
                # CATEGORÍA: RECONOCIMIENTO
                # ============================================================================
                elif tool_name.lower() == "azurehound":
                    settings.AZUREHOUND_PATH = tool_dir
                elif tool_name.lower() == "roadtools":
                    settings.ROADTOOLS_PATH = tool_dir
                elif tool_name.lower() == "aadinternals":
                    settings.AADINTERNALS_PATH = tool_dir
                
                # ============================================================================
                # CATEGORÍA: AUDITORÍA
                # ============================================================================
                elif tool_name.lower() == "monkey365":
                    settings.MONKEY365_PATH = tool_dir
                elif tool_name.lower() == "maester":
                    settings.MAESTER_PATH = tool_dir
                elif tool_name.lower() == "pnp-powershell":
                    settings.PNP_POWERSHELL_PATH = tool_dir
                
                # ============================================================================
                # CATEGORÍA: FORENSE
                # ============================================================================
                elif tool_name.lower() == "loki":
                    settings.LOKI_PATH = tool_dir / "loki.py"
                elif tool_name.lower() == "yara-rules":
                    settings.YARA_RULES_PATH = tool_dir
                elif tool_name.lower() == "cloud_katana":
                    settings.CLOUD_KATANA_PATH = tool_dir
    
    return tools_map


def get_database_selection():
    """Devuelve la URL o endpoint a usar según configuración.

    - Si `DB_MODE` == 'postgrest' y `POSTGREST_URL` está configurada, devuelve esa URL.
    - En caso contrario devuelve `DATABASE_URL` (SQLite por defecto).
    """
    if settings.DB_MODE and settings.DB_MODE.lower() == 'postgrest' and settings.POSTGREST_URL:
        return settings.POSTGREST_URL
    return settings.DATABASE_URL

# Ejecutar auto-detección (sin asignar - solo se usa localmente)
# settings.DISCOVERED_TOOLS = _discover_tools()
