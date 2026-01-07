#!/bin/bash

#############################################
# Microsoft 365 - Configuración con cURL
# Sin dependencias de Python/Azure CLI
#############################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Credenciales
EMAIL="$1"
PASSWORD="$2"

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
    echo -e "${RED}❌ Uso: $0 <email> <password>${NC}"
    exit 1
fi

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Microsoft 365 - Configuración Automática               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Paso 1: Obtener Tenant ID
echo -e "${BLUE}ℹ️  Obteniendo Tenant ID...${NC}"

DOMAIN=$(echo "$EMAIL" | cut -d'@' -f2)
OPENID_URL="https://login.microsoftonline.com/${DOMAIN}/v2.0/.well-known/openid-configuration"

OPENID_RESPONSE=$(curl -s "$OPENID_URL")

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al obtener configuración OpenID${NC}"
    exit 1
fi

# Extraer tenant ID del token_endpoint
TOKEN_ENDPOINT=$(echo "$OPENID_RESPONSE" | grep -oP '"token_endpoint":"https://login.microsoftonline.com/\K[^/]+')

if [ -z "$TOKEN_ENDPOINT" ]; then
    echo -e "${RED}❌ No se pudo obtener el Tenant ID${NC}"
    echo "Respuesta: $OPENID_RESPONSE"
    exit 1
fi

TENANT_ID="$TOKEN_ENDPOINT"
echo -e "${GREEN}✅ Tenant ID: $TENANT_ID${NC}"
echo ""

# Paso 2: Autenticar con Resource Owner Password Flow
echo -e "${BLUE}ℹ️  Autenticando con Microsoft Graph...${NC}"

AUTH_URL="https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/token"

AUTH_RESPONSE=$(curl -s -X POST "$AUTH_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=1b730954-1685-4b74-9bfd-dac224a7b894" \
    -d "scope=https://graph.microsoft.com/.default" \
    -d "username=${EMAIL}" \
    -d "password=${PASSWORD}" \
    -d "grant_type=password")

# Verificar si hay error
if echo "$AUTH_RESPONSE" | grep -q '"error"'; then
    ERROR_DESC=$(echo "$AUTH_RESPONSE" | grep -oP '"error_description":"?\K[^"]+' | head -1)
    
    if echo "$ERROR_DESC" | grep -qi "MFA\|AADSTS50076"; then
        echo -e "${RED}❌ La cuenta requiere MFA${NC}"
        echo -e "${YELLOW}Usa el método interactivo:${NC}"
        echo "   ./setup_m365_interactive.sh"
        exit 1
    else
        echo -e "${RED}❌ Error de autenticación:${NC}"
        echo "$ERROR_DESC"
        exit 1
    fi
fi

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | grep -oP '"access_token":"?\K[^"]+')

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}❌ No se pudo obtener el token de acceso${NC}"
    echo "Respuesta: $AUTH_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Autenticación exitosa${NC}"
echo ""

# Paso 3: Crear App Registration
echo -e "${BLUE}ℹ️  Creando App Registration...${NC}"

APP_NAME="MCP-Kali-Forensics-$(date +%s)"

APP_MANIFEST='{
  "displayName": "'$APP_NAME'",
  "signInAudience": "AzureADMyOrg",
  "requiredResourceAccess": [
    {
      "resourceAppId": "00000003-0000-0000-c000-000000000000",
      "resourceAccess": [
        {"id": "230c1aed-a721-4c5d-9cb4-a90514e508ef", "type": "Role"},
        {"id": "7ab1d382-f21e-4acd-a863-ba3e13f7da61", "type": "Role"},
        {"id": "df021288-bdef-4463-88db-98f22de89214", "type": "Role"},
        {"id": "b0afded3-3588-46d8-8b3d-9842eff778da", "type": "Role"},
        {"id": "dc5007c0-2d7d-4c42-879c-2dab87571379", "type": "Role"},
        {"id": "6e472fd1-ad78-48da-a0f0-97ab2c6b769e", "type": "Role"}
      ]
    },
    {
      "resourceAppId": "c5393580-f805-4401-95e8-94b7a6ef2fc2",
      "resourceAccess": [
        {"id": "9e640a1d-4c34-4d0a-8c45-8c2b1e7f6ade", "type": "Role"},
        {"id": "e330f4f8-0a5e-4c2d-8e2f-3b8e5b8a9c4f", "type": "Role"},
        {"id": "4a06efd2-f825-4e34-813e-82a57b03d1ee", "type": "Role"},
        {"id": "18c6d0d5-8c5e-4f3f-8e4e-1e4b9e0c8d2a", "type": "Role"},
        {"id": "0e263e50-5827-48a4-b97c-d940288653c7", "type": "Role"},
        {"id": "f1493658-876a-4c87-8fa7-edb559b3476a", "type": "Role"},
        {"id": "2f51be20-0bb4-4fed-bf7b-db946066c75e", "type": "Role"},
        {"id": "65a6bfb9-57fc-4685-b1e6-8e28e9e5cf4a", "type": "Role"}
      ]
    }
  ]
}'

APP_RESPONSE=$(curl -s -X POST "https://graph.microsoft.com/v1.0/applications" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$APP_MANIFEST")

if echo "$APP_RESPONSE" | grep -q '"error"'; then
    ERROR_MSG=$(echo "$APP_RESPONSE" | grep -oP '"message":"?\K[^"]+' | head -1)
    echo -e "${RED}❌ Error al crear aplicación:${NC}"
    echo "$ERROR_MSG"
    exit 1
fi

APP_ID=$(echo "$APP_RESPONSE" | grep -oP '"appId":"?\K[^"]+')
OBJECT_ID=$(echo "$APP_RESPONSE" | grep -oP '"id":"?\K[^"]+' | head -1)

if [ -z "$APP_ID" ]; then
    echo -e "${RED}❌ No se pudo crear la aplicación${NC}"
    echo "Respuesta: $APP_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Aplicación creada${NC}"
echo "   App ID: $APP_ID"
echo ""

# Paso 4: Crear Client Secret
echo -e "${BLUE}ℹ️  Generando Client Secret...${NC}"

SECRET_PAYLOAD='{
  "passwordCredential": {
    "displayName": "MCP-Forensics-Secret",
    "endDateTime": "2027-12-31T23:59:59Z"
  }
}'

SECRET_RESPONSE=$(curl -s -X POST "https://graph.microsoft.com/v1.0/applications/${OBJECT_ID}/addPassword" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$SECRET_PAYLOAD")

CLIENT_SECRET=$(echo "$SECRET_RESPONSE" | grep -oP '"secretText":"?\K[^"]+')

if [ -z "$CLIENT_SECRET" ]; then
    echo -e "${RED}❌ No se pudo generar el Client Secret${NC}"
    echo "Respuesta: $SECRET_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Client Secret generado${NC}"
echo ""

# Paso 5: Crear Service Principal
echo -e "${BLUE}ℹ️  Creando Service Principal...${NC}"

SP_PAYLOAD='{"appId": "'$APP_ID'"}'

SP_RESPONSE=$(curl -s -X POST "https://graph.microsoft.com/v1.0/servicePrincipals" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$SP_PAYLOAD")

if echo "$SP_RESPONSE" | grep -q '"id"'; then
    echo -e "${GREEN}✅ Service Principal creado${NC}"
else
    echo -e "${YELLOW}⚠️  Service Principal no creado (puede ya existir)${NC}"
fi
echo ""

# Paso 6: Guardar en .env
echo -e "${BLUE}ℹ️  Guardando credenciales en .env...${NC}"

ENV_FILE="../.env"

# Crear backup si existe
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%s)"
fi

# Actualizar o agregar valores
touch "$ENV_FILE"

# Función para actualizar o agregar línea
update_env() {
    local key="$1"
    local value="$2"
    
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

update_env "M365_TENANT_ID" "$TENANT_ID"
update_env "M365_CLIENT_ID" "$APP_ID"
update_env "M365_CLIENT_SECRET" "$CLIENT_SECRET"

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
echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
echo "   Un administrador debe aprobar los permisos en:"
echo -e "   ${BLUE}https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/${APP_ID}${NC}"
echo ""
echo "🔧 Próximos pasos:"
echo ""
echo "   1. Aprobar permisos (ver URL arriba)"
echo ""
echo "   2. Verificar conexión:"
echo "      cd /home/hack/mcp-kali-forensics"
echo "      python3 scripts/test_m365_connection.py"
echo ""
echo "   3. Iniciar el MCP:"
echo "      uvicorn api.main:app --host 0.0.0.0 --port 8080"
echo ""

exit 0
