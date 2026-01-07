"""
MCP Kali Forensics - Investigation Models
Modelos SQLAlchemy para Investigaciones IR
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from api.database import Base


class InvestigationStatus(str, enum.Enum):
    """Estados posibles de una investigación"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class InvestigationSeverity(str, enum.Enum):
    """Niveles de severidad"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


def generate_investigation_id():
    """Generar ID único para investigación en formato IR-YYYY-NNN"""
    today = datetime.utcnow()
    short_uuid = uuid.uuid4().hex[:3].upper()
    return f"IR-{today.year}-{short_uuid}"


class Investigation(Base):
    """
    Investigación de Incidente de Seguridad.
    Representa un caso de IR completo.
    """
    __tablename__ = "investigations"

    id = Column(String(50), primary_key=True, default=generate_investigation_id)
    
    # Basic info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification
    severity = Column(String(20), default="medium", index=True)
    status = Column(String(30), default="open", index=True)
    investigation_type = Column(String(50), nullable=True)  # BEC, Ransomware, Phishing, etc.
    
    # Assignment
    assigned_to = Column(String(100), nullable=True)
    team = Column(String(100), nullable=True)
    
    # Tenant/Customer info
    tenant_id = Column(String(100), nullable=True, index=True)
    tenant_name = Column(String(255), nullable=True)
    customer_name = Column(String(255), nullable=True)
    
    # Affected assets
    affected_users = Column(JSON, nullable=True)  # ["user1@domain.com", "user2@domain.com"]
    affected_hosts = Column(JSON, nullable=True)  # ["PC-001", "SRV-WEB-01"]
    affected_systems = Column(JSON, nullable=True)  # ["Exchange", "Azure AD"]
    
    # Impact assessment
    business_impact = Column(Text, nullable=True)
    data_breach = Column(String(10), default="unknown")  # yes/no/unknown
    financial_impact = Column(String(255), nullable=True)
    
    # MITRE ATT&CK
    mitre_tactics = Column(JSON, nullable=True)  # ["TA0001", "TA0003"]
    mitre_techniques = Column(JSON, nullable=True)  # ["T1566.001", "T1078"]
    
    # Timeline
    incident_date = Column(DateTime, nullable=True)  # Fecha del incidente
    detected_at = Column(DateTime, nullable=True)  # Fecha de detección
    contained_at = Column(DateTime, nullable=True)  # Fecha de contención
    resolved_at = Column(DateTime, nullable=True)  # Fecha de resolución
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metrics
    time_to_detect = Column(Integer, nullable=True)  # Minutes
    time_to_contain = Column(Integer, nullable=True)  # Minutes
    time_to_resolve = Column(Integer, nullable=True)  # Minutes
    
    # External references
    external_ticket = Column(String(100), nullable=True)  # ServiceNow, Jira, etc.
    
    # Relationships
    ioc_links = relationship("InvestigationIocLink", back_populates="investigation", cascade="all, delete-orphan")
    timeline_events = relationship("InvestigationTimeline", back_populates="investigation", cascade="all, delete-orphan", order_by="InvestigationTimeline.timestamp")

    def __repr__(self):
        return f"<Investigation(id={self.id}, title={self.title[:30]}...)>"
    
    def to_dict(self):
        """Convertir a diccionario para API responses"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "investigation_type": self.investigation_type,
            "assigned_to": self.assigned_to,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "affected_users": self.affected_users or [],
            "affected_hosts": self.affected_hosts or [],
            "mitre_tactics": self.mitre_tactics or [],
            "mitre_techniques": self.mitre_techniques or [],
            "incident_date": self.incident_date.isoformat() if self.incident_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "ioc_count": len(self.ioc_links) if self.ioc_links else 0
        }


class InvestigationIocLink(Base):
    """
    Tabla de asociación entre Investigaciones e IOCs.
    Permite vincular múltiples IOCs a una investigación con contexto.
    """
    __tablename__ = "investigation_ioc_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    investigation_id = Column(String(50), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Context of the link
    reason = Column(Text, nullable=True)  # Por qué se vinculó este IOC
    context = Column(Text, nullable=True)  # Contexto adicional
    relevance = Column(String(20), default="high")  # high/medium/low
    
    # Who linked it
    linked_by = Column(String(100), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    investigation = relationship("Investigation", back_populates="ioc_links")
    ioc = relationship("IocItem", back_populates="investigation_links")

    def __repr__(self):
        return f"<InvestigationIocLink(investigation={self.investigation_id}, ioc={self.ioc_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "ioc_id": self.ioc_id,
            "reason": self.reason,
            "relevance": self.relevance,
            "linked_by": self.linked_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ioc": self.ioc.to_dict() if self.ioc else None
        }


class InvestigationTimeline(Base):
    """
    Eventos de timeline para una investigación.
    Registra acciones, hallazgos y cambios durante la investigación.
    """
    __tablename__ = "investigation_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    investigation_id = Column(String(50), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event info
    event_type = Column(String(50), nullable=False)  # action/finding/status_change/ioc_added/note/evidence
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Source of the event
    source = Column(String(100), nullable=True)  # Tool or system that generated the event
    actor = Column(String(100), nullable=True)  # User or system that performed the action
    
    # Optional references
    ioc_id = Column(String(50), nullable=True)
    evidence_id = Column(String(50), nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)  # Flexible data storage (renamed from metadata - reserved)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    investigation = relationship("Investigation", back_populates="timeline_events")

    def __repr__(self):
        return f"<InvestigationTimeline(investigation={self.investigation_id}, type={self.event_type})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "actor": self.actor,
            "ioc_id": self.ioc_id,
            "evidence_id": self.evidence_id,
            "extra_data": self.extra_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
