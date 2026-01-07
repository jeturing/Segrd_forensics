
$ErrorActionPreference = 'Continue'
Import-Module "/home/hack/mcp-kali-forensics/tools/Monkey365/monkey365.psd1" -Force

$options = @{
    Instance = 'Microsoft365'
    ExportTo = 'HTML'
    OutputDir = '/home/hack/mcp-kali-forensics/forensics-evidence/monkey365_scans/scan_20251208_113430_security_assessment'
    IncludeEntraID = $true
    PromptBehavior = 'Auto'
}

# Collectors específicos


try {
    Invoke-Monkey365 @options
    Write-Output "SCAN_COMPLETED_SUCCESSFULLY"
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
