"""
Kali Tools Service - Catálogo y ejecución de herramientas de seguridad
Organizado por categorías de trabajo de investigación
"""

import asyncio
import shutil
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categorías de herramientas de seguridad"""
    RECONNAISSANCE = "reconnaissance"
    SCANNING = "scanning"
    ENUMERATION = "enumeration"
    VULNERABILITY = "vulnerability"
    EXPLOITATION = "exploitation"
    PASSWORD = "password"
    WIRELESS = "wireless"
    FORENSICS = "forensics"
    WEB = "web"
    NETWORK = "network"
    OSINT = "osint"
    CRYPTO = "crypto"
    REPORTING = "reporting"


class ToolStatus(str, Enum):
    """Estado de la herramienta"""
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    RUNNING = "running"
    REQUIRES_ROOT = "requires_root"


@dataclass
class ToolParameter:
    """Parámetro de una herramienta"""
    name: str
    type: str  # string, number, boolean, select, file, ip, domain, url
    description: str
    required: bool = False
    default: Any = None
    options: List[str] = field(default_factory=list)  # Para type=select
    placeholder: str = ""
    validation: str = ""  # Regex pattern para validación


@dataclass
class KaliTool:
    """Definición de una herramienta de Kali"""
    id: str
    name: str
    description: str
    category: ToolCategory
    command: str  # Comando base
    icon: str = "🔧"
    parameters: List[ToolParameter] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    requires_root: bool = False
    dangerous: bool = False  # Herramientas que pueden causar daño
    timeout_seconds: int = 300
    output_parser: Optional[str] = None  # Nombre del parser personalizado
    documentation_url: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# CATÁLOGO DE HERRAMIENTAS KALI
# ============================================================================

KALI_TOOLS_CATALOG: Dict[str, KaliTool] = {}


def register_tool(tool: KaliTool):
    """Registrar herramienta en el catálogo"""
    KALI_TOOLS_CATALOG[tool.id] = tool


# -----------------------------------------------------------------------------
# RECONNAISSANCE - Reconocimiento
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="whois",
    name="WHOIS Lookup",
    description="Consulta información de registro de dominios (propietario, registrar, fechas, nameservers)",
    category=ToolCategory.RECONNAISSANCE,
    command="whois",
    icon="🔍",
    parameters=[
        ToolParameter(
            name="target",
            type="domain",
            description="Dominio a consultar",
            required=True,
            placeholder="ejemplo.com"
        )
    ],
    examples=["whois google.com", "whois 8.8.8.8"],
    timeout_seconds=30
))

register_tool(KaliTool(
    id="dig",
    name="DNS Lookup (dig)",
    description="Consulta registros DNS detallados (A, AAAA, MX, TXT, NS, SOA, CNAME)",
    category=ToolCategory.RECONNAISSANCE,
    command="dig",
    icon="🌐",
    parameters=[
        ToolParameter(
            name="target",
            type="domain",
            description="Dominio a consultar",
            required=True,
            placeholder="ejemplo.com"
        ),
        ToolParameter(
            name="record_type",
            type="select",
            description="Tipo de registro DNS",
            required=False,
            default="ANY",
            options=["A", "AAAA", "MX", "TXT", "NS", "SOA", "CNAME", "PTR", "ANY"]
        ),
        ToolParameter(
            name="dns_server",
            type="ip",
            description="Servidor DNS a usar (opcional)",
            required=False,
            placeholder="8.8.8.8"
        )
    ],
    examples=["dig google.com ANY", "dig @8.8.8.8 example.com MX"],
    timeout_seconds=30
))

register_tool(KaliTool(
    id="host",
    name="Host Lookup",
    description="Resolución rápida de nombres DNS a IPs y viceversa",
    category=ToolCategory.RECONNAISSANCE,
    command="host",
    icon="🏠",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Dominio o IP a resolver",
            required=True,
            placeholder="ejemplo.com o 8.8.8.8"
        )
    ],
    examples=["host google.com", "host 8.8.8.8"],
    timeout_seconds=20
))

register_tool(KaliTool(
    id="nslookup",
    name="NSLookup",
    description="Consulta servidores de nombres y registros DNS",
    category=ToolCategory.RECONNAISSANCE,
    command="nslookup",
    icon="📡",
    parameters=[
        ToolParameter(
            name="target",
            type="domain",
            description="Dominio a consultar",
            required=True,
            placeholder="ejemplo.com"
        ),
        ToolParameter(
            name="dns_server",
            type="ip",
            description="Servidor DNS (opcional)",
            required=False,
            placeholder="8.8.8.8"
        )
    ],
    examples=["nslookup google.com", "nslookup example.com 8.8.8.8"],
    timeout_seconds=20
))

register_tool(KaliTool(
    id="theHarvester",
    name="theHarvester",
    description="Recolecta emails, subdominios, hosts, nombres de empleados desde fuentes públicas",
    category=ToolCategory.OSINT,
    command="theHarvester",
    icon="🌾",
    parameters=[
        ToolParameter(
            name="domain",
            type="domain",
            description="Dominio objetivo",
            required=True,
            placeholder="ejemplo.com"
        ),
        ToolParameter(
            name="source",
            type="select",
            description="Fuente de datos",
            required=False,
            default="all",
            options=["all", "google", "bing", "linkedin", "twitter", "shodan", "virustotal", "dnsdumpster", "crtsh"]
        ),
        ToolParameter(
            name="limit",
            type="number",
            description="Límite de resultados",
            required=False,
            default=100
        )
    ],
    examples=["theHarvester -d example.com -b all -l 200"],
    timeout_seconds=300
))

# -----------------------------------------------------------------------------
# SCANNING - Escaneo
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="nmap_quick",
    name="Nmap Quick Scan",
    description="Escaneo rápido de puertos comunes y detección de servicios",
    category=ToolCategory.SCANNING,
    command="nmap",
    icon="🎯",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="IP, rango o dominio a escanear",
            required=True,
            placeholder="192.168.1.1 o ejemplo.com"
        ),
        ToolParameter(
            name="scan_type",
            type="select",
            description="Tipo de escaneo",
            required=False,
            default="quick",
            options=["quick", "full", "stealth", "udp", "version"]
        )
    ],
    examples=["nmap -sV 192.168.1.1", "nmap -sS -T4 10.0.0.0/24"],
    requires_root=True,
    timeout_seconds=600
))

register_tool(KaliTool(
    id="nmap_vuln",
    name="Nmap Vulnerability Scan",
    description="Escaneo de vulnerabilidades con scripts NSE",
    category=ToolCategory.VULNERABILITY,
    command="nmap",
    icon="🔓",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="IP o dominio objetivo",
            required=True,
            placeholder="192.168.1.1"
        ),
        ToolParameter(
            name="script_category",
            type="select",
            description="Categoría de scripts",
            required=False,
            default="vuln",
            options=["vuln", "safe", "exploit", "auth", "default", "discovery"]
        )
    ],
    examples=["nmap --script vuln 192.168.1.1"],
    requires_root=True,
    dangerous=True,
    timeout_seconds=900
))

register_tool(KaliTool(
    id="masscan",
    name="Masscan",
    description="Escáner de puertos ultrarrápido para grandes rangos de red",
    category=ToolCategory.SCANNING,
    command="masscan",
    icon="⚡",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="IP o rango CIDR",
            required=True,
            placeholder="10.0.0.0/8"
        ),
        ToolParameter(
            name="ports",
            type="string",
            description="Puertos a escanear",
            required=False,
            default="1-1000",
            placeholder="80,443,22 o 1-65535"
        ),
        ToolParameter(
            name="rate",
            type="number",
            description="Paquetes por segundo",
            required=False,
            default=1000
        )
    ],
    examples=["masscan 10.0.0.0/8 -p80,443 --rate 10000"],
    requires_root=True,
    timeout_seconds=600
))

# -----------------------------------------------------------------------------
# NETWORK - Red
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="netcat",
    name="Netcat",
    description="Herramienta de red para lectura/escritura de conexiones TCP/UDP",
    category=ToolCategory.NETWORK,
    command="nc",
    icon="🔌",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Host objetivo",
            required=True,
            placeholder="192.168.1.1"
        ),
        ToolParameter(
            name="port",
            type="number",
            description="Puerto",
            required=True,
            placeholder="80"
        ),
        ToolParameter(
            name="mode",
            type="select",
            description="Modo de operación",
            required=False,
            default="connect",
            options=["connect", "listen", "scan"]
        )
    ],
    examples=["nc -zv 192.168.1.1 1-1000", "nc -lvp 4444"],
    timeout_seconds=60
))

register_tool(KaliTool(
    id="tcpdump",
    name="TCPDump",
    description="Captura y analiza tráfico de red en tiempo real",
    category=ToolCategory.NETWORK,
    command="tcpdump",
    icon="📦",
    parameters=[
        ToolParameter(
            name="interface",
            type="string",
            description="Interfaz de red",
            required=False,
            default="any",
            placeholder="eth0"
        ),
        ToolParameter(
            name="filter",
            type="string",
            description="Filtro BPF",
            required=False,
            placeholder="port 80 or port 443"
        ),
        ToolParameter(
            name="count",
            type="number",
            description="Número de paquetes a capturar",
            required=False,
            default=100
        )
    ],
    examples=["tcpdump -i eth0 port 80", "tcpdump -c 100 host 192.168.1.1"],
    requires_root=True,
    timeout_seconds=120
))

register_tool(KaliTool(
    id="traceroute",
    name="Traceroute",
    description="Muestra la ruta de paquetes hacia un host destino",
    category=ToolCategory.NETWORK,
    command="traceroute",
    icon="🛤️",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Host destino",
            required=True,
            placeholder="google.com"
        ),
        ToolParameter(
            name="max_hops",
            type="number",
            description="Máximo de saltos",
            required=False,
            default=30
        )
    ],
    examples=["traceroute google.com", "traceroute -m 15 8.8.8.8"],
    timeout_seconds=120
))

register_tool(KaliTool(
    id="ping",
    name="Ping",
    description="Verifica conectividad con un host usando ICMP",
    category=ToolCategory.NETWORK,
    command="ping",
    icon="📶",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Host a verificar",
            required=True,
            placeholder="192.168.1.1"
        ),
        ToolParameter(
            name="count",
            type="number",
            description="Número de pings",
            required=False,
            default=4
        )
    ],
    examples=["ping -c 4 google.com"],
    timeout_seconds=30
))

# -----------------------------------------------------------------------------
# WEB - Análisis Web
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="curl",
    name="cURL",
    description="Realiza peticiones HTTP/HTTPS con headers y métodos personalizados",
    category=ToolCategory.WEB,
    command="curl",
    icon="🌍",
    parameters=[
        ToolParameter(
            name="url",
            type="url",
            description="URL objetivo",
            required=True,
            placeholder="https://ejemplo.com"
        ),
        ToolParameter(
            name="method",
            type="select",
            description="Método HTTP",
            required=False,
            default="GET",
            options=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
        ),
        ToolParameter(
            name="headers",
            type="string",
            description="Headers adicionales (formato: 'Header: Value')",
            required=False,
            placeholder="Authorization: Bearer token123"
        ),
        ToolParameter(
            name="data",
            type="string",
            description="Datos para POST/PUT",
            required=False,
            placeholder='{"key": "value"}'
        ),
        ToolParameter(
            name="follow_redirects",
            type="boolean",
            description="Seguir redirecciones",
            required=False,
            default=True
        )
    ],
    examples=["curl -I https://google.com", "curl -X POST -d 'data' https://api.com"],
    timeout_seconds=60
))

register_tool(KaliTool(
    id="wget",
    name="Wget",
    description="Descarga archivos y sitios web completos",
    category=ToolCategory.WEB,
    command="wget",
    icon="⬇️",
    parameters=[
        ToolParameter(
            name="url",
            type="url",
            description="URL a descargar",
            required=True,
            placeholder="https://ejemplo.com/archivo.pdf"
        ),
        ToolParameter(
            name="recursive",
            type="boolean",
            description="Descarga recursiva",
            required=False,
            default=False
        ),
        ToolParameter(
            name="depth",
            type="number",
            description="Profundidad de recursión",
            required=False,
            default=2
        )
    ],
    examples=["wget https://example.com/file.pdf", "wget -r -l 2 https://site.com"],
    timeout_seconds=300
))

register_tool(KaliTool(
    id="nikto",
    name="Nikto",
    description="Scanner de vulnerabilidades web (XSS, SQLi, configuraciones)",
    category=ToolCategory.WEB,
    command="nikto",
    icon="🕷️",
    parameters=[
        ToolParameter(
            name="target",
            type="url",
            description="URL del sitio web",
            required=True,
            placeholder="https://ejemplo.com"
        ),
        ToolParameter(
            name="ssl",
            type="boolean",
            description="Usar SSL",
            required=False,
            default=True
        ),
        ToolParameter(
            name="tuning",
            type="select",
            description="Tipo de pruebas",
            required=False,
            default="x",
            options=["1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "x"]
        )
    ],
    examples=["nikto -h https://example.com", "nikto -h target -ssl"],
    dangerous=True,
    timeout_seconds=900
))

register_tool(KaliTool(
    id="whatweb",
    name="WhatWeb",
    description="Identifica tecnologías web (CMS, frameworks, servidores, plugins)",
    category=ToolCategory.WEB,
    command="whatweb",
    icon="🔬",
    parameters=[
        ToolParameter(
            name="target",
            type="url",
            description="URL objetivo",
            required=True,
            placeholder="https://ejemplo.com"
        ),
        ToolParameter(
            name="aggression",
            type="select",
            description="Nivel de agresividad",
            required=False,
            default="1",
            options=["1", "2", "3", "4"]
        )
    ],
    examples=["whatweb https://example.com", "whatweb -a 3 https://target.com"],
    timeout_seconds=120
))

register_tool(KaliTool(
    id="gobuster",
    name="Gobuster",
    description="Fuerza bruta de directorios y archivos web",
    category=ToolCategory.WEB,
    command="gobuster",
    icon="📁",
    parameters=[
        ToolParameter(
            name="target",
            type="url",
            description="URL objetivo",
            required=True,
            placeholder="https://ejemplo.com"
        ),
        ToolParameter(
            name="mode",
            type="select",
            description="Modo de operación",
            required=False,
            default="dir",
            options=["dir", "dns", "vhost", "fuzz"]
        ),
        ToolParameter(
            name="wordlist",
            type="select",
            description="Diccionario a usar",
            required=False,
            default="common",
            options=["common", "medium", "big", "raft-small", "raft-medium"]
        ),
        ToolParameter(
            name="extensions",
            type="string",
            description="Extensiones a probar",
            required=False,
            placeholder="php,html,js,txt"
        )
    ],
    examples=["gobuster dir -u https://site.com -w /usr/share/wordlists/dirb/common.txt"],
    dangerous=True,
    timeout_seconds=600
))

register_tool(KaliTool(
    id="wpscan",
    name="WPScan",
    description="Scanner de seguridad para WordPress (plugins, temas, usuarios)",
    category=ToolCategory.WEB,
    command="wpscan",
    icon="📝",
    parameters=[
        ToolParameter(
            name="target",
            type="url",
            description="URL del sitio WordPress",
            required=True,
            placeholder="https://wordpress-site.com"
        ),
        ToolParameter(
            name="enumerate",
            type="select",
            description="Qué enumerar",
            required=False,
            default="vp",
            options=["vp", "ap", "p", "vt", "at", "t", "u", "m"]
        )
    ],
    examples=["wpscan --url https://wp.com --enumerate vp"],
    dangerous=True,
    timeout_seconds=600
))

# -----------------------------------------------------------------------------
# ENUMERATION - Enumeración
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="enum4linux",
    name="Enum4linux",
    description="Enumera información de sistemas Windows/Samba (usuarios, shares, políticas)",
    category=ToolCategory.ENUMERATION,
    command="enum4linux",
    icon="🪟",
    parameters=[
        ToolParameter(
            name="target",
            type="ip",
            description="IP del objetivo",
            required=True,
            placeholder="192.168.1.100"
        ),
        ToolParameter(
            name="all",
            type="boolean",
            description="Enumeración completa",
            required=False,
            default=True
        )
    ],
    examples=["enum4linux -a 192.168.1.100"],
    timeout_seconds=300
))

register_tool(KaliTool(
    id="smbclient",
    name="SMBClient",
    description="Cliente para conectar y explorar shares SMB/CIFS",
    category=ToolCategory.ENUMERATION,
    command="smbclient",
    icon="📂",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Share SMB (//host/share)",
            required=True,
            placeholder="//192.168.1.100/share"
        ),
        ToolParameter(
            name="username",
            type="string",
            description="Usuario (opcional)",
            required=False,
            placeholder="admin"
        ),
        ToolParameter(
            name="password",
            type="string",
            description="Contraseña (opcional)",
            required=False
        )
    ],
    examples=["smbclient -L //192.168.1.100", "smbclient //host/share -U user"],
    timeout_seconds=60
))

register_tool(KaliTool(
    id="ldapsearch",
    name="LDAP Search",
    description="Consulta directorios LDAP/Active Directory",
    category=ToolCategory.ENUMERATION,
    command="ldapsearch",
    icon="📒",
    parameters=[
        ToolParameter(
            name="host",
            type="string",
            description="Servidor LDAP",
            required=True,
            placeholder="ldap://dc.empresa.com"
        ),
        ToolParameter(
            name="base_dn",
            type="string",
            description="Base DN",
            required=True,
            placeholder="dc=empresa,dc=com"
        ),
        ToolParameter(
            name="filter",
            type="string",
            description="Filtro LDAP",
            required=False,
            default="(objectClass=*)",
            placeholder="(sAMAccountName=admin)"
        )
    ],
    examples=["ldapsearch -x -H ldap://dc.com -b 'dc=empresa,dc=com'"],
    timeout_seconds=120
))

# -----------------------------------------------------------------------------
# PASSWORD - Análisis de Contraseñas
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="hashid",
    name="Hash-Identifier",
    description="Identifica el tipo de hash (MD5, SHA, bcrypt, etc.)",
    category=ToolCategory.PASSWORD,
    command="hashid",
    icon="🔐",
    parameters=[
        ToolParameter(
            name="hash",
            type="string",
            description="Hash a identificar",
            required=True,
            placeholder="5f4dcc3b5aa765d61d8327deb882cf99"
        )
    ],
    examples=["hashid 5f4dcc3b5aa765d61d8327deb882cf99"],
    timeout_seconds=10
))

register_tool(KaliTool(
    id="john",
    name="John the Ripper",
    description="Cracker de contraseñas con múltiples formatos",
    category=ToolCategory.PASSWORD,
    command="john",
    icon="🔨",
    parameters=[
        ToolParameter(
            name="hash_file",
            type="file",
            description="Archivo con hashes",
            required=True,
            placeholder="/path/to/hashes.txt"
        ),
        ToolParameter(
            name="format",
            type="select",
            description="Formato del hash",
            required=False,
            default="auto",
            options=["auto", "md5", "sha1", "sha256", "sha512", "ntlm", "bcrypt", "raw-md5"]
        ),
        ToolParameter(
            name="wordlist",
            type="select",
            description="Diccionario",
            required=False,
            default="rockyou",
            options=["rockyou", "common", "fasttrack", "custom"]
        )
    ],
    examples=["john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt"],
    dangerous=True,
    timeout_seconds=1800
))

register_tool(KaliTool(
    id="hashcat",
    name="Hashcat",
    description="Cracker de contraseñas acelerado por GPU",
    category=ToolCategory.PASSWORD,
    command="hashcat",
    icon="⚡",
    parameters=[
        ToolParameter(
            name="hash_file",
            type="file",
            description="Archivo con hashes",
            required=True,
            placeholder="/path/to/hashes.txt"
        ),
        ToolParameter(
            name="hash_type",
            type="select",
            description="Tipo de hash (modo)",
            required=True,
            options=["0", "100", "1400", "1700", "1000", "3200", "500", "1800"]
        ),
        ToolParameter(
            name="attack_mode",
            type="select",
            description="Modo de ataque",
            required=False,
            default="0",
            options=["0", "1", "3", "6", "7"]
        )
    ],
    examples=["hashcat -m 0 -a 0 hashes.txt wordlist.txt"],
    dangerous=True,
    timeout_seconds=3600
))

register_tool(KaliTool(
    id="hydra",
    name="Hydra",
    description="Fuerza bruta de protocolos de autenticación (SSH, FTP, HTTP, etc.)",
    category=ToolCategory.PASSWORD,
    command="hydra",
    icon="🐍",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Host objetivo",
            required=True,
            placeholder="192.168.1.100"
        ),
        ToolParameter(
            name="protocol",
            type="select",
            description="Protocolo",
            required=True,
            options=["ssh", "ftp", "http-get", "http-post", "mysql", "rdp", "smb", "telnet", "vnc"]
        ),
        ToolParameter(
            name="username",
            type="string",
            description="Usuario o archivo de usuarios",
            required=True,
            placeholder="admin"
        ),
        ToolParameter(
            name="password_list",
            type="select",
            description="Lista de contraseñas",
            required=False,
            default="rockyou",
            options=["rockyou", "common", "fasttrack"]
        )
    ],
    examples=["hydra -l admin -P passwords.txt 192.168.1.100 ssh"],
    dangerous=True,
    timeout_seconds=1800
))

# -----------------------------------------------------------------------------
# FORENSICS - Forense
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="yara_scan",
    name="YARA Scan",
    description="Escanea archivos con reglas YARA para detectar malware",
    category=ToolCategory.FORENSICS,
    command="yara",
    icon="🦠",
    parameters=[
        ToolParameter(
            name="rules",
            type="select",
            description="Conjunto de reglas YARA",
            required=True,
            options=["malware", "ransomware", "webshell", "packer", "custom"]
        ),
        ToolParameter(
            name="target_path",
            type="string",
            description="Ruta a escanear",
            required=True,
            placeholder="/home/user/suspicious/"
        ),
        ToolParameter(
            name="recursive",
            type="boolean",
            description="Escaneo recursivo",
            required=False,
            default=True
        )
    ],
    examples=["yara -r /opt/yara-rules/malware.yar /suspicious/"],
    timeout_seconds=600
))

register_tool(KaliTool(
    id="strings",
    name="Strings",
    description="Extrae cadenas de texto de archivos binarios",
    category=ToolCategory.FORENSICS,
    command="strings",
    icon="📜",
    parameters=[
        ToolParameter(
            name="file",
            type="file",
            description="Archivo a analizar",
            required=True,
            placeholder="/path/to/binary"
        ),
        ToolParameter(
            name="min_length",
            type="number",
            description="Longitud mínima de cadena",
            required=False,
            default=4
        ),
        ToolParameter(
            name="encoding",
            type="select",
            description="Codificación",
            required=False,
            default="s",
            options=["s", "S", "b", "l", "B", "L"]
        )
    ],
    examples=["strings -n 8 malware.exe", "strings -el binary"],
    timeout_seconds=120
))

register_tool(KaliTool(
    id="file",
    name="File Type",
    description="Identifica el tipo de archivo mediante magic bytes",
    category=ToolCategory.FORENSICS,
    command="file",
    icon="📄",
    parameters=[
        ToolParameter(
            name="file",
            type="file",
            description="Archivo a identificar",
            required=True,
            placeholder="/path/to/file"
        )
    ],
    examples=["file unknown.bin", "file suspicious.pdf"],
    timeout_seconds=10
))

register_tool(KaliTool(
    id="exiftool",
    name="ExifTool",
    description="Extrae metadatos de archivos (imágenes, documentos, videos)",
    category=ToolCategory.FORENSICS,
    command="exiftool",
    icon="📷",
    parameters=[
        ToolParameter(
            name="file",
            type="file",
            description="Archivo a analizar",
            required=True,
            placeholder="/path/to/image.jpg"
        )
    ],
    examples=["exiftool photo.jpg", "exiftool document.pdf"],
    timeout_seconds=30
))

register_tool(KaliTool(
    id="binwalk",
    name="Binwalk",
    description="Análisis y extracción de firmware/archivos embebidos",
    category=ToolCategory.FORENSICS,
    command="binwalk",
    icon="🔩",
    parameters=[
        ToolParameter(
            name="file",
            type="file",
            description="Archivo firmware",
            required=True,
            placeholder="/path/to/firmware.bin"
        ),
        ToolParameter(
            name="extract",
            type="boolean",
            description="Extraer archivos encontrados",
            required=False,
            default=False
        )
    ],
    examples=["binwalk firmware.bin", "binwalk -e firmware.bin"],
    timeout_seconds=300
))

register_tool(KaliTool(
    id="volatility",
    name="Volatility 3",
    description="Análisis forense de dumps de memoria RAM",
    category=ToolCategory.FORENSICS,
    command="vol.py",
    icon="🧠",
    parameters=[
        ToolParameter(
            name="memory_dump",
            type="file",
            description="Dump de memoria",
            required=True,
            placeholder="/path/to/memory.dmp"
        ),
        ToolParameter(
            name="plugin",
            type="select",
            description="Plugin de análisis",
            required=True,
            options=["windows.pslist", "windows.pstree", "windows.netscan", "windows.malfind", "windows.cmdline", "windows.filescan", "linux.pslist", "linux.bash"]
        )
    ],
    examples=["vol.py -f memory.dmp windows.pslist", "vol.py -f dump.raw windows.malfind"],
    timeout_seconds=900
))

# -----------------------------------------------------------------------------
# OSINT - Inteligencia de Fuentes Abiertas
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="sherlock",
    name="Sherlock",
    description="Busca nombres de usuario en 300+ redes sociales",
    category=ToolCategory.OSINT,
    command="sherlock",
    icon="🔎",
    parameters=[
        ToolParameter(
            name="username",
            type="string",
            description="Nombre de usuario a buscar",
            required=True,
            placeholder="johndoe"
        ),
        ToolParameter(
            name="timeout",
            type="number",
            description="Timeout por sitio (segundos)",
            required=False,
            default=10
        )
    ],
    examples=["sherlock johndoe", "sherlock --timeout 5 targetuser"],
    timeout_seconds=300
))

register_tool(KaliTool(
    id="amass",
    name="Amass",
    description="Mapeo de superficie de ataque y descubrimiento de subdominios",
    category=ToolCategory.OSINT,
    command="amass",
    icon="🗺️",
    parameters=[
        ToolParameter(
            name="domain",
            type="domain",
            description="Dominio objetivo",
            required=True,
            placeholder="ejemplo.com"
        ),
        ToolParameter(
            name="mode",
            type="select",
            description="Modo de operación",
            required=False,
            default="enum",
            options=["enum", "intel", "db"]
        ),
        ToolParameter(
            name="passive",
            type="boolean",
            description="Solo reconocimiento pasivo",
            required=False,
            default=True
        )
    ],
    examples=["amass enum -d example.com -passive"],
    timeout_seconds=900
))

register_tool(KaliTool(
    id="recon-ng",
    name="Recon-ng",
    description="Framework de reconocimiento web completo",
    category=ToolCategory.OSINT,
    command="recon-ng",
    icon="🕵️",
    parameters=[
        ToolParameter(
            name="workspace",
            type="string",
            description="Nombre del workspace",
            required=True,
            placeholder="investigation-001"
        ),
        ToolParameter(
            name="module",
            type="select",
            description="Módulo a ejecutar",
            required=False,
            default="recon/domains-hosts/hackertarget",
            options=[
                "recon/domains-hosts/hackertarget",
                "recon/domains-contacts/whois_pocs",
                "recon/hosts-hosts/resolve",
                "recon/netblocks-hosts/shodan_net"
            ]
        )
    ],
    examples=["recon-ng -w workspace -m recon/domains-hosts/hackertarget"],
    timeout_seconds=300
))

# -----------------------------------------------------------------------------
# CRYPTO - Criptografía
# -----------------------------------------------------------------------------

register_tool(KaliTool(
    id="openssl",
    name="OpenSSL",
    description="Análisis de certificados SSL/TLS y operaciones criptográficas",
    category=ToolCategory.CRYPTO,
    command="openssl",
    icon="🔏",
    parameters=[
        ToolParameter(
            name="operation",
            type="select",
            description="Operación",
            required=True,
            options=["s_client", "x509", "rsa", "enc", "dgst"]
        ),
        ToolParameter(
            name="target",
            type="string",
            description="Host:puerto o archivo",
            required=True,
            placeholder="google.com:443"
        )
    ],
    examples=["openssl s_client -connect google.com:443", "openssl x509 -in cert.pem -text"],
    timeout_seconds=30
))

register_tool(KaliTool(
    id="sslyze",
    name="SSLyze",
    description="Analiza configuración SSL/TLS de servidores",
    category=ToolCategory.CRYPTO,
    command="sslyze",
    icon="🔐",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Host:puerto",
            required=True,
            placeholder="ejemplo.com:443"
        ),
        ToolParameter(
            name="certinfo",
            type="boolean",
            description="Mostrar info del certificado",
            required=False,
            default=True
        )
    ],
    examples=["sslyze --certinfo google.com:443"],
    timeout_seconds=120
))


# ============================================================================
# FUNCIONES DE SERVICIO
# ============================================================================

def get_all_tools() -> List[Dict]:
    """Obtiene todas las herramientas del catálogo"""
    return [tool.to_dict() for tool in KALI_TOOLS_CATALOG.values()]


def get_tools_by_category(category: ToolCategory) -> List[Dict]:
    """Obtiene herramientas de una categoría específica"""
    return [
        tool.to_dict() 
        for tool in KALI_TOOLS_CATALOG.values() 
        if tool.category == category
    ]


def get_tool_by_id(tool_id: str) -> Optional[KaliTool]:
    """Obtiene una herramienta por su ID"""
    return KALI_TOOLS_CATALOG.get(tool_id)


def get_categories() -> List[Dict]:
    """Obtiene todas las categorías con conteo de herramientas"""
    category_counts = {}
    for tool in KALI_TOOLS_CATALOG.values():
        cat = tool.category.value
        if cat not in category_counts:
            category_counts[cat] = {
                "id": cat,
                "name": cat.replace("_", " ").title(),
                "count": 0,
                "icon": get_category_icon(cat)
            }
        category_counts[cat]["count"] += 1
    return list(category_counts.values())


def get_category_icon(category: str) -> str:
    """Obtiene el ícono de una categoría"""
    icons = {
        "reconnaissance": "🔍",
        "scanning": "📡",
        "enumeration": "📋",
        "vulnerability": "🔓",
        "exploitation": "💥",
        "password": "🔑",
        "wireless": "📶",
        "forensics": "🔬",
        "web": "🌐",
        "network": "🔌",
        "osint": "🕵️",
        "crypto": "🔐",
        "reporting": "📊"
    }
    return icons.get(category, "🔧")


def check_tool_availability(tool_id: str) -> ToolStatus:
    """Verifica si una herramienta está disponible en el sistema"""
    tool = get_tool_by_id(tool_id)
    if not tool:
        return ToolStatus.NOT_INSTALLED
    
    # Verificar si el comando existe
    cmd = tool.command.split()[0]
    if not shutil.which(cmd):
        return ToolStatus.NOT_INSTALLED
    
    if tool.requires_root and os.geteuid() != 0:
        return ToolStatus.REQUIRES_ROOT
    
    return ToolStatus.AVAILABLE


def get_tools_status() -> Dict[str, str]:
    """Obtiene el estado de todas las herramientas"""
    status = {}
    for tool_id in KALI_TOOLS_CATALOG:
        status[tool_id] = check_tool_availability(tool_id).value
    return status


# ============================================================================
# CONSTRUCCIÓN DE COMANDOS
# ============================================================================

WORDLIST_PATHS = {
    "rockyou": "/usr/share/wordlists/rockyou.txt",
    "common": "/usr/share/wordlists/dirb/common.txt",
    "medium": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
    "big": "/usr/share/wordlists/dirb/big.txt",
    "raft-small": "/usr/share/wordlists/seclists/Discovery/Web-Content/raft-small-words.txt",
    "raft-medium": "/usr/share/wordlists/seclists/Discovery/Web-Content/raft-medium-words.txt",
    "fasttrack": "/usr/share/wordlists/fasttrack.txt"
}

YARA_RULES_PATHS = {
    "malware": "/opt/forensics-tools/yara-rules/gen_malware.yar",
    "ransomware": "/opt/forensics-tools/yara-rules/ransomware.yar",
    "webshell": "/opt/forensics-tools/yara-rules/webshells.yar",
    "packer": "/opt/forensics-tools/yara-rules/packers.yar",
    "custom": "/opt/forensics-tools/yara-rules/custom.yar"
}


def build_command(tool_id: str, params: Dict[str, Any]) -> List[str]:
    """Construye el comando a ejecutar basado en los parámetros"""
    tool = get_tool_by_id(tool_id)
    if not tool:
        raise ValueError(f"Tool {tool_id} not found")
    
    cmd = [tool.command]
    
    # Construir comando según la herramienta
    if tool_id == "whois":
        cmd.append(params["target"])
    
    elif tool_id == "dig":
        if params.get("dns_server"):
            cmd.append(f"@{params['dns_server']}")
        cmd.append(params["target"])
        cmd.append(params.get("record_type", "ANY"))
    
    elif tool_id == "host":
        cmd.append(params["target"])
    
    elif tool_id == "nslookup":
        cmd.append(params["target"])
        if params.get("dns_server"):
            cmd.append(params["dns_server"])
    
    elif tool_id == "theHarvester":
        cmd.extend(["-d", params["domain"]])
        cmd.extend(["-b", params.get("source", "all")])
        cmd.extend(["-l", str(params.get("limit", 100))])
    
    elif tool_id == "nmap_quick":
        scan_type = params.get("scan_type", "quick")
        if scan_type == "quick":
            cmd.extend(["-sV", "-T4", "--top-ports", "1000"])
        elif scan_type == "full":
            cmd.extend(["-sV", "-sC", "-p-"])
        elif scan_type == "stealth":
            cmd.extend(["-sS", "-T2"])
        elif scan_type == "udp":
            cmd.extend(["-sU", "--top-ports", "100"])
        elif scan_type == "version":
            cmd.extend(["-sV", "-sC"])
        cmd.append(params["target"])
    
    elif tool_id == "nmap_vuln":
        script_cat = params.get("script_category", "vuln")
        cmd.extend(["--script", script_cat])
        cmd.append(params["target"])
    
    elif tool_id == "masscan":
        cmd.extend(["-p", params.get("ports", "1-1000")])
        cmd.extend(["--rate", str(params.get("rate", 1000))])
        cmd.append(params["target"])
    
    elif tool_id == "netcat":
        mode = params.get("mode", "connect")
        if mode == "connect":
            cmd.extend(["-zv", params["target"], str(params["port"])])
        elif mode == "listen":
            cmd.extend(["-lvp", str(params["port"])])
        elif mode == "scan":
            cmd.extend(["-zv", params["target"], "1-1000"])
    
    elif tool_id == "tcpdump":
        cmd.extend(["-i", params.get("interface", "any")])
        cmd.extend(["-c", str(params.get("count", 100))])
        if params.get("filter"):
            cmd.append(params["filter"])
    
    elif tool_id == "traceroute":
        cmd.extend(["-m", str(params.get("max_hops", 30))])
        cmd.append(params["target"])
    
    elif tool_id == "ping":
        cmd.extend(["-c", str(params.get("count", 4))])
        cmd.append(params["target"])
    
    elif tool_id == "curl":
        cmd.extend(["-X", params.get("method", "GET")])
        if params.get("follow_redirects", True):
            cmd.append("-L")
        cmd.append("-v")
        if params.get("headers"):
            cmd.extend(["-H", params["headers"]])
        if params.get("data"):
            cmd.extend(["-d", params["data"]])
        cmd.append(params["url"])
    
    elif tool_id == "wget":
        cmd.append("--no-check-certificate")
        if params.get("recursive"):
            cmd.extend(["-r", "-l", str(params.get("depth", 2))])
        cmd.extend(["-O", "-"])  # Output to stdout for capture
        cmd.append(params["url"])
    
    elif tool_id == "nikto":
        cmd.extend(["-h", params["target"]])
        if params.get("ssl", True):
            cmd.append("-ssl")
        if params.get("tuning"):
            cmd.extend(["-Tuning", params["tuning"]])
    
    elif tool_id == "whatweb":
        cmd.extend(["-a", params.get("aggression", "1")])
        cmd.append(params["target"])
    
    elif tool_id == "gobuster":
        cmd.append(params.get("mode", "dir"))
        cmd.extend(["-u", params["target"]])
        wordlist = WORDLIST_PATHS.get(params.get("wordlist", "common"), WORDLIST_PATHS["common"])
        cmd.extend(["-w", wordlist])
        if params.get("extensions"):
            cmd.extend(["-x", params["extensions"]])
    
    elif tool_id == "wpscan":
        cmd.extend(["--url", params["target"]])
        cmd.extend(["--enumerate", params.get("enumerate", "vp")])
        cmd.append("--no-update")
    
    elif tool_id == "enum4linux":
        if params.get("all", True):
            cmd.append("-a")
        cmd.append(params["target"])
    
    elif tool_id == "smbclient":
        cmd.extend(["-L", params["target"]])
        if params.get("username"):
            cmd.extend(["-U", params["username"]])
        else:
            cmd.append("-N")  # No password
    
    elif tool_id == "ldapsearch":
        cmd.extend(["-x", "-H", params["host"]])
        cmd.extend(["-b", params["base_dn"]])
        cmd.append(params.get("filter", "(objectClass=*)"))
    
    elif tool_id == "hashid":
        cmd.append(params["hash"])
    
    elif tool_id == "john":
        format_type = params.get("format", "auto")
        if format_type != "auto":
            cmd.extend(["--format=" + format_type])
        wordlist = WORDLIST_PATHS.get(params.get("wordlist", "rockyou"), WORDLIST_PATHS["rockyou"])
        cmd.extend(["--wordlist=" + wordlist])
        cmd.append(params["hash_file"])
    
    elif tool_id == "hashcat":
        cmd.extend(["-m", params["hash_type"]])
        cmd.extend(["-a", params.get("attack_mode", "0")])
        cmd.append(params["hash_file"])
        wordlist = WORDLIST_PATHS.get("rockyou", WORDLIST_PATHS["rockyou"])
        cmd.append(wordlist)
    
    elif tool_id == "hydra":
        protocol = params["protocol"]
        cmd.extend(["-l", params["username"]])
        wordlist = WORDLIST_PATHS.get(params.get("password_list", "rockyou"), WORDLIST_PATHS["rockyou"])
        cmd.extend(["-P", wordlist])
        cmd.append(params["target"])
        cmd.append(protocol)
    
    elif tool_id == "yara_scan":
        if params.get("recursive", True):
            cmd.append("-r")
        rules_path = YARA_RULES_PATHS.get(params["rules"], YARA_RULES_PATHS["malware"])
        cmd.append(rules_path)
        cmd.append(params["target_path"])
    
    elif tool_id == "strings":
        cmd.extend(["-n", str(params.get("min_length", 4))])
        cmd.extend(["-e", params.get("encoding", "s")])
        cmd.append(params["file"])
    
    elif tool_id == "file":
        cmd.append(params["file"])
    
    elif tool_id == "exiftool":
        cmd.append(params["file"])
    
    elif tool_id == "binwalk":
        if params.get("extract"):
            cmd.append("-e")
        cmd.append(params["file"])
    
    elif tool_id == "volatility":
        cmd.extend(["-f", params["memory_dump"]])
        cmd.append(params["plugin"])
    
    elif tool_id == "sherlock":
        cmd.append(params["username"])
        cmd.extend(["--timeout", str(params.get("timeout", 10))])
    
    elif tool_id == "amass":
        cmd.append(params.get("mode", "enum"))
        cmd.extend(["-d", params["domain"]])
        if params.get("passive", True):
            cmd.append("-passive")
    
    elif tool_id == "openssl":
        operation = params["operation"]
        if operation == "s_client":
            cmd.extend(["s_client", "-connect", params["target"]])
        elif operation == "x509":
            cmd.extend(["x509", "-in", params["target"], "-text", "-noout"])
    
    elif tool_id == "sslyze":
        if params.get("certinfo", True):
            cmd.append("--certinfo")
        cmd.append(params["target"])
    
    return cmd


# ============================================================================
# EJECUCIÓN DE HERRAMIENTAS
# ============================================================================

async def execute_tool(
    tool_id: str,
    params: Dict[str, Any],
    output_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Ejecuta una herramienta y retorna los resultados
    
    Args:
        tool_id: ID de la herramienta
        params: Parámetros de ejecución
        output_callback: Función para enviar output en tiempo real
    
    Returns:
        Diccionario con resultados de la ejecución
    """
    tool = get_tool_by_id(tool_id)
    if not tool:
        return {
            "success": False,
            "error": f"Tool '{tool_id}' not found",
            "output": ""
        }
    
    # Verificar disponibilidad
    status = check_tool_availability(tool_id)
    if status == ToolStatus.NOT_INSTALLED:
        return {
            "success": False,
            "error": f"Tool '{tool.command}' is not installed on this system",
            "output": "",
            "suggestion": f"Install with: sudo apt install {tool.command}"
        }
    
    if status == ToolStatus.REQUIRES_ROOT:
        return {
            "success": False,
            "error": f"Tool '{tool.name}' requires root privileges",
            "output": "",
            "suggestion": "Run the MCP service with sudo or configure proper permissions"
        }
    
    try:
        # Construir comando
        cmd = build_command(tool_id, params)
        logger.info(f"🔧 Executing: {' '.join(cmd)}")
        
        if output_callback:
            output_callback(f"$ {' '.join(cmd)}\n")
        
        # Ejecutar proceso
        start_time = datetime.now()
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Leer output en tiempo real si hay callback
        output_lines = []
        error_lines = []
        
        if output_callback and process.stdout:
            async for line in process.stdout:
                decoded = line.decode('utf-8', errors='replace')
                output_lines.append(decoded)
                output_callback(decoded)
        
        # Esperar con timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=tool.timeout_seconds
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": f"Tool execution timed out after {tool.timeout_seconds} seconds",
                "output": "".join(output_lines),
                "command": " ".join(cmd)
            }
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Combinar output
        if not output_lines:
            output = stdout.decode('utf-8', errors='replace')
        else:
            output = "".join(output_lines)
        
        error_output = stderr.decode('utf-8', errors='replace')
        
        # Enviar cualquier error restante
        if output_callback and error_output:
            output_callback(f"\n[STDERR]\n{error_output}")
        
        return {
            "success": process.returncode == 0,
            "return_code": process.returncode,
            "output": output,
            "stderr": error_output,
            "command": " ".join(cmd),
            "duration_seconds": duration,
            "tool": tool.name,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error executing tool {tool_id}")
        return {
            "success": False,
            "error": str(e),
            "output": "",
            "tool": tool.name if tool else tool_id
        }


async def execute_tool_with_streaming(
    tool_id: str,
    params: Dict[str, Any],
    websocket_manager,
    session_id: str
) -> Dict[str, Any]:
    """
    Ejecuta herramienta con streaming de output via WebSocket
    """
    async def send_output(line: str):
        await websocket_manager.broadcast(
            f"tool-execution-{session_id}",
            {
                "type": "tool_output",
                "tool_id": tool_id,
                "line": line,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Notificar inicio
    await websocket_manager.broadcast(
        f"tool-execution-{session_id}",
        {
            "type": "tool_started",
            "tool_id": tool_id,
            "params": params,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    result = await execute_tool(tool_id, params, send_output)
    
    # Notificar fin
    await websocket_manager.broadcast(
        f"tool-execution-{session_id}",
        {
            "type": "tool_completed",
            "tool_id": tool_id,
            "success": result.get("success", False),
            "duration": result.get("duration_seconds", 0),
            "timestamp": datetime.now().isoformat()
        }
    )
    
    return result
