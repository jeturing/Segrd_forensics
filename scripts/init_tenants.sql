-- Multi-Tenancy Schema for MCP Forensics
-- Version: 4.6.0
-- Created: 2024-12-27

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================
-- TENANTS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    tenant_code VARCHAR(50) NOT NULL UNIQUE,
    settings JSONB DEFAULT '{}',
    features JSONB DEFAULT '{"m365": true, "redteam": false, "agents": false}',
    limits JSONB DEFAULT '{"max_cases": 100, "max_users": 10, "max_storage_gb": 50}',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'trial', 'deleted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Default tenant
INSERT INTO tenants (id, name, slug, tenant_code, features, limits) VALUES 
(
    '00000000-0000-0000-0000-000000000000',
    'Jeturing Default',
    'jeturing-default',
    'Jeturing_00000000-0000-0000-0000-000000000000',
    '{"m365": true, "redteam": true, "agents": true, "llm": true}',
    '{"max_cases": 1000, "max_users": 100, "max_storage_gb": 500}'
) ON CONFLICT (id) DO NOTHING;

-- =============================================
-- USERS TABLE (Multi-tenant)
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'analyst' CHECK (role IN ('admin', 'analyst', 'viewer', 'operator', 'redteam')),
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

-- Default admin user (password: admin123 - CHANGE IN PRODUCTION)
INSERT INTO users (tenant_id, email, hashed_password, full_name, role, is_superuser) VALUES
(
    '00000000-0000-0000-0000-000000000000',
    'admin@jeturing.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4E/dIGNV8MBVxQ.y',
    'System Administrator',
    'admin',
    true
) ON CONFLICT DO NOTHING;

-- =============================================
-- API KEYS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    scopes JSONB DEFAULT '["read", "write"]',
    rate_limit INTEGER DEFAULT 100,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- LLM SESSIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS llm_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    model_used VARCHAR(100) NOT NULL,
    provider VARCHAR(50) DEFAULT 'ollama' CHECK (provider IN ('ollama', 'openai', 'anthropic', 'azure')),
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    context JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE
);

-- =============================================
-- INDEXES
-- =============================================
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_llm_sessions_tenant ON llm_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_sessions_user ON llm_sessions(user_id);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_sessions ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation_users ON users
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_api_keys ON api_keys
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_llm_sessions ON llm_sessions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- =============================================
-- TRIGGER: Updated At
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================
-- GRANT PERMISSIONS
-- =============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO forensics;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO forensics;
