"""
Reports Routes
==============
Endpoints para generación y gestión de reportes forenses
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import os

from api.services.reports import reports_service

router = APIRouter(tags=["reports"])


# ==================== ENUMS ====================

class ReportType(str, Enum):
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    EVIDENCE = "evidence"
    INCIDENT = "incident"
    TIMELINE = "timeline"
    IOC = "ioc"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "md"
    DOCX = "docx"


class ReportStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== REQUEST MODELS ====================

class GenerateReportRequest(BaseModel):
    """Request para generar un reporte"""
    case_id: str = Field(..., description="ID del caso")
    report_type: ReportType = Field(..., description="Tipo de reporte")
    format: ReportFormat = Field(ReportFormat.PDF, description="Formato de salida")
    language: str = Field("es", description="Idioma del reporte (en, es, zh-CN, zh-HK)")
    title: Optional[str] = Field(None, description="Título personalizado")
    include_sections: Optional[List[str]] = Field(
        None, 
        description="Secciones a incluir (None = todas)"
    )
    exclude_sections: Optional[List[str]] = Field(
        None,
        description="Secciones a excluir"
    )
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Opciones adicionales de generación"
    )
    use_llm_summary: bool = Field(True, description="Generar resumen ejecutivo con LLM")
    include_raw_evidence: bool = Field(False, description="Incluir evidencia raw")
    auto_ingest: bool = Field(True, description="Consumir evidencia del caso automáticamente")


class TemplateCreateRequest(BaseModel):
    """Request para crear template personalizado"""
    name: str = Field(..., min_length=3, max_length=100)
    description: str
    report_type: ReportType
    sections: List[Dict[str, Any]] = Field(..., min_items=1)
    header_template: Optional[str] = None
    footer_template: Optional[str] = None
    css_styles: Optional[str] = None


class RegenerateReportRequest(BaseModel):
    """Request para regenerar un reporte"""
    format: Optional[ReportFormat] = None
    options: Optional[Dict[str, Any]] = None


# ==================== RESPONSE MODELS ====================

class ReportResponse(BaseModel):
    """Respuesta de reporte generado"""
    report_id: str
    case_id: str
    report_type: str
    format: str
    status: str
    title: str
    created_at: datetime
    completed_at: Optional[datetime]
    file_path: Optional[str]
    file_size: Optional[int]
    download_url: Optional[str]


# ==================== ENDPOINTS ====================

@router.get("/")
async def get_reports_status():
    """Estado del servicio de reportes"""
    stats = await reports_service.get_stats()
    return {
        "service": "reports",
        "status": "operational",
        "report_types": [t.value for t in ReportType],
        "formats": [f.value for f in ReportFormat],
        "statistics": stats
    }


@router.post("/generate")
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks
):
    """
    Generar un nuevo reporte forense
    
    Tipos de reporte:
    - technical: Reporte técnico detallado con IOCs, timeline, hallazgos
    - executive: Resumen ejecutivo para management
    - evidence: Cadena de custodia y evidencias
    - incident: Reporte de incidente con impacto y remediación
    - timeline: Timeline visual de eventos
    - ioc: Lista de IOCs para compartir
    - custom: Template personalizado
    """
    # Crear registro de reporte
    report_id = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    report_info = await reports_service.create_report_record(
        report_id=report_id,
        case_id=request.case_id,
        report_type=request.report_type.value,
        format=request.format.value,
        title=request.title,
        language=request.language,
        options=request.options,
        auto_ingest=request.auto_ingest
    )
    
    # Generar en background
    background_tasks.add_task(
        reports_service.generate_report,
        report_id=report_id,
        case_id=request.case_id,
        report_type=request.report_type.value,
        format=request.format.value,
        title=request.title,
        include_sections=request.include_sections,
        exclude_sections=request.exclude_sections,
        options=request.options,
        use_llm=request.use_llm_summary,
        include_raw=request.include_raw_evidence,
        language=request.language,
        auto_ingest=request.auto_ingest
    )
    
    return {
        "report_id": report_id,
        "case_id": request.case_id,
        "status": "generating",
        "message": f"Generando reporte {request.report_type.value} en formato {request.format.value}",
        "estimated_time": "30-120 segundos según complejidad"
    }


@router.get("/case/{case_id}")
async def get_case_reports(
    case_id: str,
    report_type: Optional[ReportType] = None,
    status: Optional[ReportStatus] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Obtener todos los reportes de un caso
    """
    filters = {}
    if report_type:
        filters["report_type"] = report_type.value
    if status:
        filters["status"] = status.value
    
    reports = await reports_service.get_case_reports(
        case_id=case_id,
        filters=filters,
        limit=limit
    )
    
    return {
        "case_id": case_id,
        "total_reports": len(reports),
        "reports": reports
    }


# ==================== TEMPLATES ====================
# NOTA: Estas rutas DEBEN estar antes de /{report_id} para evitar conflictos

@router.get("/templates")
async def list_templates(report_type: Optional[ReportType] = None):
    """Listar templates de reportes disponibles"""
    templates = await reports_service.get_templates(
        report_type=report_type.value if report_type else None
    )
    
    return {
        "total_templates": len(templates),
        "templates": templates
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Obtener un template específico"""
    template = await reports_service.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    
    return template


@router.post("/templates")
async def create_template(request: TemplateCreateRequest):
    """Crear un template de reporte personalizado"""
    template_id = request.name.lower().replace(" ", "_")
    
    existing = await reports_service.get_template(template_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un template con el nombre '{request.name}'"
        )
    
    template = await reports_service.create_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        report_type=request.report_type.value,
        sections=request.sections,
        header_template=request.header_template,
        footer_template=request.footer_template,
        css_styles=request.css_styles
    )
    
    return {
        "created": True,
        "template_id": template_id,
        "message": f"Template '{request.name}' creado exitosamente"
    }


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Eliminar un template personalizado"""
    deleted = await reports_service.delete_template(template_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    
    return {"deleted": True, "template_id": template_id}


# ==================== REPORT BY ID (rutas con parámetros dinámicos) ====================

@router.get("/{report_id}")
async def get_report(report_id: str):
    """Obtener información de un reporte específico"""
    report = await reports_service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    
    return report


@router.get("/{report_id}/status")
async def get_report_status(report_id: str):
    """Obtener estado de generación de un reporte"""
    status = await reports_service.get_report_status(report_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    
    return {
        "report_id": report_id,
        "status": status["status"],
        "progress": status.get("progress", 0),
        "current_step": status.get("current_step"),
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "estimated_completion": status.get("estimated_completion"),
        "download_url": status.get("download_url"),
        "share_url": status.get("share_url")
    }


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    """
    Descargar un reporte generado
    """
    report = await reports_service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    
    if report["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Reporte no está listo. Estado: {report['status']}"
        )
    
    file_path = report.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo de reporte no encontrado")
    
    # Determinar media type
    format_to_media = {
        "pdf": "application/pdf",
        "html": "text/html",
        "json": "application/json",
        "md": "text/markdown",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    
    media_type = format_to_media.get(report["format"], "application/octet-stream")
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@router.post("/{report_id}/regenerate")
async def regenerate_report(
    report_id: str,
    request: RegenerateReportRequest,
    background_tasks: BackgroundTasks
):
    """
    Regenerar un reporte existente
    
    Útil cuando se agregó nueva evidencia o se quiere otro formato
    """
    report = await reports_service.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    
    # Crear nuevo reporte basado en el anterior
    new_report_id = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    await reports_service.create_report_record(
        report_id=new_report_id,
        case_id=report["case_id"],
        report_type=report["report_type"],
        format=request.format.value if request.format else report["format"],
        title=report.get("title"),
        options={**report.get("options", {}), **(request.options or {})},
        parent_report_id=report_id,
        language=report.get("language", "es"),
        auto_ingest=report.get("auto_ingest", False)
    )
    
    background_tasks.add_task(
        reports_service.regenerate_report,
        original_report_id=report_id,
        new_report_id=new_report_id,
        format=request.format.value if request.format else None,
        options=request.options
    )
    
    return {
        "original_report_id": report_id,
        "new_report_id": new_report_id,
        "status": "generating",
        "message": "Regenerando reporte con nuevos parámetros"
    }


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """Eliminar un reporte"""
    deleted = await reports_service.delete_report(report_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    
    return {"deleted": True, "report_id": report_id}


# ==================== SECTIONS ====================

@router.get("/sections")
async def get_available_sections():
    """
    Obtener secciones disponibles para reportes
    
    Cada tipo de reporte tiene diferentes secciones disponibles
    """
    sections = {
        "technical": [
            {"id": "executive_summary", "name": "Resumen Ejecutivo", "required": True},
            {"id": "scope", "name": "Alcance de la Investigación", "required": True},
            {"id": "timeline", "name": "Línea de Tiempo", "required": True},
            {"id": "findings", "name": "Hallazgos Técnicos", "required": True},
            {"id": "iocs", "name": "Indicadores de Compromiso", "required": True},
            {"id": "affected_assets", "name": "Activos Afectados", "required": False},
            {"id": "attack_chain", "name": "Cadena de Ataque (MITRE)", "required": False},
            {"id": "recommendations", "name": "Recomendaciones", "required": True},
            {"id": "appendix", "name": "Anexos", "required": False}
        ],
        "executive": [
            {"id": "summary", "name": "Resumen", "required": True},
            {"id": "impact", "name": "Impacto al Negocio", "required": True},
            {"id": "key_findings", "name": "Hallazgos Clave", "required": True},
            {"id": "risk_assessment", "name": "Evaluación de Riesgo", "required": True},
            {"id": "recommendations", "name": "Recomendaciones", "required": True},
            {"id": "next_steps", "name": "Próximos Pasos", "required": True}
        ],
        "evidence": [
            {"id": "chain_of_custody", "name": "Cadena de Custodia", "required": True},
            {"id": "evidence_list", "name": "Lista de Evidencias", "required": True},
            {"id": "acquisition_methods", "name": "Métodos de Adquisición", "required": True},
            {"id": "integrity_verification", "name": "Verificación de Integridad", "required": True},
            {"id": "storage_location", "name": "Ubicación de Almacenamiento", "required": True}
        ],
        "incident": [
            {"id": "incident_overview", "name": "Resumen del Incidente", "required": True},
            {"id": "detection", "name": "Detección", "required": True},
            {"id": "containment", "name": "Contención", "required": True},
            {"id": "eradication", "name": "Erradicación", "required": True},
            {"id": "recovery", "name": "Recuperación", "required": True},
            {"id": "lessons_learned", "name": "Lecciones Aprendidas", "required": True},
            {"id": "metrics", "name": "Métricas del Incidente", "required": False}
        ],
        "ioc": [
            {"id": "ip_addresses", "name": "Direcciones IP", "required": False},
            {"id": "domains", "name": "Dominios", "required": False},
            {"id": "urls", "name": "URLs", "required": False},
            {"id": "file_hashes", "name": "Hashes de Archivos", "required": False},
            {"id": "email_addresses", "name": "Direcciones de Email", "required": False},
            {"id": "yara_rules", "name": "Reglas YARA", "required": False},
            {"id": "sigma_rules", "name": "Reglas Sigma", "required": False}
        ]
    }
    
    return {
        "report_types": list(sections.keys()),
        "sections": sections
    }


# ==================== PREVIEW ====================

@router.post("/preview")
async def preview_report(request: GenerateReportRequest):
    """
    Generar preview de un reporte (sin guardar)
    
    Útil para ver cómo quedará el reporte antes de generarlo
    """
    preview = await reports_service.generate_preview(
        case_id=request.case_id,
        report_type=request.report_type.value,
        include_sections=request.include_sections,
        exclude_sections=request.exclude_sections
    )
    
    return {
        "case_id": request.case_id,
        "report_type": request.report_type.value,
        "preview_html": preview["html"],
        "sections_included": preview["sections"],
        "estimated_pages": preview["estimated_pages"]
    }


# ==================== BATCH ====================

@router.post("/batch")
async def generate_batch_reports(
    case_id: str,
    report_types: List[ReportType],
    format: ReportFormat = ReportFormat.PDF,
    background_tasks: BackgroundTasks = None
):
    """
    Generar múltiples reportes para un caso
    """
    report_ids = []
    
    for report_type in report_types:
        report_id = f"RPT-{report_type.value}-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
        
        await reports_service.create_report_record(
            report_id=report_id,
            case_id=case_id,
            report_type=report_type.value,
            format=format.value,
            title=None,
            options={}
        )
        
        background_tasks.add_task(
            reports_service.generate_report,
            report_id=report_id,
            case_id=case_id,
            report_type=report_type.value,
            format=format.value
        )
        
        report_ids.append({
            "report_id": report_id,
            "report_type": report_type.value
        })
    
    return {
        "case_id": case_id,
        "batch_size": len(report_ids),
        "reports": report_ids,
        "status": "generating"
    }
