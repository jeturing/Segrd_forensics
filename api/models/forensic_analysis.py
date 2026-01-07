"""
MCP Kali Forensics - ForensicAnalysis Model
Registro de análisis forenses ejecutados sobre casos
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from datetime import datetime
import uuid

from api.database import Base


def generate_analysis_id():
    """Generar ID único para análisis: FA-YYYY-XXXXX"""
    today = datetime.utcnow()
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"FA-{today.year}-{short_uuid}"


class ForensicAnalysis(Base):
    """
    Registro de un análisis forense ejecutado.
    Vincula herramientas, hallazgos y evidencia a un caso específico.
    """
    __tablename__ = "forensic_analyses"

    # Identificación
    id = Column(String(50), primary_key=True, default=generate_analysis_id)
    case_id = Column(String(50), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Herramienta y tipo
    tool_name = Column(String(100), nullable=False)  # sparrow, hawk, o365, azurehound, etc.
    analysis_type = Column(String(50), nullable=False)  # m365_forensic, endpoint, credential, reconnaissance, audit
    category = Column(String(50), nullable=True)  # BÁSICO, RECONOCIMIENTO, AUDITORÍA, FORENSE
    
    # Estado
    status = Column(String(30), default="queued", index=True)  # queued/running/completed/failed/partial
    progress = Column(Integer, default=0)  # 0-100%
    
    # Configuración ejecutada
    config = Column(JSON, nullable=True)  # {days_back: 90, scope: [...], parameters: {...}}
    parameters = Column(JSON, nullable=True)  # {target_users: [...], target_hosts: [...]}
    
    # Resultados
    findings_count = Column(Integer, default=0)
    findings = Column(JSON, nullable=True)  # Array de hallazgos estructurados
    summary = Column(Text, nullable=True)  # Resumen ejecutivo
    
    # Auditoría de ejecución
    executed_by = Column(String(100), nullable=True)  # Email del analyst
    executed_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Tool version
    tool_version = Column(String(100), nullable=True)  # Versión de la herramienta usada
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Evidencia generada
    evidence_files = Column(JSON, nullable=True)  # [{name: "sparrow_results.json", size: 1024, type: "json"}]
    evidence_ids = Column(JSON, nullable=True)  # [EVD-001, EVD-002] - referencias a CaseEvidence
    
    # Decisiones interactivas
    user_decisions = Column(JSON, nullable=True)  # [{prompt: "...", decision: "...", timestamp: "..."}]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ForensicAnalysis(id={self.id}, tool={self.tool_name}, case={self.case_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "tool_name": self.tool_name,
            "analysis_type": self.analysis_type,
            "category": self.category,
            "status": self.status,
            "progress": self.progress,
            "findings_count": self.findings_count,
            "summary": self.summary,
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "tool_version": self.tool_version,
            "status_code": "success" if self.status == "completed" else ("failed" if self.status == "failed" else "running"),
            "evidence_ids": self.evidence_ids or []
        }

    def to_detailed_dict(self):
        """Retorna objeto completo con hallazgos"""
        return {
            **self.to_dict(),
            "findings": self.findings or [],
            "config": self.config or {},
            "parameters": self.parameters or {},
            "evidence_files": self.evidence_files or [],
            "user_decisions": self.user_decisions or [],
            "error_message": self.error_message
        }
