-- ============================================================================
-- COST MANAGEMENT & PRICING SYSTEM v1.0
-- Gestión de costos, precios y configuración de planes
-- Created: 2025-12-29
-- ============================================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. TABLA DE PLANES DE SERVICIO
-- ============================================================================
CREATE TABLE IF NOT EXISTS service_plans (
    id SERIAL PRIMARY KEY,
    plan_code VARCHAR(50) UNIQUE NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    plan_description TEXT,
    
    -- Precios en USD (centavos)
    price_monthly_cents INTEGER NOT NULL DEFAULT 0,
    price_annually_cents INTEGER NOT NULL DEFAULT 0,
    
    -- Stripe IDs (se llenan después de crear en Stripe)
    stripe_product_id VARCHAR(100),
    stripe_price_monthly_id VARCHAR(100),
    stripe_price_annually_id VARCHAR(100),
    
    -- Límites del plan
    max_users INTEGER DEFAULT -1, -- -1 = ilimitado
    max_cases_monthly INTEGER DEFAULT -1,
    max_analyses_monthly INTEGER DEFAULT -1,
    max_storage_gb INTEGER DEFAULT -1,
    max_api_calls_daily INTEGER DEFAULT -1,
    
    -- Features incluidas (JSONB para flexibilidad)
    features JSONB DEFAULT '{}',
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    is_visible BOOLEAN DEFAULT true, -- Mostrar en página de precios
    sort_order INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    CONSTRAINT check_prices CHECK (
        price_monthly_cents >= 0 AND 
        price_annually_cents >= 0
    )
);

CREATE INDEX idx_service_plans_active ON service_plans(is_active, is_visible);
CREATE INDEX idx_service_plans_code ON service_plans(plan_code);

-- ============================================================================
-- 2. TABLA DE COSTOS DE RECURSOS
-- ============================================================================
CREATE TABLE IF NOT EXISTS resource_costs (
    id SERIAL PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL, -- 'analysis', 'storage', 'api_call', 'user'
    resource_name VARCHAR(100) NOT NULL,
    resource_description TEXT,
    
    -- Costos en USD (centavos)
    cost_per_unit_cents INTEGER NOT NULL,
    billing_unit VARCHAR(50) DEFAULT 'unit', -- 'unit', 'gb', 'hour', 'thousand'
    
    -- Costos específicos por herramienta
    tool_name VARCHAR(100), -- 'sparrow', 'hawk', 'loki', 'yara', etc.
    
    -- Configuración de facturación
    is_billable BOOLEAN DEFAULT true,
    min_billable_units INTEGER DEFAULT 1,
    
    -- Metadata
    effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_cost_positive CHECK (cost_per_unit_cents >= 0)
);

CREATE INDEX idx_resource_costs_type ON resource_costs(resource_type, is_active);
CREATE INDEX idx_resource_costs_tool ON resource_costs(tool_name);
CREATE INDEX idx_resource_costs_effective ON resource_costs(effective_from, effective_until);

-- ============================================================================
-- 3. TABLA DE USO DE RECURSOS (Para facturación)
-- ============================================================================
CREATE TABLE IF NOT EXISTS resource_usage (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID,
    case_id UUID,
    
    -- Recurso consumido
    resource_cost_id INTEGER REFERENCES resource_costs(id),
    resource_type VARCHAR(50) NOT NULL,
    resource_name VARCHAR(100),
    
    -- Cantidad consumida
    units_consumed DECIMAL(10, 4) NOT NULL DEFAULT 1,
    cost_per_unit_cents INTEGER NOT NULL,
    total_cost_cents INTEGER NOT NULL,
    
    -- Contexto de uso
    analysis_id UUID,
    tool_name VARCHAR(100),
    execution_time_seconds INTEGER,
    
    -- Facturación
    billing_period VARCHAR(20), -- 'YYYY-MM'
    is_billed BOOLEAN DEFAULT false,
    invoice_id UUID,
    
    -- Metadata
    consumed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_usage_positive CHECK (
        units_consumed > 0 AND 
        cost_per_unit_cents >= 0 AND 
        total_cost_cents >= 0
    )
);

CREATE INDEX idx_resource_usage_tenant ON resource_usage(tenant_id, billing_period);
CREATE INDEX idx_resource_usage_case ON resource_usage(case_id);
CREATE INDEX idx_resource_usage_period ON resource_usage(billing_period, is_billed);
CREATE INDEX idx_resource_usage_consumed ON resource_usage(consumed_at);

-- Particionado por mes (para performance en facturación)
CREATE TABLE IF NOT EXISTS resource_usage_2025_01 PARTITION OF resource_usage
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE IF NOT EXISTS resource_usage_2025_02 PARTITION OF resource_usage
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE IF NOT EXISTS resource_usage_2025_03 PARTITION OF resource_usage
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

-- ============================================================================
-- 4. TABLA DE CONFIGURACIÓN DE PRECIOS PERSONALIZADOS
-- ============================================================================
CREATE TABLE IF NOT EXISTS custom_pricing (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL UNIQUE,
    
    -- Plan base
    base_plan_id INTEGER REFERENCES service_plans(id),
    
    -- Descuentos
    discount_percentage DECIMAL(5, 2) DEFAULT 0,
    discount_amount_cents INTEGER DEFAULT 0,
    discount_reason TEXT,
    
    -- Límites personalizados
    custom_max_users INTEGER,
    custom_max_cases_monthly INTEGER,
    custom_max_analyses_monthly INTEGER,
    custom_max_storage_gb INTEGER,
    custom_max_api_calls_daily INTEGER,
    
    -- Precios personalizados (override de plan base)
    custom_price_monthly_cents INTEGER,
    custom_price_annually_cents INTEGER,
    
    -- Features adicionales
    additional_features JSONB DEFAULT '{}',
    
    -- Vigencia
    effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    approved_by VARCHAR(100),
    notes TEXT
);

CREATE INDEX idx_custom_pricing_tenant ON custom_pricing(tenant_id);
CREATE INDEX idx_custom_pricing_active ON custom_pricing(is_active, effective_from, effective_until);

-- ============================================================================
-- 5. VISTA DE COSTOS POR TENANT
-- ============================================================================
CREATE OR REPLACE VIEW v_tenant_costs_summary AS
SELECT 
    ru.tenant_id,
    ru.billing_period,
    COUNT(*) as total_operations,
    SUM(ru.units_consumed) as total_units,
    SUM(ru.total_cost_cents) as total_cost_cents,
    ROUND(SUM(ru.total_cost_cents)::numeric / 100, 2) as total_cost_usd,
    COUNT(DISTINCT ru.case_id) as cases_count,
    COUNT(DISTINCT ru.user_id) as users_count,
    MIN(ru.consumed_at) as period_start,
    MAX(ru.consumed_at) as period_end
FROM resource_usage ru
GROUP BY ru.tenant_id, ru.billing_period;

-- ============================================================================
-- 6. VISTA DE COSTOS POR HERRAMIENTA
-- ============================================================================
CREATE OR REPLACE VIEW v_tool_costs_summary AS
SELECT 
    ru.tenant_id,
    ru.tool_name,
    ru.billing_period,
    COUNT(*) as execution_count,
    SUM(ru.units_consumed) as total_units,
    SUM(ru.total_cost_cents) as total_cost_cents,
    ROUND(SUM(ru.total_cost_cents)::numeric / 100, 2) as total_cost_usd,
    AVG(ru.execution_time_seconds) as avg_execution_seconds,
    MAX(ru.consumed_at) as last_used
FROM resource_usage ru
WHERE ru.tool_name IS NOT NULL
GROUP BY ru.tenant_id, ru.tool_name, ru.billing_period;

-- ============================================================================
-- 7. FUNCIÓN PARA REGISTRAR USO DE RECURSOS
-- ============================================================================
CREATE OR REPLACE FUNCTION register_resource_usage(
    p_tenant_id UUID,
    p_resource_type VARCHAR,
    p_resource_name VARCHAR,
    p_units DECIMAL,
    p_user_id UUID DEFAULT NULL,
    p_case_id UUID DEFAULT NULL,
    p_analysis_id UUID DEFAULT NULL,
    p_tool_name VARCHAR DEFAULT NULL,
    p_execution_seconds INTEGER DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_usage_id UUID;
    v_cost_per_unit INTEGER;
    v_total_cost INTEGER;
    v_billing_period VARCHAR;
    v_resource_cost_id INTEGER;
BEGIN
    -- Obtener costo actual del recurso
    SELECT id, cost_per_unit_cents 
    INTO v_resource_cost_id, v_cost_per_unit
    FROM resource_costs
    WHERE resource_type = p_resource_type
      AND (tool_name = p_tool_name OR tool_name IS NULL)
      AND is_active = true
      AND effective_from <= CURRENT_TIMESTAMP
      AND (effective_until IS NULL OR effective_until > CURRENT_TIMESTAMP)
    ORDER BY tool_name DESC NULLS LAST
    LIMIT 1;
    
    -- Si no hay costo configurado, usar 0
    IF v_cost_per_unit IS NULL THEN
        v_cost_per_unit := 0;
    END IF;
    
    -- Calcular costo total
    v_total_cost := (p_units * v_cost_per_unit)::INTEGER;
    
    -- Periodo de facturación actual
    v_billing_period := TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM');
    
    -- Insertar registro de uso
    INSERT INTO resource_usage (
        tenant_id, user_id, case_id, analysis_id,
        resource_cost_id, resource_type, resource_name,
        units_consumed, cost_per_unit_cents, total_cost_cents,
        tool_name, execution_time_seconds,
        billing_period, consumed_at
    ) VALUES (
        p_tenant_id, p_user_id, p_case_id, p_analysis_id,
        v_resource_cost_id, p_resource_type, p_resource_name,
        p_units, v_cost_per_unit, v_total_cost,
        p_tool_name, p_execution_seconds,
        v_billing_period, CURRENT_TIMESTAMP
    ) RETURNING id INTO v_usage_id;
    
    RETURN v_usage_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. DATOS INICIALES - PLANES DE SERVICIO
-- ============================================================================
INSERT INTO service_plans (
    plan_code, plan_name, plan_description,
    price_monthly_cents, price_annually_cents,
    max_users, max_cases_monthly, max_analyses_monthly,
    max_storage_gb, max_api_calls_daily,
    features, is_active, is_visible, sort_order
) VALUES 
-- Plan Gratuito (Free/Starter)
(
    'free',
    'Free Tier',
    'Plan gratuito con funcionalidades básicas para empezar',
    0, -- $0/mes
    0, -- $0/año
    1, -- 1 usuario
    5, -- 5 casos/mes
    10, -- 10 análisis/mes
    1, -- 1GB storage
    100, -- 100 API calls/día
    '{
        "m365_basic_analysis": true,
        "credential_check": true,
        "basic_reports": true,
        "community_support": true,
        "data_retention_days": 30
    }'::jsonb,
    true, true, 1
),
-- Plan Professional
(
    'professional',
    'Professional',
    'Para equipos pequeños con necesidades avanzadas',
    9900, -- $99/mes
    95040, -- $950.40/año ($79.20/mes - 20% descuento)
    5, -- 5 usuarios
    50, -- 50 casos/mes
    200, -- 200 análisis/mes
    50, -- 50GB storage
    1000, -- 1000 API calls/día
    '{
        "all_forensic_tools": true,
        "advanced_m365_analysis": true,
        "endpoint_analysis": true,
        "credential_monitoring": true,
        "custom_reports": true,
        "email_support": true,
        "api_access": true,
        "data_retention_days": 90,
        "webhook_integrations": true
    }'::jsonb,
    true, true, 2
),
-- Plan Enterprise
(
    'enterprise',
    'Enterprise',
    'Para organizaciones grandes con requisitos enterprise',
    49900, -- $499/mes
    479040, -- $4,790.40/año ($399.20/mes - 20% descuento)
    -1, -- Usuarios ilimitados
    -1, -- Casos ilimitados
    -1, -- Análisis ilimitados
    500, -- 500GB storage
    10000, -- 10,000 API calls/día
    '{
        "all_forensic_tools": true,
        "advanced_m365_analysis": true,
        "endpoint_analysis": true,
        "credential_monitoring": true,
        "custom_reports": true,
        "priority_support": true,
        "dedicated_account_manager": true,
        "api_access": true,
        "data_retention_days": 365,
        "webhook_integrations": true,
        "sso_saml": true,
        "custom_integrations": true,
        "sla_99_9": true,
        "white_label": true,
        "on_premise_deployment": true
    }'::jsonb,
    true, true, 3
)
ON CONFLICT (plan_code) DO NOTHING;

-- ============================================================================
-- 9. DATOS INICIALES - COSTOS DE RECURSOS
-- ============================================================================
INSERT INTO resource_costs (
    resource_type, resource_name, resource_description,
    cost_per_unit_cents, billing_unit, tool_name, is_billable
) VALUES 
-- Análisis M365
('analysis', 'M365 Sparrow Analysis', 'Análisis con Sparrow para M365', 500, 'unit', 'sparrow', true),
('analysis', 'M365 Hawk Analysis', 'Análisis con Hawk para Exchange', 300, 'unit', 'hawk', true),
('analysis', 'M365 O365 Extractor', 'Extracción de logs con O365 Extractor', 200, 'unit', 'o365_extractor', true),

-- Análisis de Endpoints
('analysis', 'Loki Scanner', 'Escaneo con Loki IOC Scanner', 100, 'unit', 'loki', true),
('analysis', 'YARA Scan', 'Escaneo con reglas YARA', 50, 'unit', 'yara', true),
('analysis', 'OSQuery Analysis', 'Análisis con OSQuery', 75, 'unit', 'osquery', true),
('analysis', 'Volatility Memory Analysis', 'Análisis de memoria con Volatility', 1000, 'unit', 'volatility', true),

-- Verificación de credenciales
('analysis', 'HIBP Check', 'Verificación en HaveIBeenPwned', 1, 'unit', 'hibp', true),
('analysis', 'Dehashed Check', 'Búsqueda en Dehashed', 5, 'unit', 'dehashed', true),

-- Storage
('storage', 'Evidence Storage', 'Almacenamiento de evidencia', 10, 'gb', NULL, true),
('storage', 'Report Storage', 'Almacenamiento de reportes', 5, 'gb', NULL, true),

-- API Calls
('api_call', 'API Request', 'Llamada a API REST', 0, 'thousand', NULL, false),

-- Usuarios adicionales (para planes con límite)
('user', 'Additional User', 'Usuario adicional más allá del límite del plan', 1000, 'unit', NULL, true)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. TRIGGER PARA ACTUALIZAR updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_cost_tables_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_service_plans_timestamp
    BEFORE UPDATE ON service_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_cost_tables_timestamp();

CREATE TRIGGER trigger_update_resource_costs_timestamp
    BEFORE UPDATE ON resource_costs
    FOR EACH ROW
    EXECUTE FUNCTION update_cost_tables_timestamp();

CREATE TRIGGER trigger_update_custom_pricing_timestamp
    BEFORE UPDATE ON custom_pricing
    FOR EACH ROW
    EXECUTE FUNCTION update_cost_tables_timestamp();

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================
DO $$ 
BEGIN
    RAISE NOTICE 'Cost Management System initialized successfully';
    RAISE NOTICE 'Service Plans: %', (SELECT COUNT(*) FROM service_plans);
    RAISE NOTICE 'Resource Costs: %', (SELECT COUNT(*) FROM resource_costs);
END $$;
