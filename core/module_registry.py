"""
Module Registry - Auto-generación de módulos
============================================
Sistema para gestionar y auto-generar módulos del sistema
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Directorio base
BASE_DIR = Path(__file__).parent.parent
MODULES_FILE = BASE_DIR / "modules.json"


class ModuleRegistry:
    """
    Registry central de módulos del sistema
    
    Features:
    - Carga módulos desde modules.json
    - Valida estructura de módulos
    - Genera código CRUD automático
    - Genera componentes frontend
    - Genera documentación
    """
    
    def __init__(self):
        self.modules: Dict[str, Dict] = {}
        self.categories: Dict[str, Dict] = {}
        self.config: Dict = {}
        self._loaded = False
        
    def load(self) -> bool:
        """Carga módulos desde modules.json"""
        try:
            if not MODULES_FILE.exists():
                logger.warning(f"⚠️ modules.json no encontrado en {MODULES_FILE}")
                return False
            
            with open(MODULES_FILE, 'r') as f:
                data = json.load(f)
            
            self.config = data
            self.categories = data.get("categories", {})
            
            for module in data.get("modules", []):
                self.modules[module["id"]] = module
            
            self._loaded = True
            logger.info(f"📦 Registry cargado: {len(self.modules)} módulos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando registry: {e}")
            return False
    
    def get_module(self, module_id: str) -> Optional[Dict]:
        """Obtiene un módulo por ID"""
        if not self._loaded:
            self.load()
        return self.modules.get(module_id)
    
    def get_all_modules(self, category: Optional[str] = None) -> List[Dict]:
        """Lista todos los módulos, opcionalmente filtrados por categoría"""
        if not self._loaded:
            self.load()
        
        modules = list(self.modules.values())
        
        if category:
            modules = [m for m in modules if m.get("category") == category]
        
        return modules
    
    def get_active_modules(self) -> List[Dict]:
        """Lista módulos activos"""
        return [m for m in self.get_all_modules() if m.get("status") == "active"]
    
    def get_endpoints(self, module_id: str) -> List[Dict]:
        """Obtiene endpoints de un módulo"""
        module = self.get_module(module_id)
        if not module:
            return []
        return module.get("api_endpoints", [])
    
    def get_all_endpoints(self) -> List[Dict]:
        """Lista todos los endpoints del sistema"""
        endpoints = []
        for module in self.get_all_modules():
            prefix = module.get("routes", {}).get("prefix", "")
            for ep in module.get("api_endpoints", []):
                endpoints.append({
                    "module": module["id"],
                    "method": ep["method"],
                    "path": prefix + ep["path"],
                    "description": ep.get("description", ""),
                    "auth_required": module.get("routes", {}).get("auth_required", True)
                })
        return endpoints
    
    def get_dependencies(self, module_id: str) -> List[str]:
        """Obtiene dependencias de un módulo"""
        module = self.get_module(module_id)
        if not module:
            return []
        return module.get("dependencies", [])
    
    def validate_module(self, module_data: Dict) -> Dict:
        """Valida estructura de un módulo"""
        errors = []
        warnings = []
        
        # Campos requeridos
        required = ["id", "name", "status", "category"]
        for field in required:
            if field not in module_data:
                errors.append(f"Campo requerido faltante: {field}")
        
        # Verificar archivos existen
        if "routes" in module_data and module_data["routes"]:
            route_file = BASE_DIR / module_data["routes"]["file"]
            if not route_file.exists():
                warnings.append(f"Archivo de rutas no existe: {route_file}")
        
        if "service" in module_data and module_data["service"]:
            service_file = BASE_DIR / module_data["service"]["file"]
            if not service_file.exists():
                warnings.append(f"Archivo de servicio no existe: {service_file}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def validate_all(self) -> Dict:
        """Valida todos los módulos"""
        results = {}
        for module_id, module in self.modules.items():
            results[module_id] = self.validate_module(module)
        
        valid_count = sum(1 for r in results.values() if r["valid"])
        
        return {
            "total": len(results),
            "valid": valid_count,
            "invalid": len(results) - valid_count,
            "results": results
        }


class ModuleGenerator:
    """
    Generador automático de código para módulos
    """
    
    def __init__(self, registry: ModuleRegistry):
        self.registry = registry
        self.templates_dir = BASE_DIR / "core" / "templates"
        
    def generate_route(self, module_id: str) -> str:
        """Genera código de rutas FastAPI para un módulo"""
        module = self.registry.get_module(module_id)
        if not module:
            raise ValueError(f"Módulo no encontrado: {module_id}")
        
        endpoints = module.get("api_endpoints", [])
        prefix = module.get("routes", {}).get("prefix", f"/{module_id}")
        
        # Template básico
        code = f'''"""
{module['name']} Routes
{'='*len(module['name'] + ' Routes')}
Auto-generated from modules.json
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(tags=["{module['name']}"])


# ==================== REQUEST/RESPONSE MODELS ====================

class {module_id.title()}CreateRequest(BaseModel):
    name: str
    # TODO: Add fields


class {module_id.title()}UpdateRequest(BaseModel):
    name: Optional[str] = None
    # TODO: Add fields


# ==================== ENDPOINTS ====================

'''
        
        for ep in endpoints:
            method = ep["method"].lower()
            path = ep["path"]
            description = ep.get("description", "")
            
            if method == "get":
                code += f'''
@router.get("{path}")
async def get_{module_id}_{path.replace("/", "_").replace("{{", "").replace("}}", "").strip("_")}():
    """{description}"""
    # TODO: Implement
    return {{"status": "ok"}}

'''
            elif method == "post":
                code += f'''
@router.post("{path}")
async def create_{module_id}_{path.replace("/", "_").replace("{{", "").replace("}}", "").strip("_")}():
    """{description}"""
    # TODO: Implement
    return {{"created": True}}

'''
            elif method == "put":
                code += f'''
@router.put("{path}")
async def update_{module_id}_{path.replace("/", "_").replace("{{", "").replace("}}", "").strip("_")}():
    """{description}"""
    # TODO: Implement
    return {{"updated": True}}

'''
            elif method == "delete":
                code += f'''
@router.delete("{path}")
async def delete_{module_id}_{path.replace("/", "_").replace("{{", "").replace("}}", "").strip("_")}():
    """{description}"""
    # TODO: Implement
    return {{"deleted": True}}

'''
        
        return code
    
    def generate_service(self, module_id: str) -> str:
        """Genera código de servicio para un módulo"""
        module = self.registry.get_module(module_id)
        if not module:
            raise ValueError(f"Módulo no encontrado: {module_id}")
        
        class_name = "".join(word.title() for word in module_id.split("_")) + "Service"
        singleton_name = f"{module_id}_service"
        
        code = f'''"""
{module['name']} Service
{'='*len(module['name'] + ' Service')}
Auto-generated from modules.json
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class {class_name}:
    """
    {module.get('description', 'Service for ' + module['name'])}
    
    Features:
    {chr(10).join('    - ' + f for f in module.get('features', []))}
    """
    
    def __init__(self):
        self.data: Dict[str, Any] = {{}}
        logger.info("📦 {class_name} inicializado")
    
    async def create(self, **kwargs) -> Dict:
        """Crear nuevo registro"""
        item_id = f"{{module_id}}_{{datetime.utcnow().strftime('%Y%m%d%H%M%S')}}"
        self.data[item_id] = {{
            "id": item_id,
            "created_at": datetime.utcnow().isoformat(),
            **kwargs
        }}
        return self.data[item_id]
    
    async def get(self, item_id: str) -> Optional[Dict]:
        """Obtener registro por ID"""
        return self.data.get(item_id)
    
    async def list(self, limit: int = 100) -> List[Dict]:
        """Listar registros"""
        return list(self.data.values())[:limit]
    
    async def update(self, item_id: str, **kwargs) -> Optional[Dict]:
        """Actualizar registro"""
        if item_id not in self.data:
            return None
        self.data[item_id].update(kwargs)
        self.data[item_id]["updated_at"] = datetime.utcnow().isoformat()
        return self.data[item_id]
    
    async def delete(self, item_id: str) -> bool:
        """Eliminar registro"""
        if item_id in self.data:
            del self.data[item_id]
            return True
        return False


# Singleton
{singleton_name} = {class_name}()
'''
        
        return code
    
    def generate_frontend_page(self, module_id: str) -> str:
        """Genera código de página React para un módulo"""
        module = self.registry.get_module(module_id)
        if not module:
            raise ValueError(f"Módulo no encontrado: {module_id}")
        
        component_name = "".join(word.title() for word in module_id.split("_")) + "Page"
        prefix = module.get("routes", {}).get("prefix", f"/{module_id}")
        
        code = f'''/**
 * {module['name']} Page
 * Auto-generated from modules.json
 */

import React, {{ useState, useEffect }} from 'react';
import {{ {module.get('icon', 'Box')} }} from 'lucide-react';
import api from '../services/api';

const {component_name} = () => {{
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {{
    fetchData();
  }}, []);

  const fetchData = async () => {{
    try {{
      setLoading(true);
      const response = await api.get('{prefix}/');
      setData(response.data);
    }} catch (err) {{
      setError(err.message);
    }} finally {{
      setLoading(false);
    }}
  }};

  if (loading) {{
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }}

  if (error) {{
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Error: {{error}}</p>
      </div>
    );
  }}

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <{module.get('icon', 'Box')} className="w-8 h-8" style={{{{ color: '{module.get('color', '#3B82F6')}' }}}} />
        <h1 className="text-2xl font-bold">{module['name']}</h1>
      </div>
      
      <p className="text-gray-600 mb-6">{module.get('description', '')}</p>
      
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Data</h2>
        <pre className="bg-gray-100 p-4 rounded overflow-auto">
          {{JSON.stringify(data, null, 2)}}
        </pre>
      </div>
    </div>
  );
}};

export default {component_name};
'''
        
        return code
    
    def save_generated_code(self, module_id: str, code_type: str, code: str) -> str:
        """Guarda código generado en archivo"""
        module = self.registry.get_module(module_id)
        if not module:
            raise ValueError(f"Módulo no encontrado: {module_id}")
        
        if code_type == "route":
            output_dir = BASE_DIR / "api" / "routes" / "generated"
            filename = f"{module_id}_generated.py"
        elif code_type == "service":
            output_dir = BASE_DIR / "api" / "services" / "generated"
            filename = f"{module_id}_service_generated.py"
        elif code_type == "frontend":
            output_dir = BASE_DIR / "frontend-react" / "src" / "modules" / module_id.title()
            filename = f"{module_id.title()}Page.jsx"
        else:
            raise ValueError(f"Tipo de código no soportado: {code_type}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(code)
        
        logger.info(f"💾 Código guardado: {output_path}")
        return str(output_path)


# Instancias globales
module_registry = ModuleRegistry()
module_generator = ModuleGenerator(module_registry)


# ==================== API ENDPOINTS ====================

def get_registry_info() -> Dict:
    """Obtiene información del registry"""
    module_registry.load()
    return {
        "version": module_registry.config.get("version", "unknown"),
        "modules_count": len(module_registry.modules),
        "categories": list(module_registry.categories.keys()),
        "modules": [
            {
                "id": m["id"],
                "name": m["name"],
                "status": m["status"],
                "category": m["category"]
            }
            for m in module_registry.get_all_modules()
        ]
    }


def generate_module_code(module_id: str, save: bool = False) -> Dict:
    """Genera todo el código para un módulo"""
    module_registry.load()
    
    results = {}
    
    try:
        route_code = module_generator.generate_route(module_id)
        results["route"] = {
            "code": route_code,
            "lines": len(route_code.split("\n"))
        }
        if save:
            results["route"]["path"] = module_generator.save_generated_code(
                module_id, "route", route_code
            )
    except Exception as e:
        results["route"] = {"error": str(e)}
    
    try:
        service_code = module_generator.generate_service(module_id)
        results["service"] = {
            "code": service_code,
            "lines": len(service_code.split("\n"))
        }
        if save:
            results["service"]["path"] = module_generator.save_generated_code(
                module_id, "service", service_code
            )
    except Exception as e:
        results["service"] = {"error": str(e)}
    
    try:
        frontend_code = module_generator.generate_frontend_page(module_id)
        results["frontend"] = {
            "code": frontend_code,
            "lines": len(frontend_code.split("\n"))
        }
        if save:
            results["frontend"]["path"] = module_generator.save_generated_code(
                module_id, "frontend", frontend_code
            )
    except Exception as e:
        results["frontend"] = {"error": str(e)}
    
    return results
