"""
MCP Kali Forensics - Case Models
Modelos SQLAlchemy para gestión de casos y evidencia
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from api.database import Base


def generate_case_id():
    """Generar ID único para caso en formato CASE-YYYY-XXXXX"""
    today = datetime.utcnow()
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"CASE-{today.year}-{short_uuid}"


class Case(Base):
    """
    Caso forense - contenedor principal para investigaciones.
    Un caso puede tener múltiples evidencias, notas y estar vinculado a investigaciones.
    """
    __tablename__ = "cases"

    id = Column(String(50), primary_key=True, default=generate_case_id)
    
    # Basic info
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification
    case_type = Column(String(50), nullable=True)  # forensic/ir/threat_hunting/compliance
    priority = Column(String(20), default="medium")  # critical/high/medium/low
    status = Column(String(30), default="open", index=True)  # open/in_progress/pending/closed
    
    # Assignment
    lead_analyst = Column(String(100), nullable=True)
    team_members = Column(JSON, nullable=True)  # ["analyst1", "analyst2"]
    
    # Customer/Tenant
    customer_name = Column(String(255), nullable=True)
    customer_contact = Column(String(255), nullable=True)
    
    # Legal/Compliance
    legal_hold = Column(Boolean, default=False)
    chain_of_custody = Column(Boolean, default=True)
    confidentiality_level = Column(String(50), default="internal")  # public/internal/confidential/restricted
    
    # Evidence summary
    evidence_count = Column(Integer, default=0)
    
    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # External references
    external_reference = Column(String(255), nullable=True)  # Ticket externo
    
    # Relationships
    evidences = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan", order_by="CaseNote.created_at.desc()")

    def __repr__(self):
        return f"<Case(id={self.id}, name={self.name[:30]}...)>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "case_type": self.case_type,
            "priority": self.priority,
            "status": self.status,
            "lead_analyst": self.lead_analyst,
            "customer_name": self.customer_name,
            "legal_hold": self.legal_hold,
            "evidence_count": self.evidence_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class CaseEvidence(Base):
    """
    Evidencia asociada a un caso.
    Puede ser archivos, capturas de memoria, logs, etc.
    """
    __tablename__ = "case_evidences"

    id = Column(String(50), primary_key=True, default=lambda: f"EVD-{uuid.uuid4().hex[:8].upper()}")
    case_id = Column(String(50), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Evidence info
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    evidence_type = Column(String(50), nullable=False)  # file/memory_dump/network_capture/log/disk_image/screenshot
    
    # File info
    file_path = Column(String(1024), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # Bytes
    file_hash_md5 = Column(String(32), nullable=True)
    file_hash_sha256 = Column(String(64), nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Source
    source_host = Column(String(255), nullable=True)
    source_path = Column(String(1024), nullable=True)
    collected_by = Column(String(100), nullable=True)
    collection_method = Column(String(100), nullable=True)  # manual/automated/tool
    
    # Chain of custody
    custody_chain = Column(JSON, nullable=True)  # [{"action": "collected", "by": "analyst", "at": "timestamp"}]
    
    # Analysis status
    analyzed = Column(Boolean, default=False)
    analysis_notes = Column(Text, nullable=True)
    
    # Timestamps
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    case = relationship("Case", back_populates="evidences")

    def __repr__(self):
        return f"<CaseEvidence(id={self.id}, name={self.name[:30]}...)>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "name": self.name,
            "description": self.description,
            "evidence_type": self.evidence_type,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_hash_sha256": self.file_hash_sha256,
            "source_host": self.source_host,
            "collected_by": self.collected_by,
            "analyzed": self.analyzed,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class CaseNote(Base):
    """
    Notas y comentarios asociados a un caso.
    """
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Note content
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default="general")  # general/finding/action/recommendation
    
    # Author
    author = Column(String(100), nullable=True)
    
    # Visibility
    is_internal = Column(Boolean, default=True)  # Internal vs customer-visible
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    case = relationship("Case", back_populates="notes")

    def __repr__(self):
        return f"<CaseNote(id={self.id}, case={self.case_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "content": self.content,
            "note_type": self.note_type,
            "author": self.author,
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
