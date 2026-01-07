#!/bin/bash
# Script de instalación de gestión de agentes LLM v4.6
# Instala dependencias y configura permisos Docker

set -e

echo "🚀 Instalación de Gestión de Agentes LLM v4.6"
echo "=============================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "⚠️  Entorno virtual no encontrado. Creando..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Instalar/actualizar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install docker==7.1.0

# Verificar instalación
echo "✅ Verificando instalación de Docker SDK..."
python3 -c "import docker; print(f'Docker SDK version: {docker.__version__}')"

# Verificar acceso a Docker
echo "🐳 Verificando acceso a Docker..."
if docker ps > /dev/null 2>&1; then
    echo "✅ Docker accesible"
else
    echo "⚠️  Docker no accesible. Configurando permisos..."
    
    # Verificar si el usuario está en el grupo docker
    if ! groups | grep -q docker; then
        echo "Agregando usuario al grupo docker..."
        sudo usermod -aG docker $USER
        echo "⚠️  IMPORTANTE: Cierra sesión y vuelve a entrar para aplicar cambios"
        echo "   O ejecuta: newgrp docker"
    fi
fi

# Verificar que los componentes React existen
echo "🔍 Verificando componentes React..."
if [ -f "frontend-react/src/components/LLMAgentManager.jsx" ]; then
    echo "✅ LLMAgentManager.jsx encontrado"
else
    echo "❌ LLMAgentManager.jsx NO encontrado"
fi

if [ -f "frontend-react/src/components/TenantManagement.jsx" ]; then
    echo "✅ TenantManagement.jsx encontrado"
else
    echo "❌ TenantManagement.jsx NO encontrado"
fi

# Verificar que el router backend existe
echo "🔍 Verificando router backend..."
if [ -f "api/routes/llm_agents.py" ]; then
    echo "✅ llm_agents.py encontrado"
else
    echo "❌ llm_agents.py NO encontrado"
fi

# Crear directorio para evidencia si no existe
echo "📁 Verificando directorios de evidencia..."
mkdir -p forensics-evidence/cases-data

# Test de conexión a Docker via Python
echo "🧪 Probando conexión Docker vía Python..."
cat > /tmp/test_docker.py << 'EOF'
import docker

try:
    client = docker.from_env()
    containers = client.containers.list(all=True)
    print(f"✅ Docker SDK funcional. Contenedores encontrados: {len(containers)}")
    
    # Listar contenedores Ollama existentes
    ollama_containers = [c for c in containers if 'ollama' in c.name]
    if ollama_containers:
        print(f"📦 Contenedores Ollama existentes:")
        for c in ollama_containers:
            status = "🟢" if c.status == "running" else "🔴"
            print(f"   {status} {c.name} ({c.status})")
    else:
        print("ℹ️  No hay contenedores Ollama actualmente")
except Exception as e:
    print(f"❌ Error: {e}")
EOF

python3 /tmp/test_docker.py
rm /tmp/test_docker.py

echo ""
echo "=============================================="
echo "✅ Instalación completada!"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Reiniciar backend: ./restart_backend.sh"
echo "   2. Navegar a: http://localhost:8888/docs"
echo "   3. Verificar endpoint: GET /api/llm-agents/"
echo "   4. Integrar componentes React (ver INTEGRATION_EXAMPLE.jsx)"
echo ""
echo "🧪 Test rápido:"
echo "   curl -H 'X-API-Key: mcp-forensics-dev-key' \\"
echo "        http://localhost:8888/api/llm-agents/"
echo ""
echo "📚 Documentación completa en:"
echo "   docs/v4.6/LLM_AGENT_MANAGEMENT.md"
echo "=============================================="
