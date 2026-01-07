# 📱 MOBILE AGENT: HERRAMIENTAS DISPONIBLES SIN DESARROLLO CUSTOM

**Fecha**: 2025-12-05  
**Objetivo**: Evaluar herramientas existentes para recolección en endpoints  
**Alcance**: Windows, Mac, iOS, Android  

---

## 📊 MATRIZ DE HERRAMIENTAS

| Herramienta | Windows | Mac | Linux | iOS | Android | Costo | Facilidad | Ranking |
|---|---|---|---|---|---|---|---|---|
| **Microsoft Intune** | ✅ | ✅ | ✅ | ✅ | ✅ | Incluido M365 | ⭐⭐⭐⭐ | 🥇 #1 |
| **OSQuery** | ✅ | ✅ | ✅ | ✗ | ✗ | Gratis | ⭐⭐⭐ | 🥇 #2 |
| **Velociraptor** | ✅ | ✅ | ✅ | ✗ | ✗ | Gratis | ⭐⭐⭐ | 🥇 #3 |
| **Kolide Fleet** | ✅ | ✅ | ✅ | ✗ | ✗ | Gratis/$$ | ⭐⭐⭐ | 🥈 #4 |
| **MobileIron** | ✅ | ✅ | ✗ | ✅ | ✅ | $$$$ | ⭐⭐⭐⭐ | 🥈 #5 |
| **Jamf Pro** | ✗ | ✅ | ✗ | ✅ | ✗ | $$$$ | ⭐⭐⭐⭐ | 🥈 #6 |
| **CrowdStrike Falcon** | ✅ | ✅ | ✅ | ✗ | ✗ | $$$$ | ⭐⭐⭐⭐ | 🥇 #7 |
| **SentinelOne** | ✅ | ✅ | ✅ | ✗ | ✗ | $$$ | ⭐⭐⭐⭐ | 🥇 #8 |

---

## 🥇 OPCIÓN #1: MICROSOFT INTUNE (RECOMENDADO)

### ✅ Ventajas

```
✓ Nativo en ecosistema M365
✓ Zero cost (incluido en Intune license)
✓ Control remoto completo
✓ MDM/MAM integrado
✓ Soporte multiplataforma
✓ Scripts PowerShell/Bash
✓ Seguridad enterprise
✓ Compliance automation
```

### ❌ Desventajas

```
✗ Requiere M365 subscription
✗ Curva de aprendizaje
✗ Requiere infraestructura Azure AD
```

### 💻 Capacidades

| Capacidad | Windows | Mac | iOS | Android |
|---|---|---|---|---|
| Inventario de dispositivos | ✅ | ✅ | ✅ | ✅ |
| Ejecutar PowerShell scripts | ✅ | ✗ | ✗ | ✗ |
| Ejecutar Shell scripts | ✗ | ✅ | ✗ | ✗ |
| Recolectar logs | ✅ | ✅ | ✅ | ✅ |
| Wipe remoto | ✅ | ✅ | ✅ | ✅ |
| Lock remoto | ✅ | ✅ | ✅ | ✅ |
| Recolectar archivos | ✅ | ✅ | ⚠️ Limitado | ⚠️ Limitado |

### 🔗 Integración Backend

```python
# api/services/intune_agent.py

from azure.identity import DefaultAzureCredential
from msgraph.core import GraphClient
import asyncio

class IntuneRemoteAgent:
    """
    Integración con Microsoft Intune para endpoints
    """
    
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.client = GraphClient(credential=self.credential)
    
    async def get_managed_devices(self) -> List[Dict]:
        """
        Obtiene lista de dispositivos administrados en Intune
        
        GET /deviceManagement/managedDevices
        """
        response = await self.client.get(
            '/deviceManagement/managedDevices'
        )
        return response['value']
    
    async def run_remote_script(
        self, 
        device_id: str, 
        script_content: str,
        script_type: str = 'powershell'  # powershell | bash
    ) -> Dict:
        """
        Ejecuta script remoto en dispositivo
        
        POST /deviceManagement/deviceConfigurations/{configId}/assignments
        """
        
        if script_type == 'powershell':
            return await self._run_powershell_script(device_id, script_content)
        elif script_type == 'bash':
            return await self._run_bash_script(device_id, script_content)
    
    async def collect_device_logs(
        self, 
        device_id: str,
        case_id: str
    ) -> Dict:
        """
        Recolecta logs del dispositivo
        """
        # Puede ejecutar script que recolecta:
        # - Windows: Event Logs, Sysmon, PowerShell history
        # - Mac: System logs, unified logs, shell history
        # - iOS: App logs, network logs
        
        script = """
        # Windows
        Get-EventLog -LogName Application -Newest 1000 | Export-Csv
        Get-Process | Export-Csv
        netstat -an
        
        # Mac
        log collect
        system_profiler
        """
        
        return await self.run_remote_script(device_id, script)
    
    async def collect_forensic_artifacts(
        self, 
        device_id: str,
        case_id: str,
        artifacts: List[str]  # 'registry', 'mft', 'memory', 'network'
    ) -> Dict:
        """
        Recolecta artefactos forenses
        
        artifacts = [
            'registry_hive',  # Windows: SAM, SYSTEM, SOFTWARE
            'mft',            # Windows: Master File Table
            'memory',         # Minidump o full dump
            'network_logs',   # Firewall, proxy, DNS
            'event_logs',     # Security, System, Application
            'bash_history',   # Mac/Linux: ~/.bash_history
            'auth_log'        # Mac/Linux: /var/log/auth.log
        ]
        """
        
        results = {}
        
        for artifact in artifacts:
            if artifact == 'registry_hive':
                results['registry'] = await self._dump_registry(device_id)
            elif artifact == 'memory':
                results['memory'] = await self._dump_memory(device_id)
            elif artifact == 'network_logs':
                results['network'] = await self._collect_network_logs(device_id)
        
        return results

# Ejemplo de uso en routes
@router.post("/forensics/mobile-agent/intune/run-script")
async def run_intune_script(request: IntuneScriptRequest):
    """
    POST /forensics/mobile-agent/intune/run-script
    {
      "device_id": "12345-67890",
      "script": "Get-Process | Export-Csv",
      "case_id": "IR-2025-001"
    }
    """
    agent = IntuneRemoteAgent()
    result = await agent.run_remote_script(
        request.device_id, 
        request.script,
        'powershell'
    )
    return result
```

### 📋 Scripts PowerShell Predefinidos

```powershell
# 1. Recolectar procesos activos
Get-Process | Select ProcessName, Id, Memory, CPU | Export-Csv processes.csv

# 2. Listar conexiones de red
Get-NetTCPConnection | Where-Object {$_.State -eq "Established"} | Export-Csv connections.csv

# 3. Event logs de seguridad
Get-EventLog -LogName Security -Newest 1000 | Export-Csv security_events.csv

# 4. Ejecutable recientes
Get-ChildItem C:\Users\*\AppData\Roaming\Microsoft\Windows\Recent -Recurse

# 5. Prefetch files (ejecución histórica)
Get-ChildItem C:\Windows\Prefetch

# 6. Registry de ejecución (Run key)
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Run

# 7. Scheduled Tasks
Get-ScheduledTask | Where-Object {$_.State -eq "Running"}

# 8. Installed Software
Get-WmiObject -Class Win32_Product | Export-Csv software.csv

# 9. Network configuration
ipconfig /all > network_config.txt
arp -a >> network_config.txt

# 10. Firewall rules
Get-NetFirewallRule -Enabled True | Export-Csv firewall_rules.csv
```

---

## 🥇 OPCIÓN #2: OSQUERY (RECOMENDADO PARA MULTIPLATAFORMA)

### ✅ Ventajas

```
✓ Gratuito y open-source
✓ Multiplataforma (Win/Mac/Linux)
✓ Agente muy ligero (~5MB)
✓ Queries SQL-like
✓ Real-time collection
✓ Muy usado en empresas
✓ Excelente documentación
✓ Community grande
```

### ❌ Desventajas

```
✗ No soporta iOS/Android
✗ Curva de aprendizaje (SQL queries)
✗ Requiere servidor Osquery
```

### 💻 Capacidades

```
✓ Procesos: SELECT * FROM processes
✓ Conexiones: SELECT * FROM process_open_sockets
✓ Archivos: SELECT * FROM file
✓ Registry (Win): SELECT * FROM registry
✓ Sistema: SELECT * FROM system_info
✓ Usuarios: SELECT * FROM users
✓ Events (Win): SELECT * FROM windows_events
✓ Shell history: SELECT * FROM shell_history
✓ Packages: SELECT * FROM deb_packages (Linux)
```

### 🔗 Integración Backend

```python
# api/services/osquery_agent.py

import requests
import json
from typing import List, Dict

class OSQueryAgent:
    """
    Agente OSQuery para recolección multiplataforma
    """
    
    OSQUERY_DOWNLOAD_URLS = {
        'windows': 'https://osquery.io/downloads/windows/osquery-5.12.1.msi',
        'mac': 'https://osquery.io/downloads/osx/osquery-5.12.1.pkg',
        'linux_deb': 'https://osquery.io/downloads/linux/osquery_5.12.1-1.linux_amd64.deb',
        'linux_rpm': 'https://osquery.io/downloads/linux/osquery-5.12.1-1.linux.x86_64.rpm'
    }
    
    def __init__(self, osquery_server_url: str = "http://localhost:5000"):
        self.server_url = osquery_server_url
    
    async def deploy_agent(
        self, 
        device_id: str, 
        os_type: str,  # windows | mac | linux
        case_id: str
    ) -> Dict:
        """
        Genera link de descarga para desplegar agente
        
        Retorna URL pública para descargar OSQuery
        """
        
        download_url = self.OSQUERY_DOWNLOAD_URLS.get(os_type)
        
        return {
            "download_url": download_url,
            "installation_steps": self._get_installation_steps(os_type),
            "configuration": self._get_osquery_config(device_id, case_id),
            "case_id": case_id,
            "device_id": device_id
        }
    
    def _get_installation_steps(self, os_type: str) -> List[str]:
        """Pasos de instalación por SO"""
        
        steps = {
            'windows': [
                "1. Descargar: osquery-5.12.1.msi",
                "2. Ejecutar: msiexec /i osquery-5.12.1.msi",
                "3. Configurar: C:\\Program Files\\osquery\\osquery.conf",
                "4. Iniciar servicio: osqueryd --flagfile=C:\\Program Files\\osquery\\osquery.flags"
            ],
            'mac': [
                "1. Descargar: osquery-5.12.1.pkg",
                "2. Instalar: sudo installer -pkg osquery-5.12.1.pkg -target /",
                "3. Configurar: /var/osquery/osquery.conf",
                "4. Iniciar: sudo launchctl load /Library/LaunchDaemons/com.facebook.osqueryd.plist"
            ],
            'linux': [
                "1. Descargar: osquery_5.12.1-1.linux_amd64.deb",
                "2. Instalar: sudo dpkg -i osquery_5.12.1-1.linux_amd64.deb",
                "3. Configurar: /etc/osquery/osquery.conf",
                "4. Iniciar: sudo systemctl start osqueryd"
            ]
        }
        
        return steps.get(os_type, [])
    
    def _get_osquery_config(self, device_id: str, case_id: str) -> Dict:
        """Retorna configuración OSQuery optimizada"""
        
        return {
            "options": {
                "config_plugin": "filesystem",
                "logger_plugin": "filesystem",
                "logger_path": f"/var/log/osquery/case_{case_id}",
                "disable_logging": False,
                "schedule_splay_percent": 10
            },
            "schedule": {
                "processes": {
                    "query": "SELECT * FROM processes",
                    "interval": 10  # cada 10 segundos
                },
                "process_sockets": {
                    "query": "SELECT * FROM process_open_sockets",
                    "interval": 30
                },
                "system_info": {
                    "query": "SELECT * FROM system_info",
                    "interval": 3600  # cada hora
                },
                "users": {
                    "query": "SELECT * FROM users",
                    "interval": 300
                },
                "installed_packages": {
                    "query": "SELECT * FROM deb_packages",
                    "interval": 3600
                }
            }
        }
    
    async def execute_query(
        self, 
        device_id: str, 
        query: str,
        case_id: str
    ) -> Dict:
        """
        Ejecuta query SQL en endpoint remoto
        
        Ejemplos:
        - "SELECT * FROM processes WHERE name LIKE '%svchost%'"
        - "SELECT * FROM process_open_sockets WHERE port = 443"
        - "SELECT * FROM shell_history LIMIT 100"
        """
        
        payload = {
            "device_id": device_id,
            "query": query,
            "case_id": case_id,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{self.server_url}/api/query",
            json=payload
        )
        
        return response.json()
    
    async def collect_artifacts(
        self, 
        device_id: str,
        case_id: str,
        artifact_type: str  # 'all', 'processes', 'network', 'files'
    ) -> Dict:
        """
        Recolecta artefactos predefinidos
        """
        
        queries = {
            'all': [
                ("processes", "SELECT * FROM processes"),
                ("sockets", "SELECT * FROM process_open_sockets"),
                ("files_recent", "SELECT * FROM file WHERE mtime > datetime('now', '-1 day')"),
                ("users", "SELECT * FROM users"),
                ("shell_history", "SELECT * FROM shell_history LIMIT 1000"),
                ("system", "SELECT * FROM system_info"),
            ],
            'processes': [
                ("processes", "SELECT * FROM processes"),
                ("process_memory", "SELECT * FROM process_memory_map"),
            ],
            'network': [
                ("sockets", "SELECT * FROM process_open_sockets"),
                ("connections", "SELECT * FROM process_open_files WHERE path LIKE '%.so'"),
                ("dns_cache", "SELECT * FROM dns_cache"),
            ],
            'files': [
                ("recent_files", "SELECT * FROM file WHERE mtime > datetime('now', '-24 hours')"),
                ("suspicious_extensions", "SELECT * FROM file WHERE name LIKE '%.ps1' OR name LIKE '%.bat'"),
            ]
        }
        
        results = {}
        for name, query in queries.get(artifact_type, []):
            results[name] = await self.execute_query(device_id, query, case_id)
        
        return results

# Ejemplo de uso en API
@router.post("/forensics/mobile-agent/osquery/deploy")
async def deploy_osquery(request: OSQueryDeployRequest):
    """
    POST /forensics/mobile-agent/osquery/deploy
    {
      "device_id": "WORKSTATION-01",
      "os_type": "windows",
      "case_id": "IR-2025-001"
    }
    
    Retorna link público para descargar OSQuery
    """
    agent = OSQueryAgent()
    result = await agent.deploy_agent(
        request.device_id,
        request.os_type,
        request.case_id
    )
    return result

@router.post("/forensics/mobile-agent/osquery/query")
async def run_osquery(request: OSQueryRequest):
    """
    POST /forensics/mobile-agent/osquery/query
    {
      "device_id": "WORKSTATION-01",
      "query": "SELECT * FROM processes WHERE name LIKE '%svchost%'",
      "case_id": "IR-2025-001"
    }
    """
    agent = OSQueryAgent()
    result = await agent.execute_query(
        request.device_id,
        request.query,
        request.case_id
    )
    return result
```

### 📋 Queries OSQuery Predefinidas

```sql
-- 1. Procesos sospechosos (espacios en ruta)
SELECT * FROM processes 
WHERE path LIKE '% %.exe' 
OR cmdline LIKE '%powershell%' 
OR cmdline LIKE '%cmd.exe%';

-- 2. Conexiones establecidas
SELECT * FROM process_open_sockets 
WHERE state = 'ESTABLISHED' 
ORDER BY remote_port DESC;

-- 3. Archivos recientes ejecutados
SELECT * FROM file 
WHERE path LIKE 'C:\\Users\\%\\AppData\\Roaming\\Microsoft\\Windows\\Recent\\%'
AND mtime > datetime('now', '-24 hours');

-- 4. Registry Run keys (autostart)
SELECT * FROM registry 
WHERE path LIKE '%Software\\Microsoft\\Windows\\CurrentVersion\\Run%';

-- 5. Drivers sospechosos
SELECT * FROM drivers 
WHERE base IS NOT NULL 
AND base < 0x400000;

-- 6. Event logs (últimos 100)
SELECT * FROM windows_events 
WHERE channel = 'Security' 
LIMIT 100;

-- 7. Procesos sin firma digital (Windows)
SELECT * FROM processes 
WHERE signed != 1;

-- 8. Shell history (Linux/Mac)
SELECT * FROM shell_history 
WHERE command LIKE '%sudo%' 
OR command LIKE '%curl%'
LIMIT 100;

-- 9. Sudoers configuration
SELECT * FROM sudoers;

-- 10. SSH keys
SELECT * FROM ssh_authorized_keys;
```

---

## 🥇 OPCIÓN #3: VELOCIRAPTOR (EDR GRATUITO)

### ✅ Ventajas

```
✓ EDR completo gratuito
✓ Análisis forense avanzado
✓ YARA integration
✓ VQL (Velociraptor Query Language)
✓ Muy usado en empresas
✓ Open source
✓ Web UI profesional
```

### ❌ Desventajas

```
✗ Requiere servidor Velociraptor
✗ Curva de aprendizaje (VQL)
✗ No soporta iOS/Android
```

### 🔗 Integración Backend

```python
# api/services/velociraptor_agent.py

import pyvelociraptor  # pip install pyvelociraptor
import asyncio

class VelociraptorAgent:
    """
    Integración con Velociraptor EDR
    """
    
    def __init__(self, server_url: str, api_key: str):
        self.client = pyvelociraptor.VelociraptorClient(
            server_url=server_url,
            api_key=api_key
        )
    
    async def deploy_client(
        self, 
        case_id: str,
        os_type: str  # windows | linux | mac
    ) -> Dict:
        """
        Genera installer de cliente Velociraptor
        """
        
        # Generar config con servidor Velociraptor
        config = {
            "client": {
                "server_urls": ["https://velociraptor.example.com:8000"],
                "certificate": "<CERTIFICATE>",
                "nonce": "<NONCE>"
            }
        }
        
        # Generar ejecutable personalizado
        installer_url = f"https://velociraptor.example.com/api/v1/client/download/{os_type}"
        
        return {
            "installer_url": installer_url,
            "config": config,
            "instructions": self._get_velociraptor_instructions(os_type),
            "case_id": case_id
        }
    
    async def collect_artifacts(
        self, 
        client_id: str,
        artifacts: List[str],  # predefined artifacts
        case_id: str
    ) -> Dict:
        """
        Recolecta artefactos predefinidos
        
        Ejemplos:
        - Windows.Registry.SAM
        - Windows.EventLogs.Application
        - Linux.Auditd
        - Linux.Syslog
        """
        
        predefined_artifacts = {
            'Windows.Registry.SAM': 'SAM registry hive',
            'Windows.Registry.SYSTEM': 'SYSTEM registry hive',
            'Windows.Registry.SECURITY': 'SECURITY registry hive',
            'Windows.EventLogs.Application': 'Application event logs',
            'Windows.EventLogs.Security': 'Security event logs',
            'Windows.System.Processes': 'Running processes',
            'Windows.System.Network.Connections': 'Network connections',
            'Linux.Auditd': 'Auditd logs',
            'Linux.Syslog': 'System logs',
        }
        
        results = {}
        for artifact in artifacts:
            if artifact in predefined_artifacts:
                # Ejecutar recolección
                result = self.client.collect_artifact(
                    client_id=client_id,
                    artifact_name=artifact
                )
                results[artifact] = result
        
        return results

# Ejemplo de uso
@router.post("/forensics/mobile-agent/velociraptor/deploy")
async def deploy_velociraptor(request: VelociraptorDeployRequest):
    """Deploy cliente Velociraptor"""
    agent = VelociraptorAgent(
        server_url=settings.VELOCIRAPTOR_URL,
        api_key=settings.VELOCIRAPTOR_KEY
    )
    result = await agent.deploy_client(request.case_id, request.os_type)
    return result
```

---

## 📱 OPCIÓN #4: MOBILE DEVICE (iOS/Android)

### Para iOS

**Herramientas Recomendadas**:

1. **Apple MDM Profile**
   - Incluido en Apple Business Manager
   - Control remoto limitado pero seguro
   
2. **Mobile Iron**
   - MDM/MAM completo
   - Recolección de logs
   - Wipe remoto

### Para Android

**Herramientas Recomendadas**:

1. **Google Android Enterprise**
   - MDM integrado
   - Managed Play
   - Restricciones de aplicaciones

2. **MobileIron**
   - MDM/MAM para Android
   - Recolección de forensics

---

## 🚀 ESTRATEGIA RECOMENDADA: HÍBRIDA

```
┌─────────────────────────────────────────────────────────┐
│          MOBILE AGENT - ESTRATEGIA HÍBRIDA              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  NIVEL 1: INTUNE (Para M365 environments)              │
│  ├─ Windows: ✅ Full forensics via PowerShell         │
│  ├─ Mac: ✅ Full forensics via Shell                  │
│  ├─ iOS: ⚠️ Limited (MDM basics)                      │
│  └─ Android: ⚠️ Limited (MDM basics)                  │
│                                                         │
│  NIVEL 2: OSQUERY (Multiplataforma ligero)             │
│  ├─ Windows: ✅ Process, network, files               │
│  ├─ Mac: ✅ Process, network, files                   │
│  ├─ Linux: ✅ Full support                            │
│  ├─ iOS: ❌ Not supported                             │
│  └─ Android: ❌ Not supported                         │
│                                                         │
│  NIVEL 3: VELOCIRAPTOR (EDR Gratuito)                 │
│  ├─ Windows: ✅ Advanced EDR                          │
│  ├─ Mac: ✅ Advanced EDR                              │
│  ├─ Linux: ✅ Advanced EDR                            │
│  ├─ iOS: ❌ Not supported                             │
│  └─ Android: ❌ Not supported                         │
│                                                         │
│  NIVEL 4: Mobile Device Management                     │
│  ├─ iOS: Apple MDM (Intune/Jamf)                      │
│  └─ Android: Android Enterprise (Google)              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 💼 COMPARATIVA FINAL

| Criterio | Intune | OSQuery | Velociraptor | Opción Pago |
|----------|--------|---------|--------------|------------|
| Costo | 💚 Gratis | 💚 Gratis | 💚 Gratis | 🔴 $$$ |
| Facilidad | 🟢 Media | 🟡 Media-Alta | 🟡 Media-Alta | 🟢 Fácil |
| Windows | 🟢🟢🟢 | 🟢🟢 | 🟢🟢🟢 | 🟢🟢🟢 |
| Mac | 🟢🟢 | 🟢🟢 | 🟢🟢🟢 | 🟢🟢🟢 |
| Linux | 🟢 | 🟢🟢🟢 | 🟢🟢🟢 | 🟢🟢 |
| iOS | 🟡 | 🔴 | 🔴 | 🟢🟢 |
| Android | 🟡 | 🔴 | 🔴 | 🟢🟢 |
| Escalabilidad | 🟢🟢🟢 | 🟢🟢 | 🟢🟢 | 🟢🟢🟢 |
| **Recomendación** | **#1** | **#2** | **#3** | Opcional |

---

## ✅ IMPLEMENTACIÓN: Módulo Mobile Agent

```python
# api/routes/mobile_agents.py

from fastapi import APIRouter, BackgroundTasks
from ..services.intune_agent import IntuneRemoteAgent
from ..services.osquery_agent import OSQueryAgent
from ..services.velociraptor_agent import VelociraptorAgent

router = APIRouter(prefix="/forensics/mobile-agent", tags=["Mobile Agents"])

# --- INTUNE ENDPOINTS ---

@router.get("/intune/devices")
async def list_intune_devices():
    """Lista dispositivos administrados por Intune"""
    agent = IntuneRemoteAgent()
    devices = await agent.get_managed_devices()
    return devices

@router.post("/intune/execute-script")
async def execute_intune_script(device_id: str, script: str, case_id: str):
    """Ejecuta script PowerShell en dispositivo Intune"""
    agent = IntuneRemoteAgent()
    result = await agent.run_remote_script(device_id, script)
    return result

@router.post("/intune/collect-logs")
async def collect_intune_logs(device_id: str, case_id: str):
    """Recolecta logs del dispositivo"""
    agent = IntuneRemoteAgent()
    result = await agent.collect_device_logs(device_id, case_id)
    return result

# --- OSQUERY ENDPOINTS ---

@router.post("/osquery/deploy")
async def deploy_osquery(device_id: str, os_type: str, case_id: str):
    """Genera link para descargar OSQuery"""
    agent = OSQueryAgent()
    result = await agent.deploy_agent(device_id, os_type, case_id)
    return result

@router.post("/osquery/query")
async def run_osquery_query(device_id: str, query: str, case_id: str):
    """Ejecuta query SQL en OSQuery"""
    agent = OSQueryAgent()
    result = await agent.execute_query(device_id, query, case_id)
    return result

@router.post("/osquery/collect-artifacts")
async def collect_osquery_artifacts(
    device_id: str, 
    artifact_type: str,  # all, processes, network, files
    case_id: str
):
    """Recolecta artefactos con OSQuery"""
    agent = OSQueryAgent()
    result = await agent.collect_artifacts(device_id, case_id, artifact_type)
    return result

# --- VELOCIRAPTOR ENDPOINTS ---

@router.post("/velociraptor/deploy")
async def deploy_velociraptor(os_type: str, case_id: str):
    """Genera installer de Velociraptor"""
    agent = VelociraptorAgent(
        server_url=settings.VELOCIRAPTOR_URL,
        api_key=settings.VELOCIRAPTOR_KEY
    )
    result = await agent.deploy_client(case_id, os_type)
    return result

@router.post("/velociraptor/collect")
async def collect_velociraptor_artifacts(
    client_id: str,
    artifacts: List[str],
    case_id: str
):
    """Recolecta artefactos con Velociraptor"""
    agent = VelociraptorAgent(
        server_url=settings.VELOCIRAPTOR_URL,
        api_key=settings.VELOCIRAPTOR_KEY
    )
    result = await agent.collect_artifacts(client_id, artifacts, case_id)
    return result
```

---

**Documento Completado**: 2025-12-05  
**Recomendación Final**: Implementar INTUNE + OSQUERY (mejor cobertura/costo)  
**Viabilidad**: 🟢🟢🟢 MUY ALTA (sin desarrollo custom)
