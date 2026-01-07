-- ============================================================================
-- MIGRATION: Sistema Completo de Roles y Permisos v4.6
-- Fecha: 29 de diciembre de 2025
-- Descripción: Implementa sistema jerárquico de 7 roles:
--   - GLOBAL_ADMIN (Pluton_JE)
--   - TENANT_ADMIN (creado automáticamente en onboarding)
--   - AUDIT (solo lectura)
--   - RED_TEAM (herramientas ofensivas)
--   - BLUE_TEAM (herramientas defensivas)
--   - PURPLE_TEAM (combinación red + blue)
--   - CUSTOM (permisos configurables)
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. CREAR TABLA DE PERMISOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,  -- platform, tenant, tools, audit, billing, cases, reports
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE permissions IS 'Catálogo de permisos granulares del sistema';
COMMENT ON COLUMN permissions.code IS 'Código único del permiso (ej: platform:manage)';
COMMENT ON COLUMN permissions.category IS 'Categoría: platform, tenant, tools, audit, billing, cases, reports';

-- Índices
CREATE INDEX IF NOT EXISTS idx_permissions_category ON permissions(category);
CREATE INDEX IF NOT EXISTS idx_permissions_active ON permissions(is_active);

-- ============================================================================
-- 2. CREAR TABLA DE ROLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    tenant_id UUID,  -- NULL = rol global/sistema
    is_system_role BOOLEAN DEFAULT FALSE,  -- TRUE = no editable por usuarios
    is_active BOOLEAN DEFAULT TRUE,
    hierarchy_level INTEGER DEFAULT 100,  -- Menor = más privilegios
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE roles IS 'Roles del sistema con jerarquía';
COMMENT ON COLUMN roles.tenant_id IS 'NULL para roles globales, UUID para roles específicos de tenant';
COMMENT ON COLUMN roles.is_system_role IS 'TRUE indica que el rol no puede ser modificado';
COMMENT ON COLUMN roles.hierarchy_level IS 'Nivel jerárquico: 0=Global Admin, 10=Tenant Admin, etc.';

-- Índices
CREATE INDEX IF NOT EXISTS idx_roles_tenant ON roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_code ON roles(code);
CREATE INDEX IF NOT EXISTS idx_roles_system ON roles(is_system_role);
CREATE INDEX IF NOT EXISTS idx_roles_hierarchy ON roles(hierarchy_level);

-- ============================================================================
-- 3. CREAR TABLA DE RELACIÓN ROLES-PERMISOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    granted_by UUID,  -- Usuario que asignó el permiso
    UNIQUE (role_id, permission_id)
);

COMMENT ON TABLE role_permissions IS 'Relación N:M entre roles y permisos';

-- Índices
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);

-- ============================================================================
-- 4. CREAR TABLA DE RELACIÓN USUARIOS-ROLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- Referencia a users.id
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    tenant_id UUID,  -- Contexto de tenant para el rol
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by UUID,  -- Usuario que asignó el rol
    expires_at TIMESTAMP WITH TIME ZONE,  -- Rol temporal (opcional)
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE (user_id, role_id, tenant_id)
);

COMMENT ON TABLE user_roles IS 'Asignación de roles a usuarios por tenant';
COMMENT ON COLUMN user_roles.expires_at IS 'Fecha de expiración para roles temporales';

-- Índices
CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_tenant ON user_roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_active ON user_roles(is_active);

-- ============================================================================
-- 5. CREAR TABLA DE AUDITORÍA DE ROLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS role_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL,  -- ASSIGN, REVOKE, CREATE, UPDATE, DELETE
    target_type VARCHAR(50) NOT NULL,  -- ROLE, PERMISSION, USER_ROLE
    target_id UUID NOT NULL,
    actor_id UUID,  -- Usuario que realizó la acción
    actor_ip VARCHAR(45),
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE role_audit_log IS 'Auditoría de cambios en roles y permisos';

-- Índices
CREATE INDEX IF NOT EXISTS idx_role_audit_action ON role_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_role_audit_target ON role_audit_log(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_role_audit_actor ON role_audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_role_audit_date ON role_audit_log(created_at);

-- ============================================================================
-- 6. ACTUALIZAR TABLA TENANTS (agregar plan_id si no existe)
-- ============================================================================

DO $$
BEGIN
    -- Agregar columna plan_id si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'plan_id'
    ) THEN
        ALTER TABLE tenants ADD COLUMN plan_id INTEGER;
    END IF;
    
    -- Agregar columna stripe_customer_id si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'stripe_customer_id'
    ) THEN
        ALTER TABLE tenants ADD COLUMN stripe_customer_id VARCHAR(100);
    END IF;
    
    -- Agregar columna subscription_status si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'subscription_status'
    ) THEN
        ALTER TABLE tenants ADD COLUMN subscription_status VARCHAR(50) DEFAULT 'active';
    END IF;
END $$;

-- ============================================================================
-- 7. INSERTAR PERMISOS DEL SISTEMA
-- ============================================================================

INSERT INTO permissions (code, name, description, category) VALUES
    -- Plataforma (Global Admin only)
    ('platform:manage', 'Gestión de Plataforma', 'Control total de la plataforma', 'platform'),
    ('platform:view-all-tenants', 'Ver Todos los Tenants', 'Visualizar todos los tenants del sistema', 'platform'),
    ('platform:manage-plans', 'Gestionar Planes', 'CRUD de planes y precios', 'platform'),
    ('platform:view-metrics', 'Ver Métricas Globales', 'Dashboard de métricas de plataforma', 'platform'),
    ('platform:impersonate', 'Impersonar Usuario', 'Actuar como otro usuario', 'platform'),
    
    -- Tenant
    ('tenant:manage', 'Gestionar Tenant', 'Configuración general del tenant', 'tenant'),
    ('tenant:view', 'Ver Tenant', 'Ver información del tenant', 'tenant'),
    ('tenant:billing', 'Gestionar Facturación', 'Ver y gestionar facturación del tenant', 'tenant'),
    ('tenant:integrations', 'Gestionar Integraciones', 'Configurar M365, Azure AD, etc.', 'tenant'),
    
    -- Usuarios
    ('users:manage', 'Gestionar Usuarios', 'CRUD de usuarios del tenant', 'users'),
    ('users:view', 'Ver Usuarios', 'Listar usuarios del tenant', 'users'),
    ('users:invite', 'Invitar Usuarios', 'Enviar invitaciones a nuevos usuarios', 'users'),
    ('users:deactivate', 'Desactivar Usuarios', 'Suspender acceso de usuarios', 'users'),
    
    -- Roles
    ('roles:manage', 'Gestionar Roles', 'CRUD de roles custom', 'roles'),
    ('roles:assign', 'Asignar Roles', 'Asignar roles a usuarios', 'roles'),
    ('roles:view', 'Ver Roles', 'Listar roles disponibles', 'roles'),
    
    -- Casos
    ('cases:read', 'Leer Casos', 'Ver casos e investigaciones', 'cases'),
    ('cases:write', 'Escribir Casos', 'Crear y editar casos', 'cases'),
    ('cases:delete', 'Eliminar Casos', 'Eliminar casos', 'cases'),
    ('cases:assign', 'Asignar Casos', 'Asignar casos a analistas', 'cases'),
    ('cases:close', 'Cerrar Casos', 'Marcar casos como cerrados', 'cases'),
    
    -- Herramientas M365
    ('tools:m365', 'Herramientas M365', 'Ejecutar análisis M365 (Sparrow, Hawk)', 'tools'),
    ('tools:m365-sparrow', 'Sparrow Analysis', 'Ejecutar Sparrow específicamente', 'tools'),
    ('tools:m365-hawk', 'Hawk Analysis', 'Ejecutar Hawk específicamente', 'tools'),
    ('tools:m365-extractor', 'O365 Extractor', 'Ejecutar O365 Extractor', 'tools'),
    
    -- Herramientas Endpoint
    ('tools:endpoint', 'Herramientas Endpoint', 'Ejecutar análisis de endpoints', 'tools'),
    ('tools:endpoint-loki', 'Loki Scanner', 'Ejecutar Loki IOC scanner', 'tools'),
    ('tools:endpoint-yara', 'YARA Rules', 'Ejecutar reglas YARA', 'tools'),
    ('tools:endpoint-osquery', 'OSQuery', 'Ejecutar consultas OSQuery', 'tools'),
    ('tools:endpoint-volatility', 'Volatility', 'Análisis de memoria', 'tools'),
    
    -- Herramientas Credenciales
    ('tools:credentials', 'Herramientas Credenciales', 'Verificar exposición de credenciales', 'tools'),
    ('tools:credentials-hibp', 'HIBP Check', 'Verificar en HaveIBeenPwned', 'tools'),
    ('tools:credentials-dehashed', 'Dehashed Check', 'Verificar en Dehashed', 'tools'),
    
    -- Herramientas Red Team (Ofensivas)
    ('tools:pentest', 'Herramientas Pentest', 'Herramientas de pruebas de penetración', 'tools'),
    ('tools:redteam', 'Herramientas Red Team', 'Simulación de ataques', 'tools'),
    ('tools:redteam-hexstrike', 'HexStrike', 'Herramientas HexStrike', 'tools'),
    ('tools:redteam-c2', 'Command & Control', 'Herramientas C2', 'tools'),
    
    -- Agentes LLM
    ('agents:manage', 'Gestionar Agentes', 'CRUD de agentes LLM', 'agents'),
    ('agents:view', 'Ver Agentes', 'Listar agentes disponibles', 'agents'),
    ('agents:query', 'Consultar Agentes', 'Enviar queries a agentes', 'agents'),
    ('agents:configure', 'Configurar Agentes', 'Modificar configuración de agentes', 'agents'),
    
    -- Auditoría
    ('audit:read', 'Leer Auditoría', 'Ver logs de auditoría', 'audit'),
    ('audit:export', 'Exportar Auditoría', 'Descargar logs de auditoría', 'audit'),
    ('audit:search', 'Buscar Auditoría', 'Búsqueda avanzada en logs', 'audit'),
    
    -- Reportes
    ('reports:generate', 'Generar Reportes', 'Crear reportes de casos', 'reports'),
    ('reports:view', 'Ver Reportes', 'Ver reportes existentes', 'reports'),
    ('reports:export', 'Exportar Reportes', 'Descargar reportes en PDF/CSV', 'reports'),
    ('reports:schedule', 'Programar Reportes', 'Crear reportes automáticos', 'reports'),
    
    -- Facturación (visible para tenant)
    ('billing:view', 'Ver Facturación', 'Ver facturas y uso', 'billing'),
    ('billing:manage-payment', 'Gestionar Pagos', 'Actualizar método de pago', 'billing'),
    ('billing:download-invoices', 'Descargar Facturas', 'Descargar PDFs de facturas', 'billing')
    
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 8. INSERTAR ROLES DEL SISTEMA
-- ============================================================================

INSERT INTO roles (code, name, description, is_system_role, hierarchy_level) VALUES
    ('global_admin', 'Global Administrator', 
     'Administrador global de la plataforma. Acceso total a todos los tenants y configuraciones.',
     TRUE, 0),
    
    ('tenant_admin', 'Tenant Administrator',
     'Administrador del tenant. Gestiona usuarios, roles y configuración del tenant.',
     TRUE, 10),
    
    ('audit', 'Auditor',
     'Rol de solo lectura. Acceso a logs, reportes y casos sin capacidad de modificación.',
     TRUE, 50),
    
    ('red_team', 'Red Team Operator',
     'Operador de equipo rojo. Acceso a herramientas ofensivas y de pentesting.',
     TRUE, 30),
    
    ('blue_team', 'Blue Team Analyst',
     'Analista de equipo azul. Acceso a herramientas defensivas, forenses y respuesta a incidentes.',
     TRUE, 30),
    
    ('purple_team', 'Purple Team Specialist',
     'Especialista equipo púrpura. Combinación de capacidades red team y blue team.',
     TRUE, 20),
    
    ('custom', 'Custom Role',
     'Rol personalizable. El Tenant Admin asigna permisos según necesidad.',
     FALSE, 40)
     
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 9. ASIGNAR PERMISOS A ROLES
-- ============================================================================

-- Helper: Obtener IDs de roles
DO $$
DECLARE
    v_global_admin_id UUID;
    v_tenant_admin_id UUID;
    v_audit_id UUID;
    v_red_team_id UUID;
    v_blue_team_id UUID;
    v_purple_team_id UUID;
BEGIN
    SELECT id INTO v_global_admin_id FROM roles WHERE code = 'global_admin';
    SELECT id INTO v_tenant_admin_id FROM roles WHERE code = 'tenant_admin';
    SELECT id INTO v_audit_id FROM roles WHERE code = 'audit';
    SELECT id INTO v_red_team_id FROM roles WHERE code = 'red_team';
    SELECT id INTO v_blue_team_id FROM roles WHERE code = 'blue_team';
    SELECT id INTO v_purple_team_id FROM roles WHERE code = 'purple_team';
    
    -- ====== GLOBAL ADMIN: TODOS LOS PERMISOS ======
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_global_admin_id, id FROM permissions
    ON CONFLICT DO NOTHING;
    
    -- ====== TENANT ADMIN ======
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_tenant_admin_id, id FROM permissions
    WHERE code IN (
        'tenant:manage', 'tenant:view', 'tenant:billing', 'tenant:integrations',
        'users:manage', 'users:view', 'users:invite', 'users:deactivate',
        'roles:manage', 'roles:assign', 'roles:view',
        'cases:read', 'cases:write', 'cases:delete', 'cases:assign', 'cases:close',
        'tools:m365', 'tools:m365-sparrow', 'tools:m365-hawk', 'tools:m365-extractor',
        'tools:endpoint', 'tools:endpoint-loki', 'tools:endpoint-yara', 'tools:endpoint-osquery', 'tools:endpoint-volatility',
        'tools:credentials', 'tools:credentials-hibp', 'tools:credentials-dehashed',
        'tools:pentest', 'tools:redteam',
        'agents:manage', 'agents:view', 'agents:query', 'agents:configure',
        'audit:read', 'audit:export', 'audit:search',
        'reports:generate', 'reports:view', 'reports:export', 'reports:schedule',
        'billing:view', 'billing:manage-payment', 'billing:download-invoices'
    )
    ON CONFLICT DO NOTHING;
    
    -- ====== AUDIT (Solo Lectura) ======
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_audit_id, id FROM permissions
    WHERE code IN (
        'tenant:view',
        'users:view',
        'roles:view',
        'cases:read',
        'agents:view',
        'audit:read', 'audit:export', 'audit:search',
        'reports:view', 'reports:export',
        'billing:view', 'billing:download-invoices'
    )
    ON CONFLICT DO NOTHING;
    
    -- ====== RED TEAM ======
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_red_team_id, id FROM permissions
    WHERE code IN (
        'cases:read', 'cases:write',
        'tools:pentest', 'tools:redteam', 'tools:redteam-hexstrike', 'tools:redteam-c2',
        'tools:credentials', 'tools:credentials-hibp', 'tools:credentials-dehashed',
        'agents:view', 'agents:query',
        'reports:generate', 'reports:view', 'reports:export'
    )
    ON CONFLICT DO NOTHING;
    
    -- ====== BLUE TEAM ======
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_blue_team_id, id FROM permissions
    WHERE code IN (
        'cases:read', 'cases:write', 'cases:assign',
        'tools:m365', 'tools:m365-sparrow', 'tools:m365-hawk', 'tools:m365-extractor',
        'tools:endpoint', 'tools:endpoint-loki', 'tools:endpoint-yara', 'tools:endpoint-osquery', 'tools:endpoint-volatility',
        'tools:credentials', 'tools:credentials-hibp', 'tools:credentials-dehashed',
        'agents:view', 'agents:query',
        'audit:read', 'audit:search',
        'reports:generate', 'reports:view', 'reports:export'
    )
    ON CONFLICT DO NOTHING;
    
    -- ====== PURPLE TEAM (Red + Blue) ======
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_purple_team_id, id FROM permissions
    WHERE code IN (
        'cases:read', 'cases:write', 'cases:assign',
        'tools:m365', 'tools:m365-sparrow', 'tools:m365-hawk', 'tools:m365-extractor',
        'tools:endpoint', 'tools:endpoint-loki', 'tools:endpoint-yara', 'tools:endpoint-osquery', 'tools:endpoint-volatility',
        'tools:credentials', 'tools:credentials-hibp', 'tools:credentials-dehashed',
        'tools:pentest', 'tools:redteam', 'tools:redteam-hexstrike',
        'agents:view', 'agents:query', 'agents:configure',
        'audit:read', 'audit:search',
        'reports:generate', 'reports:view', 'reports:export'
    )
    ON CONFLICT DO NOTHING;
    
    RAISE NOTICE '✅ Permisos asignados a todos los roles';
END $$;

-- ============================================================================
-- 10. ACTUALIZAR USUARIO Pluton_JE COMO GLOBAL ADMIN
-- ============================================================================

DO $$
DECLARE
    v_pluton_user_id UUID;
    v_global_admin_role_id UUID;
    v_jeturing_tenant_id VARCHAR(100);
BEGIN
    -- Buscar usuario Pluton_JE
    SELECT id INTO v_pluton_user_id FROM users WHERE username = 'Pluton_JE';
    
    -- Buscar rol global_admin
    SELECT id INTO v_global_admin_role_id FROM roles WHERE code = 'global_admin';
    
    -- Buscar tenant jeturing
    SELECT id INTO v_jeturing_tenant_id FROM tenants WHERE id = 'jeturing' OR name ILIKE '%jeturing%' LIMIT 1;
    
    IF v_pluton_user_id IS NOT NULL AND v_global_admin_role_id IS NOT NULL THEN
        -- Actualizar rol en tabla users
        UPDATE users SET role = 'global_admin' WHERE id = v_pluton_user_id;
        
        -- Asignar rol en user_roles
        INSERT INTO user_roles (user_id, role_id, tenant_id, assigned_by)
        VALUES (v_pluton_user_id, v_global_admin_role_id, NULL, v_pluton_user_id)
        ON CONFLICT (user_id, role_id, tenant_id) DO UPDATE SET is_active = TRUE;
        
        -- Registrar en auditoría
        INSERT INTO role_audit_log (action, target_type, target_id, actor_id, new_value, reason)
        VALUES (
            'ASSIGN',
            'USER_ROLE',
            v_pluton_user_id,
            v_pluton_user_id,
            jsonb_build_object('role', 'global_admin', 'user', 'Pluton_JE'),
            'Migración inicial - asignación de Global Admin'
        );
        
        RAISE NOTICE '✅ Usuario Pluton_JE actualizado como GLOBAL_ADMIN';
    ELSE
        RAISE NOTICE '⚠️ Usuario Pluton_JE no encontrado o rol global_admin no existe';
    END IF;
END $$;

-- ============================================================================
-- 11. CREAR FUNCIÓN PARA ASIGNAR ROL A NUEVO USUARIO
-- ============================================================================

CREATE OR REPLACE FUNCTION assign_role_to_user(
    p_user_id UUID,
    p_role_code VARCHAR(50),
    p_tenant_id UUID DEFAULT NULL,
    p_assigned_by UUID DEFAULT NULL,
    p_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_role_id UUID;
    v_assignment_id UUID;
BEGIN
    -- Obtener rol por código
    SELECT id INTO v_role_id FROM roles WHERE code = p_role_code AND is_active = TRUE;
    
    IF v_role_id IS NULL THEN
        RAISE EXCEPTION 'Rol % no encontrado o inactivo', p_role_code;
    END IF;
    
    -- Insertar asignación
    INSERT INTO user_roles (user_id, role_id, tenant_id, assigned_by, expires_at)
    VALUES (p_user_id, v_role_id, p_tenant_id, p_assigned_by, p_expires_at)
    ON CONFLICT (user_id, role_id, tenant_id) 
    DO UPDATE SET 
        is_active = TRUE,
        expires_at = p_expires_at,
        assigned_by = p_assigned_by,
        assigned_at = NOW()
    RETURNING id INTO v_assignment_id;
    
    -- Registrar auditoría
    INSERT INTO role_audit_log (action, target_type, target_id, actor_id, new_value)
    VALUES (
        'ASSIGN',
        'USER_ROLE',
        v_assignment_id,
        p_assigned_by,
        jsonb_build_object(
            'user_id', p_user_id,
            'role_code', p_role_code,
            'tenant_id', p_tenant_id
        )
    );
    
    RETURN v_assignment_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 12. CREAR FUNCIÓN PARA VERIFICAR PERMISO
-- ============================================================================

CREATE OR REPLACE FUNCTION user_has_permission(
    p_user_id UUID,
    p_permission_code VARCHAR(100),
    p_tenant_id UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_has_permission BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE ur.user_id = p_user_id
          AND ur.is_active = TRUE
          AND p.code = p_permission_code
          AND p.is_active = TRUE
          AND (ur.tenant_id IS NULL OR ur.tenant_id = p_tenant_id)
          AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    ) INTO v_has_permission;
    
    RETURN v_has_permission;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 13. CREAR FUNCIÓN PARA OBTENER PERMISOS DE USUARIO
-- ============================================================================

CREATE OR REPLACE FUNCTION get_user_permissions(
    p_user_id UUID,
    p_tenant_id UUID DEFAULT NULL
)
RETURNS TABLE (
    permission_code VARCHAR(100),
    permission_name VARCHAR(100),
    category VARCHAR(50),
    role_code VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        p.code,
        p.name,
        p.category,
        r.code as role_code
    FROM user_roles ur
    JOIN roles r ON ur.role_id = r.id
    JOIN role_permissions rp ON r.id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE ur.user_id = p_user_id
      AND ur.is_active = TRUE
      AND r.is_active = TRUE
      AND p.is_active = TRUE
      AND (ur.tenant_id IS NULL OR ur.tenant_id = p_tenant_id)
      AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    ORDER BY p.category, p.code;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 14. CREAR FUNCIÓN PARA AUTO-PROVISIONAR TENANT ADMIN EN ONBOARDING
-- ============================================================================

CREATE OR REPLACE FUNCTION provision_tenant_admin(
    p_user_id UUID,
    p_tenant_id UUID,
    p_created_by UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_tenant_admin_role_id UUID;
    v_assignment_id UUID;
BEGIN
    -- Obtener rol tenant_admin
    SELECT id INTO v_tenant_admin_role_id FROM roles WHERE code = 'tenant_admin';
    
    IF v_tenant_admin_role_id IS NULL THEN
        RAISE EXCEPTION 'Rol tenant_admin no encontrado';
    END IF;
    
    -- Asignar rol
    INSERT INTO user_roles (user_id, role_id, tenant_id, assigned_by)
    VALUES (p_user_id, v_tenant_admin_role_id, p_tenant_id, COALESCE(p_created_by, p_user_id))
    ON CONFLICT (user_id, role_id, tenant_id) DO UPDATE SET is_active = TRUE
    RETURNING id INTO v_assignment_id;
    
    -- Registrar auditoría
    INSERT INTO role_audit_log (action, target_type, target_id, actor_id, new_value, reason)
    VALUES (
        'ASSIGN',
        'USER_ROLE',
        v_assignment_id,
        p_created_by,
        jsonb_build_object(
            'user_id', p_user_id,
            'role', 'tenant_admin',
            'tenant_id', p_tenant_id
        ),
        'Provisión automática de Tenant Admin en onboarding'
    );
    
    RETURN v_assignment_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 15. CREAR VISTA DE USUARIOS CON ROLES
-- ============================================================================

CREATE OR REPLACE VIEW v_users_with_roles AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    u.is_active as user_active,
    ur.tenant_id,
    r.code as role_code,
    r.name as role_name,
    r.hierarchy_level,
    ur.assigned_at,
    ur.expires_at,
    CASE 
        WHEN ur.expires_at IS NOT NULL AND ur.expires_at < NOW() THEN FALSE
        ELSE ur.is_active
    END as role_active
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
ORDER BY u.username, r.hierarchy_level;

-- ============================================================================
-- 16. CREAR TRIGGER PARA ACTUALIZAR TIMESTAMPS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_roles_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para roles
DROP TRIGGER IF EXISTS trigger_roles_updated ON roles;
CREATE TRIGGER trigger_roles_updated
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_roles_timestamp();

-- Trigger para permissions
DROP TRIGGER IF EXISTS trigger_permissions_updated ON permissions;
CREATE TRIGGER trigger_permissions_updated
    BEFORE UPDATE ON permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_roles_timestamp();

-- ============================================================================
-- 17. RESUMEN DE MIGRACIÓN
-- ============================================================================

DO $$
DECLARE
    v_roles_count INTEGER;
    v_permissions_count INTEGER;
    v_role_permissions_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_roles_count FROM roles;
    SELECT COUNT(*) INTO v_permissions_count FROM permissions;
    SELECT COUNT(*) INTO v_role_permissions_count FROM role_permissions;
    
    RAISE NOTICE '';
    RAISE NOTICE '══════════════════════════════════════════════════════════';
    RAISE NOTICE '     MIGRACIÓN DE SISTEMA DE ROLES COMPLETADA             ';
    RAISE NOTICE '══════════════════════════════════════════════════════════';
    RAISE NOTICE 'Tablas creadas:';
    RAISE NOTICE '  ✅ permissions         - Catálogo de permisos';
    RAISE NOTICE '  ✅ roles               - Definición de roles';
    RAISE NOTICE '  ✅ role_permissions    - Asignación rol→permiso';
    RAISE NOTICE '  ✅ user_roles          - Asignación usuario→rol';
    RAISE NOTICE '  ✅ role_audit_log      - Auditoría de cambios';
    RAISE NOTICE '';
    RAISE NOTICE 'Estadísticas:';
    RAISE NOTICE '  • Roles creados: %', v_roles_count;
    RAISE NOTICE '  • Permisos creados: %', v_permissions_count;
    RAISE NOTICE '  • Asignaciones rol→permiso: %', v_role_permissions_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Roles del sistema:';
    RAISE NOTICE '  🔴 global_admin  - Nivel 0  - Acceso total plataforma';
    RAISE NOTICE '  🟠 tenant_admin  - Nivel 10 - Admin de tenant';
    RAISE NOTICE '  🟡 purple_team   - Nivel 20 - Red + Blue combinado';
    RAISE NOTICE '  🔵 blue_team     - Nivel 30 - Defensivo/Forense';
    RAISE NOTICE '  🔴 red_team      - Nivel 30 - Ofensivo/Pentest';
    RAISE NOTICE '  ⚪ custom        - Nivel 40 - Configurable';
    RAISE NOTICE '  ⚫ audit         - Nivel 50 - Solo lectura';
    RAISE NOTICE '';
    RAISE NOTICE 'Usuario Global Admin:';
    RAISE NOTICE '  👤 Pluton_JE → global_admin (si existe)';
    RAISE NOTICE '══════════════════════════════════════════════════════════';
END $$;

COMMIT;
