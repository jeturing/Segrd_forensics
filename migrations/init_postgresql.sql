-- =============================================================================
-- MCP Kali Forensics - PostgreSQL Initial Schema v4.4.1
-- Ejecutar con: psql -U forensics -d forensics -f init_postgresql.sql
-- =============================================================================

-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- ============================================================================
-- TABLA: cases
-- ============================================================================
CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR(20) PRIMARY KEY,  -- IR-YYYY-NNN
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'open',
    priority VARCHAR(10) DEFAULT 'medium',
    
    -- JSONB
    metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    assignees JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_priority ON cases(priority);
CREATE INDEX IF NOT EXISTS idx_cases_created ON cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_tags_gin ON cases USING gin(tags);


-- ============================================================================
-- TABLA: forensic_analyses (con particionamiento)
-- ============================================================================
CREATE TABLE IF NOT EXISTS forensic_analyses (
    id VARCHAR(20) NOT NULL,  -- FA-YYYY-XXXXX
    case_id VARCHAR(20) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    
    -- JSONB para datos complejos
    findings JSONB DEFAULT '{}',
    logs JSONB DEFAULT '[]',
    evidence_files JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Particiones por mes (2025)
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_01 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_02 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_03 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_04 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_05 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_06 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_07 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_08 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_09 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_10 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_11 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE IF NOT EXISTS forensic_analyses_2025_12 PARTITION OF forensic_analyses
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Índices
CREATE INDEX IF NOT EXISTS idx_fa_case_id ON forensic_analyses(case_id);
CREATE INDEX IF NOT EXISTS idx_fa_case_created ON forensic_analyses(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fa_status ON forensic_analyses(status);
CREATE INDEX IF NOT EXISTS idx_fa_tool ON forensic_analyses(tool_name);
CREATE INDEX IF NOT EXISTS idx_fa_findings_gin ON forensic_analyses USING gin(findings);


-- ============================================================================
-- TABLA: analysis_logs (logs de streaming)
-- ============================================================================
CREATE TABLE IF NOT EXISTS analysis_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id VARCHAR(20) NOT NULL,
    case_id VARCHAR(20) NOT NULL,
    
    level VARCHAR(10) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_analysis ON analysis_logs(analysis_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_case ON analysis_logs(case_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON analysis_logs(level);


-- ============================================================================
-- TABLA: processes (gestión de procesos)
-- ============================================================================
CREATE TABLE IF NOT EXISTS processes (
    id VARCHAR(50) PRIMARY KEY,  -- PROC-{tool}-{uuid}
    case_id VARCHAR(20) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    
    config JSONB DEFAULT '{}',
    result JSONB,
    error TEXT,
    exit_code INTEGER,
    
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proc_case ON processes(case_id);
CREATE INDEX IF NOT EXISTS idx_proc_status ON processes(status);


-- ============================================================================
-- TABLA: iocs
-- ============================================================================
CREATE TABLE IF NOT EXISTS iocs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(20),
    
    type VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    confidence SMALLINT DEFAULT 50,
    severity VARCHAR(10) DEFAULT 'medium',
    
    source VARCHAR(100),
    description TEXT,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    related_iocs JSONB DEFAULT '[]',
    
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ioc_case ON iocs(case_id);
CREATE INDEX IF NOT EXISTS idx_ioc_type ON iocs(type);
CREATE INDEX IF NOT EXISTS idx_ioc_value ON iocs(value);
CREATE INDEX IF NOT EXISTS idx_ioc_value_trgm ON iocs USING gin(value gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ioc_tags_gin ON iocs USING gin(tags);


-- ============================================================================
-- TABLA: timeline_events
-- ============================================================================
CREATE TABLE IF NOT EXISTS timeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(20) NOT NULL,
    
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    severity VARCHAR(10) DEFAULT 'info',
    
    source VARCHAR(100),
    source_id VARCHAR(100),
    
    data JSONB DEFAULT '{}',
    artifacts JSONB DEFAULT '[]',
    
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_case ON timeline_events(case_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_events(event_type);
CREATE INDEX IF NOT EXISTS idx_timeline_severity ON timeline_events(severity);


-- ============================================================================
-- TABLA: users (para RBAC)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    
    role VARCHAR(20) DEFAULT 'analyst',
    permissions JSONB DEFAULT '[]',
    
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);


-- ============================================================================
-- TABLA: api_keys (para RBAC)
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(256) NOT NULL,
    key_prefix VARCHAR(16) NOT NULL,  -- Primeros 16 chars para identificar
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    user_id UUID REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'analyst',
    permissions JSONB DEFAULT '[]',
    
    rate_limit INTEGER DEFAULT 100,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    is_active BOOLEAN DEFAULT true,
    last_used TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);


-- ============================================================================
-- FUNCIONES
-- ============================================================================

-- Generar ID de análisis
CREATE OR REPLACE FUNCTION generate_analysis_id() 
RETURNS VARCHAR(20) AS $$
DECLARE
    year_str VARCHAR(4);
    next_seq INTEGER;
    result VARCHAR(20);
BEGIN
    year_str := EXTRACT(YEAR FROM NOW())::VARCHAR;
    
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(id FROM 9 FOR 5) AS INTEGER)
    ), 0) + 1 INTO next_seq
    FROM forensic_analyses
    WHERE id LIKE 'FA-' || year_str || '-%';
    
    result := 'FA-' || year_str || '-' || LPAD(next_seq::VARCHAR, 5, '0');
    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- Agregar log de análisis
CREATE OR REPLACE FUNCTION add_analysis_log(
    p_analysis_id VARCHAR(20),
    p_level VARCHAR(10),
    p_message TEXT,
    p_context JSONB DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    v_case_id VARCHAR(20);
    v_log_id UUID;
BEGIN
    SELECT case_id INTO v_case_id
    FROM forensic_analyses
    WHERE id = p_analysis_id;
    
    IF v_case_id IS NULL THEN
        RAISE EXCEPTION 'Analysis not found: %', p_analysis_id;
    END IF;
    
    INSERT INTO analysis_logs(analysis_id, case_id, level, message, context)
    VALUES (p_analysis_id, v_case_id, p_level, p_message, p_context)
    RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;


-- Actualizar timestamp de case
CREATE OR REPLACE FUNCTION update_case_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_case_updated
    BEFORE UPDATE ON cases
    FOR EACH ROW
    EXECUTE FUNCTION update_case_timestamp();


-- ============================================================================
-- VISTAS
-- ============================================================================

-- Resumen de casos
CREATE OR REPLACE VIEW v_case_summary AS
SELECT 
    c.id,
    c.name,
    c.status,
    c.priority,
    c.created_at,
    c.updated_at,
    (SELECT COUNT(*) FROM forensic_analyses fa WHERE fa.case_id = c.id) as analysis_count,
    (SELECT COUNT(*) FROM iocs i WHERE i.case_id = c.id) as ioc_count,
    (SELECT COUNT(*) FROM timeline_events te WHERE te.case_id = c.id) as event_count,
    (SELECT COUNT(*) FROM processes p WHERE p.case_id = c.id AND p.status = 'running') as running_processes
FROM cases c;


-- Análisis recientes
CREATE OR REPLACE VIEW v_recent_analyses AS
SELECT 
    fa.id,
    fa.case_id,
    fa.tool_name,
    fa.analysis_type,
    fa.status,
    fa.created_at,
    fa.completed_at,
    EXTRACT(EPOCH FROM (fa.completed_at - fa.started_at)) as duration_seconds,
    jsonb_array_length(fa.evidence_files) as evidence_count
FROM forensic_analyses fa
ORDER BY fa.created_at DESC
LIMIT 100;


-- ============================================================================
-- DATOS INICIALES
-- ============================================================================

-- Usuario administrador por defecto
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@localhost', 'CHANGE_THIS_HASH', 'admin')
ON CONFLICT (username) DO NOTHING;


-- Confirmación
SELECT 'PostgreSQL schema v4.4.1 initialized successfully' as status;
