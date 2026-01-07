# 🐕 HERRAMIENTAS DE RECONOCIMIENTO - MCP Kali Forensics

## Descripción General

Conjunto de herramientas especializadas en reconocimiento de la infraestructura Azure AD, mapeo de relaciones de confianza y análisis de ataque automatizado.

---

## 1. AzureHound

**Propósito**: Mapeo de attack paths con BloodHound para Azure

**Ubicación**: `tools/azurehound/`

**URL**: https://github.com/BloodHoundAD/AzureHound

**Características**:
- Mapeo automático de relaciones Azure AD
- Identificación de caminos de ataque
- Análisis de permisos RBAC
- Integración con BloodHound
- Visualización gráfica de activos
- Detección de misconfiguraciones

### Instalación

```bash
cd tools/azurehound
# Windows
./AzureHound.exe -TenantId "your-tenant-id" -OutputFile "azure_data.zip"

# Linux (si está disponible)
./azurehound -tenant-id "your-tenant-id" -output-file "azure_data.zip"
```

### Parámetros Principales

| Parámetro | Descripción |
|-----------|-------------|
| `-tenant-id` | ID del tenant |
| `-output-file` | Archivo de salida ZIP |
| `-refresh` | Incluir datos en tiempo real |
| `-scope` | Tipo de colección (users, groups, etc) |

### Salida BloodHound

```json
{
  "data": [
    {
      "name": "user@domain.com",
      "objectid": "AADXXXXXXX",
      "type": "User",
      "properties": {
        "name": "user@domain.com",
        "description": "Active user"
      }
    }
  ],
  "relationships": [
    {
      "source": "AADXXXXXXX",
      "target": "AADYYYYYYY",
      "relationship_type": "MemberOf"
    }
  ]
}
```

### Integración BloodHound

```bash
# 1. Exportar datos con AzureHound
./AzureHound.exe -output-file "azure.zip"

# 2. Importar en BloodHound
# Abrir BloodHound → Upload Data → Seleccionar azure.zip

# 3. Consultas útiles
# - Shortest paths to admin
# - Identidades críticas
# - Permisos no utilizados
```

---

## 2. ROADtools

**Propósito**: Reconocimiento completo de Azure AD con herramientas específicas

**Ubicación**: `tools/ROADtools/`

**URL**: https://github.com/dirkjanm/ROADtools

**Características**:
- Enumeración completa de Azure AD
- Análisis de objetos y relaciones
- Búsqueda de información sensible
- Mapping de infraestructura
- Detección de configuraciones inseguras
- Database local para análisis offline

### Instalación

```bash
cd tools/ROADtools
pip install -r requirements.txt
```

### Uso Básico

```bash
# 1. Conectar y descargar datos
python roadrecon.py -u user@domain.com -p password

# 2. Analizar datos localmente
python roadrecon.py -o -d ROADdata

# 3. Iniciar servidor web
python roadrecon_server.py

# 4. Acceder a interfaz web
# http://localhost:5000
```

### Módulos Disponibles

| Módulo | Función |
|--------|---------|
| `roadrecon` | Recolección de datos |
| `roadrecon_server` | Interfaz web |
| `roadhunter` | Búsqueda de secrets |
| `roadrecon_rw` | Lectura/escritura |

### Queries Útiles

```sql
-- Usuarios con privilegios críticos
SELECT displayName, userPrincipalName FROM users 
WHERE assigned_licenses LIKE '%admin%'

-- Aplicaciones de terceros
SELECT displayName, publisherName FROM applications
WHERE isFirstPartyApp = 0

-- Grupos de seguridad peligrosos
SELECT displayName, members 
FROM groups 
WHERE displayName LIKE '%admin%'
```

---

## 3. AADInternals

**Propósito**: Red Team toolkit para Azure AD con capacidades avanzadas

**Ubicación**: `tools/AADInternals/`

**URL**: https://github.com/Gerenios/AADInternals

**Características**:
- Recolección de información sin autenticación
- Enumeración de usuarios
- Análisis de configuración de tenant
- Identidad federada
- Attack simulation
- Exploitation de misconfiguraciones

### Instalación PowerShell

```powershell
cd tools/AADInternals

# Opción 1: Instalar como módulo
Import-Module .\AADInternals.psd1

# Opción 2: Ejecutar funciones
. .\AADInternals.ps1
```

### Funciones Principales

```powershell
# 1. Reconocimiento sin autenticación
Get-AADIntTenantDetails -Domain "domain.com"

# 2. Enumeración de usuarios
Get-AADIntUsers -UserName "admin@domain.com" -Method Normal

# 3. Análisis de configuración
Get-AADIntTenantConfiguration -Domain "domain.com"

# 4. Obtener información de aplicaciones
Get-AADIntApplications

# 5. Descargar configuración de seguridad
Get-AADIntTenantSecurityConfiguration
```

### Técnicas de Ataque

| Técnica | Descripción |
|---------|------------|
| **User Enumeration** | Identificar usuarios válidos |
| **Tenant Enumeration** | Mapear configuración del tenant |
| **Desync Attack** | Sincronización de AD-Azure AD |
| **Oauth Phishing** | Phishing de OAuth tokens |
| **MFA Bypass** | Evasión de autenticación |

### Resultado de Scan Típico

```
Tenant Details:
  - Tenant ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  - Tenant Name: company.onmicrosoft.com
  - Domain Type: Managed
  - MFA Status: Enabled

Users Found:
  - Total: 245
  - Admin users: 12
  - Guests: 3

Security Configuration:
  - Password Policy: Standard
  - MFA: Enabled for admins
  - Conditional Access: 5 policies
  - DLP: Enabled
```

---

## 📊 Comparativa de Reconocimiento

| Tool | Métodos | Output | Offline |
|------|---------|--------|---------|
| **AzureHound** | Con auth | JSON/BloodHound | Sí |
| **ROADtools** | Con auth | Web UI/SQL | Sí |
| **AADInternals** | Sin auth | Consola | No |

---

## 🔄 Flujo de Reconocimiento Recomendado

```
1. AADInternals (Sin autenticación)
   ├─ Enumeración de dominios
   ├─ Detección de usuarios
   └─ Análisis de tenant

2. AzureHound (Con credenciales)
   ├─ Mapeo de permisos
   ├─ Relaciones de confianza
   └─ Exportar para BloodHound

3. ROADtools (Base de datos)
   ├─ Análisis detallado
   ├─ Queries personalizadas
   └─ Offline analysis
```

---

## 🎯 Casos de Uso

### Caso 1: Auditoría de Seguridad Azure AD
1. Ejecutar AADInternals para detección sin auth
2. Usar AzureHound con credenciales admin
3. Importar en BloodHound para visualización
4. ROADtools para análisis detallado

### Caso 2: Mapeo de Activos
1. AzureHound: Recolectar toda la información
2. ROADtools: Base de datos para queries
3. Análisis: Identidades críticas y permisos

### Caso 3: Detección de Misconfiguraciones
1. AADInternals: Búsqueda inicial
2. AzureHound: Mapeo de permisos mal configurados
3. ROADtools: Identificar patrones de riesgo

---

## 🚨 Indicadores de Riesgo Detectables

### En AzureHound
- [ ] Usuarios con privilegios excesivos
- [ ] Caminos de ataque directos a admin
- [ ] Aplicaciones con permisos críticos
- [ ] Grupos de seguridad peligrosos

### En ROADtools
- [ ] Usuarios inactivos con privilegios
- [ ] Licencias de aplicación no utilizadas
- [ ] Configuraciones de seguridad débiles
- [ ] Objetos huérfanos

### En AADInternals
- [ ] Tenant enumerable sin autenticación
- [ ] Usuarios enumerables
- [ ] Configuración de federación débil
- [ ] MFA no requerido

---

## 🔗 Integración con MCP

```python
async def map_azure_infrastructure(case_id: str, tenant_id: str):
    """Mapear infraestructura con AzureHound"""
    result = await run_tool("AzureHound", args=[
        "-tenant-id", tenant_id,
        "-output-file", f"evidence/{case_id}/azurehound.zip"
    ])
    return result

async def enumerate_with_road(case_id: str):
    """Enumeración con ROADtools"""
    result = await run_tool("ROADtools", args=[
        "-output", f"evidence/{case_id}/roaddata"
    ])
    return result

async def reconnaissance_aad(case_id: str, domain: str):
    """Reconocimiento sin autenticación"""
    result = await run_tool("AADInternals", args=[
        "-domain", domain,
        "-enumerate"
    ])
    return result
```

---

## 📚 Referencias

- [AzureHound Documentation](https://github.com/BloodHoundAD/AzureHound/wiki)
- [ROADtools GitHub](https://github.com/dirkjanm/ROADtools)
- [AADInternals Functions](https://github.com/Gerenios/AADInternals/wiki)
- [BloodHound Enterprise](https://bloodhoundenterprise.io/)

---

**Categoría**: RECONOCIMIENTO  
**Status**: ✓ Documentado  
**Última Actualización**: 2025-12-07
