#!/bin/bash
# Instalador de todas las herramientas M365 avanzadas
# Para: MCP Kali Forensics Platform
# Usa entorno virtual para evitar conflictos con paquetes del sistema

set -e

TOOLS_DIR="/opt/forensics-tools"
VENV_DIR="/opt/forensics-tools/venv"
echo "🚀 Instalando herramientas M365 avanzadas en $TOOLS_DIR"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar permisos
if [ "$EUID" -ne 0 ]; then 
    error "Ejecutar como root o con sudo"
    exit 1
fi

# Crear directorios
mkdir -p "$TOOLS_DIR"
cd "$TOOLS_DIR"

# Crear entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    info "📦 Creando entorno virtual Python..."
    python3 -m venv "$VENV_DIR"
    info "✅ Entorno virtual creado en $VENV_DIR"
else
    warn "Entorno virtual ya existe"
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"
info "🐍 Entorno virtual activado"

# ==================== RECONNAISSANCE TOOLS ====================

info "📍 Instalando AzureHound..."
if [ ! -d "azurehound" ]; then
    git clone https://github.com/BloodHoundAD/AzureHound.git azurehound
    cd azurehound
    go build -o azurehound
    chmod +x azurehound
    cd ..
    info "✅ AzureHound instalado"
else
    warn "AzureHound ya existe"
fi

info "🗺️ Instalando ROADtools..."
pip install roadtools roadrecon roadlib
info "✅ ROADtools instalado"

info "🔓 Instalando AADInternals (PowerShell)..."
pwsh -NoProfile -Command "Install-Module -Name AADInternals -Force -Scope AllUsers" || true
info "✅ AADInternals instalado"

# ==================== AUDIT & COMPLIANCE ====================

info "🐵 Instalando Monkey365..."
if [ ! -d "monkey365" ]; then
    git clone https://github.com/silverhack/monkey365.git
    cd monkey365
    pwsh -NoProfile -Command "Install-Module -Name monkey365 -Force -Scope AllUsers" || true
    cd ..
    info "✅ Monkey365 instalado"
else
    warn "Monkey365 ya existe"
fi

info "🦅 Instalando CrowdStrike CRT..."
if [ ! -d "crt" ]; then
    git clone https://github.com/CrowdStrike/CRT.git crt
    info "✅ CrowdStrike CRT instalado"
else
    warn "CRT ya existe"
fi

info "🎯 Instalando Maester..."
if [ ! -d "maester" ]; then
    git clone https://github.com/maester365/maester.git
    cd maester
    pwsh -NoProfile -Command "Install-Module -Name Maester -Force -Scope AllUsers" || true
    cd ..
    info "✅ Maester instalado"
else
    warn "Maester ya existe"
fi

# ==================== FORENSIC TOOLS ====================

info "📦 Instalando M365 Extractor Suite..."
if [ ! -d "Microsoft-Extractor-Suite" ]; then
    git clone https://github.com/invictus-ir/Microsoft-Extractor-Suite.git
    cd Microsoft-Extractor-Suite
    pip install -r requirements.txt 2>/dev/null || pip install requests azure-identity msgraph-sdk
    cd ..
    info "✅ M365 Extractor Suite instalado"
else
    warn "M365 Extractor Suite ya existe"
fi

info "📈 Instalando Microsoft Graph SDK..."
pip install msgraph-sdk azure-identity msal
pwsh -NoProfile -Command "Install-Module -Name Microsoft.Graph -Force -Scope AllUsers" || true
info "✅ Microsoft Graph SDK instalado"

info "⚔️ Instalando Cloud Katana..."
if [ ! -d "cloud-katana" ]; then
    git clone https://github.com/Azure/Cloud-Katana.git cloud-katana
    cd cloud-katana
    pip install -r requirements.txt 2>/dev/null || pip install azure-identity azure-mgmt-resource
    cd ..
    info "✅ Cloud Katana instalado"
else
    warn "Cloud Katana ya existe"
fi

# ==================== DEPENDENCIES ====================

info "📦 Instalando dependencias PowerShell..."
pwsh -NoProfile -Command @"
Install-Module -Name Az -Force -Scope AllUsers -AllowClobber
Install-Module -Name ExchangeOnlineManagement -Force -Scope AllUsers
Install-Module -Name MicrosoftTeams -Force -Scope AllUsers
Install-Module -Name Microsoft.Online.SharePoint.PowerShell -Force -Scope AllUsers
Install-Module -Name AzureAD -Force -Scope AllUsers -AllowClobber
"@ || warn "Algunas dependencias PowerShell fallaron"

info "📦 Instalando dependencias Python en venv..."
pip install \
    azure-identity \
    azure-mgmt-resource \
    azure-mgmt-subscription \
    msgraph-sdk \
    msal \
    httpx \
    jinja2 \
    markdown \
    pydantic \
    fastapi

# ==================== REPORTS GENERATOR ====================

info "📄 Instalando herramientas para reportes..."
apt-get update && apt-get install -y wkhtmltopdf pandoc || warn "wkhtmltopdf/pandoc no instalados"

# ==================== PERMISSIONS ====================

info "🔒 Configurando permisos..."
chown -R $SUDO_USER:$SUDO_USER "$TOOLS_DIR" 2>/dev/null || true
chmod -R 755 "$TOOLS_DIR"

# Desactivar entorno virtual
deactivate

info "📝 Creando script wrapper para usar el venv automáticamente..."
cat > /usr/local/bin/forensics-tools << 'EOF'
#!/bin/bash
# Wrapper para ejecutar herramientas forenses con el venv correcto
source /opt/forensics-tools/venv/bin/activate
exec "$@"
EOF
chmod +x /usr/local/bin/forensics-tools
info "✅ Wrapper creado: forensics-tools [comando]"

# ==================== VERIFICATION ====================

info "✅ Verificando instalación..."
echo ""
echo "========================================"
echo "HERRAMIENTAS INSTALADAS:"
echo "========================================"

check_tool() {
    local name=$1
    local path=$2
    if [ -e "$path" ]; then
        echo -e "${GREEN}✓${NC} $name"
    else
        echo -e "${RED}✗${NC} $name (no encontrado)"
    fi
}

check_tool "AzureHound" "$TOOLS_DIR/azurehound/azurehound"
check_tool "ROADtools" "$(which roadrecon)"
check_tool "AADInternals" "$(pwsh -NoProfile -Command 'Get-Module -ListAvailable AADInternals' 2>/dev/null)"
check_tool "Monkey365" "$TOOLS_DIR/monkey365"
check_tool "CrowdStrike CRT" "$TOOLS_DIR/crt"
check_tool "Maester" "$TOOLS_DIR/maester"
check_tool "M365 Extractor Suite" "$TOOLS_DIR/Microsoft-Extractor-Suite"
check_tool "Cloud Katana" "$TOOLS_DIR/cloud-katana"

echo ""
echo "========================================"
echo "MÓDULOS POWERSHELL:"
echo "========================================"
pwsh -NoProfile -Command @"
\$modules = @('AADInternals', 'Az', 'ExchangeOnlineManagement', 'Microsoft.Graph', 'Maester')
foreach (\$mod in \$modules) {
    if (Get-Module -ListAvailable \$mod) {
        Write-Host "✓ \$mod" -ForegroundColor Green
    } else {
        Write-Host "✗ \$mod (no instalado)" -ForegroundColor Red
    }
}
"@

echo ""
info "🎉 Instalación completa!"
info "Ubicación de herramientas: $TOOLS_DIR"
info "Entorno virtual: $VENV_DIR"
info ""
info "MODO DE USO:"
info "  1. Desde Python/FastAPI: Las herramientas se ejecutarán automáticamente con el venv"
info "  2. Desde CLI directa: forensics-tools roadrecon auth --tenant-id xxx"
info "  3. O activar manualmente: source $VENV_DIR/bin/activate"

echo ""
warn "IMPORTANTE: Algunas herramientas requieren autenticación con Azure AD"
warn "Configura las credenciales antes de ejecutar análisis"
warn ""
warn "NOTA: Las herramientas Python se ejecutan en entorno virtual aislado"
warn "No afectarán los paquetes del sistema Kali Linux"
