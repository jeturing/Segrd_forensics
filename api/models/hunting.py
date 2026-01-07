"""
Modelos de datos para Threat Hunting
=====================================
Soporta queries de hunting, resultados, y hunts automáticos
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from api.database import Base


class HuntingQuery(Base):
    """Consulta de Threat Hunting guardada"""
    __tablename__ = 'hunting_queries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default='general')  # lateral_movement, persistence, exfiltration, etc.
    
    # Query content
    query_type = Column(String(30), default='kql')  # kql, osquery, yara, sigma
    query_content = Column(Text, nullable=False)
    
    # Metadata
    mitre_techniques = Column(JSON, default=list)  # ['T1003', 'T1059']
    severity = Column(String(20), default='medium')  # low, medium, high, critical
    tags = Column(JSON, default=list)
    
    # Execution settings
    data_sources = Column(JSON, default=list)  # ['m365_audit', 'endpoint', 'network']
    schedule_enabled = Column(Boolean, default=False)
    schedule_cron = Column(String(50), nullable=True)  # "0 */6 * * *"
    
    # Stats
    execution_count = Column(Integer, default=0)
    last_execution = Column(DateTime, nullable=True)
    avg_execution_time = Column(Integer, default=0)  # milliseconds
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    results = relationship("HuntingResult", back_populates="query", cascade="all, delete-orphan")


class HuntingResult(Base):
    """Resultado de ejecución de un hunt"""
    __tablename__ = 'hunting_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(50), unique=True, nullable=False, index=True)
    query_id = Column(String(50), ForeignKey('hunting_queries.query_id'), nullable=False)
    
    # Execution info
    execution_time = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer, default=0)
    status = Column(String(20), default='completed')  # running, completed, failed, timeout
    
    # Results
    total_hits = Column(Integer, default=0)
    results_data = Column(JSON, default=list)
    summary = Column(Text, nullable=True)
    
    # Findings
    iocs_found = Column(JSON, default=list)
    entities_affected = Column(JSON, default=list)  # users, hosts, ips
    severity_score = Column(Integer, default=0)  # 0-100
    
    # Actions taken
    case_created = Column(Boolean, default=False)
    case_id = Column(String(50), nullable=True)
    alerts_generated = Column(Integer, default=0)
    
    # LLM Analysis
    llm_analysis = Column(Text, nullable=True)
    llm_recommendations = Column(JSON, default=list)
    
    # Audit
    executed_by = Column(String(100), nullable=True)
    
    # Relationships
    query = relationship("HuntingQuery", back_populates="results")


class AutoHunt(Base):
    """Configuración de hunts automáticos"""
    __tablename__ = 'auto_hunts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hunt_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Queries incluidas
    query_ids = Column(JSON, default=list)  # Lista de query_id a ejecutar
    
    # Trigger
    trigger_type = Column(String(30), default='schedule')  # schedule, event, manual
    trigger_config = Column(JSON, default=dict)  # {"cron": "0 */4 * * *"} or {"event": "new_case"}
    
    # Targets
    target_tenants = Column(JSON, default=list)  # Lista de tenant_ids, vacío = todos
    target_cases = Column(JSON, default=list)  # Lista de case_ids, vacío = todos activos
    
    # Actions
    auto_create_case = Column(Boolean, default=False)
    auto_notify = Column(Boolean, default=True)
    notify_channels = Column(JSON, default=['email'])  # email, slack, teams
    
    # State
    is_enabled = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    
    # Audit
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
