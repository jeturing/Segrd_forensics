-- ============================================================================
-- MCP Kali Forensics v4.1 - Database Migration Script
-- Adds tables for: Tool Execution, Agents, Playbooks, Correlation, Graph
-- ============================================================================

-- NOTE: SQLite syntax. Run with: sqlite3 data/mcp_forensics.db < migrations/v4.1_schema.sql

-- ============================================================================
-- TOOL EXECUTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS tool_executions (
    id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    category TEXT,
    parameters TEXT, -- JSON
    target TEXT DEFAULT 'local', -- 'local' or 'agent'
    agent_id TEXT,
    case_id TEXT,
    status TEXT DEFAULT 'queued', -- queued, running, completed, failed, timeout, cancelled
    priority INTEGER DEFAULT 0,
    timeout INTEGER DEFAULT 300,
    
    -- Results
    output TEXT,
    result TEXT, -- JSON parsed output
    error TEXT,
    exit_code INTEGER,
    
    -- Metrics
    started_at TEXT,
    completed_at TEXT,
    duration_seconds REAL,
    
    -- Audit
    executed_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_tool_executions_case ON tool_executions(case_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool ON tool_executions(tool_name);

CREATE TABLE IF NOT EXISTS tool_parameters (
    id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    param_name TEXT NOT NULL,
    param_type TEXT DEFAULT 'string', -- string, number, boolean, file, select
    label TEXT,
    description TEXT,
    placeholder TEXT,
    default_value TEXT,
    required INTEGER DEFAULT 0,
    advanced INTEGER DEFAULT 0,
    options TEXT, -- JSON for select type
    validation_pattern TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tool_parameters_tool ON tool_parameters(tool_name);

-- ============================================================================
-- AGENTS (Blue/Red/Purple)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL, -- blue, red, purple
    hostname TEXT NOT NULL,
    ip_address TEXT,
    os TEXT,
    version TEXT,
    
    -- Status
    status TEXT DEFAULT 'offline', -- online, offline, busy, error
    last_heartbeat TEXT,
    
    -- Security
    fingerprint TEXT,
    api_key_hash TEXT,
    
    -- Metadata
    tags TEXT, -- JSON array
    metadata TEXT, -- JSON
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_hostname ON agents(hostname);

CREATE TABLE IF NOT EXISTS agent_capabilities (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    config TEXT, -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_capabilities_agent ON agent_capabilities(agent_id);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    config TEXT, -- JSON
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    priority INTEGER DEFAULT 0,
    
    result TEXT, -- JSON
    error TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    
    dispatched_by TEXT,
    
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON agent_tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);

-- ============================================================================
-- PLAYBOOKS (SOAR)
-- ============================================================================

CREATE TABLE IF NOT EXISTS playbooks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    
    trigger_type TEXT DEFAULT 'manual', -- manual, scheduled, threshold, pattern
    trigger_config TEXT, -- JSON
    
    is_enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    
    -- Metadata
    tags TEXT, -- JSON array
    mitre_tactics TEXT, -- JSON array
    
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_playbooks_trigger ON playbooks(trigger_type);
CREATE INDEX IF NOT EXISTS idx_playbooks_enabled ON playbooks(is_enabled);

CREATE TABLE IF NOT EXISTS playbook_steps (
    id TEXT PRIMARY KEY,
    playbook_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    name TEXT,
    description TEXT,
    
    action_type TEXT NOT NULL, -- execute_tool, create_alert, send_notification, isolate_host, block_ip, collect_evidence, update_case, escalate, enrich_ioc, create_ticket
    action_config TEXT NOT NULL, -- JSON
    
    -- Conditions
    condition TEXT, -- JSON: when to execute
    on_success TEXT, -- next step or action
    on_failure TEXT, -- next step or action
    timeout INTEGER DEFAULT 60,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (playbook_id) REFERENCES playbooks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_playbook_steps_playbook ON playbook_steps(playbook_id);

CREATE TABLE IF NOT EXISTS playbook_executions (
    id TEXT PRIMARY KEY,
    playbook_id TEXT NOT NULL,
    
    status TEXT DEFAULT 'running', -- running, completed, failed, cancelled
    trigger_type TEXT,
    trigger_context TEXT, -- JSON
    
    current_step INTEGER DEFAULT 0,
    steps_completed INTEGER DEFAULT 0,
    steps_failed INTEGER DEFAULT 0,
    
    result TEXT, -- JSON
    error TEXT,
    
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    
    executed_by TEXT,
    
    FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
);

CREATE INDEX IF NOT EXISTS idx_playbook_executions_playbook ON playbook_executions(playbook_id);
CREATE INDEX IF NOT EXISTS idx_playbook_executions_status ON playbook_executions(status);

-- ============================================================================
-- CORRELATION ENGINE
-- ============================================================================

CREATE TABLE IF NOT EXISTS correlation_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    
    rule_type TEXT DEFAULT 'sigma', -- sigma, ml_threshold, pattern, custom
    severity TEXT DEFAULT 'medium', -- critical, high, medium, low, info
    
    -- Rule definition
    rule_content TEXT NOT NULL, -- Sigma YAML or custom JSON
    conditions TEXT, -- JSON: additional conditions
    
    -- Behavior
    is_enabled INTEGER DEFAULT 1,
    threshold INTEGER DEFAULT 1, -- events needed to trigger
    time_window INTEGER DEFAULT 300, -- seconds
    
    -- Response
    auto_create_alert INTEGER DEFAULT 1,
    playbook_id TEXT, -- auto-trigger playbook
    
    -- MITRE
    mitre_tactics TEXT, -- JSON array
    mitre_techniques TEXT, -- JSON array
    
    -- Stats
    match_count INTEGER DEFAULT 0,
    last_match_at TEXT,
    false_positive_count INTEGER DEFAULT 0,
    
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
);

CREATE INDEX IF NOT EXISTS idx_correlation_rules_type ON correlation_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_correlation_rules_severity ON correlation_rules(severity);
CREATE INDEX IF NOT EXISTS idx_correlation_rules_enabled ON correlation_rules(is_enabled);

CREATE TABLE IF NOT EXISTS correlation_events (
    id TEXT PRIMARY KEY,
    
    -- Event source
    source_type TEXT, -- tool_output, agent_telemetry, external, manual
    source_id TEXT,
    
    -- Event data
    event_type TEXT,
    event_data TEXT NOT NULL, -- JSON
    
    -- Matching
    matched_rules TEXT, -- JSON array of rule IDs
    severity TEXT,
    
    -- Context
    case_id TEXT,
    hostname TEXT,
    ip_address TEXT,
    user_id TEXT,
    
    processed INTEGER DEFAULT 0,
    processed_at TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id)
);

CREATE INDEX IF NOT EXISTS idx_correlation_events_type ON correlation_events(event_type);
CREATE INDEX IF NOT EXISTS idx_correlation_events_case ON correlation_events(case_id);
CREATE INDEX IF NOT EXISTS idx_correlation_events_processed ON correlation_events(processed);
CREATE INDEX IF NOT EXISTS idx_correlation_events_created ON correlation_events(created_at);

-- ============================================================================
-- ATTACK GRAPH (Enhanced)
-- ============================================================================

CREATE TABLE IF NOT EXISTS graph_nodes (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    
    node_type TEXT NOT NULL, -- host, user, process, file, network, ioc, alert, evidence
    label TEXT NOT NULL,
    
    -- Properties
    properties TEXT, -- JSON
    
    -- Visual
    x REAL,
    y REAL,
    color TEXT,
    size REAL DEFAULT 1.0,
    icon TEXT,
    
    -- Source
    source_type TEXT, -- manual, tool_output, correlation, enrichment
    source_id TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_case ON graph_nodes(case_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);

CREATE TABLE IF NOT EXISTS graph_edges (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    
    edge_type TEXT NOT NULL, -- connects, executes, accesses, downloads, communicates, contains, spawns, modifies, authenticates
    label TEXT,
    
    -- Properties
    properties TEXT, -- JSON
    weight REAL DEFAULT 1.0,
    
    -- Visual
    color TEXT,
    style TEXT, -- solid, dashed, dotted
    
    -- Temporal
    timestamp TEXT,
    
    -- Source
    source_type TEXT,
    source_id TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_case ON graph_edges(case_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_node_id);

-- ============================================================================
-- SECURITY POLICIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_policies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    
    policy_type TEXT NOT NULL, -- tool_whitelist, tool_blacklist, agent_restriction, execution_limit
    
    -- Policy definition
    rules TEXT NOT NULL, -- JSON
    
    is_enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_security_policies_type ON security_policies(policy_type);
CREATE INDEX IF NOT EXISTS idx_security_policies_enabled ON security_policies(is_enabled);

-- ============================================================================
-- VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_versions (
    version TEXT PRIMARY KEY,
    description TEXT,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_versions (version, description) 
VALUES ('4.1.0', 'Added Tool Execution, Agents, Playbooks, Correlation, Graph tables');

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Sample Playbook: Ransomware Response
INSERT OR IGNORE INTO playbooks (id, name, description, trigger_type, trigger_config, is_enabled, tags, mitre_tactics)
VALUES (
    'pb-ransomware-response-001',
    'Ransomware Rapid Response',
    'Automated response playbook for ransomware detection',
    'pattern',
    '{"pattern": "ransomware|encrypt|ransom|bitcoin", "source": "correlation_alerts"}',
    1,
    '["ransomware", "critical", "automated"]',
    '["TA0040", "TA0005"]'
);

-- Sample Correlation Rule: Brute Force Detection
INSERT OR IGNORE INTO correlation_rules (id, name, description, rule_type, severity, rule_content, threshold, time_window, is_enabled, mitre_tactics, mitre_techniques)
VALUES (
    'cr-brute-force-001',
    'Brute Force Attack Detection',
    'Detects multiple failed login attempts from same source',
    'sigma',
    'high',
    'title: Brute Force Detection
logsource:
  product: windows
  service: security
detection:
  selection:
    EventID: 4625
  condition: selection
  timeframe: 5m
  count: 10',
    10,
    300,
    1,
    '["TA0006"]',
    '["T1110"]'
);

-- Sample Security Policy
INSERT OR IGNORE INTO security_policies (id, name, description, policy_type, rules, is_enabled)
VALUES (
    'sp-dangerous-tools-001',
    'Dangerous Tools Restriction',
    'Requires approval for potentially dangerous tools',
    'tool_whitelist',
    '{"require_approval": ["metasploit", "hydra", "sqlmap", "responder"], "blocked": ["rm -rf", "format", "dd if=/dev/zero"]}',
    1
);

PRAGMA foreign_keys = ON;
