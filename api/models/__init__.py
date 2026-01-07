"""
MCP Kali Forensics - SQLAlchemy Models
"""

from api.models.ioc import (
    IocItem,
    IocTag,
    IocItemTag,
    IocEnrichment,
    IocSighting
)

from api.models.investigation import (
    Investigation,
    InvestigationIocLink,
    InvestigationTimeline
)

from api.models.case import (
    Case,
    CaseEvidence,
    CaseNote
)

# v4.3 - M365 Reports
from api.models.tool_report import M365Report

# v4.5 - Configuration Management
from api.models.configuration import (
    ApiConfiguration,
    SystemSetting,
    ConfigCategory
)

# v4.5 - BRAC Authentication & User Management
from api.models.user import (
    User,
    Role,
    UserSession,
    UserAuditLog,
    UserApiKey,
    user_tenants,
    user_roles
)

# v4.5 - Tenant Model
from api.models.tenant import Tenant

# v4.6 - Evidence Management
from api.models.evidence_management import (
    EvidenceSource,
    ExternalEvidence,
    EvidenceAssociation,
    CommandLog
)

# v4.6 - API Usage Tracking
from api.middleware.usage_tracking import ApiUsage

# v4.1 - Tool Execution & Agents
from api.models.tools import (
    # Enums
    ToolCategory,
    ExecutionStatus,
    ExecutionTarget,
    ToolRiskLevel,
    AgentType,
    AgentStatus,
    PlaybookType,
    # Models
    ToolExecution,
    Agent,
    AgentTask,
    Playbook,
    PlaybookExecution,
    CorrelationRule,
    CorrelationEvent,
    GraphNode,
    GraphEdge,
    AuditLog
)

__all__ = [
    # IOC Models
    "IocItem",
    "IocTag", 
    "IocItemTag",
    "IocEnrichment",
    "IocSighting",
    
    # Investigation Models
    "Investigation",
    "InvestigationIocLink",
    "InvestigationTimeline",
    
    # Case Models
    "Case",
    "CaseEvidence",
    "CaseNote",
    
    # v4.1 - Enums
    "ToolCategory",
    "ExecutionStatus",
    "ExecutionTarget",
    "ToolRiskLevel",
    "AgentType",
    "AgentStatus",
    "PlaybookType",
    "CorrelationSeverity",
    "CorrelationRuleType",
    
    # v4.1 - Tool Execution
    "ToolExecution",
    
    # v4.1 - Agents
    "Agent",
    "AgentTask",
    
    # v4.1 - SOAR/Playbooks
    "Playbook",
    "PlaybookExecution",
    
    # v4.1 - Correlation
    "CorrelationRule",
    "CorrelationEvent",
    
    # v4.1 - Attack Graph
    "GraphNode",
    "GraphEdge",
    
    # v4.1 - Audit
    "AuditLog",
    
    # v4.3 - M365 Reports
    "M365Report",
    
    # v4.5 - Configuration Management
    "ApiConfiguration",
    "SystemSetting",
    "ConfigCategory",
    
    # v4.5 - BRAC Authentication & User Management
    "User",
    "Role",
    "UserSession",
    "UserAuditLog",
    "UserApiKey",
    "user_tenants",
    "user_roles",

    # v4.5 - Tenant Model
    "Tenant",

    # v4.6 - Evidence Management
    "EvidenceSource",
    "ExternalEvidence",
    "EvidenceAssociation",
    "CommandLog",

    # v4.6 - API Usage Tracking
    "ApiUsage",
]
