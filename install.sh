#!/bin/bash
# Punto de entrada para instalación - ejecuta scripts/install.sh
exec "$(dirname "$0")/scripts/install.sh" "$@"
