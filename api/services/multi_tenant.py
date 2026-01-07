"""
Multi-Tenant Service - Gestión de múltiples tenants M365
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
import logging
from dotenv import load_dotenv
from api.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

load_dotenv()

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "forensics.db"
EVIDENCE_DIR = settings.EVIDENCE_DIR


class MultiTenantService:
    """Servicio para gestión multi-tenant"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._active_tenant_id = None  # Tenant activo en sesión
        self._ensure_tables()
        self._load_active_tenant()
    
    def _load_active_tenant(self):
        """Cargar el tenant activo desde la configuración"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Verificar si existe la tabla tenants
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'")
            if not cursor.fetchone():
                logger.warning("⚠️ Tabla 'tenants' no existe aún. Se creará en el startup.")
                conn.close()
                return
            
            # Buscar tenant activo usando la columna 'is_active' del modelo SQLAlchemy
            cursor.execute('SELECT tenant_id FROM tenants WHERE is_active = 1 LIMIT 1')
            row = cursor.fetchone()
            if row:
                self._active_tenant_id = row['tenant_id']
                logger.info(f"✅ Tenant activo cargado: {self._active_tenant_id}")
            else:
                # Si no hay ninguno activo, activar el primero
                cursor.execute('SELECT tenant_id FROM tenants ORDER BY id LIMIT 1')
                row = cursor.fetchone()
                if row:
                    self._active_tenant_id = row['tenant_id']
                    cursor.execute('UPDATE tenants SET is_active = 1 WHERE tenant_id = ?', (self._active_tenant_id,))
                    conn.commit()
                    logger.info(f"✅ Primer tenant activado: {self._active_tenant_id}")
            
            conn.close()
        except Exception as e:
            logger.error(f"Error cargando tenant activo: {e}")
    
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Crear tablas para multi-tenant (excepto tenants, manejada por SQLAlchemy)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # NOTA: La tabla 'tenants' es manejada por SQLAlchemy en api/models/tenant.py
        # No la creamos aquí para evitar conflictos de esquema
        
        # Verificar si la tabla tenants ya existe (creada por SQLAlchemy)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'")
        tenants_exists = cursor.fetchone() is not None
        
        if not tenants_exists:
            logger.warning("⚠️ Tabla 'tenants' no existe. Se creará via SQLAlchemy en el startup.")
        
        # Actualizar tabla de casos para multi-tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                title TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                assigned_to TEXT,
                threat_type TEXT,
                UNIQUE(case_id, tenant_id)
            )
        ''')
        
        # Tabla de IOCs por tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iocs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                case_id TEXT,
                ioc_type TEXT,
                value TEXT,
                severity TEXT,
                source TEXT,
                description TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
            )
        ''')
        
        # Tabla de usuarios M365 por tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS m365_users (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                display_name TEXT,
                user_principal_name TEXT,
                mail TEXT,
                job_title TEXT,
                department TEXT,
                account_enabled INTEGER,
                last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
            )
        ''')
        
        # Tabla de actividad por tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                action_type TEXT,
                message TEXT,
                case_id TEXT,
                user TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
            )
        ''')
        
        # Tabla de análisis por tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                case_id TEXT,
                tool TEXT,
                status TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                results_path TEXT,
                findings_count INTEGER DEFAULT 0,
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Tablas multi-tenant inicializadas")
    
    # ==================== TENANT MANAGEMENT ====================
    
    async def onboard_tenant(self, tenant_id: str, client_id: str, client_secret: str,
                            notes: str = None, created_by: str = None) -> Dict:
        """
        Onboarding de un nuevo tenant - valida credenciales y registra
        """
        logger.info(f"🔧 Iniciando onboarding de tenant: {tenant_id}")
        
        # Verificar si ya existe
        existing = self.get_tenant(tenant_id)
        if existing:
            return {
                "success": False,
                "error": f"El tenant {tenant_id} ya está registrado",
                "tenant": existing
            }
        
        # Validar credenciales obteniendo info del tenant
        org_info = await self._validate_tenant_credentials(tenant_id, client_id, client_secret)
        
        if not org_info:
            return {
                "success": False,
                "error": "Credenciales inválidas o sin permisos. Verifica Client ID, Secret y permisos de la App."
            }
        
        # Registrar tenant
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tenants 
                (tenant_id, tenant_name, primary_domain, all_domains, client_id, client_secret, 
                 total_users, status, created_by, notes, last_sync)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, CURRENT_TIMESTAMP)
            ''', (
                tenant_id,
                org_info.get('display_name', 'Unknown'),
                org_info.get('verified_domains', [''])[0] if org_info.get('verified_domains') else '',
                ','.join(org_info.get('verified_domains', [])),
                client_id,
                client_secret,  # En producción, encriptar esto
                org_info.get('users_count', 0),
                created_by,
                notes
            ))
            
            # Registrar actividad
            cursor.execute('''
                INSERT INTO activity_log (tenant_id, action_type, message, user)
                VALUES (?, 'tenant_onboarded', ?, ?)
            ''', (tenant_id, f'Tenant onboarded: {org_info.get("display_name")}', created_by))
            
            conn.commit()
            
            # Crear directorio de evidencia para el tenant
            tenant_evidence_dir = EVIDENCE_DIR / tenant_id
            tenant_evidence_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"✅ Tenant onboarded: {org_info.get('display_name')}")
            
            return {
                "success": True,
                "tenant_id": tenant_id,
                "tenant_name": org_info.get('display_name'),
                "primary_domain": org_info.get('verified_domains', [''])[0],
                "users_count": org_info.get('users_count', 0),
                "message": "Tenant registrado exitosamente"
            }
            
        except sqlite3.IntegrityError as e:
            return {"success": False, "error": f"Error de integridad: {e}"}
        finally:
            conn.close()
    
    async def _validate_tenant_credentials(self, tenant_id: str, client_id: str, 
                                          client_secret: str) -> Optional[Dict]:
        """Validar credenciales obteniendo info del tenant"""
        try:
            # Obtener token
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            token_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data)
                
                if token_response.status_code != 200:
                    logger.error(f"Error obteniendo token: {token_response.text}")
                    return None
                
                token = token_response.json().get("access_token")
                
                # Obtener información de la organización
                org_response = await client.get(
                    "https://graph.microsoft.com/v1.0/organization",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if org_response.status_code != 200:
                    return None
                
                org_data = org_response.json().get("value", [])
                if not org_data:
                    return None
                
                org = org_data[0]
                
                # Obtener conteo de usuarios
                users_response = await client.get(
                    "https://graph.microsoft.com/v1.0/users?$count=true&$top=1",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "ConsistencyLevel": "eventual"
                    }
                )
                
                users_count = 0
                if users_response.status_code == 200:
                    users_count = users_response.json().get("@odata.count", 0)
                
                return {
                    "id": org.get("id"),
                    "display_name": org.get("displayName"),
                    "verified_domains": [d.get("name") for d in org.get("verifiedDomains", [])],
                    "users_count": users_count
                }
                
        except Exception as e:
            logger.error(f"Error validando credenciales: {e}")
            return None
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Obtener información de un tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tenants WHERE tenant_id = ?', (tenant_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            tenant = dict(row)
            # No exponer el client_secret completo
            if tenant.get('client_secret'):
                tenant['client_secret'] = '***' + tenant['client_secret'][-4:]
            return tenant
        return None
    
    def get_all_tenants(self, include_inactive: bool = False) -> List[Dict]:
        """Obtener todos los tenants con estadísticas"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        if include_inactive:
            cursor.execute('SELECT * FROM tenants ORDER BY tenant_name')
        else:
            cursor.execute("SELECT * FROM tenants WHERE status = 'active' ORDER BY tenant_name")
        
        tenants = []
        for row in cursor.fetchall():
            tenant = dict(row)
            # No exponer secrets
            if tenant.get('client_secret'):
                tenant['client_secret'] = '***' + tenant['client_secret'][-4:]
            
            # Agregar estadísticas
            cursor.execute('SELECT COUNT(*) as count FROM m365_users WHERE tenant_id = ?', (tenant['tenant_id'],))
            tenant['users_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM cases WHERE tenant_id = ?', (tenant['tenant_id'],))
            tenant['cases_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM iocs WHERE tenant_id = ?', (tenant['tenant_id'],))
            tenant['iocs_count'] = cursor.fetchone()['count']
            
            # Renombrar para consistencia con frontend
            tenant['name'] = tenant.get('tenant_name', 'Sin nombre')
            tenant['is_active'] = bool(tenant.get('is_active', 0))
            
            tenants.append(tenant)
        
        conn.close()
        return tenants
    
    def get_active_tenant(self) -> Optional[Dict]:
        """Obtener el tenant actualmente activo"""
        # Si no hay tenant activo en memoria, intentar cargarlo de la BD
        if not self._active_tenant_id:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT tenant_id FROM tenants WHERE is_active = 1 LIMIT 1')
            row = cursor.fetchone()
            if row:
                self._active_tenant_id = row['tenant_id']
            conn.close()
        
        if not self._active_tenant_id:
            return None
        return self.get_tenant(self._active_tenant_id)
    
    def set_active_tenant(self, tenant_id: str) -> Dict:
        """Establecer el tenant activo"""
        # Verificar que el tenant existe
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant no encontrado"}
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Desactivar todos
        cursor.execute('UPDATE tenants SET is_active = 0')
        
        # Activar el seleccionado
        cursor.execute('UPDATE tenants SET is_active = 1 WHERE tenant_id = ?', (tenant_id,))
        
        # Registrar actividad
        cursor.execute('''
            INSERT INTO activity_log (tenant_id, action_type, message)
            VALUES (?, 'tenant_switched', ?)
        ''', (tenant_id, f'Tenant cambiado a: {tenant.get("tenant_name")}'))
        
        conn.commit()
        conn.close()
        
        self._active_tenant_id = tenant_id
        logger.info(f"✅ Tenant activo cambiado a: {tenant_id}")
        
        return {"success": True, "tenant_id": tenant_id, "tenant_name": tenant.get('tenant_name')}
    
    def update_tenant(self, tenant_id: str, **kwargs) -> Dict:
        """Actualizar información de un tenant"""
        allowed_fields = ['tenant_name', 'notes', 'status', 'client_id', 'client_secret']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        
        if not updates:
            return {"success": False, "error": "No hay campos para actualizar"}
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [tenant_id]
        
        cursor.execute(f'UPDATE tenants SET {set_clause} WHERE tenant_id = ?', values)
        conn.commit()
        conn.close()
        
        return {"success": True, "updated_fields": list(updates.keys())}
    
    def delete_tenant(self, tenant_id: str, hard_delete: bool = False) -> Dict:
        """Eliminar o desactivar un tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        if hard_delete:
            # Eliminar todo relacionado al tenant
            cursor.execute('DELETE FROM m365_users WHERE tenant_id = ?', (tenant_id,))
            cursor.execute('DELETE FROM iocs WHERE tenant_id = ?', (tenant_id,))
            cursor.execute('DELETE FROM analyses WHERE tenant_id = ?', (tenant_id,))
            cursor.execute('DELETE FROM activity_log WHERE tenant_id = ?', (tenant_id,))
            cursor.execute('DELETE FROM cases WHERE tenant_id = ?', (tenant_id,))
            cursor.execute('DELETE FROM tenants WHERE tenant_id = ?', (tenant_id,))
            message = "Tenant eliminado permanentemente"
        else:
            cursor.execute("UPDATE tenants SET status = 'inactive' WHERE tenant_id = ?", (tenant_id,))
            message = "Tenant desactivado"
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": message}
    
    # ==================== SYNC OPERATIONS ====================
    
    async def sync_tenant_users(self, tenant_id: str, access_token: str = None) -> Dict:
        """Sincronizar usuarios de un tenant específico"""
        tenant = self._get_tenant_with_secret(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant no encontrado"}
        
        try:
            # Obtener token
            token = access_token
            if not token:
                token = await self._get_tenant_token(
                    tenant['tenant_id'],
                    tenant['client_id'],
                    tenant['client_secret']
                )
            
            if not token:
                return {"success": False, "error": "No se pudo obtener token"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/users?$select=id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled&$top=999",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code != 200:
                    return {"success": False, "error": f"Error API: {response.status_code}"}
                
                users = response.json().get("value", [])
                
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # Limpiar usuarios anteriores de este tenant
                cursor.execute('DELETE FROM m365_users WHERE tenant_id = ?', (tenant_id,))
                
                for user in users:
                    cursor.execute('''
                        INSERT INTO m365_users 
                        (id, tenant_id, display_name, user_principal_name, mail, job_title, department, account_enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user.get('id'),
                        tenant_id,
                        user.get('displayName'),
                        user.get('userPrincipalName'),
                        user.get('mail'),
                        user.get('jobTitle'),
                        user.get('department'),
                        1 if user.get('accountEnabled') else 0
                    ))
                
                # Actualizar last_sync y total_users
                cursor.execute('''
                    UPDATE tenants SET last_sync = CURRENT_TIMESTAMP, total_users = ?
                    WHERE tenant_id = ?
                ''', (len(users), tenant_id))
                
                # Registrar actividad
                cursor.execute('''
                    INSERT INTO activity_log (tenant_id, action_type, message)
                    VALUES (?, 'users_sync', ?)
                ''', (tenant_id, f'{len(users)} usuarios sincronizados'))
                
                conn.commit()
                conn.close()
                
                return {"success": True, "users_synced": len(users)}
                
        except Exception as e:
            logger.error(f"Error sincronizando usuarios: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_tenant_with_secret(self, tenant_id: str) -> Optional[Dict]:
        """Obtener tenant con secret (uso interno)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tenants WHERE tenant_id = ?', (tenant_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    async def _get_tenant_token(self, tenant_id: str, client_id: str, 
                               client_secret: str) -> Optional[str]:
        """Obtener token de acceso para un tenant"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": "https://graph.microsoft.com/.default",
                        "grant_type": "client_credentials"
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("access_token")
                return None
        except:
            return None
    
    # ==================== TENANT-SCOPED OPERATIONS ====================
    
    def get_tenant_stats(self, tenant_id: str) -> Dict:
        """Obtener estadísticas de un tenant específico"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Casos
        cursor.execute('''
            SELECT status, COUNT(*) as count FROM cases 
            WHERE tenant_id = ? GROUP BY status
        ''', (tenant_id,))
        cases_by_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # IOCs
        cursor.execute('SELECT COUNT(*) as count FROM iocs WHERE tenant_id = ?', (tenant_id,))
        iocs_count = cursor.fetchone()['count']
        
        # Usuarios
        cursor.execute('SELECT COUNT(*) as count FROM m365_users WHERE tenant_id = ?', (tenant_id,))
        users_count = cursor.fetchone()['count']
        
        # Análisis
        cursor.execute('''
            SELECT COUNT(*) as count FROM analyses 
            WHERE tenant_id = ? AND status = 'completed'
        ''', (tenant_id,))
        analyses_count = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            "tenant_id": tenant_id,
            "cases": {
                "active": cases_by_status.get('active', 0) + cases_by_status.get('investigating', 0),
                "closed": cases_by_status.get('closed', 0),
                "total": sum(cases_by_status.values())
            },
            "iocs": iocs_count,
            "users": users_count,
            "analyses_completed": analyses_count
        }
    
    def get_tenant_cases(self, tenant_id: str, status: str = None) -> List[Dict]:
        """Obtener casos de un tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM cases WHERE tenant_id = ? AND status = ?
                ORDER BY created_at DESC
            ''', (tenant_id, status))
        else:
            cursor.execute('''
                SELECT * FROM cases WHERE tenant_id = ?
                ORDER BY created_at DESC
            ''', (tenant_id,))
        
        cases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cases
    
    def get_tenant_users(self, tenant_id: str) -> List[Dict]:
        """Obtener usuarios de un tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM m365_users WHERE tenant_id = ?
            ORDER BY display_name
        ''', (tenant_id,))
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_tenant_activity(self, tenant_id: str, limit: int = 50) -> List[Dict]:
        """Obtener actividad de un tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM activity_log WHERE tenant_id = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (tenant_id, limit))
        activity = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return activity

    async def initiate_device_auth(self, tenant_id: str) -> Dict[str, Any]:
        """Inicia flujo de autenticación Device Code"""
        client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46" # Azure CLI client ID
        scope = "https://graph.microsoft.com/.default"
        
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data={
                "client_id": client_id,
                "scope": scope
            })
            
            if response.status_code != 200:
                raise Exception(f"Error iniciando device auth: {response.text}")
                
            return response.json()

    async def poll_device_token(self, tenant_id: str, device_code: str) -> Dict[str, Any]:
        """Consulta el token usando el device code"""
        client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46" # Azure CLI client ID
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_code
            })
            
            return response.json()

    async def onboard_tenant_with_token(self, tenant_id: str, access_token: str, name: str = None) -> Dict[str, Any]:
        """Onboarding de tenant usando token obtenido via Device Code"""
        try:
            async with httpx.AsyncClient() as client:
                # Obtener info de la organización
                org_response = await client.get(
                    "https://graph.microsoft.com/v1.0/organization",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if org_response.status_code != 200:
                    return {"success": False, "error": f"Error obteniendo organización: {org_response.text}"}
                
                org_data = org_response.json()
                org = org_data.get("value", [{}])[0]
                
                # Obtener dominios
                domains = [d.get("name") for d in org.get("verifiedDomains", [])]
                primary_domain = next((d.get("name") for d in org.get("verifiedDomains", []) if d.get("isDefault")), domains[0] if domains else None)
                
                # Obtener conteo de usuarios
                users_response = await client.get(
                    "https://graph.microsoft.com/v1.0/users?$count=true&$top=1",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "ConsistencyLevel": "eventual"
                    }
                )
                users_count = users_response.json().get("@odata.count", 0) if users_response.status_code == 200 else 0
                
                # Guardar en BD (sin client_id/secret ya que usa Device Code)
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                tenant_name = name or org.get("displayName") or primary_domain or tenant_id
                
                cursor.execute('''
                    INSERT OR REPLACE INTO tenants 
                    (tenant_id, tenant_name, primary_domain, all_domains, total_users, status, onboarded_at)
                    VALUES (?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
                ''', (
                    tenant_id,
                    tenant_name,
                    primary_domain,
                    ",".join(domains),
                    users_count
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"✅ Tenant onboarded via Device Code: {tenant_name} ({tenant_id})")
                
                return {
                    "success": True,
                    "tenant_id": tenant_id,
                    "tenant_name": tenant_name,
                    "primary_domain": primary_domain,
                    "users_count": users_count
                }
                
        except Exception as e:
            logger.error(f"Error onboarding tenant via device code: {e}")
            return {"success": False, "error": str(e)}

    async def create_tenant_schema(self, tenant_id: str, session: AsyncSession):
        """Creates a new schema for a tenant (PostgreSQL only)"""
        # Sanitize tenant_id
        safe_tenant_id = tenant_id.replace("-", "_").replace(":", "_")
        schema_name = f"tenant_{safe_tenant_id}"
        
        try:
            # Check if we are using PostgreSQL
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            if "PostgreSQL" not in version:
                logger.warning("Multi-tenancy via schemas is only supported on PostgreSQL. Skipping schema creation.")
                return False

            await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await session.commit()
            logger.info(f"Schema {schema_name} created")
            return True
        except Exception as e:
            logger.error(f"Error creating schema {schema_name}: {e}")
            await session.rollback()
            return False

    async def set_tenant_context(self, tenant_id: str, session: AsyncSession):
        """Sets the search path to the tenant's schema"""
        safe_tenant_id = tenant_id.replace("-", "_").replace(":", "_")
        schema_name = f"tenant_{safe_tenant_id}"
        
        try:
            # Check if we are using PostgreSQL
            # We can check dialect or just try-except
            await session.execute(text(f"SET search_path TO {schema_name}, public"))
        except Exception as e:
            # Likely not PostgreSQL or schema doesn't exist
            logger.debug(f"Could not set search_path (might be SQLite): {e}")


# Instancia global (lazy initialization)
_multi_tenant_instance = None

def get_multi_tenant() -> MultiTenantService:
    """Get or create the MultiTenantService singleton"""
    global _multi_tenant_instance
    if _multi_tenant_instance is None:
        _multi_tenant_instance = MultiTenantService()
    return _multi_tenant_instance

# Alias for backward compatibility
multi_tenant = property(lambda self: get_multi_tenant())

class MultiTenantProxy:
    """Proxy class for lazy initialization"""
    def __getattr__(self, name):
        return getattr(get_multi_tenant(), name)

multi_tenant = MultiTenantProxy()
