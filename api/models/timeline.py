"""
Modelos de datos para Timeline de Incidentes
=============================================
Eventos ordenados cronológicamente con correlación
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, Float
from datetime import datetime

from api.database import Base


class TimelineEvent(Base):
    """Evento individual en la línea de tiempo"""
    __tablename__ = 'timeline_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Asociación
    case_id = Column(String(50), nullable=True, index=True)
    investigation_id = Column(String(50), nullable=True, index=True)
    
    # Timestamp preciso
    event_time = Column(DateTime, nullable=False, index=True)
    event_time_end = Column(DateTime, nullable=True)  # Para eventos con duración
    timezone = Column(String(50), default='UTC')
    
    # Clasificación
    event_type = Column(String(50), nullable=False)  # login, file_access, command, network, etc.
    category = Column(String(50), default='general')  # authentication, execution, persistence, etc.
    subcategory = Column(String(50), nullable=True)
    
    # Contenido
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    raw_data = Column(JSON, default=dict)
    
    # Entidades relacionadas
    source_type = Column(String(30), nullable=True)  # user, host, ip, application
    source_id = Column(String(200), nullable=True)
    source_name = Column(String(200), nullable=True)
    
    target_type = Column(String(30), nullable=True)
    target_id = Column(String(200), nullable=True)
    target_name = Column(String(200), nullable=True)
    
    # Ubicación
    source_ip = Column(String(45), nullable=True)
    destination_ip = Column(String(45), nullable=True)
    geo_location = Column(JSON, default=dict)  # {"country": "US", "city": "New York", "lat": 40.7, "lon": -74.0}
    
    # Clasificación de seguridad
    severity = Column(String(20), default='info')  # info, low, medium, high, critical
    confidence = Column(Float, default=1.0)  # 0.0 - 1.0
    is_suspicious = Column(Boolean, default=False)
    is_malicious = Column(Boolean, default=False)
    
    # MITRE ATT&CK
    mitre_tactic = Column(String(50), nullable=True)  # initial_access, execution, etc.
    mitre_technique = Column(String(20), nullable=True)  # T1003, T1059, etc.
    mitre_subtechnique = Column(String(20), nullable=True)  # T1003.001
    
    # IOCs relacionados
    ioc_refs = Column(JSON, default=list)  # ["ioc_123", "ioc_456"]
    
    # Fuente del evento
    data_source = Column(String(100), nullable=True)  # m365_audit, sentinel, endpoint, network
    original_id = Column(String(200), nullable=True)  # ID del evento en sistema origen
    
    # Correlación
    correlation_id = Column(String(50), nullable=True, index=True)
    parent_event_id = Column(String(50), nullable=True)
    related_events = Column(JSON, default=list)
    
    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    
    # LLM Analysis
    llm_summary = Column(Text, nullable=True)
    llm_classification = Column(JSON, default=dict)
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimelineCorrelation(Base):
    """Correlación entre eventos de timeline"""
    __tablename__ = 'timeline_correlations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Caso/Investigación
    case_id = Column(String(50), nullable=True, index=True)
    
    # Metadata
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    correlation_type = Column(String(50), default='manual')  # manual, auto, llm
    
    # Eventos correlacionados
    event_ids = Column(JSON, default=list)
    event_count = Column(Integer, default=0)
    
    # Timeframe
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    # Análisis
    attack_phase = Column(String(50), nullable=True)  # initial_access, lateral_movement, exfiltration
    kill_chain_stage = Column(String(50), nullable=True)
    confidence_score = Column(Float, default=0.0)
    severity = Column(String(20), default='medium')
    
    # LLM
    llm_narrative = Column(Text, nullable=True)  # Historia del ataque generada por LLM
    llm_recommendations = Column(JSON, default=list)
    
    # Estado
    is_confirmed = Column(Boolean, default=False)
    confirmed_by = Column(String(100), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
