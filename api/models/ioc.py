"""
MCP Kali Forensics - IOC Models
Modelos SQLAlchemy para IOC Store
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from api.database import Base


def generate_ioc_id():
    """Generar ID único para IOC en formato IOC-YYYYMMDD-XXXXX"""
    today = datetime.utcnow().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"IOC-{today}-{short_uuid}"


class IocItem(Base):
    """
    Indicador de Compromiso (IOC).
    Tipos soportados: ip, domain, url, email, hash_md5, hash_sha1, hash_sha256,
    file_name, file_path, registry_key, process_name, user_account, yara_rule,
    cve, mutex, user_agent
    """
    __tablename__ = "ioc_items"

    id = Column(String(50), primary_key=True, default=generate_ioc_id)
    value = Column(String(1024), nullable=False, index=True)
    ioc_type = Column(String(50), nullable=False, index=True)
    
    # Threat assessment
    threat_level = Column(String(20), default="medium", index=True)  # critical/high/medium/low/info
    confidence_score = Column(Float, default=50.0)  # 0-100
    
    # Status and source
    status = Column(String(20), default="active", index=True)  # active/expired/whitelisted/false_positive
    source = Column(String(50), default="manual")  # manual/investigation/threat_intel/hibp/virustotal/etc
    
    # Metadata
    description = Column(Text, nullable=True)
    context = Column(Text, nullable=True)  # Contexto adicional del IOC
    
    # Case linking
    case_id = Column(String(50), nullable=True, index=True)
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Stats
    hit_count = Column(Integer, default=0)
    
    # External references
    external_id = Column(String(255), nullable=True)  # ID en sistema externo (MISP, STIX)
    external_source = Column(String(100), nullable=True)  # Nombre del sistema externo
    
    # JSON fields for flexible data
    raw_data = Column(JSON, nullable=True)  # Datos originales del import
    enrichment_data = Column(JSON, nullable=True)  # Datos de enriquecimiento
    
    # Relationships
    tags = relationship("IocItemTag", back_populates="ioc", cascade="all, delete-orphan")
    enrichments = relationship("IocEnrichment", back_populates="ioc", cascade="all, delete-orphan")
    sightings = relationship("IocSighting", back_populates="ioc", cascade="all, delete-orphan")
    investigation_links = relationship("InvestigationIocLink", back_populates="ioc", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<IocItem(id={self.id}, type={self.ioc_type}, value={self.value[:30]}...)>"
    
    def to_dict(self):
        """Convertir a diccionario para API responses"""
        return {
            "id": self.id,
            "value": self.value,
            "ioc_type": self.ioc_type,
            "threat_level": self.threat_level,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "source": self.source,
            "description": self.description,
            "case_id": self.case_id,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "hit_count": self.hit_count,
            "tags": [t.tag.name for t in self.tags] if self.tags else [],
            "enrichment": self.enrichment_data or {}
        }


class IocTag(Base):
    """
    Tags para categorizar IOCs.
    Ejemplos: malware, phishing, c2, apt, ransomware, credential-theft
    """
    __tablename__ = "ioc_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="gray")  # Para UI
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    iocs = relationship("IocItemTag", back_populates="tag")

    def __repr__(self):
        return f"<IocTag(name={self.name})>"


class IocItemTag(Base):
    """
    Tabla de asociación many-to-many entre IOCs y Tags.
    """
    __tablename__ = "ioc_item_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("ioc_tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ioc = relationship("IocItem", back_populates="tags")
    tag = relationship("IocTag", back_populates="iocs")

    def __repr__(self):
        return f"<IocItemTag(ioc={self.ioc_id}, tag={self.tag_id})>"


class IocEnrichment(Base):
    """
    Datos de enriquecimiento de IOCs desde fuentes externas.
    Fuentes: virustotal, abuseipdb, shodan, greynoise, urlhaus, etc.
    """
    __tablename__ = "ioc_enrichments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"), nullable=False)
    
    source = Column(String(50), nullable=False)  # virustotal, abuseipdb, etc.
    
    # Enrichment results
    reputation_score = Column(Float, nullable=True)  # Score de reputación
    malicious_count = Column(Integer, nullable=True)  # Detecciones maliciosas
    suspicious_count = Column(Integer, nullable=True)
    harmless_count = Column(Integer, nullable=True)
    
    # Categories/Tags from source
    categories = Column(JSON, nullable=True)  # ["malware", "botnet"]
    
    # Raw response
    raw_response = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default="success")  # success/failed/pending
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    queried_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Cuándo expira el cache
    
    # Relationship
    ioc = relationship("IocItem", back_populates="enrichments")

    def __repr__(self):
        return f"<IocEnrichment(ioc={self.ioc_id}, source={self.source})>"


class IocSighting(Base):
    """
    Registro de avistamientos/detecciones de un IOC.
    Cada vez que un IOC es detectado en un sistema, se registra aquí.
    """
    __tablename__ = "ioc_sightings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"), nullable=False)
    
    # Where was it seen
    source_system = Column(String(100), nullable=True)  # SIEM, EDR, Firewall, etc.
    source_host = Column(String(255), nullable=True)  # Hostname donde se detectó
    source_ip = Column(String(45), nullable=True)  # IP donde se detectó
    
    # Context
    context = Column(Text, nullable=True)  # Descripción del avistamiento
    raw_event = Column(JSON, nullable=True)  # Evento raw del SIEM/EDR
    
    # Case linking
    case_id = Column(String(50), nullable=True)
    
    # Timestamp
    sighted_at = Column(DateTime, default=datetime.utcnow)
    
    # User who reported
    reported_by = Column(String(100), nullable=True)
    
    # Relationship
    ioc = relationship("IocItem", back_populates="sightings")

    def __repr__(self):
        return f"<IocSighting(ioc={self.ioc_id}, at={self.sighted_at})>"
