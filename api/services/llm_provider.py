"""
LLM Provider Manager - Model Agnostic
======================================
Gestiona múltiples proveedores LLM con detección automática de modelos.
Soporta LM Studio, OpenAI API compatible, Ollama, y fallback offline.

Características:
- Auto-detecta modelos disponibles via /v1/models
- Selecciona automáticamente el primer modelo cargado
- Soporte para completions y chat/completions
- Cache de modelos disponibles
- Fallback inteligente entre proveedores
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Tipos de proveedores LLM soportados"""
    LM_STUDIO = "lm_studio"
    OLLAMA = "ollama"
    OPENAI = "openai"
    LOCAL = "local"
    OFFLINE = "offline"


@dataclass
class ModelInfo:
    """Información de un modelo disponible"""
    id: str
    name: str
    provider: ProviderType
    loaded: bool = False
    size: Optional[int] = None
    context_length: int = 4096
    capabilities: List[str] = field(default_factory=lambda: ["completion", "chat"])
    last_seen: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "loaded": self.loaded,
            "size": self.size,
            "context_length": self.context_length,
            "capabilities": self.capabilities,
            "last_seen": self.last_seen.isoformat()
        }


@dataclass
class ProviderConfig:
    """Configuración de un proveedor"""
    type: ProviderType
    base_url: str
    api_key: Optional[str] = None
    enabled: bool = True
    priority: int = 0
    timeout: int = 120
    max_tokens: int = 2000
    temperature: float = 0.7


class LLMProviderManager:
    """
    Gestor central de proveedores LLM - Agnóstico al modelo
    
    Detecta automáticamente modelos disponibles y usa el primero cargado.
    Soporta múltiples proveedores con fallback inteligente.
    """
    
    def __init__(self):
        self.providers: Dict[ProviderType, ProviderConfig] = {}
        self.models_cache: Dict[str, ModelInfo] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.last_cache_update: Optional[datetime] = None
        self.active_model: Optional[ModelInfo] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configurar proveedores por defecto
        self._setup_default_providers()
        
    def _setup_default_providers(self):
        """Configura proveedores por defecto desde variables de entorno"""
        import os
        
        # Ollama (prioridad más alta en Docker)
        ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        ollama_enabled = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
        self.providers[ProviderType.OLLAMA] = ProviderConfig(
            type=ProviderType.OLLAMA,
            base_url=ollama_url,
            priority=1,
            enabled=ollama_enabled,
            timeout=int(os.getenv("OLLAMA_TIMEOUT", "180"))
        )
        
        # LM Studio (prioridad 2 - servidor externo)
        lm_studio_url = os.getenv("LM_STUDIO_URL", "http://100.101.115.5:2714")
        self.providers[ProviderType.LM_STUDIO] = ProviderConfig(
            type=ProviderType.LM_STUDIO,
            base_url=lm_studio_url,
            priority=2,
            enabled=os.getenv("LM_STUDIO_ENABLED", "true").lower() == "true",
            timeout=int(os.getenv("LLM_STUDIO_TIMEOUT", "120"))
        )
        
        # OpenAI (si hay API key)
        openai_key = os.getenv("OPENAI_API_KEY")
        self.providers[ProviderType.OPENAI] = ProviderConfig(
            type=ProviderType.OPENAI,
            base_url="https://api.openai.com",
            api_key=openai_key,
            priority=3,
            enabled=bool(openai_key)
        )
        
        # Local (Phi-4 or other local model)
        self.providers[ProviderType.LOCAL] = ProviderConfig(
            type=ProviderType.LOCAL,
            base_url="http://localhost:1234/v1",
            priority=4,
            enabled=False
        )

        # Offline fallback (siempre disponible)
        self.providers[ProviderType.OFFLINE] = ProviderConfig(
            type=ProviderType.OFFLINE,
            base_url="",
            priority=99,
            enabled=True
        )
        
        logger.info(f"🤖 LLM Providers configurados: Ollama={ollama_enabled} ({ollama_url}), LM_Studio={lm_studio_url}")
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea sesión HTTP"""
        if self.session is None or self.session.closed:
            # Aumentar timeout para LLMs que pueden tardar más
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=180)  # 3 minutos para LLM
            )
        return self.session
        
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
            
    # ==================== DETECCIÓN DE MODELOS ====================
    
    async def get_available_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """
        Obtiene lista de modelos disponibles de todos los proveedores.
        
        Args:
            force_refresh: Forzar actualización del cache
            
        Returns:
            Lista de ModelInfo con modelos disponibles
        """
        now = datetime.now()
        
        # Usar cache si es válido
        if not force_refresh and self.last_cache_update:
            if now - self.last_cache_update < self.cache_ttl:
                return list(self.models_cache.values())
        
        models = []
        
        # Consultar cada proveedor habilitado
        for provider_type, config in self.providers.items():
            if not config.enabled or provider_type == ProviderType.OFFLINE:
                continue
                
            try:
                provider_models = await self._fetch_models_from_provider(config)
                models.extend(provider_models)
                logger.info(f"✅ {provider_type.value}: {len(provider_models)} modelos encontrados")
            except Exception as e:
                logger.warning(f"⚠️ {provider_type.value}: Error obteniendo modelos - {e}")
        
        # Actualizar cache
        self.models_cache = {m.id: m for m in models}
        self.last_cache_update = now
        
        # Auto-seleccionar modelo activo si no hay uno
        if not self.active_model and models:
            loaded_models = [m for m in models if m.loaded]
            if loaded_models:
                self.active_model = loaded_models[0]
                logger.info(f"🎯 Modelo activo auto-seleccionado: {self.active_model.id}")
            else:
                self.active_model = models[0]
                logger.info(f"🎯 Modelo seleccionado (no cargado): {self.active_model.id}")
        
        return models
    
    async def _fetch_models_from_provider(self, config: ProviderConfig) -> List[ModelInfo]:
        """Obtiene modelos de un proveedor específico"""
        
        if config.type == ProviderType.LM_STUDIO:
            return await self._fetch_lm_studio_models(config)
        elif config.type == ProviderType.OLLAMA:
            return await self._fetch_ollama_models(config)
        elif config.type == ProviderType.OPENAI:
            return await self._fetch_openai_models(config)
        
        return []
    
    async def _fetch_lm_studio_models(self, config: ProviderConfig) -> List[ModelInfo]:
        """Obtiene modelos desde LM Studio"""
        session = await self._get_session()
        models = []
        
        try:
            # LM Studio usa endpoint OpenAI compatible
            # Timeout corto (5s) para no bloquear si el servidor no responde
            async with session.get(
                f"{config.base_url}/v1/models",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for model_data in data.get("data", []):
                        model = ModelInfo(
                            id=model_data.get("id", "unknown"),
                            name=model_data.get("id", "unknown"),
                            provider=ProviderType.LM_STUDIO,
                            loaded=True,  # Si aparece en /v1/models, está cargado
                            context_length=model_data.get("context_length", 4096)
                        )
                        models.append(model)
                        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"⚠️ LM Studio no disponible: {e}")
            
        return models
    
    async def _fetch_ollama_models(self, config: ProviderConfig) -> List[ModelInfo]:
        """Obtiene modelos desde Ollama"""
        session = await self._get_session()
        models = []
        
        try:
            async with session.get(
                f"{config.base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for model_data in data.get("models", []):
                        model = ModelInfo(
                            id=model_data.get("name", "unknown"),
                            name=model_data.get("name", "unknown"),
                            provider=ProviderType.OLLAMA,
                            loaded=True,
                            size=model_data.get("size")
                        )
                        models.append(model)
                        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"Ollama no disponible: {e}")
            
        return models
    
    async def _fetch_openai_models(self, config: ProviderConfig) -> List[ModelInfo]:
        """Obtiene modelos desde OpenAI API"""
        if not config.api_key:
            return []
            
        session = await self._get_session()
        models = []
        
        try:
            headers = {"Authorization": f"Bearer {config.api_key}"}
            async with session.get(
                f"{config.base_url}/v1/models",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Filtrar solo modelos de chat/completion
                    chat_models = ["gpt-4", "gpt-3.5"]
                    for model_data in data.get("data", []):
                        model_id = model_data.get("id", "")
                        if any(prefix in model_id for prefix in chat_models):
                            model = ModelInfo(
                                id=model_id,
                                name=model_id,
                                provider=ProviderType.OPENAI,
                                loaded=True
                            )
                            models.append(model)
                            
        except aiohttp.ClientError as e:
            logger.debug(f"OpenAI no disponible: {e}")
            
        return models
    
    # ==================== GESTIÓN DE MODELOS ====================
    
    async def get_active_model(self) -> Optional[ModelInfo]:
        """Obtiene el modelo activo actual"""
        if not self.active_model:
            await self.get_available_models()
        return self.active_model
    
    async def set_active_model(self, model_id: str) -> bool:
        """
        Establece el modelo activo por ID.
        
        Args:
            model_id: ID del modelo a activar
            
        Returns:
            True si se estableció correctamente
        """
        # Actualizar cache primero
        await self.get_available_models(force_refresh=True)
        
        if model_id in self.models_cache:
            self.active_model = self.models_cache[model_id]
            logger.info(f"🎯 Modelo activo cambiado a: {model_id}")
            return True
        else:
            logger.warning(f"⚠️ Modelo no encontrado: {model_id}")
            return False
    
    async def load_model(self, model_id: str, provider: ProviderType = None) -> Tuple[bool, str]:
        """
        Carga un modelo en el proveedor (si es soportado).
        
        Nota: LM Studio no soporta carga remota, se hace desde GUI.
        Ollama sí soporta carga via API.
        
        Args:
            model_id: ID del modelo a cargar
            provider: Proveedor específico (auto-detecta si None)
            
        Returns:
            Tuple (éxito, mensaje)
        """
        if provider == ProviderType.OLLAMA or (not provider and ProviderType.OLLAMA in self.providers):
            config = self.providers.get(ProviderType.OLLAMA)
            if config and config.enabled:
                try:
                    session = await self._get_session()
                    async with session.post(
                        f"{config.base_url}/api/pull",
                        json={"name": model_id}
                    ) as resp:
                        if resp.status == 200:
                            return True, f"Modelo {model_id} cargado en Ollama"
                except Exception as e:
                    return False, f"Error cargando modelo: {e}"
        
        # LM Studio requiere carga manual desde GUI
        if provider == ProviderType.LM_STUDIO or (not provider):
            return False, "LM Studio requiere cargar modelos desde la interfaz gráfica"
        
        return False, "Proveedor no soporta carga remota de modelos"
    
    # ==================== GENERACIÓN DE TEXTO ====================
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model_id: Optional[str] = None,
        use_chat: bool = True
    ) -> Dict[str, Any]:
        """
        Genera texto usando el modelo activo o especificado.
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Prompt de sistema (opcional)
            max_tokens: Máximo de tokens a generar
            temperature: Temperatura de muestreo
            model_id: ID de modelo específico (usa activo si None)
            use_chat: Usar endpoint chat/completions vs completions
            
        Returns:
            Dict con resultado de generación
        """
        # Determinar modelo a usar
        model = None
        if model_id and model_id in self.models_cache:
            model = self.models_cache[model_id]
        elif self.active_model:
            model = self.active_model
        else:
            # Intentar detectar modelos
            await self.get_available_models()
            model = self.active_model
        
        if not model:
            logger.warning("⚠️ No hay modelo disponible, usando fallback offline")
            return await self._generate_offline(prompt)
        
        # Generar según proveedor
        try:
            config = self.providers.get(model.provider)
            if not config:
                raise ValueError(f"Proveedor no configurado: {model.provider}")
            
            if model.provider == ProviderType.LM_STUDIO:
                return await self._generate_lm_studio(
                    prompt, system_prompt, model, config, max_tokens, temperature, use_chat
                )
            elif model.provider == ProviderType.OLLAMA:
                return await self._generate_ollama(
                    prompt, system_prompt, model, config, max_tokens, temperature
                )
            elif model.provider == ProviderType.OPENAI:
                return await self._generate_openai(
                    prompt, system_prompt, model, config, max_tokens, temperature
                )
            else:
                return await self._generate_offline(prompt)
                
        except Exception as e:
            logger.error(f"❌ Error generando con {model.provider.value}: {e}")
            # Fallback a siguiente proveedor o offline
            return await self._generate_with_fallback(
                prompt, system_prompt, max_tokens, temperature, exclude_provider=model.provider
            )
    
    async def _generate_lm_studio(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: ModelInfo,
        config: ProviderConfig,
        max_tokens: int,
        temperature: float,
        use_chat: bool = True
    ) -> Dict[str, Any]:
        """Genera texto con LM Studio"""
        session = await self._get_session()
        
        if use_chat:
            # Usar chat/completions (preferido)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": model.id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            async with session.post(
                f"{config.base_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {
                        "success": True,
                        "content": content,
                        "model": model.id,
                        "provider": "lm_studio",
                        "usage": data.get("usage", {}),
                        "finish_reason": data.get("choices", [{}])[0].get("finish_reason")
                    }
                else:
                    error_text = await resp.text()
                    raise Exception(f"LM Studio error {resp.status}: {error_text}")
        else:
            # Usar completions legacy
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
                
            payload = {
                "model": model.id,
                "prompt": full_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            async with session.post(
                f"{config.base_url}/v1/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("choices", [{}])[0].get("text", "")
                    return {
                        "success": True,
                        "content": content,
                        "model": model.id,
                        "provider": "lm_studio",
                        "usage": data.get("usage", {})
                    }
                else:
                    error_text = await resp.text()
                    raise Exception(f"LM Studio error {resp.status}: {error_text}")
    
    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: ModelInfo,
        config: ProviderConfig,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Genera texto con Ollama"""
        session = await self._get_session()
        
        payload = {
            "model": model.id,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        async with session.post(
            f"{config.base_url}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=config.timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "success": True,
                    "content": data.get("response", ""),
                    "model": model.id,
                    "provider": "ollama",
                    "eval_count": data.get("eval_count"),
                    "eval_duration": data.get("eval_duration")
                }
            else:
                error_text = await resp.text()
                raise Exception(f"Ollama error {resp.status}: {error_text}")
    
    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: ModelInfo,
        config: ProviderConfig,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Genera texto con OpenAI API"""
        session = await self._get_session()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model.id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        headers = {"Authorization": f"Bearer {config.api_key}"}
        
        async with session.post(
            f"{config.base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=config.timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {
                    "success": True,
                    "content": content,
                    "model": model.id,
                    "provider": "openai",
                    "usage": data.get("usage", {})
                }
            else:
                error_text = await resp.text()
                raise Exception(f"OpenAI error {resp.status}: {error_text}")
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        exclude_provider: ProviderType
    ) -> Dict[str, Any]:
        """Intenta generar con proveedores alternativos"""
        
        # Ordenar proveedores por prioridad
        sorted_providers = sorted(
            self.providers.items(),
            key=lambda x: x[1].priority
        )
        
        for provider_type, config in sorted_providers:
            if provider_type == exclude_provider or not config.enabled:
                continue
            if provider_type == ProviderType.OFFLINE:
                continue
                
            # Buscar modelo de este proveedor
            for model in self.models_cache.values():
                if model.provider == provider_type and model.loaded:
                    try:
                        logger.info(f"🔄 Intentando fallback con {provider_type.value}")
                        if provider_type == ProviderType.LM_STUDIO:
                            return await self._generate_lm_studio(
                                prompt, system_prompt, model, config, max_tokens, temperature, True
                            )
                        elif provider_type == ProviderType.OLLAMA:
                            return await self._generate_ollama(
                                prompt, system_prompt, model, config, max_tokens, temperature
                            )
                        elif provider_type == ProviderType.OPENAI:
                            return await self._generate_openai(
                                prompt, system_prompt, model, config, max_tokens, temperature
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ Fallback {provider_type.value} falló: {e}")
                        continue
        
        # Último recurso: offline
        return await self._generate_offline(prompt)
    
    async def _generate_offline(self, prompt: str) -> Dict[str, Any]:
        """Genera respuesta offline cuando no hay LLM disponible"""
        logger.warning("📴 Usando modo offline - análisis limitado")
        
        # Análisis básico del prompt para respuestas contextuales
        prompt_lower = prompt.lower()
        
        if "m365" in prompt_lower or "microsoft" in prompt_lower or "azure" in prompt_lower:
            content = """## Análisis Offline - M365/Azure

⚠️ **Análisis realizado sin LLM disponible**

### Recomendaciones Generales:
1. Verificar logs de inicio de sesión en Azure AD
2. Revisar cambios en políticas de acceso condicional
3. Auditar delegaciones de permisos en Exchange Online
4. Buscar reglas de buzón sospechosas
5. Verificar registros de aplicaciones OAuth

### Indicadores a Buscar:
- Inicios de sesión desde ubicaciones inusuales
- Horarios de acceso fuera de patrón
- Cambios masivos en configuración
- Nuevas reglas de reenvío de correo
- Tokens de actualización comprometidos

*Conecte un modelo LLM para análisis detallado.*"""

        elif "credential" in prompt_lower or "password" in prompt_lower or "breach" in prompt_lower:
            content = """## Análisis Offline - Credenciales

⚠️ **Análisis realizado sin LLM disponible**

### Acciones Recomendadas:
1. Forzar cambio de contraseñas comprometidas
2. Habilitar MFA en todas las cuentas afectadas
3. Revocar sesiones activas
4. Auditar accesos recientes
5. Buscar en registros de stealer logs

*Conecte un modelo LLM para análisis detallado.*"""

        elif "endpoint" in prompt_lower or "malware" in prompt_lower or "ioc" in prompt_lower:
            content = """## Análisis Offline - Endpoint

⚠️ **Análisis realizado sin LLM disponible**

### Pasos de Remediación:
1. Aislar endpoint de la red
2. Capturar memoria volátil
3. Ejecutar escaneo YARA completo
4. Verificar persistencia (servicios, tareas, registro)
5. Analizar conexiones de red

*Conecte un modelo LLM para análisis detallado.*"""

        else:
            content = """## Análisis Offline

⚠️ **No hay modelo LLM disponible**

El análisis detallado requiere conexión a un proveedor LLM.

### Opciones:
1. **LM Studio**: Cargar un modelo en la interfaz gráfica
2. **Ollama**: `ollama run llama3.3`
3. **OpenAI**: Configurar OPENAI_API_KEY

*El análisis básico de herramientas forenses está disponible.*"""

        return {
            "success": True,
            "content": content,
            "model": "offline",
            "provider": "offline",
            "warning": "LLM no disponible - respuesta generada offline"
        }
    
    # ==================== HEALTH CHECK ====================
    
    async def is_available(self) -> bool:
        """
        v4.6: Verifica rápidamente si algún LLM está disponible
        Retorna True si hay al menos un proveedor saludable
        """
        try:
            health = await self.health_check()
            return health.get("healthy", False)
        except Exception:
            return False
    
    async def generate_text(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        v4.6: Wrapper simple para generación de texto
        Retorna solo el texto generado o None si falla
        """
        try:
            result = await self.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                require_loaded=True
            )
            if result.get("success"):
                return result.get("response", "").strip()
            return None
        except Exception as e:
            logger.warning(f"Error en generate_text: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica estado de todos los proveedores"""
        status = {
            "healthy": False,
            "providers": {},
            "active_model": None,
            "total_models": 0
        }
        
        for provider_type, config in self.providers.items():
            if not config.enabled:
                status["providers"][provider_type.value] = {"status": "disabled"}
                continue
            if provider_type == ProviderType.OFFLINE:
                status["providers"][provider_type.value] = {"status": "available"}
                continue
                
            try:
                session = await self._get_session()
                
                if provider_type == ProviderType.LM_STUDIO:
                    url = f"{config.base_url}/v1/models"
                elif provider_type == ProviderType.OLLAMA:
                    url = f"{config.base_url}/api/tags"
                elif provider_type == ProviderType.OPENAI:
                    url = f"{config.base_url}/v1/models"
                else:
                    continue
                
                headers = {}
                if provider_type == ProviderType.OPENAI and config.api_key:
                    headers["Authorization"] = f"Bearer {config.api_key}"
                
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        status["providers"][provider_type.value] = {
                            "status": "healthy",
                            "url": config.base_url
                        }
                        status["healthy"] = True
                    else:
                        status["providers"][provider_type.value] = {
                            "status": "error",
                            "code": resp.status
                        }
                        
            except Exception as e:
                status["providers"][provider_type.value] = {
                    "status": "unreachable",
                    "error": str(e)
                }
        
        # Info del modelo activo
        if self.active_model:
            status["active_model"] = self.active_model.to_dict()
        status["total_models"] = len(self.models_cache)
        
        return status
    
    # ==================== ANÁLISIS FORENSE ====================
    
    async def analyze_forensic_findings(
        self,
        findings: Dict[str, Any],
        context: str = "m365",
        severity_threshold: str = "medium",
        full_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analiza hallazgos forenses con LLM.
        
        Args:
            findings: Resultados de herramientas forenses
            context: Contexto del análisis (m365, endpoint, credentials)
            severity_threshold: Umbral de severidad para alertas
            full_context: Contexto enriquecido del caso (opcional)
            
        Returns:
            Análisis enriquecido con recomendaciones
        """
        # Construir prompt según contexto
        if context == "m365":
            system_prompt = """Eres un analista de seguridad especializado en Microsoft 365.
Analiza los hallazgos forenses y proporciona:
1. Resumen ejecutivo del incidente
2. Indicadores de compromiso (IOCs) identificados
3. Línea de tiempo del ataque (si es posible reconstruir)
4. Evaluación de impacto y severidad
5. Recomendaciones de remediación ordenadas por prioridad
6. Acciones de contención inmediata

Responde en español y formato Markdown."""
            
        elif context == "endpoint":
            system_prompt = """Eres un analista de malware y respuesta a incidentes.
Analiza los hallazgos del endpoint y proporciona:
1. Clasificación de la amenaza detectada
2. Indicadores de compromiso (IOCs)
3. Técnicas MITRE ATT&CK identificadas
4. Análisis de persistencia
5. Pasos de remediación
6. Recomendaciones de hardening

Responde en español y formato Markdown."""
            
        elif context == "credentials":
            system_prompt = """Eres un especialista en gestión de credenciales y breaches.
Analiza los hallazgos de credenciales y proporciona:
1. Resumen de exposición
2. Fuentes del leak identificadas
3. Evaluación de riesgo por cuenta
4. Priorización de remediación
5. Acciones inmediatas requeridas
6. Recomendaciones de seguridad

Responde en español y formato Markdown."""
        else:
            system_prompt = """Eres un analista de ciberseguridad.
Analiza los hallazgos y proporciona un informe detallado con recomendaciones.
Responde en español y formato Markdown."""
        
        # Formatear findings para el prompt
        findings_text = json.dumps(findings, indent=2, default=str, ensure_ascii=False)
        
        if full_context:
            prompt = f"""ANÁLISIS FORENSE AVANZADO

CONTEXTO COMPLETO DEL CASO:
{full_context}

HALLAZGOS ESPECÍFICOS A ANALIZAR:
```json
{findings_text}
```

Proporciona un análisis detallado correlacionando los hallazgos con el contexto del caso.
Identifica patrones de ataque, severidad y recomienda acciones."""
        else:
            prompt = f"""Analiza los siguientes hallazgos forenses:

```json
{findings_text}
```

Proporciona un análisis detallado con recomendaciones accionables."""
        
        # Generar análisis
        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3000,
            temperature=0.3  # Más determinístico para análisis
        )
        
        # Agregar metadata
        result["context"] = context
        result["findings_count"] = len(findings) if isinstance(findings, list) else 1
        result["severity_threshold"] = severity_threshold
        
        return result


# ==================== INSTANCIA GLOBAL ====================

# Singleton del manager
_llm_manager: Optional[LLMProviderManager] = None


def get_llm_manager() -> LLMProviderManager:
    """Obtiene la instancia global del LLM Manager"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMProviderManager()
    return _llm_manager


async def init_llm_manager() -> LLMProviderManager:
    """Inicializa el LLM Manager y detecta modelos"""
    manager = get_llm_manager()
    await manager.get_available_models()
    return manager


async def cleanup_llm_manager():
    """Limpia recursos del LLM Manager"""
    global _llm_manager
    if _llm_manager:
        await _llm_manager.close()
        _llm_manager = None
