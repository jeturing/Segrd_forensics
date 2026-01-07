"""
🎭 Auto-Generated Playbooks for Tools
Genera playbooks SOAR automáticamente para cada herramienta
"""

from typing import Dict, List, Any
from api.services.tool_catalog_extended import (
    METASPLOIT_TOOLS,
    M365_TOOLS,
    BLUETEAM_TOOLS
)

def generate_playbook_for_tool(tool_id: str, tool_data: Dict) -> Dict[str, Any]:
    """Genera un playbook automático para una herramienta"""
    
    category = tool_data.get("category", "")
    
    # Template base
    playbook = {
        "id": f"PB-AUTO-{tool_id.upper()}",
        "name": f"Auto: {tool_data['name']}",
        "description": f"Playbook automático para {tool_data['description']}",
        "team_type": get_team_type_for_category(category),
        "category": category,
        "tags": [tool_id, "auto-generated", category],
        "trigger": "manual",
        "requires_approval": tool_data.get("requires_root", False),
        "estimated_duration_minutes": 15,
        "steps": []
    }
    
    # Paso 1: Validar herramienta instalada
    playbook["steps"].append({
        "order": 1,
        "name": "Verificar herramienta instalada",
        "description": f"Validar que {tool_data['name']} esté disponible",
        "action_type": "condition",
        "condition": f"tool_installed:{tool_id}",
        "on_failure": "install_tool"
    })
    
    # Paso 2: Ejecutar herramienta
    execute_step = {
        "order": 2,
        "name": f"Ejecutar {tool_data['name']}",
        "description": tool_data["description"],
        "action_type": "tool_execute",
        "tool_id": tool_id,
        "parameters": {},
        "wait_for_completion": True,
        "timeout_seconds": 300
    }
    
    # Agregar parámetros dinámicos
    for param in tool_data.get("parameters", []):
        if param.get("required"):
            execute_step["parameters"][param["name"]] = f"${{input.{param['name']}}}"
    
    playbook["steps"].append(execute_step)
    
    # Paso 3: Parsear resultados según categoría
    if category in ["m365_forensics", "m365_recon"]:
        playbook["steps"].append({
            "order": 3,
            "name": "Extraer IOCs de M365",
            "description": "Parsear logs y extraer indicadores de compromiso",
            "action_type": "enrich_ioc",
            "source": "tool_output",
            "ioc_types": ["ip", "domain", "email", "user"]
        })
    
    elif category in ["reconnaissance", "network"]:
        playbook["steps"].append({
            "order": 3,
            "name": "Crear nodos en grafo",
            "description": "Agregar hosts/IPs descubiertos al grafo de ataque",
            "action_type": "graph_enrich",
            "node_type": "auto_detect"
        })
    
    elif category == "exploitation":
        playbook["steps"].append({
            "order": 3,
            "name": "Registrar explotación",
            "description": "Documentar intento de explotación",
            "action_type": "update_timeline",
            "event_type": "exploitation_attempt"
        })
    
    # Paso 4: Notificación
    playbook["steps"].append({
        "order": 4,
        "name": "Notificar resultado",
        "description": "Enviar resumen de ejecución",
        "action_type": "notification",
        "channels": ["dashboard", "webhook"],
        "template": "tool_execution_complete"
    })
    
    return playbook


def get_team_type_for_category(category: str) -> str:
    """Determina el tipo de equipo según la categoría"""
    blue_categories = [
        "m365_forensics", "threat_hunting", "log_analysis", 
        "detection_rules", "edr", "forensics"
    ]
    
    red_categories = [
        "exploitation", "password_attacks", "reconnaissance",
        "m365_recon", "web", "wireless"
    ]
    
    if category in blue_categories:
        return "blue"
    elif category in red_categories:
        return "red"
    else:
        return "purple"


def get_all_auto_playbooks() -> List[Dict[str, Any]]:
    """Genera playbooks para todas las herramientas"""
    playbooks = []
    
    all_tools = {
        **METASPLOIT_TOOLS,
        **M365_TOOLS,
        **BLUETEAM_TOOLS
    }
    
    for tool_id, tool_data in all_tools.items():
        playbook = generate_playbook_for_tool(tool_id, tool_data)
        playbooks.append(playbook)
    
    return playbooks


# Playbooks especializados para investigaciones comunes

INVESTIGATION_PLAYBOOKS = {
    "m365_full_investigation": {
        "id": "PB-INV-M365-FULL",
        "name": "Investigación Completa M365",
        "description": "Investigación forense completa de tenant M365/Azure AD",
        "team_type": "purple",
        "category": "investigation",
        "tags": ["m365", "azure", "full-investigation"],
        "trigger": "manual",
        "estimated_duration_minutes": 120,
        "steps": [
            {
                "order": 1,
                "name": "Ejecutar Sparrow",
                "action_type": "tool_execute",
                "tool_id": "sparrow",
                "parameters": {
                    "tenant_id": "${input.tenant_id}",
                    "days_to_search": 90
                }
            },
            {
                "order": 2,
                "name": "Ejecutar Hawk",
                "action_type": "tool_execute",
                "tool_id": "hawk",
                "parameters": {
                    "tenant": "${input.tenant}"
                }
            },
            {
                "order": 3,
                "name": "Ejecutar AzureHound",
                "action_type": "tool_execute",
                "tool_id": "azurehound",
                "parameters": {
                    "tenant": "${input.tenant_id}"
                }
            },
            {
                "order": 4,
                "name": "Correlacionar hallazgos",
                "action_type": "run_correlation",
                "sources": ["sparrow", "hawk", "azurehound"]
            },
            {
                "order": 5,
                "name": "Generar reporte",
                "action_type": "create_report",
                "template": "m365_investigation"
            }
        ]
    },
    
    "metasploit_exploitation": {
        "id": "PB-INV-METASPLOIT",
        "name": "Explotación con Metasploit",
        "description": "Workflow completo de explotación",
        "team_type": "red",
        "category": "exploitation",
        "tags": ["metasploit", "exploitation"],
        "trigger": "manual",
        "estimated_duration_minutes": 60,
        "steps": [
            {
                "order": 1,
                "name": "Escanear target",
                "action_type": "tool_execute",
                "tool_id": "nmap",
                "parameters": {
                    "target": "${input.target}",
                    "scan_type": "-sV -sC"
                }
            },
            {
                "order": 2,
                "name": "Generar payload",
                "action_type": "tool_execute",
                "tool_id": "msfvenom",
                "parameters": {
                    "payload": "${input.payload}",
                    "lhost": "${input.lhost}",
                    "lport": "${input.lport}",
                    "format": "${input.format}"
                }
            },
            {
                "order": 3,
                "name": "Ejecutar exploit",
                "action_type": "tool_execute",
                "tool_id": "msfconsole",
                "parameters": {
                    "resource_file": "${step2.output_file}"
                }
            },
            {
                "order": 4,
                "name": "Post-explotación",
                "action_type": "human_approval",
                "message": "Continuar con post-explotación?"
            }
        ]
    },
    
    "purple_team_validation": {
        "id": "PB-INV-PURPLE-VAL",
        "name": "Validación Purple Team",
        "description": "Validar detección de técnicas MITRE ATT&CK",
        "team_type": "purple",
        "category": "validation",
        "tags": ["purple-team", "mitre", "validation"],
        "trigger": "manual",
        "estimated_duration_minutes": 45,
        "steps": [
            {
                "order": 1,
                "name": "Ejecutar técnica (Red)",
                "action_type": "tool_execute",
                "tool_id": "${input.red_tool}",
                "parameters": "${input.red_params}"
            },
            {
                "order": 2,
                "name": "Esperar propagación",
                "action_type": "wait",
                "seconds": 30
            },
            {
                "order": 3,
                "name": "Buscar detección (Blue)",
                "action_type": "tool_execute",
                "tool_id": "chainsaw",
                "parameters": {
                    "evtx_path": "${input.log_path}",
                    "rules": "sigma"
                }
            },
            {
                "order": 4,
                "name": "Validar detección",
                "action_type": "condition",
                "condition": "detection_found",
                "on_success": "create_ioc",
                "on_failure": "create_alert"
            }
        ]
    }
}


def get_investigation_playbooks() -> List[Dict[str, Any]]:
    """Retorna playbooks de investigación especializados"""
    return list(INVESTIGATION_PLAYBOOKS.values())
