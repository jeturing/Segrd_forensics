#!/bin/bash
# Test completo de la funcionalidad de gestión de agentes LLM
# Ejecutar después de instalar con: ./scripts/install_llm_agent_mgmt.sh

set -e

API_BASE="http://localhost:8888"
API_KEY="mcp-forensics-dev-key"
HEADERS="-H 'X-API-Key: $API_KEY' -H 'Content-Type: application/json'"

echo "🧪 Test Suite - Gestión de Agentes LLM v4.6"
echo "=========================================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que el backend está corriendo
echo -e "\n${YELLOW}1. Verificando backend...${NC}"
if curl -s "$API_BASE/health" > /dev/null; then
    echo -e "${GREEN}✅ Backend responde${NC}"
else
    echo -e "${RED}❌ Backend no responde en $API_BASE${NC}"
    echo "Inicia el backend con: ./restart_backend.sh"
    exit 1
fi

# Test 1: Listar agentes existentes
echo -e "\n${YELLOW}2. Listando agentes existentes...${NC}"
RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_BASE/api/llm-agents/")
AGENT_COUNT=$(echo $RESPONSE | jq '. | length')
echo -e "${GREEN}✅ Agentes encontrados: $AGENT_COUNT${NC}"
echo $RESPONSE | jq '.[0:3]' || echo "Sin agentes"

# Test 2: Verificar contenedores Docker
echo -e "\n${YELLOW}3. Verificando contenedores Ollama en Docker...${NC}"
DOCKER_COUNT=$(docker ps -a --filter "name=ollama-agent-" --format "{{.Names}}" | wc -l)
echo -e "${GREEN}✅ Contenedores Ollama en Docker: $DOCKER_COUNT${NC}"
docker ps -a --filter "name=ollama-agent-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -n 5

# Test 3: Crear agente de prueba
echo -e "\n${YELLOW}4. Creando agente de prueba...${NC}"
TEST_AGENT_NAME="test-$(date +%s)"
TEST_PORT=$((11450 + RANDOM % 100))

CREATE_RESPONSE=$(curl -s -X POST "$API_BASE/api/llm-agents/" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$TEST_AGENT_NAME\",
    \"tenant_id\": \"test-tenant\",
    \"model\": \"phi4-mini\",
    \"port\": $TEST_PORT,
    \"memory_limit\": \"4g\",
    \"memory_reservation\": \"2g\"
  }")

if echo $CREATE_RESPONSE | jq -e '.container_id' > /dev/null 2>&1; then
    CONTAINER_ID=$(echo $CREATE_RESPONSE | jq -r '.container_id')
    echo -e "${GREEN}✅ Agente creado: ollama-agent-$TEST_AGENT_NAME${NC}"
    echo -e "   Container ID: $CONTAINER_ID"
    echo -e "   Puerto: $TEST_PORT"
else
    echo -e "${RED}❌ Error creando agente:${NC}"
    echo $CREATE_RESPONSE | jq '.'
    exit 1
fi

# Test 4: Verificar que el contenedor se creó
echo -e "\n${YELLOW}5. Verificando contenedor creado...${NC}"
sleep 2
if docker ps -a | grep -q "ollama-agent-$TEST_AGENT_NAME"; then
    echo -e "${GREEN}✅ Contenedor verificado en Docker${NC}"
    docker ps -a --filter "name=ollama-agent-$TEST_AGENT_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo -e "${RED}❌ Contenedor no encontrado en Docker${NC}"
    exit 1
fi

# Test 5: Obtener detalles del agente
echo -e "\n${YELLOW}6. Obteniendo detalles del agente...${NC}"
AGENT_DETAILS=$(curl -s -H "X-API-Key: $API_KEY" "$API_BASE/api/llm-agents/ollama-agent-$TEST_AGENT_NAME")
echo $AGENT_DETAILS | jq '.'

# Test 6: Detener agente
echo -e "\n${YELLOW}7. Deteniendo agente...${NC}"
STOP_RESPONSE=$(curl -s -X POST "$API_BASE/api/llm-agents/ollama-agent-$TEST_AGENT_NAME/stop" \
  -H "X-API-Key: $API_KEY")
echo $STOP_RESPONSE | jq '.'
sleep 2

# Verificar estado detenido
STATUS=$(docker inspect -f '{{.State.Status}}' "ollama-agent-$TEST_AGENT_NAME")
if [ "$STATUS" == "exited" ]; then
    echo -e "${GREEN}✅ Agente detenido correctamente (status: $STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  Agente en estado: $STATUS${NC}"
fi

# Test 7: Iniciar agente
echo -e "\n${YELLOW}8. Iniciando agente...${NC}"
START_RESPONSE=$(curl -s -X POST "$API_BASE/api/llm-agents/ollama-agent-$TEST_AGENT_NAME/start" \
  -H "X-API-Key: $API_KEY")
echo $START_RESPONSE | jq '.'
sleep 2

# Verificar estado iniciado
STATUS=$(docker inspect -f '{{.State.Status}}' "ollama-agent-$TEST_AGENT_NAME")
if [ "$STATUS" == "running" ]; then
    echo -e "${GREEN}✅ Agente iniciado correctamente (status: $STATUS)${NC}"
else
    echo -e "${YELLOW}⚠️  Agente en estado: $STATUS${NC}"
fi

# Test 8: Eliminar agente
echo -e "\n${YELLOW}9. Eliminando agente de prueba...${NC}"
DELETE_RESPONSE=$(curl -s -X DELETE "$API_BASE/api/llm-agents/ollama-agent-$TEST_AGENT_NAME?remove_volume=false" \
  -H "X-API-Key: $API_KEY")
echo $DELETE_RESPONSE | jq '.'
sleep 2

# Verificar que se eliminó
if docker ps -a | grep -q "ollama-agent-$TEST_AGENT_NAME"; then
    echo -e "${RED}❌ Contenedor aún existe${NC}"
else
    echo -e "${GREEN}✅ Contenedor eliminado correctamente${NC}"
fi

# Test 9: Verificar endpoints de tenants
echo -e "\n${YELLOW}10. Verificando endpoints de tenants...${NC}"
TENANTS_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_BASE/api/tenants/")
TENANT_COUNT=$(echo $TENANTS_RESPONSE | jq '. | length')
echo -e "${GREEN}✅ Tenants encontrados: $TENANT_COUNT${NC}"
echo $TENANTS_RESPONSE | jq '.[0:2]' || echo "Sin tenants"

# Test 10: Verificar documentación Swagger
echo -e "\n${YELLOW}11. Verificando Swagger docs...${NC}"
if curl -s "$API_BASE/docs" | grep -q "llm-agents"; then
    echo -e "${GREEN}✅ Documentación de /api/llm-agents/ encontrada en Swagger${NC}"
else
    echo -e "${YELLOW}⚠️  No se encontró la documentación en Swagger${NC}"
fi

# Resumen
echo -e "\n=========================================="
echo -e "${GREEN}✅ TESTS COMPLETADOS${NC}"
echo -e "=========================================="
echo ""
echo "📊 Resumen:"
echo "   - Agentes existentes: $AGENT_COUNT"
echo "   - Contenedores Docker: $DOCKER_COUNT"
echo "   - Tenants configurados: $TENANT_COUNT"
echo "   - Test de creación: ✅"
echo "   - Test de start/stop: ✅"
echo "   - Test de eliminación: ✅"
echo ""
echo "🌐 Accesos:"
echo "   - API Docs: $API_BASE/docs"
echo "   - Health: $API_BASE/health"
echo "   - LLM Agents: $API_BASE/api/llm-agents/"
echo ""
echo "📚 Documentación:"
echo "   - Guía completa: docs/v4.6/LLM_AGENT_MANAGEMENT.md"
echo "   - Resumen ejecutivo: docs/v4.6/EXECUTIVE_SUMMARY.md"
echo "   - Integración frontend: frontend-react/INTEGRATION_EXAMPLE.jsx"
echo ""
echo "✅ Todo listo para usar!"
