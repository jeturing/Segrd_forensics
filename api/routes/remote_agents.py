"""
🔗 Remote Agent Manager v4.5 - Real-time Remote Command Execution
Sistema de agentes remotos con descarga de scripts y WebSocket bidireccional

Features:
- Generación de scripts para Windows (PowerShell) y Linux (Bash)
- WebSocket bidireccional para comandos en tiempo real
- Token de autenticación único por sesión
- Heartbeat y reconexión automática
- Registro de comandos ejecutados por caso
"""

import asyncio
import uuid
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState

from api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/remote-agents", tags=["Remote Agents"])


# ============================================================================
# MODELOS
# ============================================================================

class AgentToken(BaseModel):
    """Token de agente remoto"""
    token: str
    agent_name: str
    os_type: str
    case_id: str
    created_at: datetime
    expires_at: datetime
    connected: bool = False
    last_heartbeat: Optional[datetime] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None


class GenerateAgentRequest(BaseModel):
    """Solicitud para generar script de agente"""
    agent_name: str = Field(..., min_length=1, max_length=100)
    os_type: str = Field(..., pattern="^(windows|linux|mac)$")
    case_id: str = Field(..., min_length=1)
    expires_hours: int = Field(default=24, ge=1, le=168)  # Max 1 semana


class CommandToAgent(BaseModel):
    """Comando a enviar al agente"""
    command: str
    timeout: int = Field(default=300, ge=5, le=3600)
    run_as_admin: bool = False
    save_output: bool = True


class AgentCommandResult(BaseModel):
    """Resultado de comando de agente"""
    command_id: str
    command: str
    output: str
    error: Optional[str] = None
    return_code: int
    execution_time: float
    timestamp: str


# ============================================================================
# ALMACENAMIENTO EN MEMORIA (Producción: usar Redis/DB)
# ============================================================================

# Tokens activos: token -> AgentToken
active_tokens: Dict[str, AgentToken] = {}

# Conexiones WebSocket activas: token -> WebSocket
agent_connections: Dict[str, WebSocket] = {}

# Cola de comandos pendientes: token -> [commands]
pending_commands: Dict[str, List[Dict]] = {}

# Resultados de comandos: command_id -> result
command_results: Dict[str, Dict] = {}

# Historial por caso: case_id -> [results]
case_command_history: Dict[str, List[Dict]] = {}


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def generate_token() -> str:
    """Generar token único de 32 caracteres"""
    return secrets.token_urlsafe(24)


def get_server_url(request: Request) -> str:
    """Obtener URL del servidor desde la request"""
    # Usar X-Forwarded headers si están disponibles (detrás de proxy)
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:9000"))
    return f"{proto}://{host}"


def cleanup_expired_tokens():
    """Limpiar tokens expirados"""
    now = datetime.utcnow()
    expired = [token for token, data in active_tokens.items() if data.expires_at < now]
    for token in expired:
        del active_tokens[token]
        if token in pending_commands:
            del pending_commands[token]
        logger.info(f"🧹 Token expirado limpiado: {token[:8]}...")


# ============================================================================
# GENERADORES DE SCRIPTS
# ============================================================================

def generate_powershell_agent(token: str, server_url: str, agent_name: str) -> str:
    """Generar script PowerShell para Windows"""
    return f'''#Requires -Version 5.1
<#
.SYNOPSIS
    MCP Forensics Remote Agent v1.0 - Windows
.DESCRIPTION
    Agente remoto para ejecución de comandos forenses en tiempo real
    Token: {token[:8]}... | Agent: {agent_name}
.NOTES
    ⚠️ Este script se conecta al servidor MCP para recibir comandos
    Solo ejecutar en equipos autorizados para investigación
#>

$ErrorActionPreference = "Continue"
$script:ServerUrl = "{server_url}"
$script:WsUrl = "{server_url.replace('http', 'ws')}/api/remote-agents/ws/{token}"
$script:Token = "{token}"
$script:AgentName = "{agent_name}"
$script:Connected = $false
$script:ReconnectDelay = 5

function Write-Log {{
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {{
        "ERROR" {{ "Red" }}
        "WARN"  {{ "Yellow" }}
        "SUCCESS" {{ "Green" }}
        default {{ "White" }}
    }}
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}}

function Send-Heartbeat {{
    param($WebSocket)
    $heartbeat = @{{
        type = "heartbeat"
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        pid = $PID
    }} | ConvertTo-Json -Compress
    
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($heartbeat)
    $segment = New-Object System.ArraySegment[byte] -ArgumentList (,$bytes)
    $WebSocket.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).Wait()
}}

function Execute-Command {{
    param($CommandData)
    
    $commandId = $CommandData.command_id
    $command = $CommandData.command
    $timeout = $CommandData.timeout
    $runAsAdmin = $CommandData.run_as_admin
    
    Write-Log "⚡ Ejecutando: $($command.Substring(0, [Math]::Min(50, $command.Length)))..."
    
    $startTime = Get-Date
    $output = ""
    $error = ""
    $returnCode = 0
    
    try {{
        if ($runAsAdmin -and -not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {{
            $error = "Se requieren privilegios de administrador"
            $returnCode = 1
        }} else {{
            # Ejecutar comando con timeout
            $job = Start-Job -ScriptBlock {{ param($cmd) Invoke-Expression $cmd }} -ArgumentList $command
            $completed = Wait-Job -Job $job -Timeout $timeout
            
            if ($completed) {{
                $output = Receive-Job -Job $job | Out-String
                $returnCode = 0
            }} else {{
                Stop-Job -Job $job
                $error = "Comando excedió timeout de $timeout segundos"
                $returnCode = 124
            }}
            Remove-Job -Job $job -Force
        }}
    }} catch {{
        $error = $_.Exception.Message
        $returnCode = 1
    }}
    
    $executionTime = ((Get-Date) - $startTime).TotalSeconds
    
    return @{{
        type = "command_result"
        command_id = $commandId
        command = $command
        output = $output
        error = $error
        return_code = $returnCode
        execution_time = [math]::Round($executionTime, 3)
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }}
}}

function Connect-ToServer {{
    while ($true) {{
        try {{
            Write-Log "🔌 Conectando a $script:WsUrl..." "INFO"
            
            $ws = New-Object System.Net.WebSockets.ClientWebSocket
            $ws.Options.SetRequestHeader("X-Agent-Token", $script:Token)
            $ws.Options.SetRequestHeader("X-Agent-Name", $script:AgentName)
            
            $uri = New-Object System.Uri($script:WsUrl)
            $ws.ConnectAsync($uri, [System.Threading.CancellationToken]::None).Wait()
            
            $script:Connected = $true
            $script:ReconnectDelay = 5
            Write-Log "✅ Conectado al servidor MCP" "SUCCESS"
            
            # Enviar registro inicial
            $register = @{{
                type = "register"
                agent_name = $script:AgentName
                hostname = $env:COMPUTERNAME
                os_type = "windows"
                os_version = [System.Environment]::OSVersion.VersionString
                username = $env:USERNAME
                pid = $PID
                timestamp = (Get-Date).ToUniversalTime().ToString("o")
            }} | ConvertTo-Json -Compress
            
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($register)
            $segment = New-Object System.ArraySegment[byte] -ArgumentList (,$bytes)
            $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).Wait()
            
            # Loop de recepción
            $buffer = New-Object byte[] 65536
            $heartbeatTimer = [System.Diagnostics.Stopwatch]::StartNew()
            
            while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {{
                # Enviar heartbeat cada 30 segundos
                if ($heartbeatTimer.Elapsed.TotalSeconds -ge 30) {{
                    Send-Heartbeat -WebSocket $ws
                    $heartbeatTimer.Restart()
                }}
                
                # Recibir mensajes con timeout corto para no bloquear heartbeat
                $segment = New-Object System.ArraySegment[byte] -ArgumentList (,$buffer)
                $cts = New-Object System.Threading.CancellationTokenSource(1000)
                
                try {{
                    $result = $ws.ReceiveAsync($segment, $cts.Token).GetAwaiter().GetResult()
                    
                    if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {{
                        Write-Log "🔌 Servidor cerró la conexión" "WARN"
                        break
                    }}
                    
                    $message = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $result.Count)
                    $data = $message | ConvertFrom-Json
                    
                    if ($data.type -eq "command") {{
                        Write-Log "📥 Comando recibido: $($data.command_id)" "INFO"
                        
                        $cmdResult = Execute-Command -CommandData $data
                        $resultJson = $cmdResult | ConvertTo-Json -Compress -Depth 10
                        
                        $resultBytes = [System.Text.Encoding]::UTF8.GetBytes($resultJson)
                        $resultSegment = New-Object System.ArraySegment[byte] -ArgumentList (,$resultBytes)
                        $ws.SendAsync($resultSegment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).Wait()
                        
                        Write-Log "📤 Resultado enviado" "SUCCESS"
                    }} elseif ($data.type -eq "ping") {{
                        # Responder pong
                        $pong = @{{ type = "pong"; timestamp = (Get-Date).ToUniversalTime().ToString("o") }} | ConvertTo-Json -Compress
                        $pongBytes = [System.Text.Encoding]::UTF8.GetBytes($pong)
                        $pongSegment = New-Object System.ArraySegment[byte] -ArgumentList (,$pongBytes)
                        $ws.SendAsync($pongSegment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).Wait()
                    }}
                }} catch [System.OperationCanceledException] {{
                    # Timeout esperado, continuar loop
                }}
            }}
            
        }} catch {{
            Write-Log "❌ Error de conexión: $($_.Exception.Message)" "ERROR"
        }} finally {{
            $script:Connected = $false
            if ($ws -and $ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {{
                $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Disconnecting", [System.Threading.CancellationToken]::None).Wait()
            }}
        }}
        
        Write-Log "🔄 Reconectando en $script:ReconnectDelay segundos..." "WARN"
        Start-Sleep -Seconds $script:ReconnectDelay
        $script:ReconnectDelay = [Math]::Min($script:ReconnectDelay * 2, 60)
    }}
}}

# Banner
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       MCP FORENSICS REMOTE AGENT v1.0 - WINDOWS          ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Agent: $($script:AgentName.PadRight(47))  ║" -ForegroundColor Green
Write-Host "║  Server: $($script:ServerUrl.PadRight(46))  ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Log "🚀 Iniciando agente remoto..." "INFO"
Write-Log "⚠️  Presiona Ctrl+C para detener" "WARN"
Write-Host ""

# Iniciar conexión
Connect-ToServer
'''


def generate_bash_agent(token: str, server_url: str, agent_name: str) -> str:
    """Generar script Bash para Linux/Mac"""
    return f'''#!/bin/bash
# MCP Forensics Remote Agent v1.0 - Linux/Mac
# Token: {token[:8]}... | Agent: {agent_name}
# ⚠️ Este script se conecta al servidor MCP para recibir comandos
# Solo ejecutar en equipos autorizados para investigación

set -e

SERVER_URL="{server_url}"
WS_URL="{server_url.replace('http', 'ws')}/api/remote-agents/ws/{token}"
TOKEN="{token}"
AGENT_NAME="{agent_name}"
RECONNECT_DELAY=5
MAX_RECONNECT_DELAY=60

# Colores
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
CYAN='\\033[0;36m'
NC='\\033[0m'

log() {{
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local color=$NC
    
    case $level in
        ERROR) color=$RED ;;
        WARN) color=$YELLOW ;;
        SUCCESS) color=$GREEN ;;
        INFO) color=$CYAN ;;
    esac
    
    echo -e "${{color}}[$timestamp] [$level] $message${{NC}}"
}}

check_dependencies() {{
    if ! command -v websocat &> /dev/null; then
        log WARN "websocat no encontrado. Intentando instalar..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y websocat || {{
                log ERROR "No se pudo instalar websocat. Instálalo manualmente:"
                echo "  cargo install websocat"
                echo "  # o descarga desde: https://github.com/vi/websocat/releases"
                exit 1
            }}
        elif command -v brew &> /dev/null; then
            brew install websocat
        else
            log ERROR "Instala websocat manualmente:"
            echo "  cargo install websocat"
            echo "  # o descarga desde: https://github.com/vi/websocat/releases"
            exit 1
        fi
    fi
    
    if ! command -v jq &> /dev/null; then
        log WARN "jq no encontrado. Intentando instalar..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        else
            log ERROR "Instala jq manualmente"
            exit 1
        fi
    fi
}}

execute_command() {{
    local command_id="$1"
    local command="$2"
    local timeout="${{3:-300}}"
    
    log INFO "⚡ Ejecutando: ${{command:0:50}}..."
    
    local start_time=$(date +%s.%N)
    local output=""
    local error=""
    local return_code=0
    
    # Ejecutar con timeout
    if output=$(timeout "$timeout" bash -c "$command" 2>&1); then
        return_code=0
    else
        return_code=$?
        if [ $return_code -eq 124 ]; then
            error="Comando excedió timeout de $timeout segundos"
        else
            error="$output"
        fi
    fi
    
    local end_time=$(date +%s.%N)
    local execution_time=$(echo "$end_time - $start_time" | bc)
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Escapar caracteres especiales para JSON
    output=$(echo "$output" | jq -Rs .)
    error=$(echo "$error" | jq -Rs .)
    
    # Construir respuesta JSON
    cat <<EOF
{{"type":"command_result","command_id":"$command_id","command":"$command","output":$output,"error":$error,"return_code":$return_code,"execution_time":$execution_time,"timestamp":"$timestamp"}}
EOF
}}

send_register() {{
    local hostname=$(hostname)
    local os_type=$(uname -s | tr '[:upper:]' '[:lower:]')
    local os_version=$(uname -r)
    local username=$(whoami)
    local pid=$$
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo '{{"type":"register","agent_name":"'"$AGENT_NAME"'","hostname":"'"$hostname"'","os_type":"'"$os_type"'","os_version":"'"$os_version"'","username":"'"$username"'","pid":'$pid',"timestamp":"'"$timestamp"'"}}'
}}

send_heartbeat() {{
    local hostname=$(hostname)
    local username=$(whoami)
    local pid=$$
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo '{{"type":"heartbeat","timestamp":"'"$timestamp"'","hostname":"'"$hostname"'","username":"'"$username"'","pid":'$pid'}}'
}}

handle_message() {{
    local message="$1"
    local msg_type=$(echo "$message" | jq -r '.type // empty')
    
    case "$msg_type" in
        command)
            local command_id=$(echo "$message" | jq -r '.command_id')
            local command=$(echo "$message" | jq -r '.command')
            local timeout=$(echo "$message" | jq -r '.timeout // 300')
            
            log INFO "📥 Comando recibido: $command_id"
            
            # Ejecutar y enviar resultado
            local result=$(execute_command "$command_id" "$command" "$timeout")
            echo "$result"
            
            log SUCCESS "📤 Resultado enviado"
            ;;
        ping)
            echo '{{"type":"pong","timestamp":"'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'"}}'
            ;;
    esac
}}

connect_to_server() {{
    while true; do
        log INFO "🔌 Conectando a $WS_URL..."
        
        # Crear pipes para comunicación bidireccional
        FIFO_IN=$(mktemp -u)
        FIFO_OUT=$(mktemp -u)
        mkfifo "$FIFO_IN" "$FIFO_OUT"
        
        trap "rm -f $FIFO_IN $FIFO_OUT" EXIT
        
        # Iniciar websocat en background
        websocat -t --ping-interval 30 --ping-timeout 60 \\
            -H "X-Agent-Token: $TOKEN" \\
            -H "X-Agent-Name: $AGENT_NAME" \\
            "$WS_URL" < "$FIFO_IN" > "$FIFO_OUT" 2>/dev/null &
        WS_PID=$!
        
        # Esperar conexión
        sleep 1
        
        if kill -0 $WS_PID 2>/dev/null; then
            log SUCCESS "✅ Conectado al servidor MCP"
            RECONNECT_DELAY=5
            
            # Enviar registro inicial
            send_register > "$FIFO_IN"
            
            # Loop de lectura
            while kill -0 $WS_PID 2>/dev/null && read -r line < "$FIFO_OUT"; do
                if [ -n "$line" ]; then
                    response=$(handle_message "$line")
                    if [ -n "$response" ]; then
                        echo "$response" > "$FIFO_IN"
                    fi
                fi
            done
            
            log WARN "🔌 Conexión cerrada"
        else
            log ERROR "❌ No se pudo conectar"
        fi
        
        # Limpiar
        kill $WS_PID 2>/dev/null || true
        rm -f "$FIFO_IN" "$FIFO_OUT"
        
        log WARN "🔄 Reconectando en $RECONNECT_DELAY segundos..."
        sleep $RECONNECT_DELAY
        RECONNECT_DELAY=$((RECONNECT_DELAY * 2))
        [ $RECONNECT_DELAY -gt $MAX_RECONNECT_DELAY ] && RECONNECT_DELAY=$MAX_RECONNECT_DELAY
    done
}}

# Banner
echo ""
echo -e "${{CYAN}}╔══════════════════════════════════════════════════════════╗${{NC}}"
echo -e "${{CYAN}}║       MCP FORENSICS REMOTE AGENT v1.0 - LINUX/MAC        ║${{NC}}"
echo -e "${{CYAN}}╠══════════════════════════════════════════════════════════╣${{NC}}"
echo -e "${{GREEN}}║  Agent: $(printf '%-47s' "$AGENT_NAME")  ║${{NC}}"
echo -e "${{YELLOW}}║  Server: $(printf '%-46s' "$SERVER_URL")  ║${{NC}}"
echo -e "${{CYAN}}╚══════════════════════════════════════════════════════════╝${{NC}}"
echo ""

log INFO "🚀 Iniciando agente remoto..."
log WARN "⚠️  Presiona Ctrl+C para detener"
echo ""

# Verificar dependencias
check_dependencies

# Trap para limpieza
trap 'log WARN "Deteniendo agente..."; exit 0' INT TERM

# Iniciar conexión
connect_to_server
'''


# ============================================================================
# ENDPOINTS HTTP
# ============================================================================

@router.post("/generate")
async def generate_agent_script(
    request: Request,
    req: GenerateAgentRequest
):
    """
    🔗 Generar script de agente remoto
    
    Genera un script descargable que se conectará a este servidor
    vía WebSocket para recibir y ejecutar comandos en tiempo real.
    
    Returns:
    - token: Token único para este agente
    - download_url: URL para descargar el script
    - websocket_url: URL del WebSocket (para referencia)
    - expires_at: Fecha/hora de expiración
    """
    cleanup_expired_tokens()
    
    token = generate_token()
    server_url = get_server_url(request)
    
    # Crear token de agente
    agent_token = AgentToken(
        token=token,
        agent_name=req.agent_name,
        os_type=req.os_type,
        case_id=req.case_id,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=req.expires_hours),
        connected=False
    )
    
    active_tokens[token] = agent_token
    pending_commands[token] = []
    
    logger.info(f"🔗 Token generado para agente '{req.agent_name}' (caso: {req.case_id})")
    
    return {
        "token": token,
        "agent_name": req.agent_name,
        "os_type": req.os_type,
        "case_id": req.case_id,
        "download_url": f"{server_url}/api/remote-agents/download/{token}",
        "websocket_url": f"{server_url.replace('http', 'ws')}/api/remote-agents/ws/{token}",
        "expires_at": agent_token.expires_at.isoformat() + "Z",
        "instructions": {
            "windows": f"powershell -ExecutionPolicy Bypass -File .\\agent_{req.agent_name}.ps1",
            "linux": f"chmod +x agent_{req.agent_name}.sh && ./agent_{req.agent_name}.sh",
            "mac": f"chmod +x agent_{req.agent_name}.sh && ./agent_{req.agent_name}.sh"
        }
    }


@router.get("/download/{token}")
async def download_agent_script(
    request: Request,
    token: str
):
    """
    📥 Descargar script de agente
    
    Devuelve el script PowerShell o Bash según el OS configurado
    """
    cleanup_expired_tokens()
    
    if token not in active_tokens:
        raise HTTPException(status_code=404, detail="Token no válido o expirado")
    
    agent_token = active_tokens[token]
    server_url = get_server_url(request)
    
    if agent_token.os_type == "windows":
        script = generate_powershell_agent(token, server_url, agent_token.agent_name)
        filename = f"mcp_agent_{agent_token.agent_name}.ps1"
        media_type = "application/x-powershell"
    else:
        script = generate_bash_agent(token, server_url, agent_token.agent_name)
        filename = f"mcp_agent_{agent_token.agent_name}.sh"
        media_type = "application/x-sh"
    
    logger.info(f"📥 Script descargado para agente '{agent_token.agent_name}'")
    
    return PlainTextResponse(
        content=script,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/tokens")
async def list_agent_tokens(
    case_id: Optional[str] = None,
    only_connected: bool = False
):
    """
    📋 Listar tokens de agentes activos
    """
    cleanup_expired_tokens()
    
    result = []
    for token, data in active_tokens.items():
        if case_id and data.case_id != case_id:
            continue
        if only_connected and not data.connected:
            continue
        
        result.append({
            "token": token[:8] + "...",  # Solo mostrar prefijo
            "agent_name": data.agent_name,
            "os_type": data.os_type,
            "case_id": data.case_id,
            "connected": data.connected,
            "created_at": data.created_at.isoformat() + "Z",
            "expires_at": data.expires_at.isoformat() + "Z",
            "last_heartbeat": data.last_heartbeat.isoformat() + "Z" if data.last_heartbeat else None,
            "ip_address": data.ip_address,
            "hostname": data.hostname
        })
    
    return {
        "total": len(result),
        "tokens": result
    }


@router.delete("/tokens/{token}")
async def revoke_token(token: str):
    """
    🗑️ Revocar token de agente
    """
    if token not in active_tokens:
        raise HTTPException(status_code=404, detail="Token no encontrado")
    
    agent_data = active_tokens[token]
    
    # Cerrar conexión WebSocket si existe
    if token in agent_connections:
        ws = agent_connections[token]
        try:
            await ws.close(code=1000, reason="Token revoked")
        except:
            pass
        del agent_connections[token]
    
    del active_tokens[token]
    if token in pending_commands:
        del pending_commands[token]
    
    logger.info(f"🗑️ Token revocado para agente '{agent_data.agent_name}'")
    
    return {"status": "revoked", "agent_name": agent_data.agent_name}


@router.post("/send-command/{token}")
async def send_command_to_agent(
    token: str,
    cmd: CommandToAgent
):
    """
    📤 Enviar comando a agente remoto
    
    El comando se enviará por WebSocket al agente conectado.
    Si el agente no está conectado, el comando se encola.
    """
    if token not in active_tokens:
        raise HTTPException(status_code=404, detail="Token no válido o expirado")
    
    agent_data = active_tokens[token]
    command_id = f"CMD-{uuid.uuid4().hex[:8].upper()}"
    
    command_data = {
        "type": "command",
        "command_id": command_id,
        "command": cmd.command,
        "timeout": cmd.timeout,
        "run_as_admin": cmd.run_as_admin,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Inicializar resultado
    command_results[command_id] = {
        "command_id": command_id,
        "command": cmd.command,
        "status": "pending",
        "agent_name": agent_data.agent_name,
        "case_id": agent_data.case_id,
        "sent_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Enviar si está conectado
    if token in agent_connections:
        ws = agent_connections[token]
        if ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_json(command_data)
                command_results[command_id]["status"] = "sent"
                logger.info(f"📤 Comando {command_id} enviado a '{agent_data.agent_name}'")
            except Exception as e:
                command_results[command_id]["status"] = "failed"
                command_results[command_id]["error"] = str(e)
                logger.error(f"❌ Error enviando comando: {e}")
    else:
        # Encolar para cuando se conecte
        pending_commands[token].append(command_data)
        command_results[command_id]["status"] = "queued"
        logger.info(f"📋 Comando {command_id} encolado para '{agent_data.agent_name}'")
    
    return {
        "command_id": command_id,
        "status": command_results[command_id]["status"],
        "agent_name": agent_data.agent_name,
        "agent_connected": token in agent_connections
    }


@router.get("/command-result/{command_id}")
async def get_command_result(command_id: str):
    """
    📊 Obtener resultado de un comando
    """
    if command_id not in command_results:
        raise HTTPException(status_code=404, detail="Comando no encontrado")
    
    return command_results[command_id]


@router.get("/history/{case_id}")
async def get_case_command_history(
    case_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """
    📜 Obtener historial de comandos por caso
    """
    history = case_command_history.get(case_id, [])
    
    return {
        "case_id": case_id,
        "total": len(history),
        "commands": sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@router.websocket("/ws/{token}")
async def websocket_agent(
    websocket: WebSocket,
    token: str
):
    """
    🔌 WebSocket para comunicación bidireccional con agente
    
    Protocol:
    - Agent -> Server: register, heartbeat, command_result, pong
    - Server -> Agent: command, ping
    """
    # Validar token
    if token not in active_tokens:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    agent_data = active_tokens[token]
    
    # Verificar expiración
    if datetime.utcnow() > agent_data.expires_at:
        await websocket.close(code=4002, reason="Token expired")
        return
    
    await websocket.accept()
    agent_connections[token] = websocket
    agent_data.connected = True
    agent_data.ip_address = websocket.client.host if websocket.client else None
    
    logger.info(f"🔌 Agente '{agent_data.agent_name}' conectado desde {agent_data.ip_address}")
    
    # Enviar mensaje de bienvenida
    await websocket.send_json({
        "type": "connected",
        "message": f"Bienvenido {agent_data.agent_name}",
        "server_time": datetime.utcnow().isoformat() + "Z"
    })
    
    # Enviar comandos pendientes
    if pending_commands.get(token):
        for cmd in pending_commands[token]:
            await websocket.send_json(cmd)
            logger.info(f"📤 Comando pendiente enviado: {cmd['command_id']}")
        pending_commands[token] = []
    
    # Ping task
    async def send_pings():
        while True:
            await asyncio.sleep(30)
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    })
                except:
                    break
            else:
                break
    
    ping_task = asyncio.create_task(send_pings())
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "register":
                agent_data.hostname = data.get("hostname")
                logger.info(f"📝 Agente registrado: {data}")
                
            elif msg_type == "heartbeat":
                agent_data.last_heartbeat = datetime.utcnow()
                
            elif msg_type == "command_result":
                command_id = data.get("command_id")
                if command_id in command_results:
                    command_results[command_id].update({
                        "status": "completed",
                        "output": data.get("output", ""),
                        "error": data.get("error"),
                        "return_code": data.get("return_code", 0),
                        "execution_time": data.get("execution_time", 0),
                        "completed_at": datetime.utcnow().isoformat() + "Z"
                    })
                    
                    # Guardar en historial del caso
                    if agent_data.case_id not in case_command_history:
                        case_command_history[agent_data.case_id] = []
                    case_command_history[agent_data.case_id].append(command_results[command_id])
                    
                    logger.info(f"✅ Resultado recibido: {command_id} (rc={data.get('return_code')})")
                
            elif msg_type == "pong":
                pass  # Heartbeat response
                
    except WebSocketDisconnect:
        logger.info(f"🔌 Agente '{agent_data.agent_name}' desconectado")
    except Exception as e:
        logger.error(f"❌ Error WebSocket: {e}")
    finally:
        ping_task.cancel()
        agent_data.connected = False
        if token in agent_connections:
            del agent_connections[token]


# ============================================================================
# STATUS ENDPOINT
# ============================================================================

@router.get("/status")
async def get_remote_agents_status():
    """
    📊 Estado general del sistema de agentes remotos
    """
    cleanup_expired_tokens()
    
    connected_count = sum(1 for t in active_tokens.values() if t.connected)
    
    return {
        "total_tokens": len(active_tokens),
        "connected_agents": connected_count,
        "pending_commands": sum(len(cmds) for cmds in pending_commands.values()),
        "command_results_cached": len(command_results),
        "cases_with_history": len(case_command_history)
    }
