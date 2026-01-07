#!/usr/bin/env bash
# deploy-lxc-forensics.sh - Crea LXC clonando template 143 para mcp-kali-forensics
# Disco: 50GB (optimizado para all-in-one deployment)

set -euo pipefail

# ========================================================================
# CONFIGURACIÓN
# ========================================================================
BASE_TEMPLATE=143
FORENSICS_LXC="${1:-}"  # ID del LXC (opcional, se auto-detecta si no se pasa)
FORENSICS_IP="${2:-}"   # IP del LXC (opcional, se auto-detecta si no se pasa)
LXC_STORAGE=50          # 50GB de disco (no 100GB)
LXC_MEMORY=8192
LXC_CORES=4
LXC_HOSTNAME="mcp-forensics"

DEFAULT_BASE_NET="10.10.10"
DEFAULT_GATEWAY="10.10.10.1"
DEFAULT_START_HOST=2
DEFAULT_END_HOST=200

# ========================================================================
# FUNCIONES
# ========================================================================
log() { printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
success() { printf "✅ %s\n" "$*"; }
info() { printf "ℹ️  %s\n" "$*"; }
warn() { printf "⚠️  %s\n" "$*"; }
err() { printf "❌ ERROR: %s\n" "$*" >&2; }

# Verificar que estamos en Proxmox
check_proxmox() {
  if ! command -v pct >/dev/null 2>&1; then
    err "Este script debe ejecutarse en un nodo Proxmox"
    err "Comandos pct/pvesh no encontrados"
    exit 1
  fi
  success "Ejecutando en nodo Proxmox"
}

# Buscar siguiente ID disponible
find_next_lxc_id() {
  local used_ids next_id=100
  used_ids=$(pvesh get /cluster/resources --type vm 2>/dev/null | grep -oP 'lxc/\K\d+' | sort -n || echo "")
  
  for id in $used_ids; do
    if [ "$id" -ge "$next_id" ]; then
      next_id=$((id + 1))
    fi
  done
  echo "$next_id"
}

# Buscar IP libre en la red
find_free_ip() {
  local base="$1" start="$2" end="$3" gw="$4"
  local used ip
  
  used=$(pct list | awk 'NR>1 {print $7}' 2>/dev/null || echo "")
  
  for h in $(seq "$start" "$end"); do
    ip="$base.$h"
    [ "$ip" = "$gw" ] && continue
    
    if printf '%s' "$used" | tr ' ' '\n' | grep -Fxq "$ip"; then
      continue
    fi
    
    if ping -c1 -W1 "$ip" >/dev/null 2>&1; then
      continue
    fi
    
    echo "$ip"
    return 0
  done
  return 1
}

# Auto-detectar storage disponible
detect_storage() {
  local node="${1:-$(hostname)}"
  local storage
  storage=$(pvesh get /nodes/$node/storage 2>/dev/null | grep -E "rootdir.*active.*1" | awk '{print $2}' | head -1 || echo "local")
  [ -z "$storage" ] && storage="local"
  echo "$storage"
}

# ========================================================================
# MAIN
# ========================================================================
log "====== Deploy LXC para MCP-Kali-Forensics ======"
log "Template base: $BASE_TEMPLATE"
log "Tamaño disco: ${LXC_STORAGE}GB"

# Verificar Proxmox
check_proxmox

# Verificar que el template existe
if ! pct status "$BASE_TEMPLATE" >/dev/null 2>&1; then
  err "Template $BASE_TEMPLATE no existe!"
  err "Verifica el ID del template con: pct list"
  exit 1
fi
success "Template $BASE_TEMPLATE encontrado"

# Auto-detectar LXC ID si no se proporcionó
if [ -z "$FORENSICS_LXC" ]; then
  FORENSICS_LXC=$(find_next_lxc_id)
  log "Auto-detectado siguiente LXC ID disponible: $FORENSICS_LXC"
fi

# Verificar que el ID no esté en uso
if pct status "$FORENSICS_LXC" >/dev/null 2>&1; then
  err "LXC $FORENSICS_LXC ya existe!"
  info "Usa un ID diferente o elimínalo primero: pct destroy $FORENSICS_LXC"
  exit 1
fi

# Auto-detectar IP si no se proporcionó
if [ -z "$FORENSICS_IP" ]; then
  FORENSICS_IP=$(find_free_ip "$DEFAULT_BASE_NET" "$DEFAULT_START_HOST" "$DEFAULT_END_HOST" "$DEFAULT_GATEWAY" || true)
  if [ -z "$FORENSICS_IP" ]; then
    err "No se encontró IP libre en ${DEFAULT_BASE_NET}.${DEFAULT_START_HOST}-${DEFAULT_END_HOST}"
    exit 1
  fi
  log "Auto-detectada IP disponible: $FORENSICS_IP"
fi

# Detectar storage
STORAGE_NAME=$(detect_storage)
log "Storage detectado: $STORAGE_NAME"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              CONFIGURACIÓN DEL LXC                        ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  Template:    $BASE_TEMPLATE"
echo "║  Nuevo LXC:   $FORENSICS_LXC"
echo "║  IP:          $FORENSICS_IP/24"
echo "║  Gateway:     $DEFAULT_GATEWAY"
echo "║  Hostname:    $LXC_HOSTNAME"
echo "║  Disco:       ${LXC_STORAGE}GB"
echo "║  RAM:         ${LXC_MEMORY}MB"
echo "║  Cores:       $LXC_CORES"
echo "║  Storage:     $STORAGE_NAME"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

read -p "¿Continuar con la creación? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  log "Cancelado por el usuario"
  exit 0
fi

# ========================================================================
# 1) Clonar template
# ========================================================================
log "Clonando template $BASE_TEMPLATE -> LXC $FORENSICS_LXC..."

pct clone "$BASE_TEMPLATE" "$FORENSICS_LXC" --full
success "Template clonado"

# ========================================================================
# 2) Configurar LXC
# ========================================================================
log "Configurando LXC $FORENSICS_LXC..."

# Red
pct set "$FORENSICS_LXC" -net0 "name=eth0,bridge=vmbr1,ip=${FORENSICS_IP}/24,gw=${DEFAULT_GATEWAY}"
success "Red configurada: ${FORENSICS_IP}/24"

# DNS
pct set "$FORENSICS_LXC" -nameserver "8.8.8.8 8.8.4.4"
success "DNS configurado"

# Hostname
pct set "$FORENSICS_LXC" -hostname "$LXC_HOSTNAME"
success "Hostname: $LXC_HOSTNAME"

# Recursos
pct set "$FORENSICS_LXC" -memory "$LXC_MEMORY" -cores "$LXC_CORES"
success "Recursos: ${LXC_MEMORY}MB RAM, ${LXC_CORES} cores"

# Redimensionar disco a 50GB
log "Redimensionando disco a ${LXC_STORAGE}GB..."
pct resize "$FORENSICS_LXC" rootfs "${LXC_STORAGE}G"
success "Disco redimensionado a ${LXC_STORAGE}GB"

# Configurar Docker support (nesting)
CONFIG_FILE="/etc/pve/lxc/${FORENSICS_LXC}.conf"
if ! grep -q "^features:" "$CONFIG_FILE" 2>/dev/null; then
  echo "features: nesting=1,keyctl=1" >> "$CONFIG_FILE"
  success "Docker nesting habilitado"
fi

# ========================================================================
# 3) Iniciar LXC
# ========================================================================
log "Iniciando LXC $FORENSICS_LXC..."
pct start "$FORENSICS_LXC"
sleep 5
success "LXC iniciado"

# Esperar a que esté listo
log "Esperando a que el LXC esté listo..."
for i in {1..30}; do
  if pct exec "$FORENSICS_LXC" -- echo "ready" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
success "LXC respondiendo"

# ========================================================================
# 4) Clonar repositorio mcp-kali-forensics
# ========================================================================
log "Clonando repositorio mcp-kali-forensics..."

pct exec "$FORENSICS_LXC" -- bash << 'CLONE_REPO'
set -euo pipefail

# Crear directorio
mkdir -p /opt/forensics

# Instalar git si no existe
if ! command -v git >/dev/null 2>&1; then
  apt-get update && apt-get install -y git
fi

# Clonar repositorio
cd /opt/forensics
if [ -d "mcp-kali-forensics" ]; then
  echo "Repositorio ya existe, actualizando..."
  cd mcp-kali-forensics && git pull
else
  git clone https://github.com/jcarvajalantigua/mcp-kali-forensics.git
fi

echo "✅ Repositorio clonado en /opt/forensics/mcp-kali-forensics"
CLONE_REPO

success "Repositorio clonado"

# ========================================================================
# 5) Resumen
# ========================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       LXC MCP-KALI-FORENSICS CREADO EXITOSAMENTE          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Detalles:"
echo "  LXC ID:     $FORENSICS_LXC"
echo "  IP:         $FORENSICS_IP"
echo "  Hostname:   $LXC_HOSTNAME"
echo "  Disco:      ${LXC_STORAGE}GB"
echo "  Repo:       /opt/forensics/mcp-kali-forensics"
echo ""
echo "Próximos pasos:"
echo "  1) Acceder al LXC:"
echo "     pct enter $FORENSICS_LXC"
echo "     # o via SSH:"
echo "     ssh root@$FORENSICS_IP"
echo ""
echo "  2) Iniciar los servicios:"
echo "     cd /opt/forensics/mcp-kali-forensics"
echo "     docker compose up -d"
echo ""
echo "  3) Verificar estado:"
echo "     docker ps"
echo ""

success "¡Deploy completado!"
