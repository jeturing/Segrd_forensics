"""
MCP v4.1 - Tool Execution Models
Modelos para ejecución de herramientas Kali con soporte híbrido MCP + Agents
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, 
    ForeignKey, Index
)
from datetime import datetime
from enum import Enum
import uuid

from api.database import Base


class ToolCategory(str, Enum):
    """Categorías de herramientas de seguridad"""
    RECON = "recon"
    ENUMERATION = "enumeration"
    VULNERABILITY = "vulnerability"
    EXPLOITATION = "exploitation"
    PASSWORD = "password"
    FORENSICS = "forensics"
    NETWORK = "network"
    WEB = "web"
    OSINT = "osint"
    MALWARE = "malware"
    DFIR = "dfir"


class ExecutionStatus(str, Enum):
    """Estados de ejecución"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionTarget(str, Enum):
    """Dónde se ejecuta la herramienta"""
    MCP_LOCAL = "mcp_local"
    AGENT_BLUE = "agent_blue"
    AGENT_RED = "agent_red"
    AGENT_PURPLE = "agent_purple"


class ToolRiskLevel(str, Enum):
    """Nivel de riesgo de la herramienta"""
    SAFE = "safe"           # Solo lectura, no intrusivo
    LOW = "low"             # Enumeración pasiva
    MEDIUM = "medium"       # Escaneo activo
    HIGH = "high"           # Potencialmente intrusivo
    OFFENSIVE = "offensive" # Red Team, requiere autorización especial


# =============================================================================
# TOOL EXECUTION MODEL
# =============================================================================

class ToolExecution(Base):
    """
    Registro de ejecución de herramienta Kali.
    Cada ejecución queda auditada con timeline, evidencia y correlación.
    """
    __tablename__ = "tool_executions"
    
    # Identificador único
    id = Column(String(50), primary_key=True)  # TOOL-EXE-XXXXXXXX
    
    # Información de la herramienta
    tool_id = Column(String(100), nullable=False, index=True)
    tool_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    risk_level = Column(String(20), default=ToolRiskLevel.SAFE.value)
    
    # Parámetros y comando
    parameters = Column(JSON, default={})
    command_executed = Column(Text)
    sanitized_command = Column(Text)  # Comando sin datos sensibles para logs
    
    # Target y contexto
    target = Column(String(500))  # IP, dominio, URL, path, etc.
    execution_target = Column(String(50), default=ExecutionTarget.MCP_LOCAL.value)
    agent_id = Column(String(50), ForeignKey("agents.id"), nullable=True)
    
    # Relación con casos/investigaciones
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=True, index=True)
    investigation_id = Column(String(50), ForeignKey("investigations.id"), nullable=True, index=True)
    
    # Usuario y tenant
    executed_by = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(50), index=True)
    
    # Estado y tiempos
    status = Column(String(20), default=ExecutionStatus.QUEUED.value, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Output
    output_file = Column(String(500))  # Path al archivo de output
    output_size_bytes = Column(Integer, default=0)
    output_hash = Column(String(64))  # SHA256 del output
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Resultados estructurados
    parsed_results = Column(JSON, default={})  # IPs, puertos, vulns encontradas
    iocs_extracted = Column(JSON, default=[])  # IOCs detectados automáticamente
    graph_nodes_created = Column(Integer, default=0)
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - Comentadas temporalmente hasta configurar en otros modelos
    # agent = relationship("Agent", back_populates="executions")
    # case = relationship("Case", back_populates="tool_executions")
    # investigation = relationship("Investigation", back_populates="tool_executions")
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_tool_exec_case_tool', 'case_id', 'tool_id'),
        Index('idx_tool_exec_status_date', 'status', 'started_at'),
        Index('idx_tool_exec_tenant_user', 'tenant_id', 'executed_by'),
    )
    
    @staticmethod
    def generate_id():
        return f"TOOL-EXE-{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "category": self.category,
            "risk_level": self.risk_level,
            "target": self.target,
            "execution_target": self.execution_target,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "executed_by": self.executed_by,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "iocs_extracted": self.iocs_extracted,
            "graph_nodes_created": self.graph_nodes_created
        }


# =============================================================================
# AGENT MODELS
# =============================================================================

class AgentType(str, Enum):
    """Tipos de agentes"""
    BLUE = "blue"    # Defensivo
    RED = "red"      # Ofensivo
    PURPLE = "purple"  # Híbrido


class AgentStatus(str, Enum):
    """Estados del agente"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class CorrelationSeverity(str, Enum):
    """Niveles de severidad para correlación"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class CorrelationRuleType(str, Enum):
    """Tipos de reglas de correlación"""
    SIGMA = "sigma"
    HEURISTIC = "heuristic"
    CUSTOM = "custom"
    ML = "ml"
    PATTERN = "pattern"


class Agent(Base):
    """
    Agente remoto para ejecución de herramientas.
    Puede ser Blue (defensivo), Red (ofensivo) o Purple (híbrido).
    """
    __tablename__ = "agents"
    
    id = Column(String(50), primary_key=True)  # AGENT-XXXX
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Tipo y configuración
    agent_type = Column(String(20), default=AgentType.BLUE.value, index=True)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45))
    os_type = Column(String(50))  # linux, windows, macos
    os_version = Column(String(100))
    
    # Autenticación
    public_key = Column(Text)
    fingerprint = Column(String(64), unique=True)
    api_key_hash = Column(String(64))
    
    # Estado
    status = Column(String(20), default=AgentStatus.OFFLINE.value, index=True)
    last_heartbeat = Column(DateTime)
    last_task_at = Column(DateTime)
    
    # Capacidades
    capabilities = Column(JSON, default=[])  # Lista de herramientas soportadas
    installed_tools = Column(JSON, default=[])
    max_concurrent_tasks = Column(Integer, default=3)
    current_tasks = Column(Integer, default=0)
    
    # Permisos
    authorized = Column(Boolean, default=False)
    authorized_by = Column(String(100))
    authorized_at = Column(DateTime)
    tenant_id = Column(String(50), index=True)
    allowed_risk_levels = Column(JSON, default=["safe", "low", "medium"])
    
    # Métricas
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    avg_execution_time = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - Comentadas para evitar errores de mapper
    # executions = relationship("ToolExecution", back_populates="agent")
    # tasks = relationship("AgentTask", back_populates="agent")
    
    # Propiedades para compatibilidad
    @property
    def last_seen(self):
        """Alias para last_heartbeat"""
        return self.last_heartbeat
    
    @staticmethod
    def generate_id(agent_type: str = "blue"):
        prefix = {"blue": "BLUE", "red": "RED", "purple": "PURP"}.get(agent_type, "AGNT")
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "agent_type": self.agent_type,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "capabilities": self.capabilities,
            "authorized": self.authorized,
            "current_tasks": self.current_tasks,
            "max_concurrent_tasks": self.max_concurrent_tasks
        }


class AgentTask(Base):
    """
    Tarea asignada a un agente para ejecución remota.
    """
    __tablename__ = "agent_tasks"
    
    id = Column(String(50), primary_key=True)  # TASK-XXXX
    agent_id = Column(String(50), ForeignKey("agents.id"), nullable=False, index=True)
    execution_id = Column(String(50), ForeignKey("tool_executions.id"), nullable=False)
    
    # Comando a ejecutar
    command = Column(Text, nullable=False)
    parameters = Column(JSON, default={})
    working_directory = Column(String(500))
    timeout_seconds = Column(Integer, default=300)
    
    # Estado
    status = Column(String(20), default="pending", index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Resultado
    exit_code = Column(Integer)
    output_path = Column(String(500))
    error_output = Column(Text)
    
    # Relationships - comentada por ahora
    # agent = relationship("Agent", back_populates="tasks")
    
    @staticmethod
    def generate_id():
        return f"TASK-{uuid.uuid4().hex[:8].upper()}"


class AgentCapability(Base):
    """
    Capacidad/herramienta instalada en un agente.
    Permite saber qué herramientas puede ejecutar cada agente.
    """
    __tablename__ = "agent_capabilities"
    
    id = Column(String(50), primary_key=True)
    agent_id = Column(String(50), ForeignKey("agents.id"), nullable=False, index=True)
    
    # Herramienta
    tool_id = Column(String(100), nullable=False)
    tool_name = Column(String(200), nullable=False)
    tool_version = Column(String(50))
    category = Column(String(50))
    
    # Estado
    installed = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    
    # Permisos
    enabled = Column(Boolean, default=True)
    risk_level = Column(String(20), default="safe")
    
    # Timestamps
    installed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def generate_id():
        return f"CAP-{uuid.uuid4().hex[:8].upper()}"


class AgentHeartbeat(Base):
    """
    Registro de heartbeat de agente.
    Historial de conexiones y estado del agente.
    """
    __tablename__ = "agent_heartbeats"
    
    id = Column(String(50), primary_key=True)
    agent_id = Column(String(50), ForeignKey("agents.id"), nullable=False, index=True)
    
    # Estado reportado
    status = Column(String(20), nullable=False)
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    disk_percent = Column(Float)
    
    # Tareas
    current_tasks = Column(Integer, default=0)
    queued_tasks = Column(Integer, default=0)
    
    # Red
    ip_address = Column(String(45))
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    @staticmethod
    def generate_id():
        return f"HB-{uuid.uuid4().hex[:8].upper()}"


# =============================================================================
# PLAYBOOK MODELS
# =============================================================================

class PlaybookType(str, Enum):
    """Tipos de playbooks"""
    BLUE_DEFENSE = "blue_defense"
    RED_ATTACK = "red_attack"
    PURPLE_VALIDATION = "purple_validation"
    RESPONSE = "response"
    INVESTIGATION = "investigation"


class PlaybookTrigger(str, Enum):
    """Tipos de triggers para playbooks"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    THRESHOLD = "threshold"
    PATTERN = "pattern"
    IOC_MATCH = "ioc_match"
    ALERT = "alert"
    API = "api"
    ON_IOC_CREATE = "on_ioc_create"
    ON_ALERT = "on_alert"


class PlaybookStatus(str, Enum):
    """Estados de playbooks"""
    ACTIVE = "active"
    DISABLED = "disabled"
    DRAFT = "draft"
    ARCHIVED = "archived"


class StepActionType(str, Enum):
    """Tipos de acciones en pasos de playbook"""
    TOOL_EXECUTE = "tool_execute"
    NOTIFICATION = "notification"
    CONDITION = "condition"
    PARALLEL = "parallel"
    DELAY = "delay"
    HUMAN_APPROVAL = "human_approval"
    SCRIPT = "script"
    API_CALL = "api_call"
    CREATE_IOC = "create_ioc"
    UPDATE_CASE = "update_case"
    UPDATE_TIMELINE = "update_timeline"
    ENRICH_IOC = "enrich_ioc"
    GRAPH_ENRICH = "graph_enrich"
    RUN_CORRELATION = "run_correlation"
    APPROVAL_GATE = "approval_gate"
    WAIT = "wait"


class Playbook(Base):
    """
    Playbook automatizado para agentes.
    Define secuencias de acciones basadas en triggers.
    """
    __tablename__ = "playbooks"
    
    id = Column(String(50), primary_key=True)  # PLAY-XXXX
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Tipo y categoría
    playbook_type = Column(String(30), default=PlaybookType.BLUE_DEFENSE.value, index=True)
    category = Column(String(50))
    tags = Column(JSON, default=[])
    
    # Trigger conditions (cuándo se activa)
    triggers = Column(JSON, default=[])  # Lista de condiciones
    trigger_logic = Column(String(10), default="any")  # any, all
    
    # Status
    status = Column(String(20), default=PlaybookStatus.ACTIVE.value, index=True)
    
    # Pasos del playbook
    steps = Column(JSON, default=[])  # Lista ordenada de acciones
    
    # Configuración
    enabled = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    auto_execute = Column(Boolean, default=False)
    max_executions_per_hour = Column(Integer, default=10)
    cooldown_seconds = Column(Integer, default=60)
    
    # Permisos
    allowed_agents = Column(JSON, default=["blue", "purple"])  # Qué agentes pueden ejecutarlo
    required_role = Column(String(50), default="analyst")
    tenant_id = Column(String(50), index=True)
    
    # Métricas
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime)
    success_rate = Column(Float, default=0.0)
    
    # Timestamps
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def generate_id():
        return f"PLAY-{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "playbook_type": self.playbook_type,
            "triggers": self.triggers,
            "steps": self.steps,
            "enabled": self.enabled,
            "auto_execute": self.auto_execute,
            "execution_count": self.execution_count
        }


class PlaybookExecution(Base):
    """Registro de ejecución de playbook"""
    __tablename__ = "playbook_executions"
    
    id = Column(String(50), primary_key=True)
    playbook_id = Column(String(50), ForeignKey("playbooks.id"), nullable=False, index=True)
    
    # Contexto de ejecución
    triggered_by = Column(String(100))  # evento, usuario, correlation
    trigger_event = Column(JSON)
    case_id = Column(String(50), index=True)
    investigation_id = Column(String(50), index=True)
    
    # Estado
    status = Column(String(20), default="running")
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer)
    steps_completed = Column(JSON, default=[])
    steps_failed = Column(JSON, default=[])
    
    # Tiempos
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Resultado
    success = Column(Boolean)
    error_message = Column(Text)
    results = Column(JSON, default={})
    
    @staticmethod
    def generate_id():
        return f"PEXE-{uuid.uuid4().hex[:8].upper()}"


# =============================================================================
# CORRELATION MODELS
# =============================================================================

class CorrelationRule(Base):
    """
    Regla de correlación (estilo Sigma + heurísticas ML).
    Detecta patrones en eventos, outputs de herramientas, logs, etc.
    """
    __tablename__ = "correlation_rules"
    
    id = Column(String(50), primary_key=True)  # CORR-RULE-XXXX
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Tipo de regla
    rule_type = Column(String(20), default="sigma")  # sigma, ml, hybrid
    severity = Column(String(20), default="medium")  # info, low, medium, high, critical
    
    # Definición de la regla
    detection = Column(JSON, default={})  # Condiciones de detección
    logsource = Column(JSON, default={})  # Fuente de logs
    condition = Column(Text)  # Expresión de condición
    
    # Para reglas ML
    ml_model = Column(String(100))  # Nombre del modelo
    ml_threshold = Column(Float, default=0.7)
    ml_features = Column(JSON, default=[])
    
    # Acciones automáticas
    actions = Column(JSON, default=[])  # Acciones a ejecutar si match
    create_alert = Column(Boolean, default=True)
    create_investigation = Column(Boolean, default=False)
    trigger_playbook = Column(String(50))  # ID del playbook a disparar
    
    # Configuración
    enabled = Column(Boolean, default=True, index=True)
    is_enabled = Column(Boolean, default=True, index=True)  # Alias for enabled
    is_builtin = Column(Boolean, default=False, index=True)  # Distingue reglas del sistema
    false_positive_rate = Column(Float, default=0.0)
    tags = Column(JSON, default=[])
    mitre_tactics = Column(JSON, default=[])
    mitre_techniques = Column(JSON, default=[])
    
    # Métricas
    total_matches = Column(Integer, default=0)
    last_matched_at = Column(DateTime)
    
    # Timestamps
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def generate_id():
        return f"CORR-RULE-{uuid.uuid4().hex[:8].upper()}"


class CorrelationEvent(Base):
    """
    Evento de correlación detectado.
    Se genera cuando una regla hace match.
    """
    __tablename__ = "correlation_events"
    
    id = Column(String(50), primary_key=True)  # CORR-EVT-XXXX
    rule_id = Column(String(50), ForeignKey("correlation_rules.id"), nullable=False, index=True)
    
    # Información del evento
    title = Column(String(500), nullable=False)
    description = Column(Text)
    severity = Column(String(20), index=True)
    confidence = Column(Float, default=1.0)  # 0-1, para reglas ML
    
    # Datos que matchearon
    matched_data = Column(JSON, default={})
    source_type = Column(String(50))  # tool_output, log, wazuh, otel
    source_id = Column(String(100))  # ID del origen
    
    # Contexto
    case_id = Column(String(50), index=True)
    investigation_id = Column(String(50), index=True)
    tenant_id = Column(String(50), index=True)
    
    # IOCs relacionados
    related_iocs = Column(JSON, default=[])
    related_ips = Column(JSON, default=[])
    related_domains = Column(JSON, default=[])
    related_hashes = Column(JSON, default=[])
    
    # Estado
    status = Column(String(20), default="new", index=True)  # new, investigating, resolved, false_positive
    assigned_to = Column(String(100))
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Acciones tomadas
    actions_triggered = Column(JSON, default=[])
    playbook_executed = Column(String(50))
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_corr_event_severity_status', 'severity', 'status'),
        Index('idx_corr_event_detected', 'detected_at'),
    )
    
    @staticmethod
    def generate_id():
        return f"CORR-EVT-{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "status": self.status,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "related_iocs": self.related_iocs,
            "case_id": self.case_id
        }


# =============================================================================
# GRAPH MODELS (Attack Graph)
# =============================================================================

class NodeType(str, Enum):
    """Tipos de nodos en el grafo de ataque"""
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    HASH = "hash"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    USER = "user"
    PROCESS = "process"
    FILE = "file"
    FILE_PATH = "file_path"
    EMAIL = "email"
    URL = "url"
    HOSTNAME = "hostname"
    HOST = "host"
    SERVICE = "service"
    CERTIFICATE = "certificate"
    REGISTRY_KEY = "registry_key"
    MALWARE = "malware"
    THREAT_ACTOR = "threat_actor"
    CAMPAIGN = "campaign"
    CVE = "cve"
    YARA_RULE = "yara_rule"
    TOOL_EXECUTION = "tool_execution"
    INDICATOR = "indicator"


class EdgeType(str, Enum):
    """Tipos de aristas en el grafo de ataque"""
    COMMUNICATES_WITH = "communicates_with"
    RESOLVES_TO = "resolves_to"
    RESOLVED_FROM = "resolved_from"
    CONTAINS = "contains"
    SPAWNED = "spawned"
    SPAWNS = "spawns"
    DOWNLOADED = "downloaded"
    DROPPED = "dropped"
    ACCESSED = "accessed"
    SIGNED_BY = "signed_by"
    RELATED_TO = "related_to"
    EXECUTED = "executed"
    EXECUTES = "executes"
    CONNECTED_TO = "connected_to"
    CONNECTS_TO = "connects_to"
    ATTRIBUTED_TO = "attributed_to"
    BELONGS_TO = "belongs_to"
    CREATES = "creates"
    DELETES = "deletes"
    DISCOVERED = "discovered"
    EXPLOITS = "exploits"
    HAS_HASH = "has_hash"
    HAS_IP = "has_ip"
    LOGGED_IN_FROM = "logged_in_from"
    MODIFIES = "modifies"
    USES = "uses"


class NodeStatus(str, Enum):
    """Estados de nodos en el grafo"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPICIOUS = "suspicious"
    CONFIRMED = "confirmed"
    BENIGN = "benign"


class GraphNode(Base):
    """
    Nodo del grafo de ataque.
    Representa una entidad: IP, dominio, hash, usuario, proceso, etc.
    """
    __tablename__ = "graph_nodes"
    
    id = Column(String(50), primary_key=True)  # NODE-XXXX
    
    # Tipo y valor
    node_type = Column(String(50), nullable=False, index=True)  # ip, domain, hash, user, process, file
    value = Column(String(500), nullable=False)
    label = Column(String(200))
    
    # Contexto
    case_id = Column(String(50), index=True)
    investigation_id = Column(String(50), index=True)
    tenant_id = Column(String(50), index=True)
    
    # Propiedades del nodo
    properties = Column(JSON, default={})
    severity = Column(String(20), default="unknown")
    confidence = Column(Float, default=0.5)
    
    # Fuente
    source = Column(String(100))  # tool_execution, correlation, manual, enrichment
    source_id = Column(String(100))
    
    # Visual
    x_position = Column(Float)
    y_position = Column(Float)
    color = Column(String(20))
    icon = Column(String(50))
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_graph_node_type_value', 'node_type', 'value'),
        Index('idx_graph_node_case', 'case_id', 'node_type'),
    )
    
    @staticmethod
    def generate_id():
        return f"NODE-{uuid.uuid4().hex[:8].upper()}"


class GraphEdge(Base):
    """
    Arista del grafo de ataque.
    Representa una relación entre nodos.
    """
    __tablename__ = "graph_edges"
    
    id = Column(String(50), primary_key=True)  # EDGE-XXXX
    
    # Nodos conectados
    source_node_id = Column(String(50), ForeignKey("graph_nodes.id"), nullable=False, index=True)
    target_node_id = Column(String(50), ForeignKey("graph_nodes.id"), nullable=False, index=True)
    
    # Tipo de relación
    edge_type = Column(String(50), nullable=False)  # connects_to, resolves_to, contains, executed, accessed
    label = Column(String(200))
    
    # Propiedades
    properties = Column(JSON, default={})
    weight = Column(Float, default=1.0)
    confidence = Column(Float, default=1.0)
    
    # Contexto
    case_id = Column(String(50), index=True)
    
    # Fuente
    source = Column(String(100))
    source_id = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_id():
        return f"EDGE-{uuid.uuid4().hex[:8].upper()}"


# =============================================================================
# AUDIT LOG
# =============================================================================

class AuditLog(Base):
    """
    Log de auditoría para todas las acciones del sistema.
    Chain of custody para evidencia forense.
    """
    __tablename__ = "audit_logs"
    
    id = Column(String(50), primary_key=True)  # AUDIT-XXXX
    
    # Acción
    action = Column(String(100), nullable=False, index=True)
    action_type = Column(String(50), index=True)  # create, read, update, delete, execute
    resource_type = Column(String(100), index=True)  # tool_execution, case, investigation, etc.
    resource_id = Column(String(100))
    
    # Detalles
    details = Column(JSON, default={})
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    # Usuario y contexto
    user_id = Column(String(100), index=True)
    user_email = Column(String(255))
    user_role = Column(String(50))
    tenant_id = Column(String(50), index=True)
    
    # Origen
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Integridad
    checksum = Column(String(64))  # SHA256 del registro
    previous_checksum = Column(String(64))  # Para chain
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_audit_action_time', 'action', 'timestamp'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )
    
    @staticmethod
    def generate_id():
        return f"AUDIT-{uuid.uuid4().hex[:12].upper()}"
