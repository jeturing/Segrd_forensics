"""
Monkey365 Integration - M365 Cloud Security Assessment
=======================================================
Integra Monkey365 para análisis de seguridad de Azure/M365/Entra ID
con dashboard embebido y exportación de hallazgos a casos.
"""

import json
import asyncio
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monkey365", tags=["M365 Cloud Security"])

# Rutas de Monkey365
PROJECT_ROOT = Path(__file__).parent.parent.parent
MONKEY365_PATH = PROJECT_ROOT / "tools" / "Monkey365"
SCANS_OUTPUT_DIR = PROJECT_ROOT / "forensics-evidence" / "monkey365_scans"

# Crear directorio de outputs si no existe
SCANS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ScanRequest(BaseModel):
    """Request para iniciar un scan de Monkey365"""
    scan_name: str = "security_assessment"
    instance: str = "Microsoft365"  # Microsoft365, Azure, EntraID
    collect: Optional[List[str]] = None  # ExchangeOnline, SharePoint, Teams, etc
    include_entra_id: bool = True
    export_format: str = "HTML"  # HTML, CSV, JSON
    case_id: Optional[str] = None  # Para asociar con un caso existente
    
    
class ScanStatus(BaseModel):
    """Estado de un scan"""
    scan_id: str
    status: str  # pending, running, completed, failed
    progress: int = 0
    message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_path: Optional[str] = None
    findings_count: int = 0


# Almacén en memoria de scans activos
active_scans: Dict[str, ScanStatus] = {}


@router.get("/status")
async def get_monkey365_status():
    """Verificar si Monkey365 está instalado y disponible"""
    is_installed = MONKEY365_PATH.exists()
    main_script = MONKEY365_PATH / "Invoke-Monkey365.ps1"
    script_exists = main_script.exists() if is_installed else False
    
    # Verificar PowerShell
    pwsh_available = shutil.which("pwsh") is not None
    
    # Listar scans previos
    previous_scans = []
    if SCANS_OUTPUT_DIR.exists():
        for scan_dir in sorted(SCANS_OUTPUT_DIR.iterdir(), reverse=True)[:10]:
            if scan_dir.is_dir():
                report_file = scan_dir / "monkey365_report.html"
                previous_scans.append({
                    "name": scan_dir.name,
                    "path": str(scan_dir),
                    "has_report": report_file.exists(),
                    "created": datetime.fromtimestamp(scan_dir.stat().st_mtime).isoformat()
                })
    
    return {
        "installed": is_installed,
        "script_available": script_exists,
        "powershell_available": pwsh_available,
        "path": str(MONKEY365_PATH) if is_installed else None,
        "scans_directory": str(SCANS_OUTPUT_DIR),
        "previous_scans": previous_scans,
        "active_scans": list(active_scans.keys()),
        "supported_instances": ["Microsoft365", "Azure", "EntraID"],
        "supported_collectors": [
            "ExchangeOnline", "SharePointOnline", "Teams", "OneDrive",
            "AzureAD", "ConditionalAccess", "SecurityCenter", "Compliance"
        ]
    }


@router.post("/scan/start")
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Iniciar un nuevo scan de seguridad con Monkey365"""
    if not MONKEY365_PATH.exists():
        raise HTTPException(
            status_code=400, 
            detail="Monkey365 no está instalado. Ejecute scripts/install.sh"
        )
    
    # Generar ID único para el scan
    scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.scan_name}"
    output_dir = SCANS_OUTPUT_DIR / scan_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear estado inicial
    scan_status = ScanStatus(
        scan_id=scan_id,
        status="pending",
        progress=0,
        message="Preparando scan...",
        started_at=datetime.now().isoformat(),
        output_path=str(output_dir)
    )
    active_scans[scan_id] = scan_status
    
    # Ejecutar scan en background
    background_tasks.add_task(
        execute_monkey365_scan,
        scan_id=scan_id,
        request=request,
        output_dir=output_dir
    )
    
    return {
        "success": True,
        "scan_id": scan_id,
        "message": "Scan iniciado en background",
        "status_url": f"/api/monkey365/scan/{scan_id}/status"
    }


async def execute_monkey365_scan(scan_id: str, request: ScanRequest, output_dir: Path):
    """Ejecuta Monkey365 en background"""
    try:
        active_scans[scan_id].status = "running"
        active_scans[scan_id].progress = 10
        active_scans[scan_id].message = "Conectando con Azure/M365..."
        
        # Construir comando PowerShell
        ps_script = f"""
$ErrorActionPreference = 'Continue'
Import-Module "{MONKEY365_PATH}/monkey365.psd1" -Force

$options = @{{
    Instance = '{request.instance}'
    ExportTo = '{request.export_format}'
    OutputDir = '{output_dir}'
    IncludeEntraID = ${str(request.include_entra_id).lower()}
    PromptBehavior = 'Auto'
}}

# Collectors específicos
{"$options['Collect'] = @('" + "','".join(request.collect) + "')" if request.collect else ""}

try {{
    Invoke-Monkey365 @options
    Write-Output "SCAN_COMPLETED_SUCCESSFULLY"
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
"""
        
        # Guardar script temporal
        script_file = output_dir / "run_scan.ps1"
        with open(script_file, 'w') as f:
            f.write(ps_script)
        
        active_scans[scan_id].progress = 20
        active_scans[scan_id].message = "Ejecutando análisis de seguridad..."
        
        # Ejecutar PowerShell
        process = await asyncio.create_subprocess_exec(
            "pwsh", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(MONKEY365_PATH)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=1800  # 30 minutos timeout
            )
            
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            # Guardar logs
            with open(output_dir / "stdout.log", 'w') as f:
                f.write(stdout_text)
            with open(output_dir / "stderr.log", 'w') as f:
                f.write(stderr_text)
            
            if "SCAN_COMPLETED_SUCCESSFULLY" in stdout_text or process.returncode == 0:
                # Buscar reporte HTML generado
                html_reports = list(output_dir.glob("**/*.html"))
                
                # Contar findings
                findings_count = 0
                json_files = list(output_dir.glob("**/*.json"))
                for jf in json_files:
                    try:
                        with open(jf, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                findings_count += len(data)
                    except:
                        pass
                
                active_scans[scan_id].status = "completed"
                active_scans[scan_id].progress = 100
                active_scans[scan_id].message = f"Scan completado. {findings_count} hallazgos encontrados."
                active_scans[scan_id].completed_at = datetime.now().isoformat()
                active_scans[scan_id].findings_count = findings_count
                
                # Si hay un case_id, asociar los resultados
                if request.case_id:
                    await link_scan_to_case(scan_id, request.case_id, output_dir)
                    
            else:
                raise Exception(f"Scan failed: {stderr_text[:500]}")
                
        except asyncio.TimeoutError:
            process.kill()
            raise Exception("Scan timeout after 30 minutes")
            
    except Exception as e:
        logger.error(f"❌ Error en scan {scan_id}: {e}")
        active_scans[scan_id].status = "failed"
        active_scans[scan_id].message = str(e)[:200]
        active_scans[scan_id].completed_at = datetime.now().isoformat()


async def link_scan_to_case(scan_id: str, case_id: str, output_dir: Path):
    """Vincula resultados del scan a un caso existente"""
    try:
        case_dir = PROJECT_ROOT / "forensics-evidence" / case_id / "monkey365"
        case_dir.mkdir(parents=True, exist_ok=True)
        
        # Copiar resultados relevantes
        for file in output_dir.glob("**/*.json"):
            shutil.copy(file, case_dir / file.name)
        
        # Crear resumen para el caso
        summary = {
            "source": "monkey365",
            "scan_id": scan_id,
            "linked_at": datetime.now().isoformat(),
            "output_path": str(output_dir)
        }
        
        with open(case_dir / "scan_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"✅ Scan {scan_id} vinculado al caso {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Error vinculando scan a caso: {e}")


@router.get("/scan/{scan_id}/status")
async def get_scan_status(scan_id: str):
    """Obtener estado de un scan"""
    if scan_id not in active_scans:
        # Buscar en directorio de scans
        scan_dir = SCANS_OUTPUT_DIR / scan_id
        if scan_dir.exists():
            # Reconstruir estado desde disco
            return {
                "scan_id": scan_id,
                "status": "completed",
                "output_path": str(scan_dir),
                "has_report": (scan_dir / "monkey365_report.html").exists() or bool(list(scan_dir.glob("**/*.html")))
            }
        raise HTTPException(status_code=404, detail="Scan no encontrado")
    
    return active_scans[scan_id]


@router.get("/scan/{scan_id}/report", response_class=HTMLResponse)
async def get_scan_report(scan_id: str):
    """Obtener reporte HTML de un scan"""
    scan_dir = SCANS_OUTPUT_DIR / scan_id
    
    if not scan_dir.exists():
        raise HTTPException(status_code=404, detail="Scan no encontrado")
    
    # Buscar archivo HTML
    html_files = list(scan_dir.glob("**/*.html"))
    
    if not html_files:
        # Retornar página de espera si no hay reporte aún
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Monkey365 - Generando Reporte</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    margin: 0;
                    background: #1a1a2e;
                    color: #eee;
                }
                .loader { 
                    text-align: center; 
                }
                .spinner {
                    width: 50px;
                    height: 50px;
                    border: 5px solid #333;
                    border-top: 5px solid #00d4ff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 20px;
                }
                @keyframes spin { 100% { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="loader">
                <div class="spinner"></div>
                <h2>Generando reporte...</h2>
                <p>Esta página se actualizará automáticamente</p>
            </div>
        </body>
        </html>
        """, status_code=200)
    
    # Leer y retornar el primer HTML encontrado
    report_file = html_files[0]
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return HTMLResponse(content=content)


@router.get("/scan/{scan_id}/findings")
async def get_scan_findings(scan_id: str, severity: Optional[str] = None):
    """Obtener hallazgos de un scan en formato JSON"""
    scan_dir = SCANS_OUTPUT_DIR / scan_id
    
    if not scan_dir.exists():
        raise HTTPException(status_code=404, detail="Scan no encontrado")
    
    findings = []
    
    # Buscar archivos JSON de findings
    for json_file in scan_dir.glob("**/*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            # Filtrar por severidad si se especifica
                            if severity:
                                item_severity = item.get("severity", item.get("level", "")).lower()
                                if item_severity != severity.lower():
                                    continue
                            findings.append({
                                "source_file": json_file.name,
                                **item
                            })
        except Exception as e:
            logger.warning(f"Error leyendo {json_file}: {e}")
    
    # Agrupar por severidad
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", f.get("level", "info")).lower()
        if sev in by_severity:
            by_severity[sev] += 1
    
    return {
        "scan_id": scan_id,
        "total_findings": len(findings),
        "by_severity": by_severity,
        "findings": findings[:100]  # Limitar a 100 para la respuesta
    }


@router.post("/scan/{scan_id}/link-to-case/{case_id}")
async def link_existing_scan_to_case(scan_id: str, case_id: str):
    """Vincular un scan existente a un caso"""
    scan_dir = SCANS_OUTPUT_DIR / scan_id
    
    if not scan_dir.exists():
        raise HTTPException(status_code=404, detail="Scan no encontrado")
    
    await link_scan_to_case(scan_id, case_id, scan_dir)
    
    return {
        "success": True,
        "message": f"Scan {scan_id} vinculado al caso {case_id}"
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Retorna el dashboard principal de Monkey365 con lista de scans"""
    scans_html = ""
    
    if SCANS_OUTPUT_DIR.exists():
        for scan_dir in sorted(SCANS_OUTPUT_DIR.iterdir(), reverse=True)[:20]:
            if scan_dir.is_dir():
                has_report = bool(list(scan_dir.glob("**/*.html")))
                status_class = "status-complete" if has_report else "status-pending"
                status_text = "Completado" if has_report else "En proceso"
                
                scans_html += f"""
                <tr class="scan-row" onclick="loadReport('{scan_dir.name}')">
                    <td>{scan_dir.name}</td>
                    <td><span class="{status_class}">{status_text}</span></td>
                    <td>{datetime.fromtimestamp(scan_dir.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}</td>
                    <td>
                        <button onclick="event.stopPropagation(); loadReport('{scan_dir.name}')" class="btn-view">Ver Reporte</button>
                    </td>
                </tr>
                """
    
    if not scans_html:
        scans_html = '<tr><td colspan="4" class="empty-state">No hay scans previos</td></tr>'
    
    dashboard_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>M365 Cloud Security - Monkey365</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                min-height: 100vh;
            }}
            .header {{
                background: linear-gradient(135deg, #1e3a5f, #0f172a);
                padding: 20px 30px;
                border-bottom: 1px solid #334155;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{
                font-size: 24px;
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .header h1 .icon {{ font-size: 32px; }}
            .header .subtitle {{ color: #94a3b8; font-size: 14px; }}
            .btn-new-scan {{
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .btn-new-scan:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 30px;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #1e293b;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #334155;
            }}
            .stat-card .value {{ font-size: 36px; font-weight: 700; color: #3b82f6; }}
            .stat-card .label {{ color: #94a3b8; margin-top: 8px; }}
            .section-title {{
                font-size: 18px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid #334155;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: #1e293b;
                border-radius: 12px;
                overflow: hidden;
            }}
            th, td {{
                padding: 15px 20px;
                text-align: left;
                border-bottom: 1px solid #334155;
            }}
            th {{
                background: #0f172a;
                font-weight: 600;
                color: #94a3b8;
                text-transform: uppercase;
                font-size: 12px;
            }}
            .scan-row {{
                cursor: pointer;
                transition: background 0.2s;
            }}
            .scan-row:hover {{
                background: #334155;
            }}
            .status-complete {{
                background: #065f46;
                color: #34d399;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
            }}
            .status-pending {{
                background: #78350f;
                color: #fbbf24;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
            }}
            .btn-view {{
                background: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
            }}
            .btn-view:hover {{ background: #2563eb; }}
            .empty-state {{
                text-align: center;
                color: #64748b;
                padding: 40px !important;
            }}
            .report-frame {{
                width: 100%;
                height: calc(100vh - 200px);
                border: none;
                border-radius: 12px;
                background: white;
                margin-top: 20px;
            }}
            .modal {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                z-index: 1000;
                justify-content: center;
                align-items: center;
            }}
            .modal-content {{
                background: #1e293b;
                border-radius: 16px;
                padding: 30px;
                width: 500px;
                max-width: 90%;
            }}
            .modal h2 {{ margin-bottom: 20px; }}
            .form-group {{
                margin-bottom: 20px;
            }}
            .form-group label {{
                display: block;
                margin-bottom: 8px;
                color: #94a3b8;
            }}
            .form-group select, .form-group input {{
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #334155;
                background: #0f172a;
                color: white;
                font-size: 14px;
            }}
            .modal-buttons {{
                display: flex;
                gap: 12px;
                justify-content: flex-end;
                margin-top: 20px;
            }}
            .btn-cancel {{
                background: #475569;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1><span class="icon">🐵</span> Monkey365 <span class="subtitle">M365 Cloud Security</span></h1>
            </div>
            <button class="btn-new-scan" onclick="openNewScan()">+ Nuevo Scan</button>
        </div>
        
        <div class="container">
            <h3 class="section-title">Scans Recientes</h3>
            <table>
                <thead>
                    <tr>
                        <th>Nombre del Scan</th>
                        <th>Estado</th>
                        <th>Fecha</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {scans_html}
                </tbody>
            </table>
            
            <div id="reportContainer" style="display: none;">
                <h3 class="section-title" style="margin-top: 30px;">
                    Reporte <button onclick="closeReport()" style="float: right; background: #475569; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer;">✕ Cerrar</button>
                </h3>
                <iframe id="reportFrame" class="report-frame"></iframe>
            </div>
        </div>
        
        <!-- Modal Nuevo Scan -->
        <div id="newScanModal" class="modal">
            <div class="modal-content">
                <h2>🔍 Nuevo Scan de Seguridad</h2>
                <form id="scanForm">
                    <div class="form-group">
                        <label>Nombre del Scan</label>
                        <input type="text" id="scanName" value="security_assessment" required>
                    </div>
                    <div class="form-group">
                        <label>Tipo de Análisis</label>
                        <select id="instance">
                            <option value="Microsoft365">Microsoft 365</option>
                            <option value="Azure">Azure Subscription</option>
                            <option value="EntraID">Microsoft Entra ID</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="includeEntraID" checked> Incluir Entra ID</label>
                    </div>
                    <div class="modal-buttons">
                        <button type="button" class="btn-cancel" onclick="closeModal()">Cancelar</button>
                        <button type="submit" class="btn-new-scan">Iniciar Scan</button>
                    </div>
                </form>
            </div>
        </div>
        
        <script>
            function loadReport(scanId) {{
                document.getElementById('reportContainer').style.display = 'block';
                document.getElementById('reportFrame').src = '/api/monkey365/scan/' + scanId + '/report';
                document.getElementById('reportContainer').scrollIntoView({{ behavior: 'smooth' }});
            }}
            
            function closeReport() {{
                document.getElementById('reportContainer').style.display = 'none';
                document.getElementById('reportFrame').src = '';
            }}
            
            function openNewScan() {{
                document.getElementById('newScanModal').style.display = 'flex';
            }}
            
            function closeModal() {{
                document.getElementById('newScanModal').style.display = 'none';
            }}
            
            document.getElementById('scanForm').onsubmit = async function(e) {{
                e.preventDefault();
                const data = {{
                    scan_name: document.getElementById('scanName').value,
                    instance: document.getElementById('instance').value,
                    include_entra_id: document.getElementById('includeEntraID').checked,
                    export_format: 'HTML'
                }};
                
                try {{
                    const resp = await fetch('/api/monkey365/scan/start', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(data)
                    }});
                    const result = await resp.json();
                    if (result.success) {{
                        alert('Scan iniciado: ' + result.scan_id);
                        closeModal();
                        location.reload();
                    }} else {{
                        alert('Error: ' + result.detail);
                    }}
                }} catch (err) {{
                    alert('Error al iniciar scan: ' + err.message);
                }}
            }};
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=dashboard_html)
