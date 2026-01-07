#!/bin/bash

#############################################
# Microsoft 365 - Autenticación con Device Code
# Compatible con MFA - Genera URL para login
#############################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Microsoft 365 - Autenticación Device Code              ║"
echo "║   Compatible con MFA                                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

TENANT_ID="3af2e132-c361-4467-9d8b-081f06630c12"
CLIENT_ID="1b730954-1685-4b74-9bfd-dac224a7b894"  # Azure CLI público

# Paso 1: Solicitar Device Code
echo -e "${BLUE}ℹ️  Solicitando código de dispositivo...${NC}"
echo ""

DEVICE_CODE_RESPONSE=$(curl -s -X POST "https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/devicecode" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=${CLIENT_ID}" \
    -d "scope=https://graph.microsoft.com/.default offline_access")

# Extraer datos
USER_CODE=$(echo "$DEVICE_CODE_RESPONSE" | grep -oP '"user_code":"?\K[^"]+')
DEVICE_CODE=$(echo "$DEVICE_CODE_RESPONSE" | grep -oP '"device_code":"?\K[^"]+')
VERIFICATION_URL=$(echo "$DEVICE_CODE_RESPONSE" | grep -oP '"verification_uri":"?\K[^"]+')
MESSAGE=$(echo "$DEVICE_CODE_RESPONSE" | grep -oP '"message":"?\K[^"]+')

if [ -z "$USER_CODE" ]; then
    echo -e "${RED}❌ Error al solicitar código de dispositivo${NC}"
    echo "Respuesta: $DEVICE_CODE_RESPONSE"
    exit 1
fi

# Mostrar instrucciones
echo -e "${GREEN}✅ Código generado exitosamente${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}📱 INSTRUCCIONES PARA AUTENTICAR:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}1. Abre esta URL en tu navegador:${NC}"
echo ""
echo -e "   ${GREEN}${VERIFICATION_URL}${NC}"
echo ""
echo -e "${CYAN}2. Ingresa este código cuando lo solicite:${NC}"
echo ""
echo -e "   ${YELLOW}┌─────────────┐${NC}"
echo -e "   ${YELLOW}│   ${USER_CODE}   │${NC}"
echo -e "   ${YELLOW}└─────────────┘${NC}"
echo ""
echo -e "${CYAN}3. Inicia sesión con tu cuenta M365 (MFA soportado)${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}⏳ Esperando que completes la autenticación...${NC}"
echo ""

# Intentar abrir el navegador automáticamente
if command -v xdg-open &> /dev/null; then
    echo -e "${YELLOW}🌐 Abriendo navegador automáticamente...${NC}"
    xdg-open "$VERIFICATION_URL" 2>/dev/null &
elif command -v wslview &> /dev/null; then
    echo -e "${YELLOW}🌐 Abriendo navegador automáticamente (WSL)...${NC}"
    wslview "$VERIFICATION_URL" 2>/dev/null &
fi

# Paso 2: Polling para obtener el token
echo ""
INTERVAL=5
MAX_ATTEMPTS=120  # 10 minutos
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep $INTERVAL
    ATTEMPT=$((ATTEMPT + 1))
    
    TOKEN_RESPONSE=$(curl -s -X POST "https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=urn:ietf:params:oauth:grant-type:device_code" \
        -d "client_id=${CLIENT_ID}" \
        -d "device_code=${DEVICE_CODE}")
    
    # Verificar si hay token
    if echo "$TOKEN_RESPONSE" | grep -q '"access_token"'; then
        ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"access_token":"?\K[^"]+')
        
        echo ""
        echo -e "${GREEN}✅ Autenticación exitosa!${NC}"
        echo ""
        break
    fi
    
    # Verificar si hay error
    ERROR=$(echo "$TOKEN_RESPONSE" | grep -oP '"error":"?\K[^"]+')
    
    if [ "$ERROR" == "authorization_pending" ]; then
        echo -ne "\r⏳ Esperando autenticación... (${ATTEMPT}/${MAX_ATTEMPTS})   "
        continue
    elif [ "$ERROR" == "slow_down" ]; then
        INTERVAL=10
        continue
    elif [ "$ERROR" == "expired_token" ]; then
        echo ""
        echo -e "${RED}❌ El código expiró. Ejecuta el script nuevamente.${NC}"
        exit 1
    elif [ -n "$ERROR" ]; then
        echo ""
        echo -e "${RED}❌ Error: $ERROR${NC}"
        exit 1
    fi
done

if [ -z "$ACCESS_TOKEN" ]; then
    echo ""
    echo -e "${RED}❌ Timeout esperando autenticación${NC}"
    exit 1
fi

# Paso 3: Crear App Registration
echo ""
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
    
    # Verificar si es problema de permisos
    if echo "$ERROR_MSG" | grep -qi "insufficient\|privileges\|unauthorized"; then
        echo ""
        echo -e "${YELLOW}⚠️  Tu usuario no tiene permisos para crear aplicaciones.${NC}"
        echo ""
        echo "Necesitas uno de estos roles:"
        echo "  • Global Administrator"
        echo "  • Application Administrator"
        echo "  • Cloud Application Administrator"
        echo ""
        echo "Opciones:"
        echo "  1. Pídele a un administrador que ejecute este script"
        echo "  2. Configura manualmente en: https://portal.azure.com"
        echo ""
        echo "Ya tienes el Tenant ID guardado:"
        echo "  M365_TENANT_ID=${TENANT_ID}"
    fi
    
    exit 1
fi

APP_ID=$(echo "$APP_RESPONSE" | grep -oP '"appId":"?\K[^"]+')
OBJECT_ID=$(echo "$APP_RESPONSE" | grep -oP '"id":"?\K[^"]+' | head -1)

if [ -z "$APP_ID" ]; then
    echo -e "${RED}❌ No se pudo crear la aplicación${NC}"
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

touch "$ENV_FILE"
update_env "M365_TENANT_ID" "$TENANT_ID"
update_env "M365_CLIENT_ID" "$APP_ID"
update_env "M365_CLIENT_SECRET" "$CLIENT_SECRET"

echo -e "${GREEN}✅ Credenciales guardadas en .env${NC}"
echo ""

# Resumen final
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
echo "📋 Permisos configurados en la aplicación:"
echo ""
echo "   Microsoft Graph (6 permisos):"
echo "   • Directory.Read.All - Leer directorio completo"
echo "   • User.Read.All - Información de usuarios"
echo "   • AuditLog.Read.All - Logs de auditoría"
echo "   • SecurityEvents.Read.All - Eventos de seguridad"
echo "   • IdentityRiskEvent.Read.All - Eventos de riesgo"
echo "   • IdentityRiskyUser.Read.All - Usuarios con riesgo"
echo ""
echo "   Microsoft Intune (8 permisos):"
echo "   • get_data_warehouse - Data warehouse de Intune"
echo "   • get_device_compliance - Cumplimiento de dispositivos"
echo "   • manage_partner_compliance_policy - Políticas de cumplimiento"
echo "   • pfx_cert_provider - Gestión de certificados PFX"
echo "   • scep_challenge_provider - Validación SCEP"
echo "   • send_data_usage - Uso de datos de dispositivos"
echo "   • update_device_attributes - Atributos de dispositivos"
echo "   • update_device_health - Estado de salud de dispositivos"
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
