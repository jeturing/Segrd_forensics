# Script para agregar permisos de auditoría a la App Registration
# Ejecutar con: pwsh -File add_audit_permissions.ps1

param(
    [Parameter(Mandatory=$true)]
    [string]$TenantId,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientId
)

# Permisos de auditoría requeridos
$auditPermissions = @(
    # Azure AD Audit Logs
    "AuditLog.Read.All",
    # Sign-in logs
    "Directory.Read.All",
    # Security events
    "SecurityEvents.Read.All",
    # Identity Risk
    "IdentityRiskEvent.Read.All",
    "IdentityRiskyUser.Read.All",
    # Reports
    "Reports.Read.All"
)

Write-Host "📋 Permisos de auditoría requeridos para la App:" -ForegroundColor Cyan
foreach ($perm in $auditPermissions) {
    Write-Host "   ✓ $perm" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔧 Para agregar estos permisos:" -ForegroundColor Yellow
Write-Host "1. Ve a https://portal.azure.com" -ForegroundColor White
Write-Host "2. Azure Active Directory → App registrations" -ForegroundColor White
Write-Host "3. Selecciona la app: $ClientId" -ForegroundColor White
Write-Host "4. API permissions → Add a permission" -ForegroundColor White
Write-Host "5. Microsoft Graph → Application permissions" -ForegroundColor White
Write-Host "6. Busca y agrega cada permiso listado arriba" -ForegroundColor White
Write-Host "7. Grant admin consent" -ForegroundColor White
Write-Host ""
Write-Host "📌 Tenant ID: $TenantId" -ForegroundColor Magenta
Write-Host "📌 Client ID: $ClientId" -ForegroundColor Magenta
