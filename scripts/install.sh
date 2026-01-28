#!/bin/bash
# Punto de entrada para instalación

# Definición de funciones de registro
log_info() { echo -e "[INFO] $1"; }
log_error() { echo -e "[ERROR] $1"; }

# Definir directorio de instalación
INSTALL_DIR="$HOME/.iacore"
mkdir -p "$INSTALL_DIR"

# Clone repository
log_info "Descargando desde GitHub..."
git clone --depth 1 https://github.com/jeturing/IA_core.git "$INSTALL_DIR" &>/dev/null || {
    log_error "Error al clonar repositorio"
    exit 1
}
