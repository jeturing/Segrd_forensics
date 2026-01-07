#!/bin/bash
# ==========================================================
# Script para iniciar Backend + Proxy en puerto 3000
# y hacer el túnel accesible
# ==========================================================

cd /Users/owner/Desktop/jcore

# Detener procesos previos
pkill -9 -f "uvicorn|simple_tunnel" 2>/dev/null || true
sleep 1

# Cargar .env
export $(grep -v '^#' .env | xargs)

# Iniciar Backend en :9000 (silencioso en background)
echo "➤ Iniciando Backend en :9000..."
source venv/bin/activate
nohup python -m uvicorn api.main:app --host 0.0.0.0 --port 9000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

sleep 5

# Iniciar Proxy en :3000 (silencioso en background)
echo "➤ Iniciando Proxy en :3000..."
nohup python3 simple_tunnel_server.py > logs/proxy.log 2>&1 &
PROXY_PID=$!
echo "  Proxy PID: $PROXY_PID"

sleep 2

# Comprobaciones
echo ""
echo "═══════════════════════════════════════════════════════"
echo "✓ Servicios iniciados"
echo ""

if curl -sf http://localhost:9000/health >/dev/null 2>&1; then
  echo "✓ Backend (:9000)  RUNNING"
else
  echo "✗ Backend (:9000)  NOT RESPONDING (checking logs...)"
  tail -20 logs/backend.log
fi

if curl -sf http://localhost:3000/health >/dev/null 2>&1; then
  echo "✓ Proxy (:3000)    RUNNING"
else
  echo "✗ Proxy (:3000)    NOT RESPONDING (checking logs...)"
  tail -20 logs/proxy.log
fi

echo ""
echo "Acceso:"
echo "  Local:       http://localhost:3000/"
echo "  Dev Tunnel:  https://nxvskjcx-3000.use.devtunnels.ms/"
echo ""
echo "Detener: pkill -f 'uvicorn|simple_tunnel'"
echo "═══════════════════════════════════════════════════════"

# ==========================================================
# Script para desplegar todos los contenedores y configurar Ollama para cada agente
# ==========================================================

echo "Iniciando despliegue de contenedores..."

# Levantar servicios con Docker Compose
docker-compose up -d

# Configurar Ollama para cada agente
AGENTS=("agent1" "agent2" "agent3")
for AGENT in "${AGENTS[@]}"; do
  echo "Configurando Ollama para $AGENT..."
  docker run -d --name "ollama-$AGENT" \
    -p 11434:11434 \
    -v ollama:/root/.ollama \
    ollama/ollama

  docker exec "ollama-$AGENT" ollama pull phi4
  docker exec "ollama-$AGENT" ollama run phi4

done

echo "Todos los contenedores están en ejecución."
