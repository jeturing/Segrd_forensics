-- =============================================================================
-- MCP Kali Forensics - Landing Content v1
-- Tabla para gestionar el contenido editable del Landing (i18n)
-- =============================================================================

CREATE TABLE IF NOT EXISTS landing_content (
    id SERIAL PRIMARY KEY,
    section VARCHAR(50) NOT NULL, -- 'plans','features','testimonials','stats','integrations','capabilities','hero'
    locale VARCHAR(8) NOT NULL DEFAULT 'es',
    content JSONB NOT NULL,
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID NULL
);

CREATE INDEX IF NOT EXISTS idx_landing_section_locale ON landing_content(section, locale);
CREATE INDEX IF NOT EXISTS idx_landing_active ON landing_content(is_active);

-- Constraint única para upsert por sección+locale
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_landing_section_locale'
  ) THEN
    ALTER TABLE landing_content
    ADD CONSTRAINT uq_landing_section_locale UNIQUE (section, locale);
  END IF;
END $$;

-- Seed inicial mínimo (es)
INSERT INTO landing_content(section, locale, content, display_order)
VALUES
('stats','es', '{"items":[{"value":"10K+","label":"Incidentes Investigados"},{"value":"500+","label":"Organizaciones"},{"value":"99.9%","label":"Uptime SLA"},{"value":"< 5min","label":"Tiempo de Respuesta"}]}'::jsonb, 0)
ON CONFLICT DO NOTHING;

INSERT INTO landing_content(section, locale, content, display_order)
VALUES
('plans','es', '{"items":[
  {"name":"Starter","price":"Free","period":"14 días trial","description":"Ideal para probar la plataforma","features":["1 usuario","1 agente LLM básico","100 queries/mes","M365 básico","Soporte comunidad"],"cta":"Comenzar Gratis","highlighted":false},
  {"name":"Professional","price":"$199","period":"/mes","description":"Para equipos de seguridad","features":["Hasta 5 usuarios","3 agentes LLM","1,000 queries/mes","M365 + Endpoints","Credential checks","SOAR básico","Soporte email 24h"],"cta":"Empezar Ahora","highlighted":true},
  {"name":"Enterprise","price":"Custom","period":"contactar","description":"Para grandes organizaciones","features":["Usuarios ilimitados","Agentes LLM ilimitados","Queries ilimitados","Todas las integraciones","On-premise disponible","SLA 99.9%","Soporte 24/7 dedicado","Capacitación incluida"],"cta":"Contactar Ventas","highlighted":false}
]}'::jsonb, 0)
ON CONFLICT DO NOTHING;

INSERT INTO landing_content(section, locale, content, display_order)
VALUES
('features','es', '{"items":[
  {"title":"Microsoft 365 Forensics","description":"Análisis completo de Azure AD, Exchange Online, SharePoint y Teams.","highlights":["Azure AD Sign-in Analysis","Unified Audit Logs","OAuth App Detection","Sparrow & Hawk Integration"],"icon":"cloud"},
  {"title":"Endpoint Analysis","description":"Análisis forense de endpoints con Loki, YARA, Volatility y OSQuery.","highlights":["Memory Forensics","IOC Scanning","YARA Rules","Process Analysis"],"icon":"terminal"}
]}'::jsonb, 0)
ON CONFLICT DO NOTHING;
