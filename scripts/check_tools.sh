#!/bin/bash
# Script de prueba rápida para verificar herramientas instaladas

echo "🔍 Verificando instalación de herramientas forenses..."
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_tool() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2 instalado"
        return 0
    else
        echo -e "${RED}✗${NC} $2 NO instalado"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2 encontrado en $1"
        return 0
    else
        echo -e "${RED}✗${NC} $2 NO encontrado en $1"
        return 1
    fi
}

echo "=== Herramientas del Sistema ==="
check_tool "python3" "Python 3"
check_tool "pwsh" "PowerShell"
check_tool "yara" "YARA"
check_tool "osqueryi" "OSQuery"
check_tool "grep" "Grep"
check_tool "ssh" "SSH"

echo ""
echo "=== Herramientas Forenses Específicas ==="
check_dir "/opt/forensics-tools/Sparrow" "Sparrow 365"
check_dir "/opt/forensics-tools/hawk" "Hawk"
check_dir "/opt/forensics-tools/sra-o365-extractor" "O365 Extractor"
check_dir "/opt/forensics-tools/Loki" "Loki Scanner"
check_dir "/opt/forensics-tools/yara-rules" "YARA Rules"

echo ""
echo "=== Volatility 3 ==="
if command -v vol.py &> /dev/null; then
    echo -e "${GREEN}✓${NC} Volatility 3 instalado (vol.py)"
elif command -v vol3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Volatility 3 instalado (vol3)"
elif command -v volatility3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Volatility 3 instalado (volatility3)"
else
    echo -e "${RED}✗${NC} Volatility 3 NO instalado"
fi

echo ""
echo "=== Directorios de Evidencia ==="
check_dir "/var/evidence" "Evidence directory"

echo ""
echo "=== Python Dependencies ==="
if python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} FastAPI instalado"
else
    echo -e "${RED}✗${NC} FastAPI NO instalado"
fi

if python3 -c "import msal" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} MSAL instalado"
else
    echo -e "${YELLOW}⚠${NC} MSAL NO instalado (necesario para M365)"
fi

if python3 -c "import yara" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} yara-python instalado"
else
    echo -e "${YELLOW}⚠${NC} yara-python NO instalado"
fi

echo ""
echo "=== Configuración ==="
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} Archivo .env encontrado"
    if grep -q "API_KEY=change-me" .env 2>/dev/null; then
        echo -e "${YELLOW}⚠${NC} API_KEY todavía tiene valor por defecto"
    fi
else
    echo -e "${RED}✗${NC} Archivo .env NO encontrado (copia .env.example)"
fi

echo ""
echo "=== Puertos ==="
if netstat -tuln 2>/dev/null | grep -q ":8080 "; then
    echo -e "${YELLOW}⚠${NC} Puerto 8080 ya está en uso"
else
    echo -e "${GREEN}✓${NC} Puerto 8080 disponible"
fi

echo ""
echo "✅ Verificación completada"
