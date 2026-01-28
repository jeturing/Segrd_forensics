"""
System Settings Routes v4.7
============================
CRUD endpoints para gestión de configuración del sistema desde BD.
Permite administrar LLM, SMTP, MINIO, API keys, etc. desde el panel admin.

Prioridad de configuración: BD > ENV > defaults (config.py)
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import json

from api.middleware.auth import get_current_user, require_global_admin
from api.config import get_settings
from api.services.settings_loader import get_settings_loader, init_settings_loader
from api.services.encryption import encrypt_value, decrypt_value, mask_secret

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/api/admin/settings",
    tags=["System Settings"],
    dependencies=[Depends(require_global_admin)]
)


# ============================================================================
# SCHEMAS
# ============================================================================

class SystemSettingResponse(BaseModel):
    """Setting individual."""
    key: str
    value: Optional[str] = None
    display_value: Optional[str] = None  # Valor enmascarado para secrets
    value_type: str = "string"
    category: str
    subcategory: Optional[str] = None
    display_name: str
    description: Optional[str] = None
    is_secret: bool = False
    is_editable: bool = True
    env_var_name: Optional[str] = None
    updated_at: Optional[datetime] = None


class SystemSettingUpdate(BaseModel):
    """Actualización de un setting."""
    key: str
    value: str


class SystemSettingsBulkUpdate(BaseModel):
    """Actualización masiva de settings."""
    settings: List[SystemSettingUpdate]


class LLMModelResponse(BaseModel):
    """Modelo LLM."""
    id: int
    provider: str
    model_id: str
    display_name: str
    description: Optional[str] = None
    context_length: int = 4096
    capabilities: List[str] = ["chat", "completion"]
    is_active: bool = True
    is_default: bool = False
    priority: int = 100
    endpoint_url: Optional[str] = None


class LLMModelCreate(BaseModel):
    """Crear nuevo modelo LLM."""
    provider: str = Field(..., description="ollama, lm_studio, openai, local")
    model_id: str = Field(..., description="Identificador del modelo (ej: llama3.2:1b)")
    display_name: str
    description: Optional[str] = None
    context_length: int = 4096
    is_active: bool = True
    is_default: bool = False
    priority: int = 100
    endpoint_url: Optional[str] = None


class LLMModelUpdate(BaseModel):
    """Actualizar modelo LLM."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    context_length: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = None
    endpoint_url: Optional[str] = None


# ============================================================================
# SYSTEM SETTINGS CRUD
# ============================================================================

@router.get("/", response_model=Dict[str, List[SystemSettingResponse]])
async def get_all_settings(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    current_user: dict = Depends(get_current_user)
):
    """
    📋 Obtener todos los settings del sistema agrupados por categoría.
    Los valores secretos se muestran enmascarados.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        result = {}
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT key, value, value_type, category, subcategory, 
                       display_name, description, is_secret, is_editable,
                       env_var_name, updated_at
                FROM system_settings
            """
            params = []
            
            if category:
                query += " WHERE category = %s"
                params.append(category)
            
            query += " ORDER BY category, priority, key"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            for row in rows:
                cat = row['category']
                if cat not in result:
                    result[cat] = []
                
                # Enmascarar secrets
                display_value = row['value']
                if row['is_secret'] and row['value']:
                    display_value = mask_secret(row['value'])
                
                result[cat].append({
                    "key": row['key'],
                    "value": row['value'] if not row['is_secret'] else None,
                    "display_value": display_value,
                    "value_type": row['value_type'],
                    "category": row['category'],
                    "subcategory": row['subcategory'],
                    "display_name": row['display_name'],
                    "description": row['description'],
                    "is_secret": row['is_secret'],
                    "is_editable": row['is_editable'],
                    "env_var_name": row['env_var_name'],
                    "updated_at": row['updated_at']
                })
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    """
    📁 Obtener lista de categorías de settings disponibles.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT category, COUNT(*) as count
                FROM system_settings
                GROUP BY category
                ORDER BY category
            """)
            
            categories = [
                {"category": row['category'], "count": row['count']}
                for row in cur.fetchall()
            ]
        
        conn.close()
        
        return {
            "success": True,
            "categories": categories
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}", response_model=SystemSettingResponse)
async def get_setting(key: str, current_user: dict = Depends(get_current_user)):
    """
    🔍 Obtener un setting específico por su key.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT key, value, value_type, category, subcategory,
                       display_name, description, is_secret, is_editable,
                       env_var_name, updated_at
                FROM system_settings
                WHERE key = %s
            """, (key,))
            
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
            
            display_value = row['value']
            if row['is_secret'] and row['value']:
                display_value = mask_secret(row['value'])
            
            result = {
                "key": row['key'],
                "value": row['value'] if not row['is_secret'] else None,
                "display_value": display_value,
                "value_type": row['value_type'],
                "category": row['category'],
                "subcategory": row['subcategory'],
                "display_name": row['display_name'],
                "description": row['description'],
                "is_secret": row['is_secret'],
                "is_editable": row['is_editable'],
                "env_var_name": row['env_var_name'],
                "updated_at": row['updated_at']
            }
        
        conn.close()
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{key}")
async def update_setting(
    key: str, 
    update: SystemSettingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ✏️ Actualizar un setting específico.
    Los valores secretos se encriptan automáticamente.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar que existe y es editable
            cur.execute("""
                SELECT key, is_secret, is_editable FROM system_settings WHERE key = %s
            """, (key,))
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
            
            if not row['is_editable']:
                raise HTTPException(status_code=403, detail=f"Setting '{key}' is read-only")
            
            # Encriptar si es secreto
            save_value = update.value
            is_encrypted = False
            if row['is_secret']:
                save_value = encrypt_value(update.value)
                is_encrypted = True
            
            # Actualizar
            cur.execute("""
                UPDATE system_settings 
                SET value = %s, is_encrypted = %s, updated_by = %s, updated_at = NOW()
                WHERE key = %s
            """, (save_value, is_encrypted, current_user.get('username', 'admin'), key))
            
            conn.commit()
        
        conn.close()
        
        # Refrescar caché
        loader = get_settings_loader()
        await loader.refresh()
        
        logger.info(f"✅ Setting {key} updated by {current_user.get('username')}")
        
        return {
            "success": True,
            "message": f"Setting '{key}' updated successfully",
            "key": key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bulk/update")
async def update_settings_bulk(
    updates: SystemSettingsBulkUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    📝 Actualizar múltiples settings a la vez.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        updated = []
        errors = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for item in updates.settings:
                try:
                    # Verificar existencia
                    cur.execute("""
                        SELECT key, is_secret, is_editable FROM system_settings WHERE key = %s
                    """, (item.key,))
                    
                    row = cur.fetchone()
                    if not row:
                        errors.append({"key": item.key, "error": "Not found"})
                        continue
                    
                    if not row['is_editable']:
                        errors.append({"key": item.key, "error": "Read-only"})
                        continue
                    
                    # Encriptar si es secreto
                    save_value = item.value
                    is_encrypted = False
                    if row['is_secret']:
                        save_value = encrypt_value(item.value)
                        is_encrypted = True
                    
                    # Actualizar
                    cur.execute("""
                        UPDATE system_settings 
                        SET value = %s, is_encrypted = %s, updated_by = %s, updated_at = NOW()
                        WHERE key = %s
                    """, (save_value, is_encrypted, current_user.get('username', 'admin'), item.key))
                    
                    updated.append(item.key)
                    
                except Exception as e:
                    errors.append({"key": item.key, "error": str(e)})
            
            conn.commit()
        
        conn.close()
        
        # Refrescar caché
        loader = get_settings_loader()
        await loader.refresh()
        
        return {
            "success": True,
            "updated": updated,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"❌ Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LLM MODELS CRUD
# ============================================================================

@router.get("/llm/models", response_model=List[LLMModelResponse])
async def get_llm_models(
    provider: Optional[str] = Query(None, description="Filtrar por proveedor"),
    active_only: bool = Query(True, description="Solo modelos activos"),
    current_user: dict = Depends(get_current_user)
):
    """
    🤖 Obtener lista de modelos LLM disponibles.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        models = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, provider, model_id, display_name, description,
                       context_length, capabilities, is_active, is_default,
                       priority, endpoint_url
                FROM llm_models
                WHERE 1=1
            """
            params = []
            
            if provider:
                query += " AND provider = %s"
                params.append(provider)
            
            if active_only:
                query += " AND is_active = true"
            
            query += " ORDER BY priority, provider, model_id"
            
            cur.execute(query, params)
            
            for row in cur.fetchall():
                capabilities = row['capabilities']
                if isinstance(capabilities, str):
                    capabilities = json.loads(capabilities)
                
                models.append({
                    "id": row['id'],
                    "provider": row['provider'],
                    "model_id": row['model_id'],
                    "display_name": row['display_name'],
                    "description": row['description'],
                    "context_length": row['context_length'],
                    "capabilities": capabilities or ["chat", "completion"],
                    "is_active": row['is_active'],
                    "is_default": row['is_default'],
                    "priority": row['priority'],
                    "endpoint_url": row['endpoint_url']
                })
        
        conn.close()
        return models
        
    except Exception as e:
        logger.error(f"❌ Error fetching LLM models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/models", response_model=LLMModelResponse)
async def create_llm_model(
    model: LLMModelCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo modelo LLM.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Si es default, quitar default de otros del mismo provider
            if model.is_default:
                cur.execute("""
                    UPDATE llm_models SET is_default = false WHERE provider = %s
                """, (model.provider,))
            
            cur.execute("""
                INSERT INTO llm_models (
                    provider, model_id, display_name, description,
                    context_length, is_active, is_default, priority, endpoint_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, provider, model_id, display_name, description,
                          context_length, capabilities, is_active, is_default, priority, endpoint_url
            """, (
                model.provider, model.model_id, model.display_name, model.description,
                model.context_length, model.is_active, model.is_default, 
                model.priority, model.endpoint_url
            ))
            
            row = cur.fetchone()
            conn.commit()
            
            if not row:
                raise HTTPException(status_code=500, detail="Failed to create model")
            
            result = {
                "id": row['id'],
                "provider": row['provider'],
                "model_id": row['model_id'],
                "display_name": row['display_name'],
                "description": row['description'],
                "context_length": row['context_length'],
                "capabilities": ["chat", "completion"],
                "is_active": row['is_active'],
                "is_default": row['is_default'],
                "priority": row['priority'],
                "endpoint_url": row['endpoint_url']
            }
        
        conn.close()
        
        logger.info(f"✅ LLM model {model.model_id} created by {current_user.get('username')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error creating LLM model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/llm/models/{model_id}")
async def update_llm_model(
    model_id: int,
    update: LLMModelUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ✏️ Actualizar un modelo LLM.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar existencia
            cur.execute("SELECT id, provider FROM llm_models WHERE id = %s", (model_id,))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
            
            # Si se marca como default, quitar default de otros
            if update.is_default:
                cur.execute("""
                    UPDATE llm_models SET is_default = false WHERE provider = %s AND id != %s
                """, (row['provider'], model_id))
            
            # Construir UPDATE dinámico
            updates = []
            params = []
            
            if update.display_name is not None:
                updates.append("display_name = %s")
                params.append(update.display_name)
            if update.description is not None:
                updates.append("description = %s")
                params.append(update.description)
            if update.context_length is not None:
                updates.append("context_length = %s")
                params.append(update.context_length)
            if update.is_active is not None:
                updates.append("is_active = %s")
                params.append(update.is_active)
            if update.is_default is not None:
                updates.append("is_default = %s")
                params.append(update.is_default)
            if update.priority is not None:
                updates.append("priority = %s")
                params.append(update.priority)
            if update.endpoint_url is not None:
                updates.append("endpoint_url = %s")
                params.append(update.endpoint_url)
            
            if updates:
                params.append(model_id)
                cur.execute(f"""
                    UPDATE llm_models SET {', '.join(updates)} WHERE id = %s
                """, params)
            
            conn.commit()
        
        conn.close()
        
        return {"success": True, "message": f"Model {model_id} updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating LLM model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/llm/models/{model_id}")
async def delete_llm_model(
    model_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    🗑️ Eliminar un modelo LLM.
    """
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor() as cur:
            cur.execute("DELETE FROM llm_models WHERE id = %s", (model_id,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"🗑️ LLM model {model_id} deleted by {current_user.get('username')}")
        
        return {"success": True, "message": f"Model {model_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting LLM model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/models/{model_id}/set-default")
async def set_default_llm_model(
    model_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    ⭐ Establecer un modelo como el predeterminado para su proveedor.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Obtener provider
            cur.execute("SELECT provider, model_id FROM llm_models WHERE id = %s", (model_id,))
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
            
            # Quitar default de todos los del mismo provider
            cur.execute("""
                UPDATE llm_models SET is_default = false WHERE provider = %s
            """, (row['provider'],))
            
            # Marcar este como default
            cur.execute("""
                UPDATE llm_models SET is_default = true WHERE id = %s
            """, (model_id,))
            
            conn.commit()
        
        conn.close()
        
        return {
            "success": True,
            "message": f"Model {row['model_id']} is now the default for {row['provider']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error setting default model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/sync-ollama")
async def sync_ollama_models(current_user: dict = Depends(get_current_user)):
    """
    🔄 Sincronizar modelos disponibles en Ollama con la BD.
    Detecta automáticamente modelos instalados en el contenedor Ollama.
    """
    try:
        import aiohttp
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        ollama_url = settings.OLLAMA_URL if hasattr(settings, 'OLLAMA_URL') else "http://ollama:11434"
        
        # Obtener modelos de Ollama
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(f"{ollama_url}/api/tags") as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=502, detail="Could not connect to Ollama")
                
                data = await resp.json()
                ollama_models = data.get('models', [])
        
        # Sincronizar con BD
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        added = []
        updated = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for model in ollama_models:
                model_name = model.get('name', '')
                model_size = model.get('size', 0)
                
                # Verificar si existe
                cur.execute("""
                    SELECT id FROM llm_models WHERE provider = 'ollama' AND model_id = %s
                """, (model_name,))
                
                existing = cur.fetchone()
                
                if existing:
                    # Actualizar
                    cur.execute("""
                        UPDATE llm_models SET is_active = true WHERE id = %s
                    """, (existing['id'],))
                    updated.append(model_name)
                else:
                    # Crear
                    display_name = model_name.replace(':', ' ').replace('-', ' ').title()
                    cur.execute("""
                        INSERT INTO llm_models (provider, model_id, display_name, is_active, priority)
                        VALUES ('ollama', %s, %s, true, 100)
                    """, (model_name, display_name))
                    added.append(model_name)
            
            conn.commit()
        
        conn.close()
        
        return {
            "success": True,
            "ollama_models": [m.get('name') for m in ollama_models],
            "added": added,
            "updated": updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error syncing Ollama models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CACHE & LOADER MANAGEMENT
# ============================================================================

@router.get("/cache/status")
async def get_cache_status(current_user: dict = Depends(get_current_user)):
    """
    📊 Obtener estado del caché de settings.
    """
    loader = get_settings_loader()
    return {
        "success": True,
        "cache": loader.cache_stats,
        "llm_models_cached": len(loader.get_llm_models())
    }


@router.post("/cache/refresh")
async def refresh_cache(current_user: dict = Depends(get_current_user)):
    """
    🔄 Refrescar el caché de settings desde la BD.
    """
    loader = get_settings_loader()
    await loader.refresh()
    
    return {
        "success": True,
        "message": "Settings cache refreshed",
        "cache": loader.cache_stats
    }
