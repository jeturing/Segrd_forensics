# Referencia de Herramientas M365 Forensics

## 🔵 BÁSICO (Esenciales)

### 🦅 Sparrow
- **Descripción**: Detección de tokens abusados y apps OAuth maliciosas
- **Uso**: Análisis de Azure AD para detectar compromisos
- **Instalado**: `/opt/forensics-tools/Sparrow`
- **Comando**: `pwsh -File Sparrow.ps1 -TenantId <id>`

### 🦅 Hawk
- **Descripción**: Reglas maliciosas, delegaciones y Teams
- **Uso**: Investigación forense de Exchange Online
- **Instalado**: `/opt/forensics-tools/hawk`
- **Comando**: `Start-HawkTenantInvestigation`

### 📦 O365
- **Descripción**: Unified Audit Logs completos
- **Uso**: Extracción masiva de logs de auditoría
- **Instalado**: `/opt/forensics-tools/sra-o365-extractor`
- **Comando**: `python3 o365-extractor.py`

---

## 🔍 RECONOCIMIENTO

### 📍 AzureHound
- **Descripción**: Attack paths en Azure AD (BloodHound)
- **Uso**: Mapeo de rutas de ataque y privilegios
- **Instalado**: `/opt/forensics-tools/azurehound`
- **Comando**: `./azurehound list --tenant <id>`
- **Web**: https://github.com/BloodHoundAD/AzureHound

### 🗺️ ROADtools
- **Descripción**: Reconocimiento completo de Azure AD
- **Uso**: Enumeración de objetos y permisos
- **Comando**: `roadrecon auth`, `roadrecon gather`
- **Web**: https://github.com/dirkjanm/ROADtools

### 🔓 AADInternals
- **Descripción**: Penetration testing Azure AD (Red Team)
- **Uso**: Ataques avanzados y pivoting
- **Comando**: `Import-Module AADInternals`
- **Web**: https://github.com/Gerenios/AADInternals

---

## 📊 AUDITORÍA

### 🐵 Monkey365
- **Descripción**: 300+ checks de seguridad M365
- **Uso**: Auditoría automatizada de configuración
- **Instalado**: `/opt/forensics-tools/monkey365`
- **Comando**: `Invoke-Monkey365 -TenantId <id>`
- **Web**: https://github.com/silverhack/monkey365

### 🦅 CrowdStrike CRT
- **Descripción**: Análisis de riesgos Azure/M365
- **Uso**: Detección de configuraciones inseguras
- **Instalado**: `/opt/forensics-tools/crt`
- **Web**: https://github.com/CrowdStrike/CRT

### 🎯 Maester
- **Descripción**: Security testing framework M365
- **Uso**: Tests automatizados de compliance
- **Instalado**: `/opt/forensics-tools/maester`
- **Comando**: `Invoke-Maester`
- **Web**: https://github.com/maester365/maester

---

## 🔬 FORENSE

### 📦 M365
- **Descripción**: Extracción forense Exchange/Teams/OneDrive
- **Uso**: Análisis profundo de evidencia digital
- **Instalado**: `/opt/forensics-tools/Microsoft-Extractor-Suite`
- **Comando**: `Get-UALAll`, `Get-MailboxAuditLog`
- **Web**: https://github.com/invictus-ir/Microsoft-Extractor-Suite

### 📈 Graph
- **Descripción**: Queries custom a Microsoft Graph API
- **Uso**: Consultas avanzadas programáticas
- **Comando**: `python3` con `msgraph-sdk`
- **Docs**: https://learn.microsoft.com/graph/api/overview

### ⚔️ Cloud
- **Descripción**: Automation de respuesta a incidentes
- **Uso**: Playbooks automatizados de IR
- **Instalado**: `/opt/forensics-tools/cloud-katana`
- **Web**: https://github.com/Azure/Cloud-Katana

---

## 🚀 Instalación Rápida

```bash
# Verificar herramientas instaladas
./scripts/verify_tools.sh

# Instalar todas las herramientas
sudo ./scripts/install.sh

# Solo herramientas M365 avanzadas
sudo ./scripts/install_m365_tools.sh
```

## 📋 Verificación de Estado

```bash
# Estado de herramientas básicas
ls -la /opt/forensics-tools/

# Verificar módulos PowerShell
pwsh -Command "Get-Module -ListAvailable | Where-Object {$_.Name -match 'AAD|Azure|Graph|Maester'}"

# Verificar paquetes Python
pip3 list | grep -E "road|msgraph|azure"
```

## 🔧 Permisos Requeridos

### Azure AD App Registration
- **AuditLog.Read.All**
- **Directory.Read.All**
- **IdentityRiskEvent.Read.All**
- **User.Read.All**
- **SecurityEvents.Read.All**
- **ThreatIndicators.Read.All**

### Exchange Online
- **ApplicationImpersonation**
- **View-Only Audit Logs**

### Microsoft Graph
- **Mail.Read**
- **Files.Read.All**
- **Sites.Read.All**

---

## 📚 Referencias

- [MCP Kali Forensics Docs](../README.md)
- [M365 Setup Guide](./M365_SETUP.md)
- [Advanced Tools Guide](./M365_ADVANCED_TOOLS.md)
