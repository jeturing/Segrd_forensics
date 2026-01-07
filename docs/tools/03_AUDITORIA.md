# 🐵 HERRAMIENTAS DE AUDITORÍA - MCP Kali Forensics

## Descripción General

Conjunto de herramientas para auditoría de seguridad, compliance y evaluación de configuración en Microsoft 365.

---

## 1. Monkey365

**Propósito**: 300+ checks de seguridad automatizados para M365

**Ubicación**: `tools/Monkey365/`

**URL**: https://github.com/silverhack/monkey365

**Características**:
- 300+ controles de seguridad
- Evaluación de configuración
- Mapeo a frameworks (CIS, NIST, ISO)
- Reporting detallado
- Remediación automática
- Soporte para multi-tenant

### Instalación

```bash
cd tools/Monkey365
pip install -r requirements.txt
```

### Uso Básico

```bash
# 1. Escanear todo el tenant
python monkey365.py -TenantId "your-tenant-id" -IncludeAll

# 2. Escanear servicios específicos
python monkey365.py -TenantId "your-tenant-id" -Services Exchange,Teams,SharePoint

# 3. Escanear solo configuración de seguridad
python monkey365.py -TenantId "your-tenant-id" -Categories Security

# 4. Generar reporte
python monkey365.py -TenantId "your-tenant-id" -Report "html" -OutputPath "./reports"
```

### Controles Disponibles

| Categoría | Controles | Ejemplos |
|-----------|-----------|----------|
| **Exchange** | ~40 | MFA, DLP, Anti-spam |
| **Teams** | ~25 | Seguridad de canales, Guests |
| **SharePoint** | ~35 | Permisos, External sharing |
| **Entra ID** | ~50 | Passwords, Conditional Access |
| **M365 General** | ~150+ | Auditoría, Compliance |

### Formato de Salida

```json
{
  "checks": [
    {
      "id": "M365-001",
      "name": "MFA enabled for all users",
      "service": "Exchange",
      "category": "Authentication",
      "result": "FAIL",
      "severity": "CRITICAL",
      "evidence": {
        "total_users": 250,
        "mfa_enabled": 240,
        "mfa_disabled": 10
      },
      "remediation": "Enable MFA for all users"
    }
  ]
}
```

### Dashboard Web

```bash
# Iniciar servidor web
python monkey365_server.py --port 8000

# Acceder a dashboard
# http://localhost:8000/dashboard
```

---

## 2. Maester

**Propósito**: Security testing framework para M365 con automatización

**Ubicación**: `tools/Maester/`

**URL**: https://github.com/maester365/maester

**Características**:
- Framework de testing de seguridad
- Tests basados en Pester (PowerShell)
- Integración CI/CD
- Reporting automático
- Remediación con Terraform
- Configuración como código

### Instalación

```powershell
cd tools/Maester

# Requisitos
Install-Module Microsoft.Graph -Force
Install-Module Pester -MinimumVersion 5.0 -Force

# Instalar Maester
Import-Module .\Maester.psd1
```

### Estructura de Tests

```powershell
# tests/eidsca/Entra-4.1.ps1
Describe "EIDSCA_4.1 Microsoft Entra - External Users" {
    Test-MaesterRule -Id "eidsca-4.1" -Description "Ensure external users can be invited" {
        # Verificar configuración
        $invitationSettings = Get-MgPolicyAuthorizationPolicy
        $invitationSettings.allowedToSignUpEmailBasedSubscriptions | Should -Be $true
    }
}
```

### Tests Disponibles

| Test | Descripción |
|------|-------------|
| EIDSCA | Entra ID Security Configuration |
| MEEECA | Exchange Online Configuration |
| SPO | SharePoint Online Configuration |
| TEAMS | Teams Configuration |
| M365DEF | Defender Configuration |

### Ejecución de Tests

```powershell
# Ejecutar todos los tests
Invoke-Pester -Path ".\tests" -Output Detailed

# Ejecutar tests específicos
Invoke-Pester -Path ".\tests\eidsca" -Output Detailed

# Generar reporte JSON
Invoke-Pester -Path ".\tests" -OutputFile "results.json" -OutputFormat NunitXml
```

---

## 3. PnP PowerShell (Auditoría)

**Propósito**: Herramienta universal para auditoría de SharePoint, Teams y OneDrive

**Ubicación**: `tools/PnP-PowerShell/`

**URL**: https://github.com/pnp/powershell

**Características**:
- Auditoría de SharePoint/OneDrive
- Análisis de permisos
- Reporte de configuración
- Automatización de compliance
- Gestión de gobernanza
- Backup y restauración

### Instalación

```powershell
# Instalar PnP PowerShell
Install-Module PnP.PowerShell -Force

# O desde el repositorio
cd tools/PnP-PowerShell
Import-Module ./PnP.PowerShell.psd1
```

### Auditorías Comunes

```powershell
# 1. Auditar permisos de SharePoint
$sites = Get-PnPTenantSite
foreach($site in $sites) {
    Connect-PnPOnline -Url $site.Url
    
    $lists = Get-PnPList
    foreach($list in $lists) {
        Get-PnPListRoleAssignment -List $list.Title
    }
}

# 2. Auditar external sharing
$sites | ForEach-Object {
    $sharing = Get-PnPSiteInformationlist -Identity $_.Url
    [PSCustomObject]@{
        Site = $_.Title
        ExternalSharing = $sharing.SharingCapability
        SharingDomains = $sharing.RestrictedDomains
    }
}

# 3. Auditar OneDrive
$users = Get-MgUser -Filter "userType eq 'Member'"
$users | ForEach-Object {
    $onedrive = Get-PnPUserProfileProperty -Account $_.UserPrincipalName
    [PSCustomObject]@{
        User = $_.UserPrincipalName
        OneDriveUrl = $onedrive.PersonalUrl
        QuotaUsed = $onedrive.PersonalSpace
    }
}

# 4. Auditar Teams
$teams = Get-PnPTeamsTeam
$teams | ForEach-Object {
    $members = Get-PnPTeamsTeamMembers -Identity $_.Id
    [PSCustomObject]@{
        Team = $_.DisplayName
        MemberCount = $members.Count
        Owners = ($members | Where-Object {$_.Roles -contains "Owner"}).Count
    }
}
```

### Reportes Personalizados

```powershell
# Generar reporte de compliance
$report = @()

Get-PnPTenantSite | ForEach-Object {
    $site = $_
    Connect-PnPOnline -Url $site.Url
    
    $report += [PSCustomObject]@{
        SiteName = $site.Title
        Url = $site.Url
        Owner = $site.Owner
        ExternalSharing = $site.SharingCapability
        LastModified = $site.LastContentModifiedTime
        Status = $site.Status
    }
}

$report | Export-Csv "compliance_report.csv" -NoTypeInformation
```

---

## 📊 Comparativa de Auditoría

| Tool | Controles | Formato | Automatización |
|------|-----------|---------|----------------|
| **Monkey365** | 300+ | JSON/HTML | ✓ Completa |
| **Maester** | 100+ | Pester/JSON | ✓ CI/CD |
| **PnP** | Custom | PowerShell | ✓ Scripts |

---

## 🔄 Flujo de Auditoría Recomendado

```
1. Monkey365 (Escaneo rápido)
   ├─ 300+ controles automáticos
   ├─ Identificar riesgos críticos
   └─ Generar report ejecutivo

2. Maester (Testing detallado)
   ├─ Validar configuración
   ├─ Tests de compliance
   └─ Generación de evidencia

3. PnP PowerShell (Custom audits)
   ├─ Auditorías específicas
   ├─ Análisis granular
   └─ Remediación
```

---

## 🎯 Casos de Uso

### Caso 1: Auditoría de Compliance
1. Ejecutar Monkey365: Escaneo inicial
2. Maester: Validar controles críticos
3. PnP: Reportes detallados por servicio

### Caso 2: Evaluación de Seguridad
1. Monkey365: Identificar riesgos
2. Maester: Validar mitigaciones
3. Crear playbook de remediación

### Caso 3: Auditoría de Gobernanza
1. PnP PowerShell: Mapear permisos
2. Monkey365: Verificar configuración
3. Generar reporte de governance

---

## 🚨 Hallazgos Comunes

### Críticos (CRITICAL)
- [ ] MFA no habilitado en cuentas admin
- [ ] External sharing sin restricciones
- [ ] Auditoría deshabilitada
- [ ] DLP no configurada

### Altos (HIGH)
- [ ] Passwords sin expiración
- [ ] Guest users con permisos excesivos
- [ ] Forwarding de correo sin control
- [ ] Backup no configurado

### Medios (MEDIUM)
- [ ] Configuración de TLS débil
- [ ] Alertas de seguridad no configuradas
- [ ] Roles con permisos no utilizados

---

## 🔗 Integración con MCP

```python
async def run_security_audit(case_id: str, tenant_id: str):
    """Ejecutar auditoría completa de seguridad"""
    
    # 1. Monkey365: Escaneo rápido
    monkey_results = await run_tool("Monkey365", args=[
        "-TenantId", tenant_id,
        "-Report", "json",
        "-OutputPath", f"evidence/{case_id}/monkey365"
    ])
    
    # 2. Maester: Testing detallado
    maester_results = await run_tool("Maester", args=[
        "-TenantId", tenant_id,
        "-OutputPath", f"evidence/{case_id}/maester"
    ])
    
    # 3. Correlacionar hallazgos
    findings = correlate_findings(monkey_results, maester_results)
    
    return findings

async def generate_compliance_report(case_id: str):
    """Generar reporte de compliance"""
    
    audit_logs = await extract_audit_logs(case_id)
    
    report = {
        "case_id": case_id,
        "audit_date": datetime.now().isoformat(),
        "findings": audit_logs,
        "recommendations": generate_recommendations(audit_logs)
    }
    
    return report
```

---

## 📚 Referencias

- [Monkey365 GitHub](https://github.com/silverhack/monkey365)
- [Maester Documentation](https://github.com/maester365/maester/wiki)
- [PnP PowerShell Docs](https://pnp.github.io/powershell/)
- [Microsoft Security Best Practices](https://docs.microsoft.com/en-us/microsoft-365/security)

---

**Categoría**: AUDITORÍA  
**Status**: ✓ Documentado  
**Última Actualización**: 2025-12-07
