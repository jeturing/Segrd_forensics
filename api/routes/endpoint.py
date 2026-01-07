"""
Router para análisis forense de endpoints
Integra Loki, YARA, OSQuery y Volatility
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import logging

from api.services.endpoint import (
    run_loki_scan,
    run_yara_scan,
    collect_osquery_artifacts,
    analyze_memory_dump
)
from api.services.cases import create_case, update_case_status

router = APIRouter()
logger = logging.getLogger(__name__)

class EndpointScanRequest(BaseModel):
    """Request para escaneo de endpoint"""
    case_id: str = Field(..., description="ID del caso")
    hostname: str = Field(..., description="Nombre del equipo")
    tailscale_ip: Optional[str] = Field(default=None, description="IP de Tailscale")
    actions: List[Literal["yara", "loki", "osquery", "collect_logs"]] = Field(
        default=["yara", "loki"],
        description="Acciones a ejecutar"
    )
    target_paths: Optional[List[str]] = Field(
        default=None,
        description="Rutas específicas a escanear"
    )
    yara_rules: Optional[List[str]] = Field(
        default=None,
        description="Reglas YARA específicas (si no se especifica, usa todas)"
    )

class EndpointScanResponse(BaseModel):
    """Response del escaneo de endpoint"""
    case_id: str
    hostname: str
    status: str
    task_id: str
    message: str

@router.post("/scan", response_model=EndpointScanResponse)
async def scan_endpoint(
    request: EndpointScanRequest,
    background_tasks: BackgroundTasks
):
    """
    Escanea un endpoint en busca de IOCs, malware y artefactos forenses
    
    ## Herramientas disponibles:
    - **loki**: Scanner de IOCs conocidos
    - **yara**: Detección de malware con reglas personalizadas
    - **osquery**: Recolección de artefactos del sistema
    - **collect_logs**: Extracción de logs de seguridad
    
    ## Requisitos:
    - Endpoint debe estar conectado a Tailscale
    - Credenciales de acceso configuradas
    - Permisos de lectura en el sistema
    """
    try:
        logger.info(f"🔍 Iniciando escaneo de endpoint {request.hostname}")
        
        # Crear caso
        case = await create_case({
            "case_id": request.case_id,
            "type": "endpoint_forensics",
            "status": "queued",
            "metadata": {
                "hostname": request.hostname,
                "tailscale_ip": request.tailscale_ip,
                "actions": request.actions
            }
        })
        
        # Ejecutar en background
        background_tasks.add_task(
            execute_endpoint_scan,
            request.case_id,
            request.hostname,
            request.tailscale_ip,
            request.actions,
            request.target_paths,
            request.yara_rules
        )
        
        return EndpointScanResponse(
            case_id=request.case_id,
            hostname=request.hostname,
            status="queued",
            task_id=case["task_id"],
            message=f"Escaneo iniciado con {len(request.actions)} acción(es)"
        )
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar escaneo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def execute_endpoint_scan(
    case_id: str,
    hostname: str,
    tailscale_ip: Optional[str],
    actions: List[str],
    target_paths: Optional[List[str]],
    yara_rules: Optional[List[str]]
):
    """
    Ejecuta el escaneo de endpoint en background
    """
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🖥️ Escaneando endpoint {hostname}")
        
        results = {}
        
        # Ejecutar Loki Scanner
        if "loki" in actions:
            logger.info(f"🔍 Ejecutando Loki Scanner en {hostname}")
            results["loki"] = await run_loki_scan(
                hostname=hostname,
                tailscale_ip=tailscale_ip,
                target_paths=target_paths
            )
        
        # Ejecutar YARA
        if "yara" in actions:
            logger.info(f"🧬 Ejecutando YARA en {hostname}")
            results["yara"] = await run_yara_scan(
                hostname=hostname,
                tailscale_ip=tailscale_ip,
                target_paths=target_paths,
                rules=yara_rules
            )
        
        # Recolectar artefactos con OSQuery
        if "osquery" in actions:
            logger.info(f"📦 Recolectando artefactos con OSQuery de {hostname}")
            results["osquery"] = await collect_osquery_artifacts(
                hostname=hostname,
                tailscale_ip=tailscale_ip
            )
        
        # Recolectar logs
        if "collect_logs" in actions:
            logger.info(f"📋 Recolectando logs de {hostname}")
            # TODO: Implementar recolección de logs
            results["logs"] = {"status": "collected", "files": []}
        
        # Generar resumen
        summary = generate_endpoint_summary(results)
        
        await update_case_status(
            case_id,
            "completed",
            results=results,
            summary=summary
        )
        
        logger.info(f"✅ Escaneo de endpoint completado para {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Error en escaneo de endpoint: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))

def generate_endpoint_summary(results: dict) -> dict:
    """Genera resumen del escaneo de endpoint"""
    summary = {
        "iocs_detected": 0,
        "malware_found": False,
        "suspicious_processes": [],
        "suspicious_files": [],
        "risk_score": 0,
        "recommendations": []
    }
    
    # Analizar resultados de Loki
    if "loki" in results:
        loki_data = results["loki"]
        summary["iocs_detected"] += loki_data.get("ioc_count", 0)
        summary["suspicious_files"].extend(loki_data.get("suspicious_files", []))
    
    # Analizar resultados de YARA
    if "yara" in results:
        yara_data = results["yara"]
        if yara_data.get("matches", []):
            summary["malware_found"] = True
            summary["suspicious_files"].extend(
                [m["file"] for m in yara_data["matches"]]
            )
    
    # Analizar resultados de OSQuery
    if "osquery" in results:
        osquery_data = results["osquery"]
        summary["suspicious_processes"].extend(
            osquery_data.get("suspicious_processes", [])
        )
    
    # Calcular risk score
    summary["risk_score"] = (
        summary["iocs_detected"] * 5 +
        (10 if summary["malware_found"] else 0) +
        len(summary["suspicious_processes"]) * 3
    )
    
    # Generar recomendaciones
    if summary["malware_found"]:
        summary["recommendations"].append("🚨 Aislar endpoint inmediatamente")
        summary["recommendations"].append("Ejecutar limpieza completa con EDR")
        summary["recommendations"].append("Revisar credenciales almacenadas")
    
    if summary["iocs_detected"] > 0:
        summary["recommendations"].append("Analizar conexiones de red salientes")
        summary["recommendations"].append("Revisar procesos en ejecución")
    
    return summary

@router.post("/memory/analyze")
async def analyze_memory(
    case_id: str,
    hostname: str,
    memory_dump: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Analiza un dump de memoria con Volatility 3
    
    Soporta formatos: raw, vmem, vmdk, lime
    """
    try:
        logger.info(f"🧠 Analizando dump de memoria para {hostname}")
        
        # Guardar dump temporalmente
        dump_path = f"/tmp/evidence/{case_id}_{hostname}.dump"
        with open(dump_path, "wb") as f:
            content = await memory_dump.read()
            f.write(content)
        
        # Crear caso
        case = await create_case({
            "case_id": case_id,
            "type": "memory_forensics",
            "status": "queued",
            "metadata": {
                "hostname": hostname,
                "dump_size_mb": len(content) / (1024 * 1024),
                "dump_path": dump_path
            }
        })
        
        # Analizar en background
        background_tasks.add_task(
            execute_memory_analysis,
            case_id,
            hostname,
            dump_path
        )
        
        return {
            "case_id": case_id,
            "status": "queued",
            "task_id": case["task_id"],
            "message": "Análisis de memoria iniciado"
        }
        
    except Exception as e:
        logger.error(f"❌ Error al analizar memoria: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def execute_memory_analysis(
    case_id: str,
    hostname: str,
    dump_path: str
):
    """
    Ejecuta análisis de memoria con Volatility 3
    """
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🧠 Analizando dump de memoria de {hostname}")
        
        result = await analyze_memory_dump(dump_path)
        
        await update_case_status(
            case_id,
            "completed",
            results=result
        )
        
        logger.info(f"✅ Análisis de memoria completado para {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de memoria: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))
