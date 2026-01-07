"""
Dashboard Data Service - Real Data Integration
Obtiene datos reales de casos, M365, herramientas y evidencia
"""

import os
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import httpx
import logging
from dotenv import load_dotenv
from api.config import settings

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

# Paths
EVIDENCE_DIR = settings.EVIDENCE_DIR
TOOLS_DIR = Path("/opt/forensics-tools")
DB_PATH = Path(__file__).parent.parent.parent / "forensics.db"
ENV_PATH = Path(__file__).parent.parent.parent / ".env"

class DashboardDataService:
    """Servicio para obtener datos reales del dashboard"""
    
    def __init__(self):
        self.evidence_dir = EVIDENCE_DIR
        self.tools_dir = TOOLS_DIR
        self.db_path = DB_PATH
        self._ensure_database()
        self._load_env()
    
    def _load_env(self):
        """Cargar variables de entorno"""
        self.m365_tenant_id = os.getenv("M365_TENANT_ID")
        self.m365_client_id = os.getenv("M365_CLIENT_ID")
        self.m365_client_secret = os.getenv("M365_CLIENT_SECRET")
    
    def _ensure_database(self):
        """Crear tablas si no existen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de configuración del tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_config (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT UNIQUE NOT NULL,
                tenant_name TEXT,
                primary_domain TEXT,
                all_domains TEXT,
                total_users INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de casos - vinculada al tenant
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                tenant_id TEXT,
                title TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                assigned_to TEXT,
                threat_type TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenant_config(tenant_id)
            )
        ''')
        
        # Tabla de IOCs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iocs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                ioc_type TEXT,
                value TEXT,
                severity TEXT,
                source TEXT,
                description TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            )
        ''')
        
        # Tabla de análisis ejecutados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                tool TEXT,
                status TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                results_path TEXT,
                findings_count INTEGER DEFAULT 0,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            )
        ''')
        
        # Tabla de actividad
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                message TEXT,
                case_id TEXT,
                user TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        ''')
        
        # Tabla de usuarios M365 (cache)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS m365_users (
                id TEXT PRIMARY KEY,
                display_name TEXT,
                user_principal_name TEXT,
                mail TEXT,
                job_title TEXT,
                department TEXT,
                account_enabled INTEGER,
                last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Base de datos inicializada: {self.db_path}")
    
    def get_db_connection(self):
        """Obtener conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== CASOS ====================
    
    def get_cases_stats(self) -> Dict:
        """Obtener estadísticas reales de casos"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Contar casos por estado
        cursor.execute("SELECT status, COUNT(*) as count FROM cases GROUP BY status")
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Contar por prioridad
        cursor.execute("SELECT priority, COUNT(*) as count FROM cases GROUP BY priority")
        priority_counts = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        # Contar por tipo de amenaza
        cursor.execute("SELECT threat_type, COUNT(*) as count FROM cases WHERE threat_type IS NOT NULL GROUP BY threat_type")
        threat_counts = {row['threat_type']: row['count'] for row in cursor.fetchall()}
        
        # Timeline de casos (últimos 30 días)
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM cases 
            WHERE created_at >= DATE('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')
        timeline_data = cursor.fetchall()
        
        conn.close()
        
        return {
            "total": sum(status_counts.values()),
            "active": status_counts.get('active', 0) + status_counts.get('investigating', 0),
            "closed": status_counts.get('closed', 0),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "by_threat": threat_counts,
            "timeline": {
                "dates": [row['date'] for row in timeline_data],
                "counts": [row['count'] for row in timeline_data]
            }
        }
    
    def get_all_cases(self) -> List[Dict]:
        """Obtener todos los casos"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM cases ORDER BY created_at DESC
        ''')
        cases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cases
    
    def create_case(self, case_id: str, title: str, priority: str = "medium", 
                   threat_type: str = None, description: str = None, tenant_id: str = None) -> Dict:
        """Crear un nuevo caso vinculado al tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Usar tenant_id proporcionado o el configurado por defecto
        target_tenant_id = tenant_id or self.m365_tenant_id
        
        try:
            # Vincular al tenant configurado
            cursor.execute('''
                INSERT INTO cases (case_id, tenant_id, title, priority, threat_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (case_id, target_tenant_id, title, priority, threat_type, description))
            
            # Crear directorio de evidencia
            case_evidence_dir = self.evidence_dir / case_id
            case_evidence_dir.mkdir(parents=True, exist_ok=True)
            
            # Registrar actividad
            cursor.execute('''
                INSERT INTO activity_log (action_type, message, case_id)
                VALUES (?, ?, ?)
            ''', ('case_created', f'Nuevo caso creado: {case_id}', case_id))
            
            conn.commit()
            
            return {"success": True, "case_id": case_id, "tenant_id": self.m365_tenant_id, "evidence_path": str(case_evidence_dir)}
        except sqlite3.IntegrityError:
            return {"success": False, "error": f"El caso {case_id} ya existe"}
        finally:
            conn.close()
    
    # ==================== TENANT ====================
    
    def get_tenant_config(self) -> Optional[Dict]:
        """Obtener configuración del tenant"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tenant_config WHERE tenant_id = ?', (self.m365_tenant_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    async def sync_tenant_info(self) -> Dict:
        """Sincronizar información del tenant desde M365"""
        org = await self.get_m365_organization()
        users = await self.get_m365_users_count()
        
        if org:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tenant_config 
                (id, tenant_id, tenant_name, primary_domain, all_domains, total_users, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                self.m365_tenant_id,
                org.get('display_name'),
                org.get('verified_domains', [''])[0] if org.get('verified_domains') else '',
                ','.join(org.get('verified_domains', [])),
                users.get('total', 0)
            ))
            conn.commit()
            conn.close()
            
            # Registrar actividad
            self.log_activity('tenant_sync', f'Tenant sincronizado: {org.get("display_name")}')
            
            return {"success": True, "organization": org.get('display_name'), "users": users.get('total')}
        
        return {"success": False, "error": "No se pudo conectar al tenant"}
    
    async def sync_m365_users(self) -> Dict:
        """Sincronizar usuarios de M365 a la base de datos local"""
        token = await self.get_m365_token()
        if not token:
            return {"success": False, "error": "No se pudo obtener token"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/users?$select=id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled&$top=999",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    users = response.json().get("value", [])
                    
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    
                    for user in users:
                        cursor.execute('''
                            INSERT OR REPLACE INTO m365_users 
                            (id, display_name, user_principal_name, mail, job_title, department, account_enabled, last_sync)
                            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (
                            user.get('id'),
                            user.get('displayName'),
                            user.get('userPrincipalName'),
                            user.get('mail'),
                            user.get('jobTitle'),
                            user.get('department'),
                            1 if user.get('accountEnabled') else 0
                        ))
                    
                    conn.commit()
                    conn.close()
                    
                    self.log_activity('users_sync', f'{len(users)} usuarios sincronizados desde M365')
                    
                    return {"success": True, "users_synced": len(users)}
                    
        except Exception as e:
            logger.error(f"Error sincronizando usuarios: {e}")
            return {"success": False, "error": str(e)}
    
    def get_m365_users_from_cache(self) -> List[Dict]:
        """Obtener usuarios de M365 desde la cache local"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM m365_users ORDER BY display_name')
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    # ==================== IOCs ====================
    
    def get_iocs_stats(self) -> Dict:
        """Obtener estadísticas de IOCs"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Total de IOCs
        cursor.execute("SELECT COUNT(*) as total FROM iocs")
        total = cursor.fetchone()['total']
        
        # Por severidad
        cursor.execute("SELECT severity, COUNT(*) as count FROM iocs GROUP BY severity")
        by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
        
        # Por tipo
        cursor.execute("SELECT ioc_type, COUNT(*) as count FROM iocs GROUP BY ioc_type")
        by_type = {row['ioc_type']: row['count'] for row in cursor.fetchall()}
        
        # Por fuente (herramienta)
        cursor.execute("SELECT source, COUNT(*) as count FROM iocs GROUP BY source")
        by_source = {row['source']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total": total,
            "by_severity": by_severity,
            "by_type": by_type,
            "by_source": by_source
        }
    
    def get_latest_iocs(self, limit: int = 10) -> List[Dict]:
        """Obtener últimos IOCs detectados"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM iocs ORDER BY detected_at DESC LIMIT ?
        ''', (limit,))
        iocs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return iocs
    
    def add_ioc(self, case_id: str, ioc_type: str, value: str, 
                severity: str, source: str, description: str = None) -> Dict:
        """Agregar un nuevo IOC"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO iocs (case_id, ioc_type, value, severity, source, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (case_id, ioc_type, value, severity, source, description))
        
        # Registrar actividad
        cursor.execute('''
            INSERT INTO activity_log (action_type, message, case_id)
            VALUES (?, ?, ?)
        ''', ('ioc_detected', f'IOC detectado: {ioc_type}={value}', case_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "ioc_type": ioc_type, "value": value}
    
    # ==================== ACTIVIDAD ====================
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict]:
        """Obtener actividad reciente"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        activities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return activities
    
    def log_activity(self, action_type: str, message: str, 
                    case_id: str = None, details: str = None):
        """Registrar actividad"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_log (action_type, message, case_id, details)
            VALUES (?, ?, ?, ?)
        ''', (action_type, message, case_id, details))
        conn.commit()
        conn.close()
    
    def add_case_activity(self, case_id: str, action_type: str, message: str, details: str = None):
        """Registrar actividad específica de un caso"""
        self.log_activity(action_type, message, case_id, details)
    
    # ==================== HERRAMIENTAS ====================
    
    def get_tools_status(self) -> Dict:
        """Verificar estado de herramientas instaladas"""
        tools = {
            "sparrow": {
                "path": self.tools_dir / "Sparrow" / "Sparrow.ps1",
                "name": "Sparrow 365",
                "type": "M365"
            },
            "hawk": {
                "path": self.tools_dir / "hawk",
                "name": "Hawk",
                "type": "M365"
            },
            "loki": {
                "path": self.tools_dir / "Loki" / "loki.py",
                "name": "Loki Scanner",
                "type": "Endpoint"
            },
            "yara_rules": {
                "path": self.tools_dir / "yara-rules",
                "name": "YARA Rules",
                "type": "Endpoint"
            },
            "volatility": {
                "path": self.tools_dir / "volatility3" / "vol.py",
                "name": "Volatility 3",
                "type": "Memory"
            },
            "o365_extractor": {
                "path": self.tools_dir / "O365-Extractor" / "o365_extractor.py",
                "name": "O365 Extractor",
                "type": "M365"
            }
        }
        
        status = {}
        for key, info in tools.items():
            installed = info["path"].exists()
            status[key] = {
                "name": info["name"],
                "type": info["type"],
                "installed": installed,
                "path": str(info["path"]) if installed else None
            }
        
        # Verificar comandos del sistema
        system_tools = ["yara", "osqueryi", "pwsh"]
        for tool in system_tools:
            try:
                result = subprocess.run(["which", tool], capture_output=True, text=True)
                status[tool] = {
                    "name": tool.capitalize(),
                    "type": "System",
                    "installed": result.returncode == 0,
                    "path": result.stdout.strip() if result.returncode == 0 else None
                }
            except:
                status[tool] = {"name": tool, "type": "System", "installed": False}
        
        return status
    
    # ==================== MICROSOFT 365 ====================
    
    async def get_m365_token(self) -> Optional[str]:
        """Obtener token de acceso para Microsoft Graph"""
        if not all([self.m365_tenant_id, self.m365_client_id, self.m365_client_secret]):
            logger.warning("❌ Credenciales M365 no configuradas")
            return None
        
        url = f"https://login.microsoftonline.com/{self.m365_tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.m365_client_id,
            "client_secret": self.m365_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    return response.json().get("access_token")
                else:
                    logger.error(f"Error obteniendo token M365: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error de conexión M365: {e}")
            return None
    
    async def get_m365_organization(self) -> Optional[Dict]:
        """Obtener información de la organización M365"""
        token = await self.get_m365_token()
        if not token:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/organization",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    org_data = response.json().get("value", [])
                    if org_data:
                        org = org_data[0]
                        return {
                            "id": org.get("id"),
                            "display_name": org.get("displayName"),
                            "verified_domains": [d.get("name") for d in org.get("verifiedDomains", [])],
                            "created": org.get("createdDateTime")
                        }
        except Exception as e:
            logger.error(f"Error obteniendo organización M365: {e}")
        return None
    
    async def get_m365_users_count(self) -> Dict:
        """Obtener conteo de usuarios M365"""
        token = await self.get_m365_token()
        if not token:
            return {"total": 0, "enabled": 0, "disabled": 0}
        
        try:
            async with httpx.AsyncClient() as client:
                # Contar usuarios totales
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/users?$count=true&$top=1",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "ConsistencyLevel": "eventual"
                    }
                )
                if response.status_code == 200:
                    total = response.json().get("@odata.count", 0)
                    return {"total": total, "enabled": total, "disabled": 0}
        except Exception as e:
            logger.error(f"Error contando usuarios M365: {e}")
        return {"total": 0, "enabled": 0, "disabled": 0}
    
    async def get_m365_risky_signins(self, days: int = 7) -> List[Dict]:
        """Obtener sign-ins de riesgo"""
        token = await self.get_m365_token()
        if not token:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/auditLogs/signIns?$filter=riskState eq 'atRisk'&$top=50",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    return response.json().get("value", [])
        except Exception as e:
            logger.error(f"Error obteniendo sign-ins de riesgo: {e}")
        return []
    
    async def get_m365_audit_logs(self, days: int = 7) -> List[Dict]:
        """Obtener logs de auditoría de Azure AD"""
        token = await self.get_m365_token()
        if not token:
            return []
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.microsoft.com/v1.0/auditLogs/directoryAudits?$filter=activityDateTime ge {start_date}&$top=100",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    return response.json().get("value", [])
        except Exception as e:
            logger.error(f"Error obteniendo logs de auditoría: {e}")
        return []
    
    # ==================== EVIDENCIA ====================
    
    def get_evidence_stats(self) -> Dict:
        """Obtener estadísticas de evidencia almacenada"""
        if not self.evidence_dir.exists():
            return {"cases": 0, "total_size_mb": 0, "files": 0}
        
        cases = list(self.evidence_dir.iterdir())
        total_size = 0
        total_files = 0
        
        for case_dir in cases:
            if case_dir.is_dir():
                for file in case_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
                        total_files += 1
        
        return {
            "cases": len([c for c in cases if c.is_dir()]),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": total_files
        }
    
    def get_case_evidence(self, case_id: str) -> Dict:
        """Obtener evidencia de un caso específico"""
        case_dir = self.evidence_dir / case_id
        if not case_dir.exists():
            return {"exists": False, "files": []}
        
        files = []
        for file in case_dir.rglob("*"):
            if file.is_file():
                files.append({
                    "name": file.name,
                    "path": str(file.relative_to(case_dir)),
                    "size_kb": round(file.stat().st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
        
        return {"exists": True, "case_id": case_id, "files": files}

    # ==================== MÉTODOS DE DETALLE ====================
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        """Obtener caso por ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE case_id = ?', (case_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_iocs_by_case(self, case_id: str) -> List[Dict]:
        """Obtener IOCs de un caso específico"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM iocs WHERE case_id = ? ORDER BY detected_at DESC', (case_id,))
        iocs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return iocs
    
    def get_case_activity(self, case_id: str) -> List[Dict]:
        """Obtener actividad de un caso específico"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM activity_log WHERE case_id = ? ORDER BY timestamp DESC', (case_id,))
        activities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return activities
    
    def get_ioc_by_id(self, ioc_id: int) -> Optional[Dict]:
        """Obtener IOC por ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM iocs WHERE id = ?', (ioc_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_case_status(self, case_id: str, status: str) -> Dict:
        """Actualizar estado de un caso"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            if status == 'closed':
                cursor.execute('''
                    UPDATE cases SET status = ?, updated_at = ?, closed_at = ? WHERE case_id = ?
                ''', (status, now, now, case_id))
            else:
                cursor.execute('''
                    UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?
                ''', (status, now, case_id))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": f"Caso {case_id} no encontrado"}
            
            # Registrar actividad
            cursor.execute('''
                INSERT INTO activity_log (action_type, message, case_id)
                VALUES (?, ?, ?)
            ''', ('status_changed', f'Estado cambiado a: {status}', case_id))
            
            conn.commit()
            return {"success": True, "case_id": case_id, "new_status": status}
        finally:
            conn.close()
    
    def delete_case(self, case_id: str) -> Dict:
        """Eliminar caso (soft delete)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE cases SET status = 'deleted', updated_at = ? WHERE case_id = ?
            ''', (datetime.now().isoformat(), case_id))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": f"Caso {case_id} no encontrado"}
            
            # Registrar actividad
            cursor.execute('''
                INSERT INTO activity_log (action_type, message, case_id)
                VALUES (?, ?, ?)
            ''', ('case_deleted', f'Caso eliminado: {case_id}', case_id))
            
            conn.commit()
            return {"success": True, "case_id": case_id}
        finally:
            conn.close()
    
    def add_case_note(self, case_id: str, note: str) -> Dict:
        """Agregar nota a un caso"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activity_log (action_type, message, case_id, details)
            VALUES (?, ?, ?, ?)
        ''', ('note_added', 'Nota agregada', case_id, note))
        
        conn.commit()
        conn.close()
        return {"success": True, "case_id": case_id}
    
    def get_analyses_by_case(self, case_id: str) -> List[Dict]:
        """Obtener análisis ejecutados para un caso"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analyses WHERE case_id = ? ORDER BY started_at DESC', (case_id,))
        analyses = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return analyses
    
    def extract_iocs_from_evidence(self, case_id: str) -> List[Dict]:
        """Extraer IOCs de los archivos de evidencia del caso"""
        
        iocs = []
        evidence_dir = settings.EVIDENCE_DIR / case_id / "m365_graph"
        
        if not evidence_dir.exists():
            return iocs
        
        # Procesar archivo de consentimientos OAuth
        oauth_file = evidence_dir / "oauth_consents.json"
        if oauth_file.exists():
            try:
                with open(oauth_file) as f:
                    consents = json.load(f)
                    for consent in consents:
                        if isinstance(consent, dict):
                            # Extraer aplicaciones sospechosas
                            app_name = consent.get('appDisplayName', 'Unknown')
                            client_id = consent.get('clientId', '')
                            scope = consent.get('scope', '')
                            
                            # Si tiene permisos amplios, es sospechoso
                            if 'Mail' in scope or 'EWS' in scope or 'user_impersonation' in scope:
                                iocs.append({
                                    'type': 'application',
                                    'value': f"{app_name} ({client_id})",
                                    'severity': 'high',
                                    'source': 'oauth_consents.json',
                                    'details': f"Scope: {scope}"
                                })
            except Exception as e:
                print(f"Error processing oauth_consents.json: {e}")
        
        # Procesar archivo de reglas de bandeja
        rules_file = evidence_dir / "inbox_rules.json"
        if rules_file.exists():
            try:
                content = rules_file.read_text()
                if content and content.strip() != '[]':
                    rules = json.loads(content) if content else []
                    for rule in rules:
                        if isinstance(rule, dict):
                            rule_name = rule.get('displayName', 'Unknown')
                            actions = rule.get('actions', [])
                            iocs.append({
                                'type': 'email_rule',
                                'value': rule_name,
                                'severity': 'medium',
                                'source': 'inbox_rules.json',
                                'details': f"Actions: {len(actions)}"
                            })
            except Exception as e:
                print(f"Error processing inbox_rules.json: {e}")
        
        # Procesar archivo de inicios de sesión arriesgados
        risky_signins_file = evidence_dir / "risky_signins.json"
        if risky_signins_file.exists():
            try:
                content = risky_signins_file.read_text()
                if content and content.strip() != '[]':
                    signins = json.loads(content) if content else []
                    for signin in signins:
                        if isinstance(signin, dict):
                            user = signin.get('userDisplayName', 'Unknown')
                            ip = signin.get('ipAddress', 'N/A')
                            if ip and ip != 'N/A':
                                iocs.append({
                                    'type': 'ip_address',
                                    'value': ip,
                                    'severity': 'high',
                                    'source': 'risky_signins.json',
                                    'details': f"User: {user}"
                                })
            except Exception as e:
                print(f"Error processing risky_signins.json: {e}")
        
        # Procesar archivo de resumen de investigación
        summary_file = evidence_dir / "investigation_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    summary = json.load(f)
                    if isinstance(summary, dict):
                        # Extraer IOCs del resumen
                        if 'suspicious_ips' in summary:
                            for ip in summary.get('suspicious_ips', []):
                                iocs.append({
                                    'type': 'ip_address',
                                    'value': ip,
                                    'severity': 'high',
                                    'source': 'investigation_summary.json',
                                    'details': 'Marked as suspicious'
                                })
                        
                        if 'compromised_accounts' in summary:
                            for account in summary.get('compromised_accounts', []):
                                iocs.append({
                                    'type': 'user_account',
                                    'value': account,
                                    'severity': 'critical',
                                    'source': 'investigation_summary.json',
                                    'details': 'Potential compromise'
                                })
            except Exception as e:
                print(f"Error processing investigation_summary.json: {e}")
        
        return iocs


# Instancia global del servicio
dashboard_data = DashboardDataService()
