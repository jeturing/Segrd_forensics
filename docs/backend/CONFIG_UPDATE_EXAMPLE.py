# Actualización de api/config.py para soportar tools locales

# Este archivo muestra qué cambios hacer en api/config.py

# ============================================================================
# AGREGAR ESTO AL INICIO DE api/config.py
# ============================================================================

from pathlib import Path
import os

# Raíz del proyecto (sube 2 niveles desde api/)
PROJECT_ROOT = Path(__file__).parent.parent

# Carpeta de tools (dentro del proyecto)
TOOLS_DIR = PROJECT_ROOT / "tools"

# Cargar configuración desde tools.env si existe
TOOLS_ENV_FILE = PROJECT_ROOT / "config" / "tools.env"

def load_tools_env():
    """Carga variables desde config/tools.env"""
    tools_config = {}
    if TOOLS_ENV_FILE.exists():
        with open(TOOLS_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                # Saltar comentarios y líneas vacías
                if line and not line.startswith("#"):
                    # Expandir variables (ej: ${PROJECT_ROOT})
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Reemplazar ${PROJECT_ROOT}
                        value = value.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
                        tools_config[key] = value
    return tools_config

TOOLS_CONFIG = load_tools_env()

# ============================================================================
# REEMPLAZAR RUTAS DE TOOLS (buscar y cambiar)
# ============================================================================

# ANTES (en /opt/forensics-tools - sistema):
# SPARROW_PATH = "/opt/forensics-tools/Sparrow/Sparrow.ps1"

# DESPUES (en ./tools - proyecto):
SPARROW_PATH = TOOLS_DIR / "Sparrow" / "Sparrow.ps1"
HAWK_PATH = TOOLS_DIR / "hawk" / "hawk.ps1"
O365_EXTRACTOR_PATH = TOOLS_DIR / "o365-extractor"
LOKI_PATH = TOOLS_DIR / "Loki"
YARA_RULES_PATH = TOOLS_DIR / "yara-rules"
AZUREHOUND_PATH = TOOLS_DIR / "azurehound" / "azurehound"
ROADTOOLS_PATH = TOOLS_DIR / "ROADtools"
MONKEY365_PATH = TOOLS_DIR / "Monkey365"
CLOUD_KATANA_PATH = TOOLS_DIR / "Cloud_Katana"

# O cargados desde tools.env:
SPARROW_PATH = TOOLS_CONFIG.get("SPARROW_PATH", SPARROW_PATH)
HAWK_PATH = TOOLS_CONFIG.get("HAWK_PATH", HAWK_PATH)
O365_EXTRACTOR_PATH = TOOLS_CONFIG.get("O365_EXTRACTOR_PATH", O365_EXTRACTOR_PATH)

# ============================================================================
# ACTUALIZAR DIRECTORIOS DE DATOS (buscar y cambiar)
# ============================================================================

# ANTES:
# EVIDENCE_DIR = "/var/evidence"
# LOG_DIR = "/var/log/mcp-forensics"

# DESPUES:
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
LOG_DIR = PROJECT_ROOT / "logs"

# Crear directorios si no existen
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# ACTUALIZAR TIMEOUTS (buscar y cambiar)
# ============================================================================

TOOL_TIMEOUT = int(TOOLS_CONFIG.get("TOOL_TIMEOUT", 3600))  # 1 hora
ANALYSIS_TIMEOUT = int(TOOLS_CONFIG.get("ANALYSIS_TIMEOUT", 7200))  # 2 horas
DECISION_TIMEOUT = int(TOOLS_CONFIG.get("DECISION_TIMEOUT", 300))  # 5 minutos

# ============================================================================
# DEBUG FLAGS
# ============================================================================

DEBUG = TOOLS_CONFIG.get("DEBUG", "false").lower() == "true"
VERBOSE = TOOLS_CONFIG.get("VERBOSE", "false").lower() == "true"
LOG_LEVEL = TOOLS_CONFIG.get("LOG_LEVEL", "INFO")

# ============================================================================
# DATABASE (cambiar si era /opt)
# ============================================================================

# ANTES:
# DATABASE_URL = "sqlite:////var/lib/mcp-forensics/forensics.db"

# DESPUES:
DB_PATH = PROJECT_ROOT / "forensics.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ============================================================================
# FUNCIÓN HELPER PARA VERIFICAR TOOLS
# ============================================================================

def verify_tools_installed():
    """Verifica que todos los tools estén instalados"""
    import logging
    logger = logging.getLogger(__name__)
    
    required_tools = {
        "Sparrow": SPARROW_PATH,
        "Hawk": HAWK_PATH,
        "O365 Extractor": O365_EXTRACTOR_PATH,
        "Loki": LOKI_PATH,
    }
    
    missing_tools = []
    for tool_name, tool_path in required_tools.items():
        path = Path(tool_path) if isinstance(tool_path, str) else tool_path
        if not path.exists():
            missing_tools.append(f"{tool_name} ({tool_path})")
            logger.warning(f"⚠️ {tool_name} not found at {tool_path}")
        else:
            logger.info(f"✓ {tool_name} found at {tool_path}")
    
    if missing_tools:
        logger.error(f"❌ Missing tools: {', '.join(missing_tools)}")
        logger.error(f"Run: cd {PROJECT_ROOT} && ./install.sh")
        return False
    
    logger.info("✓ All required tools installed")
    return True

# Verificar en startup
if __name__ != "__main__":
    # Solo verificar si no es ejecución directa
    # verify_tools_installed()
    pass

# ============================================================================
# LOGGING (actualizar rutas)
# ============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "level": LOG_LEVEL,
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "mcp-forensics.log"),
            "formatter": "default",
        },
    },
    "loggers": {
        "api": {
            "handlers": ["default", "file"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}

# ============================================================================
# EJEMPLOS DE USO EN RUTAS
# ============================================================================

# En api/routes/m365.py o services/m365.py:

from api.config import (
    SPARROW_PATH,
    TOOLS_DIR,
    EVIDENCE_DIR,
    TOOL_TIMEOUT,
    verify_tools_installed,
)

# Usar paths así:
async def execute_sparrow_analysis(case_id: str):
    # Verificar que existe
    if not SPARROW_PATH.exists():
        raise FileNotFoundError(f"Sparrow not found at {SPARROW_PATH}")
    
    # Crear directorio de evidencia
    case_evidence_dir = EVIDENCE_DIR / case_id / "sparrow"
    case_evidence_dir.mkdir(parents=True, exist_ok=True)
    
    # Ejecutar herramienta
    cmd = [
        "pwsh",
        "-ExecutionPolicy", "Bypass",
        "-File", str(SPARROW_PATH),
        "-OutputPath", str(case_evidence_dir),
        "-TenantId", tenant_id,
    ]
    
    # ... rest of execution code

# ============================================================================
# VERIFICAR INSTALACIÓN EN STARTUP
# ============================================================================

# En api/main.py, agregar en lifespan event:

from contextlib import asynccontextmanager
from api.config import verify_tools_installed

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔍 Verificando herramientas instaladas...")
    if not verify_tools_installed():
        print("❌ Algunas herramientas no están instaladas")
        print(f"Ejecuta: cd {PROJECT_ROOT} && ./install.sh")
        sys.exit(1)
    
    print("✓ Todas las herramientas están disponibles")
    
    yield
    
    # Shutdown
    print("Apagando...")

app = FastAPI(lifespan=lifespan)

# ============================================================================
# RESUMEN DE CAMBIOS
# ============================================================================

# 1. Agregar imports al inicio
# 2. Definir PROJECT_ROOT
# 3. Cambiar todas las rutas de /opt/forensics-tools a ./tools
# 4. Cambiar directorios de datos al proyecto
# 5. Agregar verify_tools_installed()
# 6. Usar en lifespan event para validar en startup

print(f"""
╔════════════════════════════════════════════════════════════╗
║ Configuración Local de Tools                              ║
╠════════════════════════════════════════════════════════════╣
║ Proyecto:         {PROJECT_ROOT}
║ Tools Dir:        {TOOLS_DIR}
║ Evidence Dir:     {EVIDENCE_DIR}
║ Logs Dir:         {LOG_DIR}
║ Database:         {DATABASE_URL}
║ Tool Timeout:     {TOOL_TIMEOUT}s
║ Debug Mode:       {DEBUG}
╚════════════════════════════════════════════════════════════╝
""")
