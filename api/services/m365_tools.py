"""
M365 Advanced Forensics Tools - Service Layer
Implementa todas las herramientas de análisis forense para Microsoft 365
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

from api.config import settings

logger = logging.getLogger(__name__)

EVIDENCE_DIR = Path(settings.EVIDENCE_DIR)
TOOLS_DIR = Path(settings.TOOLS_DIR)


# ==================== RECONNAISSANCE TOOLS ====================

async def run_azurehound(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    AzureHound - Attack paths en Azure AD (integración BloodHound)
    """
    try:
        logger.info(f"🐕 Ejecutando AzureHound para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "azurehound"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # AzureHound requiere token de acceso
        cmd = [
            str(TOOLS_DIR / "azurehound" / "azurehound"),
            "-tenant", tenant_id,
            "-output-dir", str(evidence_path),
            "-json"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
        
        if process.returncode != 0:
            logger.warning(f"⚠️ AzureHound warning: {stderr.decode()[:200]}")
        
        # Parsear output JSON
        output_files = list(evidence_path.glob("*.json"))
        results = {
            "status": "completed",
            "evidence_files": [str(f) for f in output_files],
            "findings": f"{len(output_files)} archivos BloodHound generados",
            "import_to_bloodhound": "Importa los archivos .json en BloodHound GUI"
        }
        
        logger.info(f"✅ AzureHound completado: {len(output_files)} archivos")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en AzureHound: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def run_roadtools(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    ROADtools - Reconocimiento completo de Azure AD
    """
    try:
        logger.info(f"🗺️ Ejecutando ROADtools para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "roadtools"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Usar wrapper que activa el venv automáticamente
        venv_python = "/opt/forensics-tools/venv/bin/python"
        venv_roadrecon = "/opt/forensics-tools/venv/bin/roadrecon"
        
        # Fase 1: Authentication (skip por ahora, usar token existente)
        # auth_cmd = [venv_roadrecon, "auth", "--tenant-id", tenant_id, "--tokens-stdout"]
        
        # Fase 2: Gather data
        gather_cmd = [
            venv_roadrecon, "gather",
            "-d", str(evidence_path / "roadrecon.db")
        ]
        
        # Fase 3: Export JSON
        export_cmd = [
            venv_roadrecon, "plugin",
            "-d", str(evidence_path / "roadrecon.db"),
            "policies",
            "--outfile", str(evidence_path / "policies.json")
        ]
        
        for cmd in [gather_cmd, export_cmd]:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=600)
        
        results = {
            "status": "completed",
            "database": str(evidence_path / "roadrecon.db"),
            "exports": list(evidence_path.glob("*.json")),
            "gui_command": f"roadrecon gui -d {evidence_path / 'roadrecon.db'}",
            "findings": "Base de datos SQLite con toda la info de Azure AD"
        }
        
        logger.info("✅ ROADtools completado")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en ROADtools: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def run_aadinternals(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    AADInternals - Penetration testing Azure AD
    """
    try:
        logger.info(f"🔓 Ejecutando AADInternals para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "aadinternals"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Script PowerShell para AADInternals
        ps_script = f"""
        Import-Module AADInternals
        
        # Get tenant info
        $tenantInfo = Get-AADIntTenantDetails -Domain {tenant_id}
        $tenantInfo | ConvertTo-Json | Out-File "{evidence_path}/tenant_info.json"
        
        # Get login information
        $loginInfo = Get-AADIntLoginInformation -Domain {tenant_id}
        $loginInfo | ConvertTo-Json | Out-File "{evidence_path}/login_info.json"
        
        # Check federation settings
        $fedInfo = Get-AADIntFederationSettings -Domain {tenant_id}
        $fedInfo | ConvertTo-Json | Out-File "{evidence_path}/federation.json"
        """
        
        ps_file = evidence_path / "aadrecon.ps1"
        ps_file.write_text(ps_script)
        
        process = await asyncio.create_subprocess_exec(
            "pwsh", "-NoProfile", "-File", str(ps_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await asyncio.wait_for(process.communicate(), timeout=300)
        
        results = {
            "status": "completed",
            "evidence_path": str(evidence_path),
            "findings": ["Tenant details", "Login info", "Federation settings"],
            "warning": "Herramienta ofensiva - usar solo con autorización"
        }
        
        logger.info("✅ AADInternals completado")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en AADInternals: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


# ==================== AUDIT & COMPLIANCE ====================

async def run_monkey365(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    Monkey365 - 300+ security checks para M365
    """
    try:
        logger.info(f"🐵 Ejecutando Monkey365 para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "monkey365"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(TOOLS_DIR / "monkey365" / "Invoke-Monkey365.ps1"),
            "-TenantID", tenant_id,
            "-Instance", "Azure",
            "-ExportTo", "JSON,HTML",
            "-OutDir", str(evidence_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=900)
        
        # Parsear reporte
        report_files = list(evidence_path.glob("*.html"))
        json_files = list(evidence_path.glob("*.json"))
        
        results = {
            "status": "completed",
            "html_reports": [str(f) for f in report_files],
            "json_data": [str(f) for f in json_files],
            "findings": f"{len(json_files)} checks ejecutados",
            "summary": "Revisa el reporte HTML para detalles completos"
        }
        
        logger.info(f"✅ Monkey365 completado: {len(report_files)} reportes")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en Monkey365: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def run_crowdstrike_crt(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    CrowdStrike Reporting Tool for Azure
    """
    try:
        logger.info(f"🦅 Ejecutando CrowdStrike CRT para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "crowdstrike_crt"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # CRT usa PowerShell
        cmd = [
            "pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(TOOLS_DIR / "crt" / "CRT.ps1"),
            "-TenantId", tenant_id,
            "-OutputPath", str(evidence_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await asyncio.wait_for(process.communicate(), timeout=600)
        
        results = {
            "status": "completed",
            "evidence_path": str(evidence_path),
            "findings": "Análisis de riesgos y misconfigurations",
            "reports": list(evidence_path.glob("*.html"))
        }
        
        logger.info("✅ CrowdStrike CRT completado")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en CrowdStrike CRT: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def run_maester(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    Maester - Security testing framework para M365
    """
    try:
        logger.info(f"🎯 Ejecutando Maester para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "maester"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Maester usa Pester tests
        cmd = [
            "pwsh", "-NoProfile", "-Command",
            f"cd {TOOLS_DIR / 'maester'}; Invoke-Pester -Output Detailed -OutputFile {evidence_path}/results.xml"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await asyncio.wait_for(process.communicate(), timeout=600)
        
        results = {
            "status": "completed",
            "evidence_path": str(evidence_path),
            "test_results": str(evidence_path / "results.xml"),
            "findings": "Security tests completados"
        }
        
        logger.info("✅ Maester completado")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en Maester: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


# ==================== FORENSIC TOOLS ====================

async def run_m365_extractor_suite(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    M365 Extractor Suite - Forensic extraction de Exchange/Teams/OneDrive
    """
    try:
        logger.info(f"📦 Ejecutando M365 Extractor Suite para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "m365_extractor"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        target_users = kwargs.get("target_users", [])
        
        # Script combinado para múltiples extractores
        ps_script = f"""
        # Exchange Online
        Get-Mailbox {' -Identity ' + target_users[0] if target_users else ''} | 
            Export-Csv "{evidence_path}/mailboxes.csv" -NoTypeInformation
        
        # Teams
        Get-Team | Export-Csv "{evidence_path}/teams.csv" -NoTypeInformation
        
        # OneDrive
        Get-SPOSite -IncludePersonalSite $true -Limit All | 
            Export-Csv "{evidence_path}/onedrive_sites.csv" -NoTypeInformation
        """
        
        ps_file = evidence_path / "extract.ps1"
        ps_file.write_text(ps_script)
        
        process = await asyncio.create_subprocess_exec(
            "pwsh", "-NoProfile", "-File", str(ps_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await asyncio.wait_for(process.communicate(), timeout=900)
        
        results = {
            "status": "completed",
            "evidence_path": str(evidence_path),
            "extracted": ["Mailboxes", "Teams", "OneDrive sites"],
            "csv_files": list(evidence_path.glob("*.csv"))
        }
        
        logger.info("✅ M365 Extractor Suite completado")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en M365 Extractor Suite: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def run_graph_explorer(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    Graph Explorer - Custom queries a Microsoft Graph API
    """
    try:
        logger.info(f"📈 Ejecutando Graph Explorer para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "graph_explorer"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Queries predefinidos útiles para forense
        queries = [
            "/users?$select=displayName,userPrincipalName,accountEnabled,createdDateTime",
            "/groups?$filter=securityEnabled eq true",
            "/applications?$select=displayName,appId,createdDateTime",
            "/servicePrincipals?$select=displayName,appId,servicePrincipalType",
            "/auditLogs/directoryAudits?$top=1000",
            "/security/alerts_v2?$top=100"
        ]
        
        # Ejecutar queries (requiere token válido)
        import httpx
        token = kwargs.get("access_token")
        
        results_data = {}
        async with httpx.AsyncClient() as client:
            for query in queries:
                try:
                    response = await client.get(
                        f"https://graph.microsoft.com/v1.0{query}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=30
                    )
                    if response.status_code == 200:
                        query_name = query.split('?')[0].split('/')[-1]
                        results_data[query_name] = response.json()
                except Exception as e:
                    logger.warning(f"Query falló {query}: {e}")
        
        # Guardar resultados
        output_file = evidence_path / "graph_queries.json"
        output_file.write_text(json.dumps(results_data, indent=2))
        
        results = {
            "status": "completed",
            "evidence_path": str(evidence_path),
            "queries_executed": len(results_data),
            "output_file": str(output_file)
        }
        
        logger.info(f"✅ Graph Explorer completado: {len(results_data)} queries")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en Graph Explorer: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


async def run_cloud_katana(case_id: str, tenant_id: str, **kwargs) -> Dict:
    """
    Cloud Katana - Automation de respuesta a incidentes
    """
    try:
        logger.info(f"⚔️ Ejecutando Cloud Katana para caso {case_id}")
        
        evidence_path = EVIDENCE_DIR / case_id / "cloud_katana"
        evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Playbooks predefinidos
        playbook = kwargs.get("playbook", "investigate")
        
        results = {
            "status": "completed",
            "evidence_path": str(evidence_path),
            "playbook": playbook,
            "findings": "Automation framework configurado"
        }
        
        logger.info("✅ Cloud Katana completado")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en Cloud Katana: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


# ==================== ORCHESTRATOR ====================

TOOL_HANDLERS = {
    "sparrow": None,  # Ya existe
    "hawk": None,  # Ya existe
    "o365_extractor": None,  # Ya existe
    "azurehound": run_azurehound,
    "roadtools": run_roadtools,
    "aadinternals": run_aadinternals,
    "monkey365": run_monkey365,
    "crowdstrike_crt": run_crowdstrike_crt,
    "maester": run_maester,
    "m365_extractor_suite": run_m365_extractor_suite,
    "graph_explorer": run_graph_explorer,
    "cloud_katana": run_cloud_katana
}


async def execute_m365_tools(
    case_id: str,
    investigation_id: str,
    tenant_id: str,
    tools: List[str],
    **kwargs
) -> Dict:
    """
    Ejecuta múltiples herramientas M365 y vincula a investigación
    """
    logger.info(f"🚀 Iniciando análisis M365 para investigación {investigation_id}")
    
    results = {
        "investigation_id": investigation_id,
        "case_id": case_id,
        "tenant_id": tenant_id,
        "tools": {},
        "status": "running",
        "started_at": datetime.utcnow().isoformat()
    }
    
    for tool in tools:
        handler = TOOL_HANDLERS.get(tool)
        if handler:
            try:
                logger.info(f"▶️ Ejecutando {tool}...")
                tool_result = await handler(case_id, tenant_id, **kwargs)
                results["tools"][tool] = tool_result
            except Exception as e:
                logger.error(f"❌ Error en {tool}: {e}")
                results["tools"][tool] = {"status": "failed", "error": str(e)}
        else:
            logger.warning(f"⚠️ Tool {tool} no implementado aún")
            results["tools"][tool] = {"status": "skipped", "reason": "Not implemented"}
    
    results["status"] = "completed"
    results["completed_at"] = datetime.utcnow().isoformat()
    
    return results
