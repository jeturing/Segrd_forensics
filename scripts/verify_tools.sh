#!/bin/bash
# Script de verificación de herramientas M365 Forensics
# Verifica e instala herramientas faltantes

set -e

TOOLS_DIR="/opt/forensics-tools"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Verificando herramientas M365 Forensics..."
echo ""

MISSING_TOOLS=()
INSTALLED_TOOLS=()

# Función para verificar e instalar
verify_and_install() {
    local tool_path=$1
    local tool_name=$2
    local install_command=$3
    
    if [ -d "$tool_path" ] || command -v "$tool_name" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $tool_name - Instalado"
        INSTALLED_TOOLS+=("$tool_name")
    else
        echo -e "${RED}✗${NC} $tool_name - NO INSTALADO"
        MISSING_TOOLS+=("$tool_name")
        
        if [ -n "$install_command" ]; then
            read -p "¿Instalar $tool_name ahora? (s/n): " install_now
            if [ "$install_now" = "s" ]; then
                echo "📦 Instalando $tool_name..."
                eval "$install_command"
                echo -e "${GREEN}✓${NC} $tool_name instalado"
            fi
        fi
    fi
}

echo "📋 BÁSICO:"
verify_and_install "$TOOLS_DIR/Sparrow" "Sparrow" "git clone https://github.com/cisagov/Sparrow.git $TOOLS_DIR/Sparrow"
verify_and_install "$TOOLS_DIR/hawk" "Hawk" "git clone https://github.com/T0pCyber/hawk.git $TOOLS_DIR/hawk"
verify_and_install "$TOOLS_DIR/sra-o365-extractor" "O365 Extractor" "git clone https://github.com/SecurityRiskAdvisors/o365-extractor.git $TOOLS_DIR/sra-o365-extractor"

echo ""
echo "📋 RECONOCIMIENTO:"
verify_and_install "$TOOLS_DIR/azurehound" "AzureHound" "cd $TOOLS_DIR && git clone https://github.com/BloodHoundAD/AzureHound.git azurehound"
verify_and_install "" "roadrecon" "pip3 install roadtools roadrecon roadlib"
verify_and_install "" "AADInternals" "pwsh -NoProfile -Command 'Install-Module -Name AADInternals -Force -Scope CurrentUser'"

echo ""
echo "📋 AUDITORÍA:"
verify_and_install "$TOOLS_DIR/monkey365" "Monkey365" "cd $TOOLS_DIR && git clone https://github.com/silverhack/monkey365.git"
verify_and_install "$TOOLS_DIR/crt" "CrowdStrike CRT" "cd $TOOLS_DIR && git clone https://github.com/CrowdStrike/CRT.git crt"
verify_and_install "$TOOLS_DIR/maester" "Maester" "cd $TOOLS_DIR && git clone https://github.com/maester365/maester.git"

echo ""
echo "📋 FORENSE:"
verify_and_install "$TOOLS_DIR/Microsoft-Extractor-Suite" "M365 Extractor" "cd $TOOLS_DIR && git clone https://github.com/invictus-ir/Microsoft-Extractor-Suite.git"
verify_and_install "" "msgraph-sdk" "pip3 install msgraph-sdk azure-identity msal"
verify_and_install "$TOOLS_DIR/cloud-katana" "Cloud Katana" "cd $TOOLS_DIR && git clone https://github.com/Azure/Cloud-Katana.git cloud-katana"

echo ""
echo "================================"
echo "📊 RESUMEN:"
echo "✅ Instaladas: ${#INSTALLED_TOOLS[@]}"
echo "❌ Faltantes: ${#MISSING_TOOLS[@]}"

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo ""
    echo "🔧 Herramientas faltantes:"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo "  - $tool"
    done
    echo ""
    echo "💡 Ejecuta: sudo ./scripts/install.sh para instalar todas"
fi

echo "================================"
