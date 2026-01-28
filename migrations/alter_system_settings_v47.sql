-- ============================================================================
-- ALTER SYSTEM SETTINGS TABLE v4.7
-- Agrega columnas faltantes para soporte completo de configuración dinámica
-- ============================================================================

-- Agregar columnas faltantes a system_settings
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS subcategory VARCHAR(50);
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS is_secret BOOLEAN DEFAULT FALSE;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS is_editable BOOLEAN DEFAULT TRUE;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS env_var_name VARCHAR(100);
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100);

-- Actualizar display_name con valores por defecto basados en key
UPDATE system_settings 
SET display_name = INITCAP(REPLACE(REPLACE(key, '_', ' '), '.', ' '))
WHERE display_name IS NULL;

-- Verificar llm_models
CREATE TABLE IF NOT EXISTS llm_models (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    context_length INTEGER DEFAULT 4096,
    capabilities JSONB DEFAULT '["chat", "completion"]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 100,
    endpoint_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider, model_id)
);

-- Insertar modelos LLM base (solo si no existen)
INSERT INTO llm_models (provider, model_id, display_name, description, context_length, is_active, is_default, priority, endpoint_url)
VALUES 
    ('ollama', 'llama3.2:1b', 'Llama 3.2 1B', 'Meta Llama 3.2 1B - Modelo ligero', 4096, true, true, 1, 'http://ollama:11434'),
    ('ollama', 'llama3.2:3b', 'Llama 3.2 3B', 'Meta Llama 3.2 3B - Balance rendimiento/calidad', 4096, true, false, 2, 'http://ollama:11434'),
    ('ollama', 'codellama:7b', 'CodeLlama 7B', 'CodeLlama - Especializado en código', 8192, true, false, 3, 'http://ollama:11434'),
    ('ollama', 'mistral:7b', 'Mistral 7B', 'Mistral AI 7B - Alta calidad', 8192, true, false, 4, 'http://ollama:11434'),
    ('lm_studio', 'default', 'LM Studio Default', 'Modelo configurado en LM Studio', 4096, true, false, 10, 'http://100.101.115.5:2714'),
    ('openai', 'gpt-4o-mini', 'GPT-4o Mini', 'OpenAI GPT-4o Mini', 128000, false, false, 20, 'https://api.openai.com/v1'),
    ('openai', 'gpt-4o', 'GPT-4o', 'OpenAI GPT-4o', 128000, false, false, 21, 'https://api.openai.com/v1')
ON CONFLICT (provider, model_id) DO NOTHING;

-- Insertar configuraciones base (solo si no existen)
INSERT INTO system_settings (key, value, value_type, category, display_name, description, is_secret, priority)
VALUES 
    -- LLM Settings
    ('llm.provider', 'ollama', 'string', 'llm', 'LLM Provider', 'Proveedor de LLM predeterminado (ollama, lm_studio, openai)', false, 1),
    ('llm.ollama.url', 'http://ollama:11434', 'string', 'llm', 'Ollama URL', 'URL del servidor Ollama', false, 2),
    ('llm.ollama.model', 'llama3.2:1b', 'string', 'llm', 'Ollama Model', 'Modelo predeterminado de Ollama', false, 3),
    ('llm.ollama.enabled', 'true', 'boolean', 'llm', 'Ollama Enabled', 'Habilitar integración Ollama', false, 4),
    ('llm.lmstudio.url', 'http://100.101.115.5:2714', 'string', 'llm', 'LM Studio URL', 'URL del servidor LM Studio', false, 5),
    ('llm.openai.key', '', 'string', 'llm', 'OpenAI API Key', 'API Key de OpenAI', true, 6),
    
    -- SMTP Settings
    ('smtp.server', 'smtp.zoho.com', 'string', 'email', 'SMTP Server', 'Servidor SMTP', false, 1),
    ('smtp.port', '587', 'integer', 'email', 'SMTP Port', 'Puerto SMTP', false, 2),
    ('smtp.username', '', 'string', 'email', 'SMTP Username', 'Usuario SMTP', false, 3),
    ('smtp.password', '', 'string', 'email', 'SMTP Password', 'Contraseña SMTP', true, 4),
    ('smtp.from', 'noreply@segrd.com', 'string', 'email', 'From Email', 'Email remitente', false, 5),
    ('smtp.checklist.cc', 'jcarvajal@jeturing.com,info@jeturing.com,elsaencarnacion@esecure.do', 'string', 'email', 'Checklist CC Emails', 'Emails CC para security checklist', false, 6),
    
    -- MINIO Settings
    ('minio.endpoint', 'minio:9000', 'string', 'storage', 'MinIO Endpoint', 'Endpoint MinIO', false, 1),
    ('minio.access_key', '', 'string', 'storage', 'MinIO Access Key', 'Access Key MinIO', true, 2),
    ('minio.secret_key', '', 'string', 'storage', 'MinIO Secret Key', 'Secret Key MinIO', true, 3),
    ('minio.bucket', 'forensics-evidence', 'string', 'storage', 'MinIO Bucket', 'Bucket por defecto', false, 4),
    
    -- Security Settings
    ('security.jwt_secret', '', 'string', 'security', 'JWT Secret', 'Secreto para tokens JWT', true, 1),
    ('security.api_key', '', 'string', 'security', 'API Key', 'API Key principal del sistema', true, 2),
    ('security.encryption_key', '', 'string', 'security', 'Encryption Key', 'Clave para encriptación de secrets', true, 3),
    
    -- Database Settings
    ('database.host', 'mcp-forensics-db', 'string', 'database', 'DB Host', 'Host PostgreSQL', false, 1),
    ('database.port', '5432', 'integer', 'database', 'DB Port', 'Puerto PostgreSQL', false, 2),
    ('database.name', 'forensics', 'string', 'database', 'DB Name', 'Nombre de base de datos', false, 3),
    ('database.user', 'forensics', 'string', 'database', 'DB User', 'Usuario PostgreSQL', false, 4)
    
ON CONFLICT (key) DO NOTHING;

-- Mostrar resumen
DO $$
DECLARE
    settings_count INT;
    models_count INT;
BEGIN
    SELECT COUNT(*) INTO settings_count FROM system_settings;
    SELECT COUNT(*) INTO models_count FROM llm_models;
    
    RAISE NOTICE '✅ Migración v4.7 completada';
    RAISE NOTICE '   - system_settings: % registros', settings_count;
    RAISE NOTICE '   - llm_models: % registros', models_count;
END $$;
