#!/bin/bash
# =============================================================================
# Script de Migración: Sistema de Roles v4.6
# =============================================================================
# Este script ejecuta la migración SQL para crear el sistema de roles
# con 7 roles predefinidos y 30+ permisos granulares.
#
# Uso:
#   ./scripts/run_roles_migration.sh [--dry-run]
#
# Opciones:
#   --dry-run   Muestra el SQL sin ejecutar
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MIGRATION_FILE="$PROJECT_ROOT/migrations/add_roles_system.sql"

# Cargar variables de entorno si existe .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Valores por defecto
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-forensics_db}"
POSTGRES_USER="${POSTGRES_USER:-forensics}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-forensics}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           MIGRACIÓN: Sistema de Roles v4.6                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que existe el archivo de migración
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Error: No se encontró el archivo de migración${NC}"
    echo -e "   Esperado: $MIGRATION_FILE"
    exit 1
fi

echo -e "${GREEN}✓ Archivo de migración encontrado${NC}"
echo -e "  📄 $MIGRATION_FILE"
echo ""

# Modo dry-run
if [ "$1" == "--dry-run" ]; then
    echo -e "${YELLOW}🔍 MODO DRY-RUN - Mostrando SQL sin ejecutar:${NC}"
    echo ""
    cat "$MIGRATION_FILE"
    exit 0
fi

# Verificar conexión
echo -e "${BLUE}📡 Verificando conexión a PostgreSQL...${NC}"
echo -e "   Host: $POSTGRES_HOST:$POSTGRES_PORT"
echo -e "   Database: $POSTGRES_DB"
echo -e "   User: $POSTGRES_USER"
echo ""

# Método 1: Docker
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "mcp-forensics-db\|postgres"; then
    echo -e "${GREEN}✓ Contenedor Docker de PostgreSQL detectado${NC}"
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E "mcp-forensics-db|postgres" | head -1)
    
    echo -e "${BLUE}🚀 Ejecutando migración via Docker...${NC}"
    
    docker exec -i "$CONTAINER_NAME" psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        < "$MIGRATION_FILE"
    
    RESULT=$?
    
# Método 2: psql directo
elif command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ psql local detectado${NC}"
    echo -e "${BLUE}🚀 Ejecutando migración via psql...${NC}"
    
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -f "$MIGRATION_FILE"
    
    RESULT=$?
    
else
    echo -e "${RED}❌ Error: No se encontró psql ni contenedor Docker${NC}"
    echo ""
    echo "Opciones:"
    echo "  1. Inicia el contenedor Docker: docker-compose up -d"
    echo "  2. Instala psql: apt install postgresql-client"
    echo "  3. Ejecuta manualmente en tu cliente SQL"
    exit 1
fi

echo ""

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  ✅ MIGRACIÓN EXITOSA                        ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📋 Se crearon/actualizaron:"
    echo -e "   • Tabla ${BLUE}permissions${NC} (30 permisos)"
    echo -e "   • Tabla ${BLUE}roles${NC} (7 roles de sistema)"
    echo -e "   • Tabla ${BLUE}role_permissions${NC} (matriz de permisos)"
    echo -e "   • Tabla ${BLUE}user_roles${NC} (asignaciones)"
    echo -e "   • Usuario ${YELLOW}pluton_je${NC} actualizado a GLOBAL_ADMIN"
    echo ""
    echo -e "🔐 Roles disponibles:"
    echo -e "   👑 ${YELLOW}GLOBAL_ADMIN${NC}  - Control total de la plataforma"
    echo -e "   🏢 ${BLUE}TENANT_ADMIN${NC}  - Administrador del tenant"
    echo -e "   📊 ${GREEN}AUDIT${NC}         - Solo lectura/auditoría"
    echo -e "   🔴 ${RED}RED_TEAM${NC}      - Herramientas ofensivas"
    echo -e "   🔵 ${BLUE}BLUE_TEAM${NC}     - Herramientas defensivas/forenses"
    echo -e "   🟣 PURPLE_TEAM   - Red + Blue combinado"
    echo -e "   ⚙️  CUSTOM        - Permisos personalizados"
    echo ""
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                  ❌ MIGRACIÓN FALLÓ                          ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Revisa los logs arriba para ver el error."
    exit 1
fi
