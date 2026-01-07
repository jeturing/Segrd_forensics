# 🦅 HERRAMIENTAS BÁSICAS - MCP Kali Forensics

## Descripción General

Conjunto de herramientas fundamentales para análisis de amenazas en Microsoft 365, recolección de logs y análisis de permisos OAuth.

---

## 1. Sparrow 365

**Propósito**: Análisis de tokens abusados y aplicaciones OAuth maliciosas

**Ubicación**: `tools/Sparrow/`

**URL**: https://github.com/cisagov/Sparrow

**Características**:
- Detección de aplicaciones OAuth sospechosas
- Análisis de tokens comprometidos
- Auditoría de aplicaciones de terceros
- Identificación de permisos anormales
- Generación de reportes en HTML/CSV

### Uso Básico

```powershell
cd tools/Sparrow
./Sparrow.ps1 -TenantId "your-tenant-id" -DaysToSearch 90 -OutputPath "./results"
```

### Parámetros Principales

| Parámetro | Descripción |
|-----------|-------------|
| `-TenantId` | ID del tenant Azure AD |
| `-DaysToSearch` | Días históricos a analizar |
| `-OutputPath` | Directorio de salida |
| `-AppId` | ID de aplicación específica |
| `-UserPrincipalName` | Usuario específico |

### Salida

- CSV con aplicaciones OAuth detectadas
- Reportes HTML interactivos
- Archivos de auditoría

---

## 2. Hawk

**Propósito**: Detección de reglas maliciosas, delegaciones peligrosas y anomalías en Teams

**Ubicación**: `tools/hawk/`

**URL**: https://github.com/OneMoreNicolas/hawk

**Características**:
- Análisis de reglas de correo (forwarding, etc)
- Detección de delegaciones de buzones
- Análisis de Teams y permisos de canales
- Identificación de permisos delegados
- Reporte de cambios sospechosos

### Uso Básico

```powershell
cd tools/hawk
./hawk.ps1 -TenantId "your-tenant-id" -UserEmail "user@domain.com"
```

### Análisis Disponibles

- Reglas de bandeja de entrada
- Delegaciones de buzones
- Permisos de carpetas compartidas
- Configuración de Teams
- Reenvíos de correo

---

## 3. O365 Extractor / PnP PowerShell

**Propósito**: Extracción de Unified Audit Logs completos de Office 365

**Ubicación**: `tools/o365-extractor/` o `tools/PnP-PowerShell/`

**URL**: https://github.com/pnp/powershell

**Características**:
- Búsqueda en Unified Audit Log (UAL)
- Exportación completa de auditoría
- Filtrado por tipo de evento
- Exportación a JSON/CSV
- Soporte para logs históricos

### Uso Básico

```powershell
# Conectar a PnP PowerShell
Connect-PnPOnline -Url "https://tenant.sharepoint.com"

# Buscar eventos de auditoría
Search-UnifiedAuditLog -StartDate (Get-Date).AddDays(-90) -EndDate (Get-Date) `
    -RecordType ExchangeAdmin -ResultSize 5000 | Export-Csv "audit_logs.csv"
```

### Eventos Auditables

- ExchangeAdmin - Cambios en buzones
- SharePointFileOperation - Cambios en SharePoint
- TeamsLogging - Actividades de Teams
- AzureActiveDirectorySignInEvents - Logins

---

## 📊 Resumen Comparativo

| Tool | Enfoque | Salida | Requisitos |
|------|---------|--------|------------|
| **Sparrow** | OAuth/Apps | HTML/CSV | Tenant ID |
| **Hawk** | Reglas/Delegaciones | CSV | Credenciales admin |
| **PnP PowerShell** | Audit Logs | JSON/CSV | Conexión SPO |

---

## 🔐 Permisos Requeridos

Todos los tools requieren:
- ✓ Tenant Admin
- ✓ Global Admin o Security Admin
- ✓ ExchangeOnlineManagement módulo (Hawk, PnP)

---

## 📝 Casos de Uso

### Caso 1: Investigar Tokens Comprometidos
1. Ejecutar Sparrow para detectar aplicaciones sospechosas
2. Usar PnP PowerShell para extraer logs de uso
3. Correlacionar con Hawk para delegaciones anormales

### Caso 2: Investigar Forwarding Malicioso
1. Ejecutar Hawk para encontrar reglas de reenvío
2. Extraer logs de auditoría con PnP PowerShell
3. Generar reporte de cambios sospechosos

### Caso 3: Auditoría de Seguridad Completa
1. Sparrow: Aplicaciones no autorizadas
2. Hawk: Configuraciones peligrosas
3. PnP: Logs de cambios administrativos

---

## 🚨 Indicadores de Compromiso (IOCs)

### En Sparrow
- [ ] Aplicaciones OAuth con permisos de admin
- [ ] Apps no reconocidas accediendo a correo
- [ ] Tokens con actividad fuera de horario

### En Hawk
- [ ] Reenvíos a dominios externos
- [ ] Delegaciones de buzones no autorizadas
- [ ] Cambios rápidos de configuración

### En PnP PowerShell
- [ ] Cambios de contraseña masivos
- [ ] Creación de cuentas admin
- [ ] Eliminación de logs de auditoría

---

## 🔗 Integración con MCP

```python
# api/services/forensics.py

async def analyze_oauth_threats(case_id: str, tenant_id: str):
    """Usar Sparrow para análisis de OAuth"""
    result = await run_tool("Sparrow", args=[
        "-TenantId", tenant_id,
        "-OutputPath", f"evidence/{case_id}/sparrow"
    ])
    return result

async def analyze_mailbox_threats(case_id: str, user_email: str):
    """Usar Hawk para análisis de buzones"""
    result = await run_tool("Hawk", args=[
        "-UserEmail", user_email,
        "-OutputPath", f"evidence/{case_id}/hawk"
    ])
    return result

async def extract_audit_logs(case_id: str, days: int = 90):
    """Extraer logs con PnP PowerShell"""
    result = await run_tool("PnP-PowerShell", args=[
        "-Operation", "SearchAuditLog",
        "-Days", str(days),
        "-OutputPath", f"evidence/{case_id}/audit"
    ])
    return result
```

---

## 📚 Referencias

- [Sparrow Documentation](https://github.com/cisagov/Sparrow/wiki)
- [Hawk GitHub](https://github.com/OneMoreNicolas/hawk)
- [PnP PowerShell Docs](https://pnp.github.io/powershell/)
- [Microsoft 365 Audit Log](https://docs.microsoft.com/en-us/microsoft-365/compliance/search-the-audit-log-in-security-and-compliance)

---

**Categoría**: BÁSICO  
**Status**: ✓ Documentado  
**Última Actualización**: 2025-12-07
