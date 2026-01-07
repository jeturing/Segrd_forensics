"""
Demo Data Configuration - MCP v4.1
Datos de demostración para cuando no hay datos reales en la DB.
Estos datos se usan SOLO cuando la base de datos está vacía.
Cada respuesta que use demo data incluirá: "data_source": "demo"
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any

# =============================================================================
# DEMO AGENTS - Para mostrar funcionalidad sin agentes reales
# =============================================================================

DEMO_AGENTS: List[Dict[str, Any]] = [
    {
        "id": "demo-agent-blue-001",
        "name": "Demo Blue Agent (Workstation)",
        "agent_type": "blue",
        "status": "online",
        "hostname": "DEMO-WORKSTATION-01",
        "ip_address": "192.168.1.100",
        "platform": "windows",
        "os_version": "Windows 11 Pro",
        "agent_version": "4.1.0-demo",
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": [
            "osquery", "yara_scan", "loki_scan", 
            "process_list", "network_connections", "file_collection"
        ],
        "is_demo": True
    },
    {
        "id": "demo-agent-red-001",
        "name": "Demo Red Agent (Kali)",
        "agent_type": "red",
        "status": "online",
        "hostname": "DEMO-KALI-01",
        "ip_address": "192.168.1.50",
        "platform": "linux",
        "os_version": "Kali Linux 2024.1",
        "agent_version": "4.1.0-demo",
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": [
            "nmap", "whatweb", "gobuster", "nikto",
            "amass", "nuclei", "passive_recon"
        ],
        "is_demo": True
    },
    {
        "id": "demo-agent-purple-001",
        "name": "Demo Purple Agent (Coordinator)",
        "agent_type": "purple",
        "status": "online",
        "hostname": "DEMO-COORDINATOR-01",
        "ip_address": "192.168.1.10",
        "platform": "linux",
        "os_version": "Ubuntu 22.04 LTS",
        "agent_version": "4.1.0-demo",
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": [
            "validation", "correlation", "tuning",
            "exposure_analysis", "sync_cycle"
        ],
        "is_demo": True
    }
]

# =============================================================================
# DEMO INVESTIGATIONS - Para mostrar el flujo de trabajo
# =============================================================================

DEMO_INVESTIGATIONS: List[Dict[str, Any]] = [
    {
        "id": "DEMO-IR-001",
        "name": "Demo: Email Compromise Investigation",
        "description": "Demostración de investigación de compromiso de cuenta de correo",
        "severity": "high",
        "status": "in-progress",
        "priority": "P1",
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "assigned_to": "Demo Analyst",
        "case_type": "m365_compromise",
        "iocs_count": 5,
        "evidence_count": 3,
        "is_demo": True
    },
    {
        "id": "DEMO-IR-002",
        "name": "Demo: Malware Detection",
        "description": "Demostración de detección y análisis de malware",
        "severity": "critical",
        "status": "open",
        "priority": "P0",
        "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "assigned_to": "Demo Analyst",
        "case_type": "endpoint_threat",
        "iocs_count": 8,
        "evidence_count": 5,
        "is_demo": True
    }
]

# =============================================================================
# DEMO IOCs - Indicadores de compromiso de ejemplo
# =============================================================================

DEMO_IOCS: Dict[str, List[Dict[str, Any]]] = {
    "DEMO-IR-001": [
        {
            "id": "demo-ioc-001",
            "type": "ip",
            "value": "203.0.113.45",
            "severity": "high",
            "source": "Demo - Sign-in logs",
            "description": "IP sospechosa de login",
            "is_demo": True
        },
        {
            "id": "demo-ioc-002",
            "type": "email",
            "value": "attacker@demo-malicious.com",
            "severity": "critical",
            "source": "Demo - Email headers",
            "description": "Cuenta de destino de reenvío",
            "is_demo": True
        },
        {
            "id": "demo-ioc-003",
            "type": "domain",
            "value": "demo-malicious.com",
            "severity": "high",
            "source": "Demo - URL analysis",
            "description": "Dominio malicioso",
            "is_demo": True
        }
    ],
    "DEMO-IR-002": [
        {
            "id": "demo-ioc-004",
            "type": "hash_sha256",
            "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "severity": "critical",
            "source": "Demo - YARA scan",
            "description": "Hash de archivo malicioso",
            "is_demo": True
        },
        {
            "id": "demo-ioc-005",
            "type": "file_path",
            "value": "C:\\Users\\Demo\\Downloads\\malware.exe",
            "severity": "critical",
            "source": "Demo - Loki scan",
            "description": "Ruta del archivo malicioso",
            "is_demo": True
        }
    ]
}

# =============================================================================
# DEMO TIMELINE - Eventos de ejemplo
# =============================================================================

DEMO_TIMELINE: Dict[str, List[Dict[str, Any]]] = {
    "DEMO-IR-001": [
        {
            "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "event_type": "investigation_created",
            "description": "Investigación de demo creada",
            "severity": "info",
            "source": "Demo System"
        },
        {
            "timestamp": (datetime.utcnow() - timedelta(days=1, hours=22)).isoformat(),
            "event_type": "suspicious_sign_in",
            "description": "Sign-in desde ubicación inusual detectado",
            "severity": "high",
            "source": "Demo - Azure AD"
        },
        {
            "timestamp": (datetime.utcnow() - timedelta(days=1, hours=20)).isoformat(),
            "event_type": "oauth_grant",
            "description": "App OAuth sospechosa autorizada",
            "severity": "high",
            "source": "Demo - Sparrow"
        },
        {
            "timestamp": (datetime.utcnow() - timedelta(days=1, hours=18)).isoformat(),
            "event_type": "email_rule_created",
            "description": "Regla de reenvío de email creada",
            "severity": "critical",
            "source": "Demo - Hawk"
        }
    ]
}

# =============================================================================
# DEMO ATTACK GRAPH - Nodos y aristas de ejemplo
# =============================================================================

DEMO_GRAPH: Dict[str, Dict[str, Any]] = {
    "DEMO-IR-001": {
        "nodes": [
            {"data": {"id": "user1", "label": "demo.user@example.com", "type": "user"}},
            {"data": {"id": "mailbox1", "label": "Mailbox Comprometido", "type": "mailbox"}},
            {"data": {"id": "ip1", "label": "203.0.113.45", "type": "ip"}},
            {"data": {"id": "app1", "label": "OAuth App Maliciosa", "type": "application"}},
            {"data": {"id": "external1", "label": "attacker@demo-malicious.com", "type": "email"}}
        ],
        "edges": [
            {"data": {"source": "ip1", "target": "user1", "label": "signed_in_from"}},
            {"data": {"source": "user1", "target": "app1", "label": "authorized"}},
            {"data": {"source": "mailbox1", "target": "external1", "label": "forwards_to"}},
            {"data": {"source": "user1", "target": "mailbox1", "label": "owns"}}
        ]
    }
}

# =============================================================================
# DEMO PLAYBOOKS - Playbooks de ejemplo
# =============================================================================

DEMO_PLAYBOOKS: List[Dict[str, Any]] = [
    {
        "id": "DEMO-PB-BLUE-001",
        "name": "Demo: Respuesta a Usuario Comprometido",
        "team_type": "blue",
        "category": "incident_response",
        "status": "active",
        "estimated_duration_minutes": 30,
        "steps_count": 6,
        "is_demo": True
    },
    {
        "id": "DEMO-PB-RED-001",
        "name": "Demo: Passive Recon",
        "team_type": "red",
        "category": "reconnaissance",
        "status": "active",
        "estimated_duration_minutes": 15,
        "steps_count": 8,
        "is_demo": True
    },
    {
        "id": "DEMO-PB-PURPLE-001",
        "name": "Demo: Red/Blue Sync Cycle",
        "team_type": "purple",
        "category": "coordination",
        "status": "active",
        "estimated_duration_minutes": 15,
        "steps_count": 9,
        "is_demo": True
    }
]

# =============================================================================
# DEMO TOOL EXECUTIONS - Ejecuciones de ejemplo
# =============================================================================

DEMO_TOOL_EXECUTIONS: List[Dict[str, Any]] = [
    {
        "id": "DEMO-EXE-001",
        "tool": "nmap",
        "category": "recon",
        "status": "completed",
        "execution_target": "mcp_local",
        "started_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "finished_at": (datetime.utcnow() - timedelta(minutes=55)).isoformat(),
        "exit_code": 0,
        "output_preview": "Nmap scan report for demo.target.com...",
        "is_demo": True
    },
    {
        "id": "DEMO-EXE-002",
        "tool": "yara",
        "category": "malware",
        "status": "completed",
        "execution_target": "agent_remote",
        "agent_id": "demo-agent-blue-001",
        "started_at": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
        "finished_at": (datetime.utcnow() - timedelta(minutes=25)).isoformat(),
        "exit_code": 0,
        "output_preview": "Rule matched: Demo_Malware_Signature",
        "is_demo": True
    }
]

# =============================================================================
# COMMAND TEMPLATES - Estos NO son mock, son templates útiles
# =============================================================================

COMMAND_TEMPLATES = {
    "windows": [
        {
            "category": "Procesos",
            "commands": [
                {"id": "w-proc-1", "label": "Listar procesos", "cmd": "tasklist /v", "icon": "📋"},
                {"id": "w-proc-2", "label": "Procesos por CPU", "cmd": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20", "icon": "⚙️"},
                {"id": "w-proc-3", "label": "Conexiones de red", "cmd": "Get-NetTCPConnection | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess", "icon": "🌐"}
            ]
        },
        {
            "category": "Red",
            "commands": [
                {"id": "w-net-1", "label": "Conexiones activas", "cmd": "netstat -ano", "icon": "🌐"},
                {"id": "w-net-2", "label": "Puertos escuchando", "cmd": "netstat -an | findstr LISTENING", "icon": "🔌"},
                {"id": "w-net-3", "label": "ARP cache", "cmd": "arp -a", "icon": "📡"}
            ]
        },
        {
            "category": "Sistema",
            "commands": [
                {"id": "w-sys-1", "label": "Usuarios locales", "cmd": "net user", "icon": "👤"},
                {"id": "w-sys-2", "label": "Servicios", "cmd": "Get-Service | Where-Object {$_.Status -eq 'Running'}", "icon": "⚙️"},
                {"id": "w-sys-3", "label": "Tareas programadas", "cmd": "schtasks /query /fo LIST /v", "icon": "⏰"}
            ]
        }
    ],
    "linux": [
        {
            "category": "Procesos",
            "commands": [
                {"id": "l-proc-1", "label": "Procesos", "cmd": "ps aux", "icon": "📋"},
                {"id": "l-proc-2", "label": "Árbol de procesos", "cmd": "pstree -p", "icon": "🌲"},
                {"id": "l-proc-3", "label": "Top por CPU", "cmd": "ps aux --sort=-%cpu | head -20", "icon": "⚙️"}
            ]
        },
        {
            "category": "Red",
            "commands": [
                {"id": "l-net-1", "label": "Sockets activos", "cmd": "ss -tulpn", "icon": "🌐"},
                {"id": "l-net-2", "label": "Conexiones establecidas", "cmd": "ss -t state established", "icon": "🔗"},
                {"id": "l-net-3", "label": "Reglas iptables", "cmd": "iptables -L -n -v", "icon": "🔒"}
            ]
        },
        {
            "category": "Sistema",
            "commands": [
                {"id": "l-sys-1", "label": "Usuarios", "cmd": "cat /etc/passwd", "icon": "👤"},
                {"id": "l-sys-2", "label": "Cron jobs", "cmd": "crontab -l", "icon": "⏰"},
                {"id": "l-sys-3", "label": "Servicios systemd", "cmd": "systemctl list-units --type=service --state=running", "icon": "⚙️"}
            ]
        }
    ],
    "macos": [
        {
            "category": "Procesos",
            "commands": [
                {"id": "m-proc-1", "label": "Procesos activos", "cmd": "ps aux", "icon": "📋"},
                {"id": "m-proc-2", "label": "Top por CPU", "cmd": "ps aux -r | head -20", "icon": "⚙️"}
            ]
        },
        {
            "category": "Red",
            "commands": [
                {"id": "m-net-1", "label": "Conexiones", "cmd": "lsof -i", "icon": "🌐"},
                {"id": "m-net-2", "label": "Puertos escuchando", "cmd": "netstat -an | grep LISTEN", "icon": "🔌"}
            ]
        }
    ]
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_demo_agents() -> List[Dict[str, Any]]:
    """Retorna agentes de demo con timestamps actualizados"""
    agents = DEMO_AGENTS.copy()
    for agent in agents:
        agent["last_seen"] = datetime.utcnow().isoformat()
    return agents


def get_demo_investigations() -> List[Dict[str, Any]]:
    """Retorna investigaciones de demo"""
    return DEMO_INVESTIGATIONS.copy()


def get_demo_iocs(case_id: str) -> List[Dict[str, Any]]:
    """Retorna IOCs de demo para un caso"""
    return DEMO_IOCS.get(case_id, [])


def get_demo_timeline(case_id: str) -> List[Dict[str, Any]]:
    """Retorna timeline de demo para un caso"""
    return DEMO_TIMELINE.get(case_id, [])


def get_demo_graph(case_id: str) -> Dict[str, Any]:
    """Retorna grafo de demo para un caso"""
    return DEMO_GRAPH.get(case_id, {"nodes": [], "edges": []})


def get_demo_playbooks() -> List[Dict[str, Any]]:
    """Retorna playbooks de demo"""
    return DEMO_PLAYBOOKS.copy()


def get_command_templates(os_type: str = "linux") -> List[Dict[str, Any]]:
    """Retorna templates de comandos (no son mock, son útiles)"""
    return COMMAND_TEMPLATES.get(os_type, COMMAND_TEMPLATES["linux"])


def is_demo_data(data: Dict[str, Any]) -> bool:
    """Verifica si los datos son de demo"""
    return data.get("is_demo", False)


def mark_as_demo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Marca datos como demo y agrega indicador"""
    data["is_demo"] = True
    data["data_source"] = "demo"
    return data
