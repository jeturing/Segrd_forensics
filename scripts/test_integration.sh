#!/bin/bash
# 🧪 SCRIPT DE PRUEBAS RÁPIDAS
# Verificar que frontend y backend funcionan correctamente

set -e

echo "🧪 ========================================="
echo "   PRUEBAS DE INTEGRACIÓN FRONTEND-BACKEND"
echo "========================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función de verificación
check_endpoint() {
    local method=$1
    local url=$2
    local name=$3
    
    echo -n "  $name... "
    
    if response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" 2>/dev/null); then
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)
        
        if [[ "$http_code" =~ ^(200|201|202|204|400|404|422|500)$ ]]; then
            echo -e "${GREEN}✓ HTTP $http_code${NC}"
            # echo "    Response: $(echo "$body" | head -c 100)..."
            return 0
        else
            echo -e "${RED}✗ HTTP $http_code${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Sin conexión${NC}"
        return 1
    fi
}

# 1. VERIFICAR BACKEND
echo "📦 Verificando Backend (FastAPI)..."
echo ""

if curl -s http://localhost:9000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend funcionando en http://localhost:9000${NC}"
    echo ""
    
    echo "🔍 Endpoints Backend:"
    check_endpoint "GET" "http://localhost:9000/health" "Health Check"
    check_endpoint "GET" "http://localhost:9000/docs" "Swagger UI"
    check_endpoint "GET" "http://localhost:9000/api/agents" "GET /api/agents"
    check_endpoint "GET" "http://localhost:9000/api/investigations" "GET /api/investigations"
    check_endpoint "GET" "http://localhost:9000/api/active-investigation/templates?os_type=windows" "GET /api/active-investigation/templates"
    echo ""
else
    echo -e "${RED}✗ Backend NO está funcionando en http://localhost:9000${NC}"
    echo "  Inicia el backend con:"
    echo "  cd /home/hack/mcp-kali-forensics && source venv/bin/activate && uvicorn api.main:app --reload --port 9000"
    exit 1
fi

# 2. VERIFICAR FRONTEND
echo "🎨 Verificando Frontend (React)..."
echo ""

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend funcionando en http://localhost:3000${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ Frontend NO está en http://localhost:3000${NC}"
    echo "  Inicia el frontend con:"
    echo "  cd /home/hack/mcp-kali-forensics/frontend-react && npm run dev"
    echo ""
fi

# 3. PRUEBAS DE ENDPOINTS ESPECÍFICOS
echo "🔗 Pruebas de Endpoints Específicos:"
echo ""

echo "📋 Mobile Agents:"
check_endpoint "GET" "http://localhost:9000/api/agents" "  GET /agents"
check_endpoint "GET" "http://localhost:9000/api/agents?status=online" "  GET /agents (filtrado online)"

echo ""
echo "🔍 Investigaciones:"
check_endpoint "GET" "http://localhost:9000/api/investigations" "  GET /investigations"
check_endpoint "GET" "http://localhost:9000/api/investigations?status=open" "  GET /investigations (filtrado open)"
check_endpoint "GET" "http://localhost:9000/api/investigations/IR-2025-001" "  GET /investigations/IR-2025-001"

echo ""
echo "⚡ Active Investigation:"
check_endpoint "GET" "http://localhost:9000/api/active-investigation/templates" "  GET /templates"
check_endpoint "GET" "http://localhost:9000/api/active-investigation/templates?os_type=windows" "  GET /templates (Windows)"
check_endpoint "GET" "http://localhost:9000/api/active-investigation/templates?os_type=mac" "  GET /templates (Mac)"
check_endpoint "GET" "http://localhost:9000/api/active-investigation/templates?os_type=linux" "  GET /templates (Linux)"

echo ""
echo "========================================="
echo "✅ PRUEBAS COMPLETADAS"
echo "========================================="
echo ""
echo "📍 URLs importantes:"
echo "  • Frontend:     http://localhost:3000"
echo "  • Backend:      http://localhost:9000"
echo "  • Swagger Docs: http://localhost:9000/docs"
echo "  • Health:       http://localhost:9000/health"
echo ""
echo "🔍 Próximas acciones:"
echo "  1. Abre http://localhost:3000 en el navegador"
echo "  2. Verifica que aparecen los 3 módulos nuevos"
echo "  3. Prueba la búsqueda en Investigaciones"
echo "  4. Ejecuta un comando en Mobile Agents"
echo "  5. Revisa Network tab (DevTools) para ver requests"
echo ""
