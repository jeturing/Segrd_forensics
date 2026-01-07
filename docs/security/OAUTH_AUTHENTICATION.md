# 🔐 Autenticación OAuth para Azure AD

## ✅ Implementación Completada

Se ha restaurado el tenant **SINERLEX DOMINICANA** y se ha implementado un flujo completo de autenticación OAuth 2.0 Device Code Flow que permite login seguro sin guardar contraseñas.

---

## 📋 ¿Qué es Device Code Flow?

Es un método de autenticación de Microsoft que:
- ✅ **Redirige al navegador** para login seguro
- ✅ **Permite MFA** (Multi-Factor Authentication)
- ✅ **No guarda contraseñas** en la aplicación
- ✅ **Token de acceso temporal** con refresh automático
- ✅ **Compatible con Azure AD** y Microsoft 365

---

## 🚀 Cómo Usar (Desde Dashboard)

### Paso 1: Abrir Modal de Login

1. Abre el dashboard: **http://localhost:9000/dashboard**
2. En el header superior, click en el botón **"Login OAuth"** (morado/azul)

### Paso 2: Seleccionar Tenant

El modal mostrará todos los tenants registrados:
- **SINERLEX DOMINICANA** (sinerlexrd.onmicrosoft.com)

Selecciona el tenant y click **"Iniciar Autenticación"**

### Paso 3: Login en Navegador

La app te mostrará:

```
┌─────────────────────────────────────────┐
│ Abre esta URL en tu navegador:         │
│ https://microsoft.com/devicelogin       │
│                                         │
│ E ingresa este código:                  │
│ ┌─────────────┐                         │
│ │  ABC12-DEF  │                         │
│ └─────────────┘                         │
│                                         │
│ Tiempo restante: 15:00                  │
└─────────────────────────────────────────┘
```

1. **Abre** el enlace en tu navegador (se puede abrir automáticamente)
2. **Ingresa** el código mostrado (8 caracteres)
3. **Completa** la autenticación:
   - Login con tu usuario de Azure AD
   - Si tienes MFA, completa la verificación
   - Acepta los permisos solicitados

### Paso 4: Confirmación Automática

La app verifica automáticamente cada 5 segundos si completaste la autenticación.

Cuando termines, verás:

```
✅ ¡Autenticación Exitosa!
Token de acceso obtenido correctamente
```

El modal se cerrará automáticamente y el token se guardará en el navegador.

---

## 🔧 Uso desde API (Avanzado)

### 1. Iniciar Device Code Flow

```bash
curl -X POST http://localhost:9000/api/oauth/device-code/init \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "3af2e132-c361-4467-9d8b-081f06630c12",
    "scopes": [
      "User.Read",
      "AuditLog.Read.All",
      "Directory.Read.All"
    ]
  }'
```

**Response:**
```json
{
  "device_code": "ABC123...",
  "user_code": "ABC12-DEF",
  "verification_uri": "https://microsoft.com/devicelogin",
  "expires_in": 900,
  "interval": 5,
  "message": "To sign in, use a web browser to open..."
}
```

### 2. Usuario Completa Login

El usuario abre `verification_uri` en su navegador e ingresa el `user_code`.

### 3. Verificar Token (Polling)

Ejecutar cada 5 segundos:

```bash
curl -X POST http://localhost:9000/api/oauth/device-code/poll \
  -H "Content-Type: application/json" \
  -d '{
    "device_code": "ABC123...",
    "tenant_id": "3af2e132-c361-4467-9d8b-081f06630c12"
  }'
```

**Response (esperando):**
```json
{
  "status": "pending",
  "message": "Esperando que el usuario complete la autenticación..."
}
```

**Response (exitoso):**
```json
{
  "status": "success",
  "message": "Autenticación completada exitosamente",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "0.AX0...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

### 4. Cancelar Flujo

```bash
curl -X DELETE http://localhost:9000/api/oauth/device-code/cancel \
  -H "Content-Type: application/json" \
  -d '{
    "device_code": "ABC123...",
    "tenant_id": "3af2e132-c361-4467-9d8b-081f06630c12"
  }'
```

---

## 📊 Permisos Solicitados

Al autenticarse, se solicitan los siguientes permisos de Microsoft Graph:

| Permiso | Descripción | Necesario Para |
|---------|-------------|----------------|
| **User.Read** | Leer perfil básico | Identificación del usuario |
| **AuditLog.Read.All** | Leer logs de auditoría | Análisis M365, Sparrow |
| **IdentityRiskEvent.Read.All** | Leer eventos de riesgo | Identity Protection |
| **Directory.Read.All** | Leer directorio completo | Usuarios, grupos, apps |

**Nota**: Estos permisos requieren consentimiento de administrador en Azure AD.

---

## 🔐 Almacenamiento del Token

### En el Dashboard (LocalStorage)

Los tokens se guardan en el navegador:

```javascript
localStorage.setItem('azure_token_{tenant_id}', access_token);
localStorage.setItem('azure_refresh_{tenant_id}', refresh_token);
```

**Beneficios:**
- ✅ No se envía el token al servidor innecesariamente
- ✅ Persiste entre recargas del navegador
- ✅ Cada tenant tiene su propio token

**Nota**: El token expira en 1 hora. Se puede renovar con el refresh token.

### Usar el Token en Requests

```javascript
const token = localStorage.getItem(`azure_token_${tenantId}`);

fetch('/forensics/m365/analyze', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ tenant_id: tenantId })
});
```

---

## 🛠️ Tenant Restaurado

El tenant **SINERLEX DOMINICANA** ha sido restaurado con:

- **Tenant ID**: `3af2e132-c361-4467-9d8b-081f06630c12`
- **Dominio**: `sinerlexrd.onmicrosoft.com`
- **Estado**: `active`
- **Auth Method**: Device Code Flow (OAuth 2.0)

---

## 📱 Flujo Visual

```
┌─────────────────┐
│   Dashboard     │
│  (Click Login)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Select Tenant  │
│  SINERLEX DOM   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌────────────────────┐
│ Initiate OAuth  │────▶│ Azure AD Endpoint  │
│ POST /device-   │     │ Device Code Flow   │
│      code/init  │◀────│ Returns code       │
└────────┬────────┘     └────────────────────┘
         │
         ▼
┌─────────────────┐
│ Show User Code  │
│  ABC12-DEF      │
│ + URL to visit  │
└────────┬────────┘
         │
         ├─────────────────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌────────────────────┐
│ User Opens URL  │      │ App Polls Every    │
│ in Browser      │      │ 5 seconds          │
│                 │      │ POST /device-code/ │
│ Enters Code     │      │      poll          │
│ Logs in (MFA)   │      └────────┬───────────┘
│ Accepts Perms   │               │
└────────┬────────┘               │
         │                         │
         │        status:          │
         │        pending ◀────────┤
         │                         │
         │        After login      │
         └────────────────────────▶│
                                   │
                  status: success  │
                  + access_token   │
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Save Token in   │
                          │ LocalStorage    │
                          │ Show Success    │
                          └─────────────────┘
```

---

## ⚡ Endpoints Disponibles

### OAuth Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/oauth/device-code/init` | Iniciar Device Code Flow |
| POST | `/api/oauth/device-code/poll` | Verificar si usuario completó auth |
| DELETE | `/api/oauth/device-code/cancel` | Cancelar flujo de autenticación |
| GET | `/api/oauth/status` | Estado del servicio OAuth |

### Documentación API

- **Swagger UI**: http://localhost:9000/docs
- **ReDoc**: http://localhost:9000/redoc

---

## 🧪 Testing

### 1. Verificar Servicio OAuth

```bash
curl http://localhost:9000/api/oauth/status
```

Debe retornar:
```json
{
  "status": "operational",
  "msal_installed": true,
  "active_device_flows": 0,
  "supported_flows": ["device_code"]
}
```

### 2. Test Completo desde Dashboard

1. Abre dashboard
2. Click "Login OAuth"
3. Selecciona tenant
4. Click "Iniciar Autenticación"
5. Abre el enlace en navegador
6. Ingresa código
7. Completa login (usuario + MFA si aplica)
8. Verifica éxito en dashboard

---

## 🚨 Troubleshooting

### "MSAL library not installed"
```bash
pip3 install msal --break-system-packages
```

### "Device code not found or expired"
El código expira en 15 minutos. Inicia el flujo nuevamente.

### "Authorization pending timeout"
Verifica que ingresaste el código correcto en https://microsoft.com/devicelogin

### "Invalid scopes"
Verifica que el tenant tenga los permisos necesarios configurados en Azure AD Portal.

### "Token expired"
El access token expira en 1 hora. Usa el refresh token para renovarlo.

---

## 📚 Referencias

- [Microsoft Device Code Flow](https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-device-code)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Microsoft Graph Permissions](https://learn.microsoft.com/graph/permissions-reference)

---

**Última Actualización**: 2024-12-05  
**Versión**: 1.0.0  
**Estado**: ✅ Operacional
