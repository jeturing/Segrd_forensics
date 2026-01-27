#!/bin/bash
# Reinicia el backend de MCP Kali Forensics

cd /home/hack/mcp-kali-forensics

# Matar cualquier proceso uvicorn existente
echo "🔄 Deteniendo backend existente..."
pkill -9 -f "uvicorn api.main:app" 2>/dev/null || true
sleep 1

# Activar entorno virtual
source venv/bin/activate

# Iniciar nuevo backend
echo "🚀 Iniciando backend en puerto 9000..."
nohup python -m uvicorn api.main:app --host 0.0.0.0 --port 9000 > logs/backend.log 2>&1 &

# Esperar a que arranque
sleep 3

# Verificar
if curl -s http://localhost:9000/health > /dev/null 2>&1; then
    echo "✅ Backend iniciado correctamente"
    curl -s http://localhost:9000/health | python3 -m json.tool
else
    echo "❌ Error iniciando backend"
    tail -20 logs/backend.log
fi
