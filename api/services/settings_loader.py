"""
Settings Loader Service - Dynamic Configuration from DB
========================================================
Carga configuración con prioridad: BD > env vars > defaults (config.py)

Este servicio permite:
- Leer settings desde PostgreSQL (tabla system_settings)
- Fallback automático a variables de entorno si BD no disponible
- Fallback final a valores por defecto en config.py
- Cache en memoria para evitar consultas repetidas
- Refresh automático cada N segundos
"""

import os
import asyncio
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from functools import lru_cache
import json

logger = logging.getLogger(__name__)


class SettingsLoader:
    """
    Cargador de configuración con prioridad: BD > ENV > DEFAULTS
    
    Uso:
        loader = get_settings_loader()
        value = await loader.get("smtp_host", default="localhost")
        
        # O sincrónico (usa caché):
        value = loader.get_sync("smtp_host", default="localhost")
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        self._db_available = False
        self._initialized = False
        
        # Mapeo de env vars a keys de BD
        self._env_mapping: Dict[str, str] = {}
        
    async def initialize(self, db_pool=None):
        """
        Inicializa el loader cargando settings desde BD.
        
        Args:
            db_pool: Pool de conexiones asyncpg (opcional)
        """
        if self._initialized:
            return
            
        try:
            await self._load_from_db(db_pool)
            self._initialized = True
            logger.info(f"🔧 Settings loader initialized with {len(self._cache)} settings from DB")
        except Exception as e:
            logger.warning(f"⚠️ Could not load settings from DB: {e}")
            logger.info("📁 Using env vars and defaults")
            self._db_available = False
            self._initialized = True
    
    async def _load_from_db(self, db_pool=None):
        """Carga todos los settings desde la BD."""
        try:
            # Intentar conexión con asyncpg
            import asyncpg
            
            db_url = os.getenv(
                "DATABASE_URL", 
                "postgresql://forensics:1212lne1ne12090d12@postgres:5432/forensics"
            )
            
            # Limpiar URL si tiene +asyncpg
            db_url = db_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
            
            if db_pool:
                conn = await db_pool.acquire()
            else:
                conn = await asyncpg.connect(db_url)
            
            try:
                # Verificar si la tabla existe
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'system_settings'
                    )
                """)
                
                if not table_exists:
                    logger.info("📋 system_settings table not found - running migrations needed")
                    self._db_available = False
                    return
                
                # Cargar todos los settings
                rows = await conn.fetch("""
                    SELECT key, value, value_type, is_secret, is_encrypted, env_var_name
                    FROM system_settings
                    WHERE value IS NOT NULL
                """)
                
                for row in rows:
                    key = row['key']
                    value = row['value']
                    value_type = row['value_type']
                    
                    # Desencriptar si es necesario
                    if row['is_encrypted'] and row['is_secret']:
                        from api.services.encryption import decrypt_value
                        value = decrypt_value(value)
                    
                    # Convertir tipo
                    self._cache[key] = self._convert_type(value, value_type)
                    
                    # Guardar mapeo de env var
                    if row['env_var_name']:
                        self._env_mapping[row['env_var_name']] = key
                
                self._cache_time = datetime.now()
                self._db_available = True
                
                # También cargar modelos LLM
                await self._load_llm_models(conn)
                
            finally:
                if not db_pool:
                    await conn.close()
                else:
                    await db_pool.release(conn)
                    
        except ImportError:
            logger.warning("asyncpg not installed - using sync psycopg2")
            await self._load_from_db_sync()
        except Exception as e:
            logger.error(f"Error loading settings from DB: {e}")
            self._db_available = False
            raise
    
    async def _load_from_db_sync(self):
        """Fallback síncrono con psycopg2."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://forensics:1212lne1ne12090d12@postgres:5432/forensics"
            )
            
            conn = psycopg2.connect(db_url)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Verificar tabla
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'system_settings'
                        )
                    """)
                    exists_row = cur.fetchone()
                    if not exists_row or not exists_row['exists']:
                        self._db_available = False
                        return
                    
                    # Cargar settings
                    cur.execute("""
                        SELECT key, value, value_type, is_secret, is_encrypted, env_var_name
                        FROM system_settings
                        WHERE value IS NOT NULL
                    """)
                    
                    for row in cur.fetchall():
                        key = row['key']
                        value = row['value']
                        value_type = row['value_type']
                        
                        if row['is_encrypted'] and row['is_secret']:
                            from api.services.encryption import decrypt_value
                            value = decrypt_value(value)
                        
                        self._cache[key] = self._convert_type(value, value_type)
                        
                        if row['env_var_name']:
                            self._env_mapping[row['env_var_name']] = key
                    
                    self._cache_time = datetime.now()
                    self._db_available = True
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Sync DB load failed: {e}")
            self._db_available = False
    
    async def _load_llm_models(self, conn):
        """Carga modelos LLM disponibles."""
        try:
            rows = await conn.fetch("""
                SELECT provider, model_id, display_name, context_length, 
                       is_active, is_default, priority, endpoint_url, config
                FROM llm_models
                WHERE is_active = true
                ORDER BY priority
            """)
            
            models = []
            for row in rows:
                models.append({
                    "provider": row['provider'],
                    "model_id": row['model_id'],
                    "display_name": row['display_name'],
                    "context_length": row['context_length'],
                    "is_default": row['is_default'],
                    "priority": row['priority'],
                    "endpoint_url": row['endpoint_url'],
                    "config": json.loads(row['config']) if row['config'] else {}
                })
            
            self._cache['_llm_models'] = models
            logger.info(f"🤖 Loaded {len(models)} LLM models from DB")
            
        except Exception as e:
            logger.warning(f"Could not load LLM models: {e}")
    
    def _convert_type(self, value: str, value_type: str) -> Any:
        """Convierte valor al tipo correcto."""
        if value is None:
            return None
            
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'bool':
                return value.lower() in ('true', '1', 'yes', 'on')
            elif value_type == 'json':
                return json.loads(value)
            elif value_type == 'float':
                return float(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError):
            return value
    
    def _is_cache_valid(self) -> bool:
        """Verifica si el caché es válido."""
        if not self._cache_time:
            return False
        return datetime.now() - self._cache_time < self._cache_ttl
    
    async def get(self, key: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        Obtiene un setting con prioridad: BD > ENV > default.
        
        Args:
            key: Clave del setting en BD
            default: Valor por defecto si no existe
            env_var: Variable de entorno alternativa
            
        Returns:
            Valor del setting
        """
        # 1. Buscar en caché (BD)
        if key in self._cache:
            return self._cache[key]
        
        # 2. Buscar en variables de entorno
        env_name = env_var or key.upper()
        env_value = os.getenv(env_name)
        if env_value is not None:
            return env_value
        
        # 3. Retornar default
        return default
    
    def get_sync(self, key: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        Versión síncrona de get() - usa solo caché y env vars.
        """
        # 1. Buscar en caché
        if key in self._cache:
            return self._cache[key]
        
        # 2. Variables de entorno
        env_name = env_var or key.upper()
        env_value = os.getenv(env_name)
        if env_value is not None:
            return env_value
        
        # 3. Default
        return default
    
    async def set(self, key: str, value: Any, user: str = "system") -> bool:
        """
        Guarda un setting en la BD.
        
        Args:
            key: Clave del setting
            value: Nuevo valor
            user: Usuario que hace el cambio
            
        Returns:
            True si se guardó correctamente
        """
        if not self._db_available:
            logger.warning(f"Cannot save setting {key} - DB not available")
            return False
        
        try:
            import asyncpg
            
            db_url_raw = os.getenv("DATABASE_URL", "")
            db_url = db_url_raw.replace("+asyncpg", "") if db_url_raw else ""
            conn = await asyncpg.connect(db_url)
            
            try:
                # Obtener info del setting
                row = await conn.fetchrow("""
                    SELECT is_secret, is_encrypted FROM system_settings WHERE key = $1
                """, key)
                
                if not row:
                    logger.warning(f"Setting {key} not found in DB")
                    return False
                
                # Encriptar si es necesario
                save_value = str(value)
                if row['is_secret']:
                    from api.services.encryption import encrypt_value
                    save_value = encrypt_value(save_value)
                    is_encrypted = True
                else:
                    is_encrypted = False
                
                # Actualizar
                await conn.execute("""
                    UPDATE system_settings 
                    SET value = $1, is_encrypted = $2, updated_by = $3, updated_at = NOW()
                    WHERE key = $4
                """, save_value, is_encrypted, user, key)
                
                # Actualizar caché
                self._cache[key] = value
                
                logger.info(f"✅ Setting {key} updated by {user}")
                return True
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error saving setting {key}: {e}")
            return False
    
    async def get_by_category(self, category: str) -> Dict[str, Any]:
        """Obtiene todos los settings de una categoría."""
        return {k: v for k, v in self._cache.items() 
                if not k.startswith('_')}  # Excluir claves internas
    
    def get_llm_models(self) -> List[Dict]:
        """Obtiene la lista de modelos LLM disponibles."""
        return self._cache.get('_llm_models', [])
    
    def get_default_llm_model(self) -> Optional[Dict]:
        """Obtiene el modelo LLM por defecto."""
        models = self.get_llm_models()
        for model in models:
            if model.get('is_default'):
                return model
        return models[0] if models else None
    
    async def refresh(self):
        """Recarga settings desde la BD."""
        self._cache.clear()
        self._initialized = False
        await self.initialize()
    
    @property
    def is_db_available(self) -> bool:
        return self._db_available
    
    @property
    def cache_stats(self) -> Dict:
        return {
            "entries": len(self._cache),
            "db_available": self._db_available,
            "cache_time": self._cache_time.isoformat() if self._cache_time else None,
            "cache_valid": self._is_cache_valid()
        }


# Singleton
_settings_loader: Optional[SettingsLoader] = None


def get_settings_loader() -> SettingsLoader:
    """Obtiene la instancia singleton del settings loader."""
    global _settings_loader
    if _settings_loader is None:
        _settings_loader = SettingsLoader()
    return _settings_loader


async def init_settings_loader(db_pool=None) -> SettingsLoader:
    """Inicializa el settings loader (llamar al startup de la app)."""
    loader = get_settings_loader()
    await loader.initialize(db_pool)
    return loader


# Helpers síncronos para usar en config.py
def get_setting(key: str, default: Any = None, env_var: Optional[str] = None) -> Any:
    """Helper síncrono para obtener un setting."""
    return get_settings_loader().get_sync(key, default, env_var)
