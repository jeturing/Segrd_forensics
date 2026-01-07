"""
Roles & Permissions Service v4.6
================================
Servicio completo de gestión de roles y permisos.
Soporta: GLOBAL_ADMIN, TENANT_ADMIN, AUDIT, RED_TEAM, BLUE_TEAM, PURPLE_TEAM, CUSTOM

Funciones principales:
- get_user_permissions(user_id, tenant_id) -> Set[Permission]
- assign_role_to_user(user_id, role_name, tenant_id, assigned_by)
- remove_role_from_user(user_id, role_name, tenant_id)
- create_custom_role(tenant_id, role_name, permissions, created_by)
- validate_permission(user_id, permission, tenant_id) -> bool
- get_tenant_roles(tenant_id) -> List[Role]
- get_user_roles(user_id, tenant_id) -> List[Role]
"""

import logging
from typing import Optional, Set, List, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

from api.config import get_settings
from core.rbac_config import Role, Permission, ROLE_PERMISSIONS

logger = logging.getLogger(__name__)
settings = get_settings()


def get_db_connection():
    """Obtener conexión a PostgreSQL."""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )


# ============================================================================
# PERMISSION FUNCTIONS
# ============================================================================

async def get_user_permissions(user_id: str, tenant_id: Optional[str] = None) -> Set[str]:
    """
    Obtener todos los permisos de un usuario.
    
    Args:
        user_id: ID del usuario
        tenant_id: ID del tenant (opcional para global admin)
    
    Returns:
        Set de permisos del usuario
    """
    permissions = set()
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar si es global admin
                cur.execute("""
                    SELECT is_global_admin FROM users WHERE id = %s
                """, (user_id,))
                user = cur.fetchone()
                
                if user and user.get('is_global_admin'):
                    # Global admin tiene TODOS los permisos
                    return {p.value for p in Permission}
                
                # Obtener roles del usuario
                query = """
                    SELECT DISTINCT r.name as role_name, r.is_system_role
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = %s
                """
                params = [user_id]
                
                if tenant_id:
                    query += " AND (ur.tenant_id = %s OR ur.tenant_id IS NULL)"
                    params.append(tenant_id)
                
                cur.execute(query, params)
                roles = cur.fetchall()
                
                for role in roles:
                    role_name = role['role_name']
                    
                    if role['is_system_role']:
                        # Para roles de sistema, usar ROLE_PERMISSIONS
                        try:
                            role_enum = Role(role_name)
                            role_perms = ROLE_PERMISSIONS.get(role_enum, set())
                            permissions.update({p.value for p in role_perms})
                        except ValueError:
                            logger.warning(f"Rol de sistema desconocido: {role_name}")
                    else:
                        # Para roles custom, obtener permisos de la DB
                        cur.execute("""
                            SELECT p.name 
                            FROM role_permissions rp
                            JOIN permissions p ON rp.permission_id = p.id
                            JOIN roles r ON rp.role_id = r.id
                            WHERE r.name = %s
                        """, (role_name,))
                        custom_perms = cur.fetchall()
                        permissions.update({p['name'] for p in custom_perms})
        
        logger.info(f"🔐 Usuario {user_id}: {len(permissions)} permisos")
        return permissions
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo permisos: {e}")
        return set()


async def validate_permission(
    user_id: str,
    permission: str,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Validar si un usuario tiene un permiso específico.
    
    Args:
        user_id: ID del usuario
        permission: Nombre del permiso (e.g., "cases:read")
        tenant_id: ID del tenant
    
    Returns:
        True si tiene el permiso, False si no
    """
    try:
        permissions = await get_user_permissions(user_id, tenant_id)
        has_perm = permission in permissions
        
        if not has_perm:
            logger.warning(f"⚠️ Permiso denegado: {user_id} -> {permission}")
        
        return has_perm
        
    except Exception as e:
        logger.error(f"❌ Error validando permiso: {e}")
        return False


async def check_multiple_permissions(
    user_id: str,
    required_permissions: List[str],
    tenant_id: Optional[str] = None,
    require_all: bool = True
) -> bool:
    """
    Validar múltiples permisos.
    
    Args:
        user_id: ID del usuario
        required_permissions: Lista de permisos requeridos
        tenant_id: ID del tenant
        require_all: True = requiere todos, False = requiere al menos uno
    
    Returns:
        True si cumple con los requisitos
    """
    user_perms = await get_user_permissions(user_id, tenant_id)
    
    if require_all:
        return all(p in user_perms for p in required_permissions)
    else:
        return any(p in user_perms for p in required_permissions)


# ============================================================================
# ROLE MANAGEMENT
# ============================================================================

async def get_user_roles(user_id: str, tenant_id: Optional[str] = None) -> List[Dict]:
    """
    Obtener todos los roles de un usuario.
    
    Args:
        user_id: ID del usuario
        tenant_id: ID del tenant (opcional)
    
    Returns:
        Lista de roles con metadatos
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT 
                        r.id as role_id,
                        r.name,
                        r.display_name,
                        r.description,
                        r.is_system_role,
                        ur.assigned_at,
                        ur.assigned_by,
                        ur.tenant_id
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = %s
                """
                params = [user_id]
                
                if tenant_id:
                    query += " AND (ur.tenant_id = %s OR ur.tenant_id IS NULL)"
                    params.append(tenant_id)
                
                query += " ORDER BY r.is_system_role DESC, r.name"
                
                cur.execute(query, params)
                roles = cur.fetchall()
                
                return [dict(r) for r in roles]
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo roles de usuario: {e}")
        return []


async def get_tenant_roles(tenant_id: str) -> List[Dict]:
    """
    Obtener todos los roles disponibles para un tenant.
    Incluye roles de sistema + roles custom del tenant.
    
    Args:
        tenant_id: ID del tenant
    
    Returns:
        Lista de roles disponibles
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        r.id,
                        r.name,
                        r.display_name,
                        r.description,
                        r.is_system_role,
                        r.created_at,
                        COUNT(DISTINCT ur.user_id) as users_count
                    FROM roles r
                    LEFT JOIN user_roles ur ON r.id = ur.role_id AND ur.tenant_id = %s
                    WHERE r.is_system_role = true 
                       OR r.tenant_id = %s
                    GROUP BY r.id
                    ORDER BY r.is_system_role DESC, r.name
                """, (tenant_id, tenant_id))
                
                roles = cur.fetchall()
                return [dict(r) for r in roles]
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo roles del tenant: {e}")
        return []


async def get_all_system_roles() -> List[Dict]:
    """
    Obtener todos los roles de sistema.
    Solo accesible por GLOBAL_ADMIN.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        r.id,
                        r.name,
                        r.display_name,
                        r.description,
                        r.is_system_role,
                        r.created_at,
                        COUNT(DISTINCT ur.user_id) as total_users
                    FROM roles r
                    LEFT JOIN user_roles ur ON r.id = ur.role_id
                    WHERE r.is_system_role = true
                    GROUP BY r.id
                    ORDER BY r.name
                """)
                
                roles = cur.fetchall()
                
                # Agregar permisos para cada rol de sistema
                result = []
                for role in roles:
                    role_dict = dict(role)
                    try:
                        role_enum = Role(role['name'])
                        role_dict['permissions'] = [
                            p.value for p in ROLE_PERMISSIONS.get(role_enum, set())
                        ]
                    except ValueError:
                        role_dict['permissions'] = []
                    result.append(role_dict)
                
                return result
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo roles de sistema: {e}")
        return []


async def assign_role_to_user(
    user_id: str,
    role_name: str,
    tenant_id: str,
    assigned_by: str
) -> Dict[str, Any]:
    """
    Asignar un rol a un usuario.
    
    Args:
        user_id: ID del usuario
        role_name: Nombre del rol (e.g., "blue_team")
        tenant_id: ID del tenant
        assigned_by: ID del usuario que asigna el rol
    
    Returns:
        Resultado de la operación
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar que el rol existe
                cur.execute("""
                    SELECT id, name, is_system_role, tenant_id
                    FROM roles 
                    WHERE name = %s
                """, (role_name,))
                role = cur.fetchone()
                
                if not role:
                    return {
                        "success": False,
                        "error": f"Rol no encontrado: {role_name}"
                    }
                
                # Verificar permisos del rol custom
                if not role['is_system_role'] and role['tenant_id'] != tenant_id:
                    return {
                        "success": False,
                        "error": "No se puede asignar un rol custom de otro tenant"
                    }
                
                # No permitir asignar GLOBAL_ADMIN via esta función
                if role_name == Role.GLOBAL_ADMIN.value:
                    return {
                        "success": False,
                        "error": "GLOBAL_ADMIN solo se asigna por superusuario"
                    }
                
                # Verificar si ya tiene el rol
                cur.execute("""
                    SELECT id FROM user_roles 
                    WHERE user_id = %s AND role_id = %s AND tenant_id = %s
                """, (user_id, role['id'], tenant_id))
                
                if cur.fetchone():
                    return {
                        "success": False,
                        "error": "El usuario ya tiene este rol"
                    }
                
                # Asignar el rol
                cur.execute("""
                    INSERT INTO user_roles (user_id, role_id, tenant_id, assigned_by, assigned_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    RETURNING id
                """, (user_id, role['id'], tenant_id, assigned_by))
                
                result = cur.fetchone()
                conn.commit()
                
                logger.info(f"✅ Rol {role_name} asignado a usuario {user_id}")
                
                return {
                    "success": True,
                    "assignment_id": result['id'],
                    "message": f"Rol '{role_name}' asignado exitosamente"
                }
                
    except Exception as e:
        logger.error(f"❌ Error asignando rol: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def remove_role_from_user(
    user_id: str,
    role_name: str,
    tenant_id: str
) -> Dict[str, Any]:
    """
    Remover un rol de un usuario.
    
    Args:
        user_id: ID del usuario
        role_name: Nombre del rol
        tenant_id: ID del tenant
    
    Returns:
        Resultado de la operación
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # No permitir remover GLOBAL_ADMIN via esta función
                if role_name == Role.GLOBAL_ADMIN.value:
                    return {
                        "success": False,
                        "error": "GLOBAL_ADMIN solo se modifica por superusuario"
                    }
                
                # Remover el rol
                cur.execute("""
                    DELETE FROM user_roles 
                    WHERE user_id = %s 
                      AND role_id = (SELECT id FROM roles WHERE name = %s)
                      AND tenant_id = %s
                    RETURNING id
                """, (user_id, role_name, tenant_id))
                
                deleted = cur.fetchone()
                conn.commit()
                
                if deleted:
                    logger.info(f"✅ Rol {role_name} removido de usuario {user_id}")
                    return {
                        "success": True,
                        "message": f"Rol '{role_name}' removido exitosamente"
                    }
                else:
                    return {
                        "success": False,
                        "error": "El usuario no tenía este rol"
                    }
                
    except Exception as e:
        logger.error(f"❌ Error removiendo rol: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# CUSTOM ROLE MANAGEMENT
# ============================================================================

async def create_custom_role(
    tenant_id: str,
    role_name: str,
    display_name: str,
    description: str,
    permissions: List[str],
    created_by: str
) -> Dict[str, Any]:
    """
    Crear un rol personalizado para un tenant.
    
    Args:
        tenant_id: ID del tenant
        role_name: Nombre interno del rol (snake_case)
        display_name: Nombre para mostrar
        description: Descripción del rol
        permissions: Lista de nombres de permisos
        created_by: ID del usuario creador
    
    Returns:
        Resultado con el rol creado
    """
    try:
        # Validar que los permisos existen
        valid_permissions = {p.value for p in Permission}
        invalid = [p for p in permissions if p not in valid_permissions]
        
        if invalid:
            return {
                "success": False,
                "error": f"Permisos inválidos: {invalid}"
            }
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar nombre único
                cur.execute("""
                    SELECT id FROM roles 
                    WHERE name = %s AND (tenant_id = %s OR is_system_role = true)
                """, (role_name, tenant_id))
                
                if cur.fetchone():
                    return {
                        "success": False,
                        "error": f"Ya existe un rol con el nombre: {role_name}"
                    }
                
                # Crear el rol
                cur.execute("""
                    INSERT INTO roles (name, display_name, description, is_system_role, tenant_id, created_by, created_at)
                    VALUES (%s, %s, %s, false, %s, %s, NOW())
                    RETURNING id, name, display_name, description, created_at
                """, (role_name, display_name, description, tenant_id, created_by))
                
                new_role = cur.fetchone()
                
                # Asignar permisos al rol
                for perm_name in permissions:
                    cur.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        SELECT %s, id FROM permissions WHERE name = %s
                    """, (new_role['id'], perm_name))
                
                conn.commit()
                
                logger.info(f"✅ Rol custom creado: {role_name} con {len(permissions)} permisos")
                
                return {
                    "success": True,
                    "role": {
                        "id": new_role['id'],
                        "name": new_role['name'],
                        "display_name": new_role['display_name'],
                        "description": new_role['description'],
                        "permissions": permissions,
                        "created_at": str(new_role['created_at'])
                    }
                }
                
    except Exception as e:
        logger.error(f"❌ Error creando rol custom: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def update_custom_role(
    role_id: int,
    tenant_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Actualizar un rol personalizado.
    
    Args:
        role_id: ID del rol
        tenant_id: ID del tenant (validación)
        updates: Campos a actualizar (display_name, description, permissions)
    
    Returns:
        Resultado de la operación
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar que el rol existe y pertenece al tenant
                cur.execute("""
                    SELECT id, name, is_system_role 
                    FROM roles 
                    WHERE id = %s AND tenant_id = %s
                """, (role_id, tenant_id))
                
                role = cur.fetchone()
                
                if not role:
                    return {
                        "success": False,
                        "error": "Rol no encontrado o no pertenece al tenant"
                    }
                
                if role['is_system_role']:
                    return {
                        "success": False,
                        "error": "No se pueden modificar roles de sistema"
                    }
                
                # Actualizar campos básicos
                if 'display_name' in updates or 'description' in updates:
                    set_clauses = []
                    params = []
                    
                    if 'display_name' in updates:
                        set_clauses.append("display_name = %s")
                        params.append(updates['display_name'])
                    
                    if 'description' in updates:
                        set_clauses.append("description = %s")
                        params.append(updates['description'])
                    
                    params.append(role_id)
                    
                    cur.execute(f"""
                        UPDATE roles SET {', '.join(set_clauses)}, updated_at = NOW()
                        WHERE id = %s
                    """, params)
                
                # Actualizar permisos si se proporcionan
                if 'permissions' in updates:
                    # Validar permisos
                    valid_permissions = {p.value for p in Permission}
                    invalid = [p for p in updates['permissions'] if p not in valid_permissions]
                    
                    if invalid:
                        return {
                            "success": False,
                            "error": f"Permisos inválidos: {invalid}"
                        }
                    
                    # Limpiar permisos actuales
                    cur.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
                    
                    # Insertar nuevos permisos
                    for perm_name in updates['permissions']:
                        cur.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            SELECT %s, id FROM permissions WHERE name = %s
                        """, (role_id, perm_name))
                
                conn.commit()
                
                logger.info(f"✅ Rol {role['name']} actualizado")
                
                return {
                    "success": True,
                    "message": "Rol actualizado exitosamente"
                }
                
    except Exception as e:
        logger.error(f"❌ Error actualizando rol: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def delete_custom_role(role_id: int, tenant_id: str) -> Dict[str, Any]:
    """
    Eliminar un rol personalizado.
    
    Args:
        role_id: ID del rol
        tenant_id: ID del tenant
    
    Returns:
        Resultado de la operación
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar que el rol existe y es custom
                cur.execute("""
                    SELECT id, name, is_system_role 
                    FROM roles 
                    WHERE id = %s AND tenant_id = %s
                """, (role_id, tenant_id))
                
                role = cur.fetchone()
                
                if not role:
                    return {
                        "success": False,
                        "error": "Rol no encontrado"
                    }
                
                if role['is_system_role']:
                    return {
                        "success": False,
                        "error": "No se pueden eliminar roles de sistema"
                    }
                
                # Verificar si tiene usuarios asignados
                cur.execute("""
                    SELECT COUNT(*) as count FROM user_roles WHERE role_id = %s
                """, (role_id,))
                
                if cur.fetchone()['count'] > 0:
                    return {
                        "success": False,
                        "error": "El rol tiene usuarios asignados. Remueva las asignaciones primero."
                    }
                
                # Eliminar permisos del rol
                cur.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
                
                # Eliminar el rol
                cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
                
                conn.commit()
                
                logger.info(f"✅ Rol eliminado: {role['name']}")
                
                return {
                    "success": True,
                    "message": f"Rol '{role['name']}' eliminado exitosamente"
                }
                
    except Exception as e:
        logger.error(f"❌ Error eliminando rol: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def get_all_permissions() -> List[Dict]:
    """
    Obtener todos los permisos disponibles agrupados por categoría.
    """
    permissions_by_category = {}
    
    for perm in Permission:
        category = perm.value.split(':')[0]
        if category not in permissions_by_category:
            permissions_by_category[category] = []
        
        permissions_by_category[category].append({
            "name": perm.value,
            "description": _get_permission_description(perm.value)
        })
    
    return [
        {"category": cat, "permissions": perms}
        for cat, perms in permissions_by_category.items()
    ]


def _get_permission_description(perm_name: str) -> str:
    """Obtener descripción de un permiso."""
    descriptions = {
        "platform:manage": "Gestión completa de la plataforma",
        "platform:billing": "Gestión de facturación y pagos",
        "platform:settings": "Configuración global de la plataforma",
        "tenant:manage": "Gestión completa del tenant",
        "tenant:users": "Gestión de usuarios del tenant",
        "tenant:roles": "Gestión de roles del tenant",
        "tenant:settings": "Configuración del tenant",
        "tools:m365": "Uso de herramientas M365",
        "tools:endpoint": "Uso de herramientas de endpoint",
        "tools:credentials": "Uso de herramientas de credenciales",
        "tools:pentest": "Uso de herramientas de pentesting",
        "tools:redteam": "Uso de herramientas Red Team",
        "tools:osint": "Uso de herramientas OSINT",
        "cases:read": "Lectura de casos",
        "cases:write": "Creación y edición de casos",
        "cases:delete": "Eliminación de casos",
        "cases:export": "Exportación de casos",
        "audit:read": "Lectura de logs de auditoría",
        "audit:export": "Exportación de auditoría",
        "audit:full": "Acceso completo a auditoría",
    }
    return descriptions.get(perm_name, perm_name)


async def auto_assign_tenant_admin(user_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Asignar automáticamente el rol TENANT_ADMIN a un usuario.
    Llamado después de la activación de Stripe.
    
    Args:
        user_id: ID del usuario
        tenant_id: ID del tenant
    
    Returns:
        Resultado de la operación
    """
    logger.info(f"🔐 Auto-asignando TENANT_ADMIN a {user_id} para tenant {tenant_id}")
    
    result = await assign_role_to_user(
        user_id=user_id,
        role_name=Role.TENANT_ADMIN.value,
        tenant_id=tenant_id,
        assigned_by="system"  # Asignación automática
    )
    
    if result['success']:
        logger.info(f"✅ TENANT_ADMIN auto-asignado exitosamente")
    else:
        logger.error(f"❌ Error auto-asignando TENANT_ADMIN: {result.get('error')}")
    
    return result


async def is_global_admin(user_id: str) -> bool:
    """
    Verificar si un usuario es Global Admin.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        True si es global admin
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT is_global_admin FROM users WHERE id = %s
                """, (user_id,))
                user = cur.fetchone()
                return user and user.get('is_global_admin', False)
    except Exception as e:
        logger.error(f"❌ Error verificando global admin: {e}")
        return False


async def get_role_by_name(role_name: str) -> Optional[Dict]:
    """
    Obtener un rol por su nombre.
    
    Args:
        role_name: Nombre del rol
    
    Returns:
        Diccionario con información del rol o None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, display_name, description, is_system_role, tenant_id, created_at
                    FROM roles 
                    WHERE name = %s
                """, (role_name,))
                role = cur.fetchone()
                
                if role:
                    role_dict = dict(role)
                    
                    # Si es rol de sistema, agregar permisos desde config
                    if role['is_system_role']:
                        try:
                            role_enum = Role(role_name)
                            role_dict['permissions'] = [
                                p.value for p in ROLE_PERMISSIONS.get(role_enum, set())
                            ]
                        except ValueError:
                            role_dict['permissions'] = []
                    else:
                        # Obtener permisos de la DB
                        cur.execute("""
                            SELECT p.name 
                            FROM role_permissions rp
                            JOIN permissions p ON rp.permission_id = p.id
                            WHERE rp.role_id = %s
                        """, (role['id'],))
                        role_dict['permissions'] = [p['name'] for p in cur.fetchall()]
                    
                    return role_dict
                
                return None
                
    except Exception as e:
        logger.error(f"❌ Error obteniendo rol: {e}")
        return None
