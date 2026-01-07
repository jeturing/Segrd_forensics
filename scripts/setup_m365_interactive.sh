#!/bin/bash

#############################################
# Microsoft 365 - Setup Interactivo
# Usa Azure CLI para autenticación MFA
#############################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

install_azure_cli() {
    local dist_code candidates=() success=0

    # Requisitos base (idempotente)
    sudo apt update
    sudo apt install -y ca-certificates curl apt-transport-https gnupg lsb-release jq

    echo "Instalando Azure CLI..."

    if curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash; then
        success=1
    else
        dist_code=$(lsb_release -cs 2>/dev/null || echo "")
        [ -n "$dist_code" ] && candidates+=("$dist_code")
        candidates+=("bookworm" "bullseye")

        sudo mkdir -p /etc/apt/keyrings
        curl -sL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg >/dev/null
        sudo chmod go+r /etc/apt/keyrings/microsoft.gpg

        for code in "${candidates[@]}"; do
            echo "  → Probando repositorio $code..."
            echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ $code main" | sudo tee /etc/apt/sources.list.d/azure-cli.list >/dev/null
            if sudo apt update && sudo apt install -y azure-cli; then
                success=1
                break
            fi
        done
    fi

    if [ "$success" -ne 1 ]; then
        echo -e "${RED}❌ No se pudo instalar Azure CLI automáticamente${NC}"
        echo "   Instálalo manualmente siguiendo https://learn.microsoft.com/cli/azure/install-azure-cli-linux?pivots=apt"
        return 1
    fi

    echo -e "${GREEN}✅ Azure CLI instalado${NC}"
    echo ""
}

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Microsoft 365 - Configuración Interactiva              ║"
echo "║   Compatible con MFA                                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Verificar si Azure CLI está instalado
if ! command -v az &> /dev/null; then
    echo -e "${YELLOW}⚠️  Azure CLI no está instalado${NC}"
    echo ""
    install_azure_cli || exit 1
fi

# Login interactivo
echo -e "${BLUE}ℹ️  Iniciando sesión en Microsoft 365...${NC}"
echo "   (Se abrirá una ventana del navegador)"
echo ""

az login

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al autenticar${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Autenticación exitosa${NC}"
echo ""

# Obtener Tenant ID
echo -e "${BLUE}ℹ️  Obteniendo Tenant ID...${NC}"
TENANT_ID=$(az account show --query tenantId -o tsv)

if [ -z "$TENANT_ID" ]; then
    echo -e "${RED}❌ No se pudo obtener el Tenant ID${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Tenant ID: $TENANT_ID${NC}"
echo ""

# Crear App Registration
echo -e "${BLUE}ℹ️  Creando App Registration...${NC}"

APP_NAME="MCP-Kali-Forensics-$(date +%s)"

# Crear aplicación
APP_JSON=$(az ad app create \
    --display-name "$APP_NAME" \
    --sign-in-audience AzureADMyOrg \
    --output json)

APP_ID=$(echo "$APP_JSON" | jq -r '.appId')
OBJECT_ID=$(echo "$APP_JSON" | jq -r '.id')

if [ -z "$APP_ID" ]; then
    echo -e "${RED}❌ Error al crear la aplicación${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Aplicación creada${NC}"
echo "   App ID: $APP_ID"
echo ""

# Agregar permisos de Microsoft Graph
echo -e "${BLUE}ℹ️  Configurando permisos de Microsoft Graph...${NC}"

# API de Microsoft Graph
GRAPH_ID="00000003-0000-0000-c000-000000000000"

# Permisos requeridos (Application permissions)
az ad app permission add --id "$APP_ID" --api "$GRAPH_ID" --api-permissions \
    230c1aed-a721-4c5d-9cb4-a90514e508ef=Role \
    7ab1d382-f21e-4acd-a863-ba3e13f7da61=Role \
    df021288-bdef-4463-88db-98f22de89214=Role \
    b0afded3-3588-46d8-8b3d-9842eff778da=Role \
    dc5007c0-2d7d-4c42-879c-2dab87571379=Role \
    6e472fd1-ad78-48da-a0f0-97ab2c6b769e=Role

echo -e "${GREEN}✅ Permisos agregados${NC}"
echo ""

# Crear Client Secret
echo -e "${BLUE}ℹ️  Generando Client Secret...${NC}"

SECRET_JSON=$(az ad app credential reset \
    --id "$APP_ID" \
    --append \
    --years 2 \
    --output json)

CLIENT_SECRET=$(echo "$SECRET_JSON" | jq -r '.password')

if [ -z "$CLIENT_SECRET" ]; then
    echo -e "${RED}❌ Error al generar el Client Secret${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Client Secret generado${NC}"
echo ""

# Crear Service Principal
echo -e "${BLUE}ℹ️  Creando Service Principal...${NC}"

az ad sp create --id "$APP_ID" > /dev/null 2>&1

echo -e "${GREEN}✅ Service Principal creado${NC}"
echo ""

# Aprobar permisos (requiere admin)
echo -e "${BLUE}ℹ️  Aprobando permisos (requiere permisos de administrador)...${NC}"

az ad app permission admin-consent --id "$APP_ID" 2>&1 | grep -q "Forbidden" && {
    echo -e "${YELLOW}⚠️  No tienes permisos para aprobar automáticamente${NC}"
    echo "   Un administrador global debe aprobar en:"
    echo "   https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/$APP_ID"
} || {
    echo -e "${GREEN}✅ Permisos aprobados automáticamente${NC}"
}

echo ""

# Guardar en .env
echo -e "${BLUE}ℹ️  Guardando credenciales en .env...${NC}"

ENV_FILE="../.env"

# Crear .env si no existe
if [ ! -f "$ENV_FILE" ]; then
    cp ../.env.example "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
fi

# Actualizar valores
sed -i "s/^M365_TENANT_ID=.*/M365_TENANT_ID=$TENANT_ID/" "$ENV_FILE"
sed -i "s/^M365_CLIENT_ID=.*/M365_CLIENT_ID=$APP_ID/" "$ENV_FILE"
sed -i "s/^M365_CLIENT_SECRET=.*/M365_CLIENT_SECRET=$CLIENT_SECRET/" "$ENV_FILE"

# Agregar si no existen
grep -q "M365_TENANT_ID=" "$ENV_FILE" || echo "M365_TENANT_ID=$TENANT_ID" >> "$ENV_FILE"
grep -q "M365_CLIENT_ID=" "$ENV_FILE" || echo "M365_CLIENT_ID=$APP_ID" >> "$ENV_FILE"
grep -q "M365_CLIENT_SECRET=" "$ENV_FILE" || echo "M365_CLIENT_SECRET=$CLIENT_SECRET" >> "$ENV_FILE"

echo -e "${GREEN}✅ Credenciales guardadas en .env${NC}"
echo ""

# Resumen
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Configuración completada exitosamente${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📋 Credenciales generadas:"
echo ""
echo "   Tenant ID:     $TENANT_ID"
echo "   Client ID:     $APP_ID"
echo "   Client Secret: ${CLIENT_SECRET:0:20}...${CLIENT_SECRET: -10}"
echo ""
echo "📁 Guardadas en: $ENV_FILE"
echo ""
echo "🔧 Próximos pasos:"
echo ""
echo "   1. Verificar que los permisos estén aprobados:"
echo "      https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/$APP_ID"
echo ""
echo "   2. Probar la configuración:"
echo "      cd /home/hack/mcp-kali-forensics"
echo "      source venv/bin/activate"
echo "      python3 -c \"from api.services.m365 import test_connection; test_connection()\""
echo ""
echo "   3. Iniciar el MCP:"
echo "      uvicorn api.main:app --host 0.0.0.0 --port 8080"
echo ""

exit 0
