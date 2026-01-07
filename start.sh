#!/usr/bin/env bash
# ============================================================================
# MCP Kali Forensics - Start v4.5
# Inicia todos los servicios: API (FastAPI) + Frontend (React/Vite)
# 
# Uso:
#   ./start.sh              # Inicia todos los servicios (mata procesos en uso)
#   ./start.sh --bg         # Inicia en background
#   ./start.sh --stop       # Detiene todos los servicios
#   ./start.sh --status     # Muestra estado de servicios
# ============================================================================

set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${ROOT}/logs"
BACKEND_PORT="${BACKEND_PORT:-9000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

mkdir -p "${LOG_DIR}"

# Colores
info()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
ok()    { printf "\033[1;32m[ OK ]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()   { printf "\033[1;31m[ERR]\033[0m %s\n" "$*"; }

# Banner
show_banner() {
    echo ""
    printf "\033[1;36m"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║     MCP Kali Forensics v4.5 - Forensic Analysis Platform           ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    printf "\033[0m"
    echo ""
}

# Mata procesos en un puerto específico de forma agresiva
kill_port() {
    local port=$1
    local name=$2
    
    # Método 1: fuser (usuario normal)
    if command -v fuser &>/dev/null; then
        fuser -k "${port}/tcp" 2>/dev/null && info "Liberado puerto ${port} (${name})"
    fi
    
    # Método 2: lsof + kill
    local pids=$(lsof -ti ":${port}" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null && info "Matado proceso en puerto ${port}"
    fi
    
    # Método 3: ss + kill (para sistemas sin lsof)
    if command -v ss &>/dev/null; then
        local pid=$(ss -tlnp "sport = :${port}" 2>/dev/null | grep -oP 'pid=\K\d+' | head -1)
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
    fi
    
    # Verificar si el puerto sigue ocupado y advertir
    sleep 0.5
    if ss -tln "sport = :${port}" 2>/dev/null | grep -q ":${port}"; then
        warn "Puerto ${port} aún ocupado (posiblemente por proceso de root)"
        warn "Ejecuta: sudo fuser -k ${port}/tcp"
    fi
}

# Mata todos los procesos relacionados con los servicios
kill_all_services() {
    info "Liberando puertos y matando procesos..."
    
    # Matar por nombre de proceso
    pkill -9 -f "uvicorn api.main" 2>/dev/null || true
    pkill -9 -f "uvicorn.*${BACKEND_PORT}" 2>/dev/null || true
    pkill -9 -f "vite.*${FRONTEND_PORT}" 2>/dev/null || true
    pkill -9 -f "node.*vite" 2>/dev/null || true
    
    # Matar por archivo PID
    [ -f "${LOG_DIR}/backend.pid" ] && {
        kill -9 "$(cat "${LOG_DIR}/backend.pid")" 2>/dev/null
        rm -f "${LOG_DIR}/backend.pid"
    }
    [ -f "${LOG_DIR}/frontend.pid" ] && {
        kill -9 "$(cat "${LOG_DIR}/frontend.pid")" 2>/dev/null
        rm -f "${LOG_DIR}/frontend.pid"
    }
    
    # Matar por puerto
    kill_port "${BACKEND_PORT}" "Backend API"
    kill_port "${FRONTEND_PORT}" "Frontend React"
    
    sleep 1
    ok "Puertos liberados"
}

# Detener servicios
stop_services() {
    show_banner
    kill_all_services
    ok "Todos los servicios detenidos"
}

# Mostrar estado
show_status() {
    show_banner
    echo "Estado de servicios:"
    echo ""
    
    if curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        ok "Backend API (puerto ${BACKEND_PORT}): RUNNING"
        curl -sf "http://localhost:${BACKEND_PORT}/health" 2>/dev/null | python3 -m json.tool 2>/dev/null || true
    else
        warn "Backend API (puerto ${BACKEND_PORT}): STOPPED"
    fi
    
    if curl -sf -o /dev/null "http://localhost:${FRONTEND_PORT}" 2>/dev/null; then
        ok "Frontend React (puerto ${FRONTEND_PORT}): RUNNING"
    else
        warn "Frontend React (puerto ${FRONTEND_PORT}): STOPPED"
    fi
    
    echo ""
    echo "Procesos:"
    ps aux | grep -E "(uvicorn|vite|node)" | grep -v grep | head -5 || echo "  Ninguno activo"
}

# Modo dev (interactivo con npm run dev)
start_dev_mode() {
    show_banner
    info "Modo desarrollo (interactivo)"
    
    kill_all_services
    
    cd "${ROOT}"
    
    # Activar entorno virtual si existe
    if [ -d "venv" ]; then
        info "Activando entorno virtual..."
        source venv/bin/activate
        # Instalar dependencias si es necesario
        if [ -f "requirements.txt" ]; then
             pip install --quiet -r requirements.txt 2>/dev/null || true
        fi
    fi

    [ ! -d "node_modules" ] && npm install --silent
    [ ! -d "node_modules/concurrently" ] && npm install concurrently --save-dev --silent
    
    echo ""
    echo "  🔧 API:      http://localhost:${BACKEND_PORT}"
    echo "  📚 Docs:     http://localhost:${BACKEND_PORT}/docs"
    echo "  🎨 Frontend: http://localhost:${FRONTEND_PORT}"
    echo ""
    echo "  Presiona Ctrl+C para detener"
    echo ""
    
    npm run dev
}

# Modo background
start_background_mode() {
    show_banner
    info "Modo background"
    
    kill_all_services
    
    cd "${ROOT}"
    
    [ ! -d "venv" ] && python3 -m venv venv
    source venv/bin/activate
    [ -f "requirements.txt" ] && pip install --quiet -r requirements.txt 2>/dev/null
    
    info "Iniciando Backend API..."
    nohup python -m uvicorn api.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload > "${LOG_DIR}/backend.log" 2>&1 &
    echo $! > "${LOG_DIR}/backend.pid"
    
    local attempts=0
    while [ $attempts -lt 10 ]; do
        curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1 && break
        sleep 1
        attempts=$((attempts + 1))
    done
    [ $attempts -lt 10 ] && ok "Backend OK" || warn "Backend tardó en responder"
    
    info "Iniciando Frontend React..."
    cd "${ROOT}/frontend-react"
    [ ! -d "node_modules" ] && npm install --silent
    nohup npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" > "${LOG_DIR}/frontend.log" 2>&1 &
    echo $! > "${LOG_DIR}/frontend.pid"
    
    attempts=0
    while [ $attempts -lt 15 ]; do
        curl -sf -o /dev/null "http://localhost:${FRONTEND_PORT}" 2>/dev/null && break
        sleep 1
        attempts=$((attempts + 1))
    done
    [ $attempts -lt 15 ] && ok "Frontend OK" || warn "Frontend compilando..."
    
    cd "${ROOT}"
    
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  ✓ Servicios iniciados"
    echo ""
    echo "  🔧 API:      http://localhost:${BACKEND_PORT}"
    echo "  📚 Docs:     http://localhost:${BACKEND_PORT}/docs"
    echo "  🎨 Frontend: http://localhost:${FRONTEND_PORT}"
    echo ""
    echo "  📋 Logs: tail -f logs/backend.log"
    echo "  🛑 Detener: ./start.sh --stop"
    echo "════════════════════════════════════════════════════════════════"
}

case "${1:-}" in
    --stop|-s) stop_services ;;
    --bg|-b|--background) start_background_mode ;;
    --status|--st) show_status ;;
    --help|-h)
        echo "Uso: ./start.sh [opción]"
        echo "  (sin args)  Modo desarrollo interactivo"
        echo "  --bg        Inicia en background"
        echo "  --stop      Detiene servicios"
        echo "  --status    Muestra estado"
        ;;
    *) start_dev_mode ;;
esac
