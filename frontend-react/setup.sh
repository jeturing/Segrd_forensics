#!/bin/bash

# 🚀 MCP Forensics React Frontend - Quick Setup

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🚀 MCP Kali Forensics - React Frontend Setup            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Node.js
echo -e "${BLUE}[1/5] Verificando Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado. Por favor, instálalo desde https://nodejs.org"
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js $(node -v) instalado"

# Check npm
echo -e "${BLUE}[2/5] Verificando npm...${NC}"
if ! command -v npm &> /dev/null; then
    echo "❌ npm no está instalado"
    exit 1
fi
echo -e "${GREEN}✓${NC} npm $(npm -v) instalado"

# Install dependencies
echo -e "${BLUE}[3/5] Instalando dependencias...${NC}"
npm install
echo -e "${GREEN}✓${NC} Dependencias instaladas"

# Setup .env file
echo -e "${BLUE}[4/5] Configurando variables de entorno...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Archivo .env creado"
else
    echo -e "${YELLOW}⚠${NC} Archivo .env ya existe"
fi

# Display summary
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  ✅ Setup Completado!                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}📋 Próximos pasos:${NC}"
echo ""
echo "1. Asegúrate de que el backend FastAPI está ejecutando:"
echo "   cd /home/hack/mcp-kali-forensics"
echo "   uvicorn api.main:app --reload --port 9000"
echo ""
echo "2. Inicia el servidor de desarrollo:"
echo "   cd /home/hack/mcp-kali-forensics/frontend-react"
echo "   npm run dev"
echo ""
echo "3. Abre http://localhost:3000 en tu navegador"
echo ""
echo -e "${GREEN}🎉 ¡Listo para empezar!${NC}"
echo ""
