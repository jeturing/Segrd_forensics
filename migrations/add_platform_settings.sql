-- =============================================================================
-- MCP Kali Forensics - Platform Settings Table v4.6
-- Migración para crear tabla de configuración global de la plataforma
-- Ejecutar con: psql -U forensics -d forensics -f add_platform_settings.sql
-- =============================================================================

-- ============================================================================
-- TABLA: platform_settings
-- Almacena configuración global de la plataforma (key-value)
-- ============================================================================
CREATE TABLE IF NOT EXISTS platform_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'string',  -- string, number, boolean, json
    category VARCHAR(50) DEFAULT 'general',   -- general, security, billing, email, system
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,           -- true para valores sensibles (keys, passwords)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_platform_settings_category ON platform_settings(category);
CREATE INDEX IF NOT EXISTS idx_platform_settings_updated ON platform_settings(updated_at DESC);

-- ============================================================================
-- DATOS INICIALES - Configuración por defecto
-- ============================================================================

-- General
INSERT INTO platform_settings (key, value, value_type, category, description) VALUES
('site_name', 'JETURING Forensics', 'string', 'general', 'Nombre del sitio'),
('site_url', 'https://forensics.jeturing.com', 'string', 'general', 'URL pública del sitio'),
('support_email', 'support@jeturing.com', 'string', 'general', 'Email de soporte')
ON CONFLICT (key) DO NOTHING;

-- Registration
INSERT INTO platform_settings (key, value, value_type, category, description) VALUES
('allow_public_registration', 'true', 'boolean', 'registration', 'Permitir registro público'),
('require_email_verification', 'true', 'boolean', 'registration', 'Requerir verificación de email'),
('default_trial_days', '15', 'number', 'registration', 'Días de trial gratuito')
ON CONFLICT (key) DO NOTHING;

-- Billing/Stripe
INSERT INTO platform_settings (key, value, value_type, category, description, is_secret) VALUES
('stripe_enabled', 'true', 'boolean', 'billing', 'Habilitar integración con Stripe', FALSE),
('stripe_mode', 'test', 'string', 'billing', 'Modo de Stripe (test/live)', FALSE),
('stripe_public_key', 'pk_test_placeholder', 'string', 'billing', 'Clave pública de Stripe', FALSE)
ON CONFLICT (key) DO NOTHING;

-- Email/SMTP
INSERT INTO platform_settings (key, value, value_type, category, description, is_secret) VALUES
('smtp_host', 'smtp.sendgrid.net', 'string', 'email', 'Host del servidor SMTP', FALSE),
('smtp_port', '587', 'number', 'email', 'Puerto del servidor SMTP', FALSE),
('smtp_user', 'apikey', 'string', 'email', 'Usuario SMTP', FALSE),
('from_email', 'noreply@jeturing.com', 'string', 'email', 'Email remitente', FALSE)
ON CONFLICT (key) DO NOTHING;

-- Security
INSERT INTO platform_settings (key, value, value_type, category, description) VALUES
('session_timeout', '3600', 'number', 'security', 'Timeout de sesión en segundos'),
('max_login_attempts', '5', 'number', 'security', 'Máximo intentos de login'),
('lockout_duration', '900', 'number', 'security', 'Duración del bloqueo en segundos'),
('require_mfa', 'false', 'boolean', 'security', 'Requerir MFA para todos')
ON CONFLICT (key) DO NOTHING;

-- System
INSERT INTO platform_settings (key, value, value_type, category, description) VALUES
('maintenance_mode', 'false', 'boolean', 'system', 'Modo mantenimiento activo'),
('debug_mode', 'false', 'boolean', 'system', 'Modo debug activo'),
('log_level', 'INFO', 'string', 'system', 'Nivel de logging (DEBUG, INFO, WARNING, ERROR)')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- FUNCIÓN: get_setting
-- Obtener un setting individual con valor por defecto
-- ============================================================================
CREATE OR REPLACE FUNCTION get_setting(setting_key VARCHAR, default_value TEXT DEFAULT NULL)
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    SELECT value INTO result FROM platform_settings WHERE key = setting_key;
    RETURN COALESCE(result, default_value);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCIÓN: set_setting
-- Actualizar o crear un setting
-- ============================================================================
CREATE OR REPLACE FUNCTION set_setting(
    setting_key VARCHAR, 
    setting_value TEXT,
    setting_type VARCHAR DEFAULT 'string',
    setting_category VARCHAR DEFAULT 'general',
    setting_description TEXT DEFAULT NULL,
    user_id UUID DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO platform_settings (key, value, value_type, category, description, updated_by, updated_at)
    VALUES (setting_key, setting_value, setting_type, setting_category, setting_description, user_id, NOW())
    ON CONFLICT (key) DO UPDATE 
    SET value = EXCLUDED.value,
        value_type = COALESCE(EXCLUDED.value_type, platform_settings.value_type),
        category = COALESCE(EXCLUDED.category, platform_settings.category),
        description = COALESCE(EXCLUDED.description, platform_settings.description),
        updated_by = EXCLUDED.updated_by,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMENTARIOS
-- ============================================================================
COMMENT ON TABLE platform_settings IS 'Configuración global de la plataforma JETURING';
COMMENT ON COLUMN platform_settings.key IS 'Clave única del setting (snake_case)';
COMMENT ON COLUMN platform_settings.value IS 'Valor almacenado como texto';
COMMENT ON COLUMN platform_settings.value_type IS 'Tipo del valor: string, number, boolean, json';
COMMENT ON COLUMN platform_settings.category IS 'Categoría para agrupación en UI';
COMMENT ON COLUMN platform_settings.is_secret IS 'TRUE para valores sensibles que no deben exponerse';

-- Verificación
DO $$
BEGIN
    RAISE NOTICE '✅ Tabla platform_settings creada con % registros iniciales',
        (SELECT COUNT(*) FROM platform_settings);
END $$;
