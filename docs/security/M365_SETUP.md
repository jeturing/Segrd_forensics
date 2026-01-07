# Configuración Automática de Microsoft 365

Esta guía explica cómo configurar automáticamente las credenciales de Microsoft 365 para el MCP usando tu usuario y contraseña.

## 🚀 Opción 1: Configuración Interactiva (RECOMENDADA)

**Compatible con MFA (Multi-Factor Authentication)**

Este método usa Azure CLI para autenticación interactiva en el navegador, por lo que funciona aunque tengas MFA habilitado.

```bash
cd /home/hack/mcp-kali-forensics/scripts
./setup_m365_interactive.sh
```

**Lo que hace automáticamente:**
1. ✅ Instala Azure CLI (si no está instalado)
2. ✅ Abre navegador para login interactivo (compatible con MFA)
3. ✅ Obtiene automáticamente el Tenant ID
4. ✅ Crea App Registration "MCP-Kali-Forensics"
5. ✅ Configura permisos de Microsoft Graph:
   - `Directory.Read.All`
   - `User.Read.All`
   - `AuditLog.Read.All`
   - `SecurityEvents.Read.All`
   - `IdentityRiskEvent.Read.All`
   - `Mail.Read`
6. ✅ Genera Client Secret (válido 2 años)
7. ✅ Crea Service Principal
8. ✅ Intenta aprobar permisos automáticamente (si eres Global Admin)
9. ✅ Guarda credenciales en `.env`

**Salida esperada:**
```
✅ Configuración completada exitosamente

📋 Credenciales generadas:
   Tenant ID:     xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Client ID:     yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
   Client Secret: zzzzzzzzzz...

📁 Guardadas en: .env
```

---

## 🔐 Opción 2: Script Python (Sin MFA)

**Solo si NO tienes MFA habilitado**

Este método usa autenticación con usuario/password. Solo funciona si tu cuenta NO tiene MFA.

```bash
cd /home/hack/mcp-kali-forensics/scripts
./setup_m365.py
```

Te solicitará:
```
Email: admin@tuempresa.onmicrosoft.com
Password: ************
```

**Lo que hace automáticamente:**
1. ✅ Busca el Tenant ID desde el dominio del email
2. ✅ Autentica usando Resource Owner Password Flow
3. ✅ Crea App Registration via Microsoft Graph API
4. ✅ Configura permisos necesarios
5. ✅ Genera Client Secret
6. ✅ Guarda en `.env`

**Si tienes MFA habilitado, verás:**
```
❌ La cuenta requiere autenticación multifactor (MFA)
⚠️  Usa el método interactivo: ./setup_m365_interactive.sh
```

---

## ✅ Verificar Configuración

Después de configurar, verifica que todo funcione:

```bash
cd /home/hack/mcp-kali-forensics/scripts
./test_m365_connection.py
```

**Test de conexión verifica:**
- ✅ Credenciales en `.env`
- ✅ Autenticación con Microsoft Graph
- ✅ Acceso a Organization info
- ✅ Permisos de Audit Logs
- ✅ Permisos de Users

**Salida esperada:**
```
✅ Token obtenido exitosamente
✅ Organización: Tu Empresa S.A.
   Dominio verificado: tuempresa.com
✅ Acceso a Audit Logs: OK
✅ Acceso a Users: OK

✅ Test completado
```

---

## 🔧 Aprobar Permisos Manualmente

Si ves este mensaje:
```
⚠️  Sin permisos para Audit Logs
```

Un **Global Administrator** debe aprobar los permisos:

### Método 1: Portal Azure
1. Ve a: https://portal.azure.com
2. Azure Active Directory → App registrations
3. Busca "MCP-Kali-Forensics"
4. Click en "API permissions"
5. Click en "Grant admin consent for [Your Org]"
6. Confirmar

### Método 2: PowerShell
```powershell
# Conectar como Global Admin
Connect-MgGraph -Scopes "Application.ReadWrite.All", "AppRoleAssignment.ReadWrite.All"

# Aprobar permisos
$appId = "tu-app-id-aqui"
$sp = Get-MgServicePrincipal -Filter "appId eq '$appId'"

# Listar permisos pendientes y aprobar
Grant-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id
```

### Método 3: Azure CLI
```bash
APP_ID="tu-app-id"
az ad app permission admin-consent --id "$APP_ID"
```

---

## 📋 Permisos Configurados Automáticamente

Estos son los permisos que se configuran para análisis forense:

| Permiso | Descripción | Uso en MCP |
|---------|-------------|------------|
| `Directory.Read.All` | Leer directorio completo | Sparrow, análisis de usuarios/grupos |
| `User.Read.All` | Leer información de usuarios | Hawk, análisis de compromisos |
| `AuditLog.Read.All` | Leer logs de auditoría | Sparrow, detección de actividad sospechosa |
| `SecurityEvents.Read.All` | Leer eventos de seguridad | Alertas de seguridad |
| `IdentityRiskEvent.Read.All` | Leer eventos de riesgo | Azure AD Identity Protection |
| `IdentityRiskyUser.Read.All` | Usuarios con riesgo | Detección de cuentas comprometidas |
| `Mail.Read` | Leer correos | Hawk, análisis de reglas de reenvío |

---

## 🐛 Troubleshooting

### Error: "Azure CLI not installed"

```bash
# Instalar Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Error: "Insufficient privileges to complete the operation"

Tu usuario necesita ser **Application Administrator** o **Global Administrator** para crear App Registrations.

**Solución:**
Pídele a un administrador que:
1. Ejecute el script con su usuario
2. O te asigne el rol "Application Developer" en Azure AD

### Error: "AADSTS50076: Multi-factor authentication required"

Tu cuenta tiene MFA. **Usa el método interactivo:**
```bash
./setup_m365_interactive.sh
```

### Error: "Tenant not found"

Verifica que el dominio del email sea correcto:
```bash
# Debe ser el dominio de Azure AD
admin@tuempresa.onmicrosoft.com  ✅
admin@tuempresa.com              ⚠️  Solo si el dominio está federado
```

### Error: "Invalid client secret"

El secret puede haber expirado o no guardarse correctamente. Regenera:

```bash
# Opción 1: Reejecutar script
./setup_m365_interactive.sh

# Opción 2: Regenerar manualmente en portal
# Azure Portal → App registrations → Tu app → Certificates & secrets → New client secret
```

### Verificar credenciales manualmente

```bash
# Ver contenido de .env
cat /home/hack/mcp-kali-forensics/.env | grep M365

# Debe mostrar:
M365_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
M365_CLIENT_ID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
M365_CLIENT_SECRET=zzzzzz~xxxxxxxxxxxxxxxxxx
```

---

## 🔄 Reconfigurar Credenciales

Si necesitas cambiar las credenciales:

```bash
# 1. Eliminar configuración actual
rm /home/hack/mcp-kali-forensics/.env

# 2. Reejecutar setup
cd /home/hack/mcp-kali-forensics/scripts
./setup_m365_interactive.sh
```

O editar manualmente:
```bash
nano /home/hack/mcp-kali-forensics/.env
```

---

## 🎯 Siguiente Paso

Una vez configurado, prueba el MCP:

```bash
cd /home/hack/mcp-kali-forensics
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8080

# En otra terminal, ejecutar análisis
curl -X POST http://localhost:8080/forensics/m365/analyze \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "auto",
    "case_id": "TEST-001",
    "scope": ["sparrow"]
  }'
```

Ver logs:
```bash
tail -f logs/mcp-forensics.log
```
