"""
Module Registry Routes
======================
Endpoints para gestionar el registry de módulos
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
import os

# Agregar path para importar core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.module_registry import (
    module_registry,
    get_registry_info,
    generate_module_code
)

router = APIRouter(prefix="/modules", tags=["Module Registry"])


@router.get("/")
async def get_modules_info():
    """
    Obtener información del registry de módulos
    
    Retorna lista de todos los módulos registrados con su estado
    """
    return get_registry_info()


@router.get("/list")
async def list_modules(
    category: Optional[str] = None,
    status: Optional[str] = Query(None, pattern="^(active|inactive|development)$")
):
    """
    Listar módulos con filtros opcionales
    """
    module_registry.load()
    
    modules = module_registry.get_all_modules(category=category)
    
    if status:
        modules = [m for m in modules if m.get("status") == status]
    
    return {
        "count": len(modules),
        "filters": {"category": category, "status": status},
        "modules": modules
    }


@router.get("/{module_id}")
async def get_module(module_id: str):
    """
    Obtener detalles de un módulo específico
    """
    module_registry.load()
    
    module = module_registry.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail=f"Módulo no encontrado: {module_id}")
    
    # Agregar validación
    validation = module_registry.validate_module(module)
    
    return {
        **module,
        "validation": validation
    }


@router.get("/{module_id}/endpoints")
async def get_module_endpoints(module_id: str):
    """
    Obtener endpoints de un módulo
    """
    module_registry.load()
    
    endpoints = module_registry.get_endpoints(module_id)
    if not endpoints:
        raise HTTPException(status_code=404, detail=f"Módulo no encontrado: {module_id}")
    
    return {
        "module_id": module_id,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints
    }


@router.get("/all/endpoints")
async def get_all_endpoints():
    """
    Listar todos los endpoints del sistema
    """
    module_registry.load()
    
    endpoints = module_registry.get_all_endpoints()
    
    return {
        "total_endpoints": len(endpoints),
        "by_module": {},
        "endpoints": endpoints
    }


@router.get("/validate/all")
async def validate_all_modules():
    """
    Validar todos los módulos registrados
    """
    module_registry.load()
    
    return module_registry.validate_all()


@router.post("/{module_id}/generate")
async def generate_module(
    module_id: str,
    save: bool = Query(False, description="Guardar archivos generados")
):
    """
    Generar código para un módulo
    
    Genera:
    - Rutas FastAPI
    - Servicio Python
    - Página React
    
    Si save=True, guarda los archivos en las carpetas correspondientes
    """
    module_registry.load()
    
    module = module_registry.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail=f"Módulo no encontrado: {module_id}")
    
    try:
        results = generate_module_code(module_id, save=save)
        
        return {
            "module_id": module_id,
            "generated": True,
            "saved": save,
            "results": {
                code_type: {
                    "lines": r.get("lines", 0),
                    "path": r.get("path"),
                    "error": r.get("error")
                }
                for code_type, r in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando código: {str(e)}")


@router.get("/categories")
async def get_categories():
    """
    Listar categorías de módulos
    """
    module_registry.load()
    
    return {
        "categories": module_registry.categories
    }


@router.get("/dependencies/{module_id}")
async def get_dependencies(module_id: str):
    """
    Obtener árbol de dependencias de un módulo
    """
    module_registry.load()
    
    deps = module_registry.get_dependencies(module_id)
    
    # Resolver dependencias transitivas
    all_deps = set(deps)
    for dep in deps:
        sub_deps = module_registry.get_dependencies(dep)
        all_deps.update(sub_deps)
    
    return {
        "module_id": module_id,
        "direct_dependencies": deps,
        "all_dependencies": list(all_deps)
    }
