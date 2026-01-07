"""
Modelos de datos para Reportes y PDF Generation
=================================================
Reportes técnicos, ejecutivos y de evidencia
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON
from datetime import datetime
import enum

from api.database import Base


class ReportType(str, enum.Enum):
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    EVIDENCE = "evidence"
    COMPLIANCE = "compliance"
    INCIDENT = "incident"
    THREAT_INTEL = "threat_intel"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Report(Base):
    """Reporte generado del sistema"""
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Tipo y categoría
    report_type = Column(String(30), default='technical')
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500), nullable=True)
    
    # Asociaciones
    case_id = Column(String(50), nullable=True, index=True)
    investigation_id = Column(String(50), nullable=True, index=True)
    tenant_id = Column(String(100), nullable=True)
    
    # Estado
    status = Column(String(20), default='draft')
    version = Column(Integer, default=1)
    
    # Contenido
    executive_summary = Column(Text, nullable=True)
    findings = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    iocs_included = Column(JSON, default=list)
    timeline_included = Column(Boolean, default=False)
    graph_included = Column(Boolean, default=False)
    
    # Secciones personalizadas
    sections = Column(JSON, default=list)  # [{"title": "...", "content": "...", "order": 1}]
    
    # Metadata técnica
    severity_assessment = Column(String(20), nullable=True)
    impact_assessment = Column(Text, nullable=True)
    mitre_techniques = Column(JSON, default=list)
    affected_assets = Column(JSON, default=list)
    remediation_status = Column(JSON, default=dict)
    
    # Datos para PDF
    template_name = Column(String(100), default='default')
    include_appendix = Column(Boolean, default=True)
    include_raw_logs = Column(Boolean, default=False)
    classification = Column(String(50), default='INTERNAL')  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    
    # Archivos generados
    pdf_path = Column(String(500), nullable=True)
    pdf_size_bytes = Column(Integer, default=0)
    pdf_pages = Column(Integer, default=0)
    pdf_generated_at = Column(DateTime, nullable=True)
    
    html_path = Column(String(500), nullable=True)
    json_path = Column(String(500), nullable=True)
    
    # LLM
    llm_generated = Column(Boolean, default=False)
    llm_model_used = Column(String(100), nullable=True)
    llm_sections = Column(JSON, default=list)  # Qué secciones fueron generadas por LLM
    
    # Aprobación
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Distribución
    recipients = Column(JSON, default=list)  # ["email1@...", "email2@..."]
    sent_at = Column(DateTime, nullable=True)
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime, nullable=True)
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReportTemplate(Base):
    """Plantilla para generación de reportes"""
    __tablename__ = 'report_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(50), unique=True, nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(30), default='technical')
    
    # Contenido de la plantilla
    html_template = Column(Text, nullable=True)
    css_styles = Column(Text, nullable=True)
    header_template = Column(Text, nullable=True)
    footer_template = Column(Text, nullable=True)
    
    # Secciones disponibles
    available_sections = Column(JSON, default=list)
    default_sections = Column(JSON, default=list)
    
    # Configuración
    page_size = Column(String(10), default='A4')  # A4, Letter, Legal
    orientation = Column(String(15), default='portrait')
    margin_mm = Column(Integer, default=20)
    
    # Branding
    logo_path = Column(String(500), nullable=True)
    company_name = Column(String(200), nullable=True)
    primary_color = Column(String(7), default='#1a365d')
    secondary_color = Column(String(7), default='#2563eb')
    
    # Estado
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReportSchedule(Base):
    """Programación de reportes automáticos"""
    __tablename__ = 'report_schedules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(String(50), unique=True, nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuración del reporte
    report_type = Column(String(30), default='technical')
    template_id = Column(String(50), nullable=True)
    
    # Scope
    scope_type = Column(String(30), default='tenant')  # tenant, case, all
    scope_ids = Column(JSON, default=list)  # IDs específicos
    
    # Schedule
    schedule_cron = Column(String(50), nullable=False)  # "0 0 * * 1" = cada lunes
    timezone = Column(String(50), default='UTC')
    
    # Distribución
    auto_send = Column(Boolean, default=True)
    recipients = Column(JSON, default=list)
    
    # Estado
    is_enabled = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    last_report_id = Column(String(50), nullable=True)
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
