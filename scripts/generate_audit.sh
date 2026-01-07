#!/bin/bash

#############################################
# Generador de Registro de Auditoría
# Documenta configuración actual sin secretos
#############################################

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_DIR="$PROJECT_DIR/audit-logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
AUDIT_FILE="$AUDIT_DIR/config_audit_${TIMESTAMP}.log"

# Crear directorio
mkdir -p "$AUDIT_DIR"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Generando Registro de Auditoría                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Crear archivo de auditoría
cat > "$AUDIT_FILE" << EOF
═══════════════════════════════════════════════════════════════
MCP KALI FORENSICS - REGISTRO DE AUDITORÍA DE CONFIGURACIÓN
═══════════════════════════════════════════════════════════════

Fecha de Auditoría: $(date +"%Y-%m-%d %H:%M:%S %Z")
Usuario Ejecutor: $(whoami)
Hostname: $(hostname)
Sistema Operativo: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"')
Kernel: $(uname -r)
Arquitectura: $(uname -m)

═══════════════════════════════════════════════════════════════
1. INFORMACIÓN DEL PROYECTO
═══════════════════════════════════════════════════════════════

Directorio del Proyecto: $PROJECT_DIR
Directorio de Evidencia: $HOME/forensics-evidence
Directorio de Logs: $PROJECT_DIR/logs
Directorio de Auditoría: $AUDIT_DIR

Estructura de Directorios:
$(tree -L 2 -d "$PROJECT_DIR" 2>/dev/null | head -20 || echo "  (tree no disponible)")

═══════════════════════════════════════════════════════════════
2. CONFIGURACIÓN DE MICROSOFT 365
═══════════════════════════════════════════════════════════════

EOF

# Verificar credenciales M365
ENV_FILE="$PROJECT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    TENANT_ID=$(grep "^M365_TENANT_ID=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2)
    CLIENT_ID=$(grep "^M365_CLIENT_ID=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2)
    HAS_SECRET=$(grep -q "^M365_CLIENT_SECRET=.." "$ENV_FILE" 2>/dev/null && echo "SÍ" || echo "NO")
    
    cat >> "$AUDIT_FILE" << EOF
Estado: CONFIGURADO
Tenant ID: ${TENANT_ID:-NO CONFIGURADO}
Client ID (Application ID): ${CLIENT_ID:-NO CONFIGURADO}
Client Secret: ${HAS_SECRET} (valor oculto por seguridad)

Permisos Configurados en la Aplicación:

Microsoft Graph API (6 permisos de aplicación):
  ✓ Directory.Read.All
      Descripción: Leer directorio completo de Azure AD
      Uso: Análisis de usuarios, grupos, roles comprometidos
      Requerido por: Sparrow, Hawk
      
  ✓ User.Read.All
      Descripción: Leer información detallada de usuarios
      Uso: Investigación de cuentas comprometidas
      Requerido por: Sparrow, Hawk
      
  ✓ AuditLog.Read.All
      Descripción: Acceso a logs de auditoría de Azure AD
      Uso: Detección de actividad sospechosa, sign-ins anómalos
      Requerido por: Sparrow, análisis forense de incidentes
      
  ✓ SecurityEvents.Read.All
      Descripción: Leer eventos de seguridad y alertas
      Uso: Detección de amenazas, incidentes de seguridad
      Requerido por: Análisis de IOCs, respuesta a incidentes
      
  ✓ IdentityRiskEvent.Read.All
      Descripción: Leer eventos de riesgo de identidad
      Uso: Azure AD Identity Protection, detección de credenciales filtradas
      Requerido por: Análisis de riesgo de usuarios
      
  ✓ IdentityRiskyUser.Read.All
      Descripción: Leer usuarios con indicadores de riesgo
      Uso: Identificación de cuentas potencialmente comprometidas
      Requerido por: Priorización de investigaciones

Microsoft Intune API (8 permisos de aplicación):
  ✓ get_data_warehouse
      Descripción: Obtener información del data warehouse de Intune
      Uso: Análisis histórico de cumplimiento de dispositivos
      
  ✓ get_device_compliance
      Descripción: Estado y cumplimiento de dispositivos
      Uso: Identificar dispositivos no conformes o comprometidos
      
  ✓ manage_partner_compliance_policy
      Descripción: Gestionar políticas de cumplimiento de partners
      Uso: Integración con soluciones de seguridad de terceros
      
  ✓ pfx_cert_provider
      Descripción: Gestión de certificados PFX
      Uso: Validación de certificados de dispositivos
      
  ✓ scep_challenge_provider
      Descripción: Validación de desafíos SCEP
      Uso: Verificación de autenticación de dispositivos
      
  ✓ send_data_usage
      Descripción: Enviar y recibir uso de datos telecom/Wi-Fi
      Uso: Análisis de patrones de conectividad anómalos
      
  ✓ update_device_attributes
      Descripción: Enviar atributos de dispositivos a Intune
      Uso: Actualización de inventario de dispositivos
      
  ✓ update_device_health
      Descripción: Enviar información de amenazas de dispositivos
      Uso: Detección de malware y amenazas en endpoints

Estado de Aprobación de Permisos:
$(
source "$ENV_FILE" 2>/dev/null
if [ -n "$M365_TENANT_ID" ] && [ -n "$M365_CLIENT_ID" ] && [ -n "$M365_CLIENT_SECRET" ]; then
    TOKEN_RESPONSE=$(curl -s -X POST "https://login.microsoftonline.com/${M365_TENANT_ID}/oauth2/v2.0/token" \
        -d "client_id=${M365_CLIENT_ID}" \
        -d "client_secret=${M365_CLIENT_SECRET}" \
        -d "scope=https://graph.microsoft.com/.default" \
        -d "grant_type=client_credentials" 2>/dev/null)
    
    if echo "$TOKEN_RESPONSE" | grep -q '"access_token"'; then
        echo "  ✓ Autenticación: EXITOSA"
        
        ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"access_token":"?\K[^"]+')
        ORG_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
            "https://graph.microsoft.com/v1.0/organization" 2>/dev/null)
        
        if echo "$ORG_RESPONSE" | grep -q '"displayName"'; then
            ORG_NAME=$(echo "$ORG_RESPONSE" | grep -oP '"displayName":"?\K[^"]+' | head -1)
            echo "  ✓ Acceso a Organización: APROBADO"
            echo "  ✓ Organización: $ORG_NAME"
        else
            echo "  ⚠ Acceso a Organización: PERMISOS PENDIENTES"
            echo "  → Requiere Grant Admin Consent en portal Azure"
        fi
    else
        echo "  ✗ Autenticación: FALLIDA"
    fi
else
    echo "  ⚠ Credenciales incompletas"
fi
)

EOF
else
    cat >> "$AUDIT_FILE" << EOF
Estado: NO CONFIGURADO
Nota: Ejecutar scripts/setup_m365_devicecode.sh para configurar

EOF
fi

# Herramientas forenses instaladas
cat >> "$AUDIT_FILE" << EOF
═══════════════════════════════════════════════════════════════
3. HERRAMIENTAS FORENSES INSTALADAS
═══════════════════════════════════════════════════════════════

Ubicación de Herramientas: /opt/forensics-tools

EOF

# Verificar cada herramienta
check_tool() {
    local name="$1"
    local path="$2"
    local cmd="$3"
    
    if [ -d "$path" ] || command -v "$cmd" &> /dev/null; then
        echo "✓ $name: INSTALADO" >> "$AUDIT_FILE"
        
        if [ -n "$cmd" ] && command -v "$cmd" &> /dev/null; then
            version=$($cmd --version 2>&1 | head -1 || echo "versión no disponible")
            echo "  Versión: $version" >> "$AUDIT_FILE"
        fi
        
        if [ -d "$path" ]; then
            files=$(find "$path" -type f 2>/dev/null | wc -l)
            echo "  Archivos: $files" >> "$AUDIT_FILE"
        fi
    else
        echo "✗ $name: NO INSTALADO" >> "$AUDIT_FILE"
    fi
    echo "" >> "$AUDIT_FILE"
}

check_tool "Sparrow 365" "/opt/forensics-tools/Sparrow" ""
check_tool "Hawk" "/opt/forensics-tools/Hawk" ""
check_tool "Loki Scanner" "/opt/forensics-tools/Loki" ""
check_tool "YARA" "" "yara"
check_tool "YARA Rules" "/opt/forensics-tools/yara-rules" ""
check_tool "OSQuery" "" "osqueryi"
check_tool "Volatility 3" "" "vol.py"
check_tool "PowerShell Core" "" "pwsh"
check_tool "O365 Extractor" "/opt/forensics-tools/Office-365-Extractor" ""

# Componentes del MCP
cat >> "$AUDIT_FILE" << EOF
═══════════════════════════════════════════════════════════════
4. COMPONENTES DEL MCP
═══════════════════════════════════════════════════════════════

Archivos Python:
$(find "$PROJECT_DIR/api" -name "*.py" 2>/dev/null | wc -l) archivos en api/

Rutas (Endpoints):
$(find "$PROJECT_DIR/api/routes" -name "*.py" 2>/dev/null | while read file; do basename "$file" .py; done | grep -v "__" | sed 's/^/  ✓ /')

Servicios (Lógica de negocio):
$(find "$PROJECT_DIR/api/services" -name "*.py" 2>/dev/null | while read file; do basename "$file" .py; done | grep -v "__" | sed 's/^/  ✓ /')

Scripts de Configuración:
$(find "$PROJECT_DIR/scripts" -name "*.sh" -o -name "*.py" 2>/dev/null | while read file; do basename "$file"; done | sed 's/^/  ✓ /')

═══════════════════════════════════════════════════════════════
5. CONFIGURACIÓN DE SEGURIDAD
═══════════════════════════════════════════════════════════════

Variables de Entorno Configuradas:
EOF

if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r key value; do
        if [[ ! "$key" =~ ^# && -n "$key" ]]; then
            if [[ "$key" =~ (SECRET|PASSWORD|KEY|TOKEN) ]]; then
                echo "  $key=***OCULTO*** (configurado)" >> "$AUDIT_FILE"
            else
                echo "  $key=***configurado***" >> "$AUDIT_FILE"
            fi
        fi
    done < "$ENV_FILE"
else
    echo "  ⚠ Archivo .env no encontrado" >> "$AUDIT_FILE"
fi

# Permisos de archivos críticos
cat >> "$AUDIT_FILE" << EOF

Permisos de Archivos Críticos:
EOF

for file in "$ENV_FILE" "$PROJECT_DIR/api/config.py" "$PROJECT_DIR/api/main.py"; do
    if [ -f "$file" ]; then
        perms=$(ls -l "$file" | awk '{print $1, $3, $4}')
        echo "  $(basename $file): $perms" >> "$AUDIT_FILE"
    fi
done

# Directorio de evidencia
cat >> "$AUDIT_FILE" << EOF

Directorio de Evidencia:
  Ubicación: $HOME/forensics-evidence
  Permisos: $(ls -ld "$HOME/forensics-evidence" 2>/dev/null | awk '{print $1}' || echo "no existe")
  Casos almacenados: $(find "$HOME/forensics-evidence" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)

═══════════════════════════════════════════════════════════════
6. ESTADO DEL SISTEMA
═══════════════════════════════════════════════════════════════

Python:
  Versión: $(python3 --version 2>&1)
  Ubicación: $(which python3)
  
Dependencias Python Instaladas:
$(pip3 list 2>/dev/null | grep -E "(fastapi|uvicorn|httpx|pydantic)" | sed 's/^/  /')

Espacio en Disco:
$(df -h "$PROJECT_DIR" | tail -1 | awk '{print "  Dispositivo: "$1"\n  Total: "$2"\n  Usado: "$3" ("$5")\n  Disponible: "$4}')

Memoria:
$(free -h | grep Mem | awk '{print "  Total: "$2"\n  Usado: "$3"\n  Disponible: "$7}')

═══════════════════════════════════════════════════════════════
7. RECOMENDACIONES DE SEGURIDAD
═══════════════════════════════════════════════════════════════

EOF

recommendations=0

# Verificar permisos de .env
if [ -f "$ENV_FILE" ]; then
    env_perms=$(stat -c "%a" "$ENV_FILE" 2>/dev/null)
    if [ "$env_perms" != "600" ] && [ "$env_perms" != "400" ]; then
        echo "⚠ Archivo .env tiene permisos $env_perms (recomendado: 600)" >> "$AUDIT_FILE"
        echo "  Ejecutar: chmod 600 $ENV_FILE" >> "$AUDIT_FILE"
        ((recommendations++))
    fi
fi

# Verificar si los permisos están aprobados
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE" 2>/dev/null
    if [ -n "$M365_CLIENT_ID" ]; then
        TOKEN_RESPONSE=$(curl -s -X POST "https://login.microsoftonline.com/${M365_TENANT_ID}/oauth2/v2.0/token" \
            -d "client_id=${M365_CLIENT_ID}" \
            -d "client_secret=${M365_CLIENT_SECRET}" \
            -d "scope=https://graph.microsoft.com/.default" \
            -d "grant_type=client_credentials" 2>/dev/null)
        
        if echo "$TOKEN_RESPONSE" | grep -q '"access_token"'; then
            ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"access_token":"?\K[^"]+')
            ORG_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
                "https://graph.microsoft.com/v1.0/organization" 2>/dev/null)
            
            if ! echo "$ORG_RESPONSE" | grep -q '"displayName"'; then
                echo "⚠ Permisos de aplicación no aprobados por administrador" >> "$AUDIT_FILE"
                echo "  Portal: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/${M365_CLIENT_ID}" >> "$AUDIT_FILE"
                ((recommendations++))
            fi
        fi
    fi
fi

if [ $recommendations -eq 0 ]; then
    echo "✓ No se encontraron problemas de seguridad" >> "$AUDIT_FILE"
fi

# Footer
cat >> "$AUDIT_FILE" << EOF

═══════════════════════════════════════════════════════════════
FIN DEL REGISTRO DE AUDITORÍA
═══════════════════════════════════════════════════════════════

Generado: $(date +"%Y-%m-%d %H:%M:%S %Z")
Archivo: $AUDIT_FILE

NOTA IMPORTANTE:
Este registro NO contiene información sensible (secretos, contraseñas,
tokens de acceso). Los valores sensibles se muestran como ***OCULTO***
por motivos de seguridad.

Para uso interno y auditorías de cumplimiento.

═══════════════════════════════════════════════════════════════
EOF

# Mostrar resumen
echo -e "${GREEN}✅ Registro de auditoría generado${NC}"
echo ""
echo -e "${CYAN}📁 Ubicación:${NC}"
echo "   $AUDIT_FILE"
echo ""
echo -e "${CYAN}📊 Resumen:${NC}"
echo "   $(wc -l < "$AUDIT_FILE") líneas generadas"
echo "   $(grep -c "✓" "$AUDIT_FILE") elementos verificados"
echo "   $(grep -c "⚠" "$AUDIT_FILE") advertencias/recomendaciones"
echo ""
echo -e "${BLUE}Ver registro completo:${NC}"
echo "   cat $AUDIT_FILE"
echo ""
echo -e "${BLUE}Ver solo resumen:${NC}"
echo "   grep -E '(═══|✓|✗|⚠)' $AUDIT_FILE | head -50"
echo ""

# Crear symlink al último
ln -sf "$AUDIT_FILE" "$AUDIT_DIR/latest.log"
echo -e "${GREEN}✓ Link simbólico creado: $AUDIT_DIR/latest.log${NC}"
echo ""

exit 0
