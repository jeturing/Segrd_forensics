"""
MCP Kali Forensics - M365 Report Model
Modelo SQLAlchemy para almacenar resultados de herramientas forenses M365
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Index
from datetime import datetime
import uuid

from api.database import Base


def generate_m365_report_id():
    """Generar ID único para reporte M365"""
    return f"M365-{uuid.uuid4().hex[:8].upper()}"


class M365Report(Base):
    """
    Reporte de herramienta forense M365.
    Almacena resultados de ejecución de Sparrow, Hawk, O365-Extractor, etc.
    """
    __tablename__ = "m365_reports"

    id = Column(String(50), primary_key=True, default=generate_m365_report_id)
    
    # Relación con caso
    case_id = Column(String(50), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Información de la herramienta
    tool_name = Column(String(100), nullable=False, index=True)  # sparrow, hawk, o365_extractor
    tool_version = Column(String(50), nullable=True)
    
    # Tenant info
    tenant_id = Column(String(100), nullable=True)
    tenant_name = Column(String(255), nullable=True)
    
    # Estado de ejecución
    status = Column(String(30), default="queued", index=True)  # queued/running/completed/failed/partial
    
    # Resultados
    results = Column(JSON, nullable=True)  # Diccionario con hallazgos parseados
    raw_output = Column(Text, nullable=True)  # Salida sin procesar (stdout/stderr)
    error_message = Column(Text, nullable=True)  # Mensaje de error si falló
    
    # Archivos generados
    evidence_path = Column(String(1000), nullable=True)  # Ruta a directorio con archivos
    output_files = Column(JSON, nullable=True)  # Lista de archivos generados
    
    # Métricas
    findings_count = Column(Integer, default=0)
    alerts_count = Column(Integer, default=0)
    warnings_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time_seconds = Column(Integer, nullable=True)
    
    # Metadata adicional
    parameters = Column(JSON, nullable=True)  # Parámetros usados en la ejecución
    scope = Column(JSON, nullable=True)  # ["sparrow", "hawk", "o365"]
    
    # Índices
    __table_args__ = (
        Index('idx_m365_case_tool', 'case_id', 'tool_name'),
        Index('idx_m365_status_date', 'status', 'created_at'),
    )

    def __repr__(self):
        return f"<M365Report {self.id} - {self.tool_name} ({self.status})>"
    
    def to_dict(self):
        """Convertir a diccionario para respuesta API"""
        return {
            "id": self.id,
            "case_id": self.case_id,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "status": self.status,
            "results": self.results,
            "error_message": self.error_message,
            "evidence_path": self.evidence_path,
            "output_files": self.output_files,
            "findings_count": self.findings_count,
            "alerts_count": self.alerts_count,
            "warnings_count": self.warnings_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
            "parameters": self.parameters,
            "scope": self.scope
        }
