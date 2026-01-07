"""
MCP Kali Forensics v4.4 - Case Context Manager
===============================================
Gestor central de contexto de casos para toda la aplicación.
Asegura que TODAS las acciones estén vinculadas a un caso.

Author: MCP Forensics Team
Version: 4.4.0
"""

from datetime import datetime
from typing import Dict, Optional, List
from fastapi import HTTPException, Request
import logging
import uuid
from threading import Lock

logger = logging.getLogger(__name__)


class CaseContext:
    """Contexto individual de un caso activo"""
    
    def __init__(self, case_id: str, metadata: Optional[Dict] = None):
        self.case_id = case_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.session_id = str(uuid.uuid4())
        self.actions: List[Dict] = []
        self.active_processes: List[str] = []
        
    def touch(self):
        """Actualizar timestamp de último acceso"""
        self.last_accessed = datetime.utcnow()
        
    def add_action(self, action_type: str, action_data: Dict):
        """Registrar una acción realizada en este contexto"""
        self.actions.append({
            "type": action_type,
            "data": action_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.touch()
        
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Verificar si el contexto ha expirado"""
        return (datetime.utcnow() - self.last_accessed).total_seconds() > ttl_seconds
    
    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "action_count": len(self.actions),
            "active_processes": len(self.active_processes)
        }


class CaseContextManager:
    """
    Gestor central de contexto de casos.
    
    Funcionalidades:
    - Mantiene contexto activo por sesión/usuario
    - Valida que las acciones tengan case_id
    - Cache de metadatos de casos
    - Limpieza automática de contextos expirados
    - Tracking de acciones por caso
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._contexts: Dict[str, CaseContext] = {}  # session_id -> CaseContext
        self._case_sessions: Dict[str, List[str]] = {}  # case_id -> [session_ids]
        self._case_cache: Dict[str, Dict] = {}  # case_id -> metadata cache
        self._cache_ttl = 600  # 10 minutos
        self._context_ttl = 3600  # 1 hora
        self._lock = Lock()
        self._initialized = True
        
        logger.info("🔵 CaseContextManager initialized")
    
    def create_context(self, case_id: str, metadata: Optional[Dict] = None) -> CaseContext:
        """Crear nuevo contexto para un caso"""
        ctx = CaseContext(case_id, metadata)
        
        with self._lock:
            self._contexts[ctx.session_id] = ctx
            
            if case_id not in self._case_sessions:
                self._case_sessions[case_id] = []
            self._case_sessions[case_id].append(ctx.session_id)
            
            if metadata:
                self._case_cache[case_id] = {
                    "data": metadata,
                    "cached_at": datetime.utcnow()
                }
        
        logger.info(f"🆕 Created context for case {case_id}, session: {ctx.session_id}")
        return ctx
    
    def get_context(self, session_id: str) -> Optional[CaseContext]:
        """Obtener contexto por session_id"""
        ctx = self._contexts.get(session_id)
        if ctx:
            ctx.touch()
        return ctx
    
    def get_or_create_context(self, session_id: str, case_id: str, metadata: Optional[Dict] = None) -> CaseContext:
        """Obtener contexto existente o crear uno nuevo"""
        ctx = self.get_context(session_id)
        if ctx and ctx.case_id == case_id:
            return ctx
        return self.create_context(case_id, metadata)
    
    def get_case_id(self, session_id: str) -> Optional[str]:
        """Obtener case_id de una sesión"""
        ctx = self.get_context(session_id)
        return ctx.case_id if ctx else None
    
    def require_case_id(self, request: Request) -> str:
        """
        Extraer y validar case_id de una request.
        Lanza HTTPException si no está presente.
        """
        # Intentar obtener de headers
        case_id = request.headers.get("X-Case-ID")
        
        # Intentar obtener de query params
        if not case_id:
            case_id = request.query_params.get("case_id")
        
        # Intentar obtener del body (para POST/PUT)
        # Esto requiere que el body ya haya sido parseado
        if not case_id and hasattr(request.state, 'body_case_id'):
            case_id = request.state.body_case_id
            
        if not case_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "case_id_required",
                    "message": "All forensic operations must be associated with a case. "
                               "Provide case_id via X-Case-ID header, query parameter, or request body."
                }
            )
        
        return case_id
    
    def set_case_metadata(self, case_id: str, metadata: Dict):
        """Cachear metadatos de un caso"""
        with self._lock:
            self._case_cache[case_id] = {
                "data": metadata,
                "cached_at": datetime.utcnow()
            }
    
    def get_case_metadata(self, case_id: str) -> Optional[Dict]:
        """Obtener metadatos cacheados de un caso"""
        cached = self._case_cache.get(case_id)
        if cached:
            age = (datetime.utcnow() - cached["cached_at"]).total_seconds()
            if age < self._cache_ttl:
                return cached["data"]
        return None
    
    def record_action(self, session_id: str, action_type: str, action_data: Dict):
        """Registrar una acción en el contexto"""
        ctx = self.get_context(session_id)
        if ctx:
            ctx.add_action(action_type, action_data)
            logger.debug(f"📝 Recorded action {action_type} in case {ctx.case_id}")
    
    def get_active_sessions(self, case_id: str) -> List[str]:
        """Obtener todas las sesiones activas para un caso"""
        session_ids = self._case_sessions.get(case_id, [])
        return [sid for sid in session_ids if sid in self._contexts and not self._contexts[sid].is_expired()]
    
    def get_all_active_cases(self) -> List[Dict]:
        """Obtener resumen de todos los casos activos"""
        active = []
        for case_id, session_ids in self._case_sessions.items():
            active_sessions = [
                self._contexts[sid].to_dict() 
                for sid in session_ids 
                if sid in self._contexts and not self._contexts[sid].is_expired()
            ]
            if active_sessions:
                active.append({
                    "case_id": case_id,
                    "active_sessions": len(active_sessions),
                    "sessions": active_sessions
                })
        return active
    
    def cleanup_expired(self):
        """Limpiar contextos expirados"""
        with self._lock:
            expired_sessions = [
                sid for sid, ctx in self._contexts.items()
                if ctx.is_expired(self._context_ttl)
            ]
            
            for sid in expired_sessions:
                ctx = self._contexts.pop(sid, None)
                if ctx:
                    # Remover de case_sessions
                    case_sessions = self._case_sessions.get(ctx.case_id, [])
                    if sid in case_sessions:
                        case_sessions.remove(sid)
                        
            if expired_sessions:
                logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired contexts")
    
    def close_context(self, session_id: str):
        """Cerrar un contexto específico"""
        with self._lock:
            ctx = self._contexts.pop(session_id, None)
            if ctx:
                case_sessions = self._case_sessions.get(ctx.case_id, [])
                if session_id in case_sessions:
                    case_sessions.remove(session_id)
                logger.info(f"🔴 Closed context for case {ctx.case_id}, session: {session_id}")


# Singleton instance
case_context_manager = CaseContextManager()


def get_case_context() -> CaseContextManager:
    """Dependency para inyectar el context manager"""
    return case_context_manager
