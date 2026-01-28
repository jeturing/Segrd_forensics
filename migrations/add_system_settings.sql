-- =============================================================================
-- MCP Kali Forensics - System Settings Table v4.7
-- Migración para crear tabla de configuración del sistema con encriptación
-- Ejecutar con: psql -U forensics -d forensics -f add_system_settings.sql
-- =============================================================================

-- Extensión para encriptación (si no existe)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- TABLA: system_settings
-- Almacena TODAS las configuraciones del sistema (reemplaza config.py hardcoded)
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,                            -- Valor encriptado si is_secret=true
    value_type VARCHAR(20) DEFAULT 'string',  -- string, int, bool, json, path
    category VARCHAR(50) NOT NULL,         -- llm, smtp, minio, database, tools, api_keys, security
    subcategory VARCHAR(50),               -- Para agrupar (ej: category=llm, subcategory=ollama)
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,
    is_encrypted BOOLEAN DEFAULT FALSE,    -- TRUE si value está encriptado
    is_editable BOOLEAN DEFAULT TRUE,      -- FALSE para settings de solo lectura
    validation_regex VARCHAR(500),         -- Regex para validación
    default_value TEXT,                    -- Valor por defecto
    env_var_name VARCHAR(100),             -- Nombre de variable de entorno correspondiente
    priority INT DEFAULT 100,              -- Orden de visualización
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);
CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);
CREATE INDEX IF NOT EXISTS idx_system_settings_subcategory ON system_settings(category, subcategory);

-- ============================================================================
-- TABLA: llm_models
-- Catálogo de modelos LLM disponibles
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_models (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,         -- ollama, lm_studio, openai, local
    model_id VARCHAR(200) NOT NULL,        -- llama3.2:1b, phi-4, gpt-4, etc.
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    context_length INT DEFAULT 4096,
    capabilities JSONB DEFAULT '["chat", "completion"]',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 100,              -- Menor = más prioritario
    endpoint_url VARCHAR(500),             -- URL específica del modelo (override)
    config JSONB DEFAULT '{}',             -- Configuración específica (temperature, etc)
    last_used TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(provider, model_id)
);

-- ============================================================================
-- TABLA: api_configurations (si no existe)
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_configurations (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    value TEXT,                            -- Encriptado si is_secret=true
    is_secret BOOLEAN DEFAULT TRUE,
    is_encrypted BOOLEAN DEFAULT FALSE,
    service_name VARCHAR(100),
    service_url VARCHAR(500),
    is_enabled BOOLEAN DEFAULT TRUE,
    is_configured BOOLEAN DEFAULT FALSE,
    last_validated TIMESTAMP WITH TIME ZONE,
    validation_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- ============================================================================
-- DATOS INICIALES - LLM Configuration
-- ============================================================================

-- Proveedor LLM principal
INSERT INTO system_settings (key, value, value_type, category, subcategory, display_name, description, env_var_name, priority) VALUES
('llm_provider', 'ollama', 'string', 'llm', 'general', 'Proveedor LLM Principal', 'Proveedor activo: ollama, lm_studio, openai, offline', 'LLM_PROVIDER', 10),
('llm_fallback_enabled', 'true', 'bool', 'llm', 'general', 'Fallback Automático', 'Cambiar a otro proveedor si el principal falla', NULL, 20),
('llm_timeout', '180', 'int', 'llm', 'general', 'Timeout General (segundos)', 'Tiempo máximo de espera para respuestas LLM', NULL, 30)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- Ollama
INSERT INTO system_settings (key, value, value_type, category, subcategory, display_name, description, env_var_name, priority) VALUES
('ollama_enabled', 'true', 'bool', 'llm', 'ollama', 'Ollama Habilitado', 'Habilitar proveedor Ollama', 'OLLAMA_ENABLED', 100),
('ollama_url', 'http://ollama:11434', 'string', 'llm', 'ollama', 'URL de Ollama', 'URL del servicio Ollama (Docker: ollama:11434)', 'OLLAMA_URL', 110),
('ollama_model', 'llama3.2:1b', 'string', 'llm', 'ollama', 'Modelo por Defecto', 'Modelo de Ollama a usar', 'OLLAMA_MODEL', 120),
('ollama_timeout', '180', 'int', 'llm', 'ollama', 'Timeout (segundos)', 'Tiempo máximo para generación', 'OLLAMA_TIMEOUT', 130)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- LM Studio
INSERT INTO system_settings (key, value, value_type, category, subcategory, display_name, description, env_var_name, priority) VALUES
('lm_studio_enabled', 'true', 'bool', 'llm', 'lm_studio', 'LM Studio Habilitado', 'Habilitar proveedor LM Studio', NULL, 200),
('lm_studio_url', 'http://100.101.115.5:2714/v1', 'string', 'llm', 'lm_studio', 'URL de LM Studio', 'URL del servidor LM Studio (Tailscale)', 'LLM_STUDIO_URL', 210),
('lm_studio_model', 'phi-4', 'string', 'llm', 'lm_studio', 'Modelo por Defecto', 'Modelo cargado en LM Studio', 'LLM_STUDIO_MODEL', 220),
('lm_studio_api_key', '', 'string', 'llm', 'lm_studio', 'API Key', 'API Key de LM Studio (opcional)', 'LLM_STUDIO_API_KEY', 230),
('lm_studio_timeout', '120', 'int', 'llm', 'lm_studio', 'Timeout (segundos)', 'Tiempo máximo para generación', 'LLM_STUDIO_TIMEOUT', 240)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- OpenAI
INSERT INTO system_settings (key, value, value_type, category, subcategory, display_name, description, env_var_name, is_secret, priority) VALUES
('openai_enabled', 'false', 'bool', 'llm', 'openai', 'OpenAI Habilitado', 'Habilitar proveedor OpenAI', NULL, false, 300),
('openai_api_key', '', 'string', 'llm', 'openai', 'API Key', 'API Key de OpenAI', 'OPENAI_API_KEY', true, 310),
('openai_model', 'gpt-4o-mini', 'string', 'llm', 'openai', 'Modelo por Defecto', 'Modelo de OpenAI a usar', NULL, false, 320),
('openai_base_url', 'https://api.openai.com/v1', 'string', 'llm', 'openai', 'URL Base', 'URL de la API de OpenAI', NULL, false, 330)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- DATOS INICIALES - SMTP Configuration
-- ============================================================================
INSERT INTO system_settings (key, value, value_type, category, display_name, description, env_var_name, is_secret, priority) VALUES
('smtp_host', 'mail5010.site4now.net', 'string', 'smtp', 'Servidor SMTP', 'Host del servidor de correo', 'SMTP_HOST', false, 10),
('smtp_port', '465', 'int', 'smtp', 'Puerto SMTP', 'Puerto del servidor (465=SSL, 587=TLS)', 'SMTP_PORT', false, 20),
('smtp_user', 'no-reply@sajet.us', 'string', 'smtp', 'Usuario SMTP', 'Usuario para autenticación', 'SMTP_USER', false, 30),
('smtp_password', '', 'string', 'smtp', 'Contraseña SMTP', 'Contraseña para autenticación', 'SMTP_PASSWORD', true, 40),
('smtp_ssl', 'true', 'bool', 'smtp', 'Usar SSL', 'Habilitar conexión SSL', 'SMTP_SSL', false, 50),
('smtp_from_email', 'no-reply@sajet.us', 'string', 'smtp', 'Email Remitente', 'Dirección de envío', 'SMTP_FROM_EMAIL', false, 60),
('smtp_contact_to', 'sales@jeturing.com', 'string', 'smtp', 'Email Contacto', 'Email destino para formularios de contacto', 'SMTP_CONTACT_TO', false, 70),
('smtp_checklist_cc', 'jcarvajal@jeturing.com,info@jeturing.com,elsaencarnacion@esecure.do', 'string', 'smtp', 'CC Security Checklist', 'Emails CC para formulario security checklist', 'SMTP_CHECKLIST_CC_EMAILS', false, 80)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- DATOS INICIALES - MINIO Configuration
-- ============================================================================
INSERT INTO system_settings (key, value, value_type, category, display_name, description, env_var_name, is_secret, priority) VALUES
('minio_enabled', 'true', 'bool', 'minio', 'MinIO Habilitado', 'Habilitar almacenamiento de evidencias', 'MINIO_ENABLED', false, 10),
('minio_endpoint', '10.10.10.5:9000', 'string', 'minio', 'Endpoint MinIO', 'Host:Puerto del servidor MinIO', 'MINIO_ENDPOINT', false, 20),
('minio_access_key', 'Jeturing', 'string', 'minio', 'Access Key', 'Clave de acceso', 'MINIO_ACCESS_KEY', true, 30),
('minio_secret_key', '', 'string', 'minio', 'Secret Key', 'Clave secreta', 'MINIO_SECRET_KEY', true, 40),
('minio_bucket', 'forensics-evidence', 'string', 'minio', 'Bucket por Defecto', 'Nombre del bucket para evidencias', 'MINIO_BUCKET', false, 50),
('minio_secure', 'false', 'bool', 'minio', 'Usar HTTPS', 'Conexión segura', 'MINIO_SECURE', false, 60),
('minio_console_url', 'http://10.10.10.5:9001', 'string', 'minio', 'URL Consola', 'URL de la consola web de MinIO', 'MINIO_CONSOLE_URL', false, 70)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- DATOS INICIALES - Database Configuration
-- ============================================================================
INSERT INTO system_settings (key, value, value_type, category, display_name, description, env_var_name, is_secret, is_editable, priority) VALUES
('postgres_host', 'postgres', 'string', 'database', 'Host PostgreSQL', 'Hostname del servidor', 'POSTGRES_HOST', false, false, 10),
('postgres_port', '5432', 'int', 'database', 'Puerto PostgreSQL', 'Puerto del servidor', 'POSTGRES_PORT', false, false, 20),
('postgres_db', 'forensics', 'string', 'database', 'Base de Datos', 'Nombre de la BD', 'POSTGRES_DB', false, false, 30),
('postgres_user', 'forensics', 'string', 'database', 'Usuario', 'Usuario de conexión', 'POSTGRES_USER', false, false, 40),
('database_url', 'postgresql://forensics:****@postgres:5432/forensics', 'string', 'database', 'URL de Conexión', 'Connection string (password oculto)', 'DATABASE_URL', true, false, 50)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- DATOS INICIALES - Security Configuration
-- ============================================================================
INSERT INTO system_settings (key, value, value_type, category, display_name, description, env_var_name, is_secret, priority) VALUES
('jwt_algorithm', 'HS256', 'string', 'security', 'Algoritmo JWT', 'Algoritmo de firma JWT', 'JWT_ALGORITHM', false, 10),
('jwt_expiration_hours', '24', 'int', 'security', 'Expiración JWT (horas)', 'Tiempo de vida del token', 'JWT_EXPIRATION_HOURS', false, 20),
('rbac_enabled', 'true', 'bool', 'security', 'RBAC Habilitado', 'Control de acceso basado en roles', 'RBAC_ENABLED', false, 30),
('rbac_default_role', 'viewer', 'string', 'security', 'Rol por Defecto', 'Rol asignado a nuevos usuarios', 'RBAC_DEFAULT_ROLE', false, 40)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- DATOS INICIALES - API Keys (terceros)
-- ============================================================================
INSERT INTO api_configurations (key, display_name, description, category, service_name, is_secret) VALUES
('shodan_api_key', 'Shodan API Key', 'API Key para búsquedas Shodan', 'threat_intel', 'Shodan', true),
('virustotal_api_key', 'VirusTotal API Key', 'API Key para análisis de malware', 'malware', 'VirusTotal', true),
('abuseipdb_api_key', 'AbuseIPDB API Key', 'API Key para verificación de IPs', 'threat_intel', 'AbuseIPDB', true),
('hibp_api_key', 'HIBP API Key', 'API Key para Have I Been Pwned', 'credentials', 'HaveIBeenPwned', true),
('dehashed_api_key', 'Dehashed API Key', 'API Key para búsqueda de breaches', 'credentials', 'Dehashed', true),
('securitytrails_api_key', 'SecurityTrails API Key', 'API Key para DNS/subdominios', 'network', 'SecurityTrails', true),
('hunter_api_key', 'Hunter.io API Key', 'API Key para búsqueda de emails', 'identity', 'Hunter.io', true),
('urlscan_api_key', 'URLScan.io API Key', 'API Key para análisis de URLs', 'network', 'URLScan.io', true)
ON CONFLICT (key) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- DATOS INICIALES - Modelos LLM
-- ============================================================================
INSERT INTO llm_models (provider, model_id, display_name, description, context_length, is_active, is_default, priority) VALUES
('ollama', 'llama3.2:1b', 'Llama 3.2 1B', 'Modelo compacto y rápido de Meta', 8192, true, true, 10),
('ollama', 'llama3.2:3b', 'Llama 3.2 3B', 'Modelo mediano de Meta', 8192, true, false, 20),
('ollama', 'phi4', 'Phi-4', 'Modelo de Microsoft optimizado para código', 16384, true, false, 30),
('ollama', 'qwen2.5:7b', 'Qwen 2.5 7B', 'Modelo de Alibaba multilingüe', 32768, true, false, 40),
('ollama', 'deepseek-r1:8b', 'DeepSeek R1 8B', 'Modelo de razonamiento de DeepSeek', 32768, true, false, 50),
('lm_studio', 'phi-4', 'Phi-4 (LM Studio)', 'Modelo cargado en LM Studio', 16384, true, false, 100),
('openai', 'gpt-4o-mini', 'GPT-4o Mini', 'Modelo rápido y económico de OpenAI', 128000, false, false, 200),
('openai', 'gpt-4o', 'GPT-4o', 'Modelo flagship de OpenAI', 128000, false, false, 210)
ON CONFLICT (provider, model_id) DO UPDATE SET updated_at = NOW();

-- ============================================================================
-- FUNCIONES DE UTILIDAD
-- ============================================================================

-- Obtener setting con fallback
CREATE OR REPLACE FUNCTION get_system_setting(setting_key VARCHAR, default_val TEXT DEFAULT NULL)
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    SELECT value INTO result FROM system_settings WHERE key = setting_key;
    RETURN COALESCE(result, default_val);
END;
$$ LANGUAGE plpgsql;

-- Actualizar setting
CREATE OR REPLACE FUNCTION set_system_setting(
    setting_key VARCHAR,
    new_value TEXT,
    user_name VARCHAR DEFAULT 'system'
)
RETURNS VOID AS $$
BEGIN
    UPDATE system_settings 
    SET value = new_value, updated_at = NOW(), updated_by = user_name
    WHERE key = setting_key;
END;
$$ LANGUAGE plpgsql;

-- Obtener todos los settings de una categoría
CREATE OR REPLACE FUNCTION get_settings_by_category(cat VARCHAR)
RETURNS TABLE(key VARCHAR, value TEXT, display_name VARCHAR, is_secret BOOLEAN) AS $$
BEGIN
    RETURN QUERY
    SELECT s.key, s.value, s.display_name, s.is_secret
    FROM system_settings s
    WHERE s.category = cat
    ORDER BY s.priority, s.key;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER: auto-update updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS system_settings_updated ON system_settings;
CREATE TRIGGER system_settings_updated
    BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

DROP TRIGGER IF EXISTS llm_models_updated ON llm_models;
CREATE TRIGGER llm_models_updated
    BEFORE UPDATE ON llm_models
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ system_settings: % registros', (SELECT COUNT(*) FROM system_settings);
    RAISE NOTICE '✅ llm_models: % registros', (SELECT COUNT(*) FROM llm_models);
    RAISE NOTICE '✅ api_configurations: % registros', (SELECT COUNT(*) FROM api_configurations);
END $$;
