#!/bin/bash
# ============================================================================
# MCP Kali Forensics - Instalador Completo v4.3
# Instala: Tools forenses + Dependencias Python + Dependencias NPM
# Uso: ./scripts/install.sh
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${PROJECT_ROOT}/tools"
LOG_FILE="${PROJECT_ROOT}/logs/install.log"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Funciones helper
log()     { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"; }

# Banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║     __  __  ____ ____    _  __    _ _   _____                      ║"
    echo "║    |  \/  |/ ___|  _ \  | |/ /_ _| (_) |  ___|__  _ __ ___ _ __    ║"
    echo "║    | |\/| | |   | |_) | | ' / _\` | | | | |_ / _ \| '__/ _ \ '_ \   ║"
    echo "║    | |  | | |___|  __/  | . \ (_| | | | |  _| (_) | | |  __/ | | |  ║"
    echo "║    |_|  |_|\____|_|     |_|\_\__,_|_|_| |_|  \___/|_|  \___|_| |_|  ║"
    echo "║                                                                    ║"
    echo "║    Instalador Completo v4.3 - Local Deployment                     ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Crear directorios base
setup_directories() {
    log "📁 Creando estructura de directorios..."
    mkdir -p "$TOOLS_DIR" "$PROJECT_ROOT/logs" "$PROJECT_ROOT/evidence" \
             "$PROJECT_ROOT/forensics-evidence/cases-data" \
             "$PROJECT_ROOT/forensics-evidence/tool_outputs" \
             "$PROJECT_ROOT/config"
    success "Directorios creados"
}

# Clonar repositorio
clone_repo() {
    local url=$1 name=$2
    local target="$TOOLS_DIR/$name"
    
    if [ -d "$target" ]; then
        warning "$name ya existe"
        return 0
    fi
    
    if git clone --depth 1 "$url" "$target" 2>/dev/null; then
        success "$name clonado"
        return 0
    else
        error "No se pudo clonar $name"
        return 1
    fi
}

# ============================================================================
# INSTALACIÓN DE TOOLS FORENSES
# ============================================================================

install_tools() {
    log "🔧 Instalando herramientas forenses..."
    echo ""
    
    # Array de tools: nombre|url
    declare -a TOOLS=(
        "Sparrow|https://github.com/cisagov/Sparrow.git"
        "hawk|https://github.com/OneMoreNicolas/hawk.git"
        "o365-extractor|https://github.com/SecurityRiskAdvisors/sra-o365-extractor.git"
        "Loki|https://github.com/Neo23x0/Loki.git"
        "yara-rules|https://github.com/Yara-Rules/rules.git"
        "ROADtools|https://github.com/dirkjanm/ROADtools.git"
        "Monkey365|https://github.com/silverhack/monkey365.git"
        "Cloud_Katana|https://github.com/Azure/Cloud_Katana.git"
        "AADInternals|https://github.com/Gerenios/AADInternals.git"
        "Maester|https://github.com/maester365/maester.git"
    )
    
    local installed=0 total=${#TOOLS[@]}
    
    for tool_spec in "${TOOLS[@]}"; do
        IFS="|" read -r name url <<< "$tool_spec"
        log "  📦 $name..."
        if clone_repo "$url" "$name"; then
            ((installed++))
        fi
    done
    
    # AzureHound (binario)
    if [ ! -d "$TOOLS_DIR/azurehound" ]; then
        log "  📦 AzureHound (binario)..."
        mkdir -p "$TOOLS_DIR/azurehound"
        local az_url=$(curl -s "https://api.github.com/repos/bloodhoundad/azurehound/releases/latest" 2>/dev/null | grep browser_download_url | grep -E "linux.*amd64" | head -1 | cut -d'"' -f4)
        if [ -n "$az_url" ]; then
            curl -sL "$az_url" -o "/tmp/azurehound.zip" 2>/dev/null
            unzip -q -o "/tmp/azurehound.zip" -d "$TOOLS_DIR/azurehound" 2>/dev/null
            chmod +x "$TOOLS_DIR/azurehound/azurehound" 2>/dev/null
            rm -f /tmp/azurehound.zip
            success "AzureHound instalado"
            ((installed++))
        else
            warning "AzureHound no disponible"
        fi
    else
        warning "AzureHound ya existe"
        ((installed++))
    fi
    
    echo ""
    log "📊 Tools instalados: $installed de $((total + 1))"
}

# ============================================================================
# DEPENDENCIAS PYTHON
# ============================================================================

install_python_deps() {
    log "🐍 Configurando entorno Python..."
    
    # Seleccionar intérprete Python >= 3.10
    PYTHON_CANDIDATES=(python3.11 python3.10 python3)
    PYTHON_BIN=""
    for p in "${PYTHON_CANDIDATES[@]}"; do
        if command -v "$p" >/dev/null 2>&1; then
            ver=$($p -c 'import sys; print(sys.version_info[:2])' 2>/dev/null | tr -d '(),') || ver=""
            major=$(echo "$ver" | awk -F"," '{print $1}')
            minor=$(echo "$ver" | awk -F"," '{print $2}')
            if [ -n "$major" ] && [ "$major" -ge 3 ] && [ "$minor" -ge 10 ] 2>/dev/null; then
                PYTHON_BIN=$p
                break
            fi
        fi
    done

    if [ -z "$PYTHON_BIN" ]; then
        warning "No se encontró Python >= 3.10. El backend requiere Python 3.10+. Instala Python 3.10/3.11 e intenta de nuevo."
    fi

    # Crear venv si no existe (usar el intérprete detectado)
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        if [ -n "$PYTHON_BIN" ]; then
            $PYTHON_BIN -m venv "$PROJECT_ROOT/venv"
        else
            python3 -m venv "$PROJECT_ROOT/venv" || true
        fi
        success "Entorno virtual creado"
    fi
    
    # Asegurar permisos en venv y logs (puede haber sido creado por sudo accidentalmente)
    if [ -d "$PROJECT_ROOT/venv" ]; then
        chown -R "$(whoami)":"$(id -gn)" "$PROJECT_ROOT/venv" 2>/dev/null || true
    fi
    chown -R "$(whoami)":"$(id -gn)" "$PROJECT_ROOT/logs" 2>/dev/null || true

    # Activar e instalar
    source "$PROJECT_ROOT/venv/bin/activate"
    pip install --quiet --upgrade pip setuptools wheel

    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        log "  📦 Instalando requirements.txt..."
        pip install --quiet -r "$PROJECT_ROOT/requirements.txt" 2>/dev/null || true
    fi

    # Dependencias adicionales necesarias en runtime (pydantic[email] para validación de emails, flask para proxy)
    pip install --quiet "pydantic[email]" flask requests || true

    success "Dependencias Python instaladas (intento realizado)"

    deactivate
}

# Instalación opcional de Node.js via nvm si npm no está disponible
install_node() {
    if command -v npm >/dev/null 2>&1; then
        log "Node/npm detectado; se omite instalación"
        return 0
    fi

    log "Node/npm no detectado. Intentando instalar Node.js LTS via nvm..."
    # Instalar nvm si no existe
    if [ ! -d "$HOME/.nvm" ]; then
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash || true
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    else
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi

    if command -v nvm >/dev/null 2>&1; then
        nvm install --lts || true
        nvm use --lts || true
        success "Node.js instalado (nvm)"
    else
        warning "No se pudo instalar nvm/node automáticamente. Por favor instala Node.js manualmente (brew install node o nvm)."
    fi
}

# ============================================================================
# DEPENDENCIAS NPM
# ============================================================================

install_npm_deps() {
    log "📦 Instalando dependencias NPM..."
    
    # Root package.json (concurrently)
    if [ -f "$PROJECT_ROOT/package.json" ]; then
        cd "$PROJECT_ROOT"
        npm install --silent 2>/dev/null
        success "Dependencias raíz instaladas"
    fi
    
    # Frontend
    if [ -f "$PROJECT_ROOT/frontend-react/package.json" ]; then
        cd "$PROJECT_ROOT/frontend-react"
        npm install --silent 2>/dev/null
        success "Dependencias frontend instaladas"
    fi
    
    cd "$PROJECT_ROOT"
}

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

create_config() {
    log "⚙️ Creando configuración..."
    
    cat > "$PROJECT_ROOT/config/tools.env" << 'EOF'
# Configuración de herramientas forenses - MCP Kali Forensics v4.3
TOOLS_DIR="./tools"
EVIDENCE_DIR="./forensics-evidence"
LOG_DIR="./logs"
TOOL_TIMEOUT=3600
DEBUG=false
EOF
    
    # Crear .env si no existe
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        cat > "$PROJECT_ROOT/.env" << 'EOF'
# MCP Kali Forensics - Variables de entorno
API_KEY=mcp-forensics-dev-key
DEBUG=true
EVIDENCE_DIR=./forensics-evidence
TOOLS_DIR=./tools
EOF
        success ".env creado"
    fi
    
    success "Configuración creada"
}

# ============================================================================
# VERIFICACIÓN
# ============================================================================

verify_installation() {
    echo ""
    log "🔍 Verificando instalación..."
    echo ""
    
    local tools_count=$(ls -1 "$TOOLS_DIR" 2>/dev/null | wc -l)
    local tools_size=$(du -sh "$TOOLS_DIR" 2>/dev/null | cut -f1)
    
    echo -e "${CYAN}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${GREEN}✓${NC} Tools instalados: $tools_count"
    echo -e "${CYAN}│${NC} ${GREEN}✓${NC} Tamaño total: $tools_size"
    echo -e "${CYAN}│${NC}"
    
    # Listar tools
    for tool in "$TOOLS_DIR"/*; do
        if [ -d "$tool" ]; then
            local name=$(basename "$tool")
            local size=$(du -sh "$tool" 2>/dev/null | cut -f1)
            echo -e "${CYAN}│${NC}   📦 $name ($size)"
        fi
    done
    
    echo -e "${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} ${GREEN}✓${NC} Python venv: $([ -d "$PROJECT_ROOT/venv" ] && echo "OK" || echo "No")"
    echo -e "${CYAN}│${NC} ${GREEN}✓${NC} Node modules: $([ -d "$PROJECT_ROOT/node_modules" ] && echo "OK" || echo "No")"
    echo -e "${CYAN}│${NC} ${GREEN}✓${NC} Frontend: $([ -d "$PROJECT_ROOT/frontend-react/node_modules" ] && echo "OK" || echo "No")"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────┘${NC}"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    show_banner
    
    log "📍 Proyecto: $PROJECT_ROOT"
    log "📍 Tools: $TOOLS_DIR"
    echo ""
    
    # Ejecutar instalación
    setup_directories
    install_tools
    install_python_deps
    install_npm_deps
    create_config
    verify_installation
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✓ INSTALACIÓN COMPLETADA                        ║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} Para iniciar el sistema:                                          ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   ${CYAN}./start.sh${NC}                                                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                                    ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} URLs:                                                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   🔧 API:      http://localhost:9000                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   📚 Docs:     http://localhost:9000/docs                          ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   🎨 Frontend: http://localhost:3000                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Ejecutar
main "$@"
