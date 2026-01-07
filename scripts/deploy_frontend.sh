#!/bin/bash
# Script de deployment completo - Build frontend y configurar nginx
# Este script compila React y lo copia al contenedor nginx

set -e

echo "🚀 Deployment MCP Forensics v4.6 - Frontend + Nginx"
echo "===================================================="

# Variables
FRONTEND_DIR="./frontend-react"
NGINX_HTML_DIR="./nginx/html"
DOCKER_COMPOSE_FILE="./docker-compose.yml"

# Verificar que estamos en el directorio correcto
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que existe el frontend
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: No se encuentra el directorio $FRONTEND_DIR"
    exit 1
fi

# Crear directorio para HTML si no existe
echo "📁 Creando directorio nginx/html..."
mkdir -p "$NGINX_HTML_DIR"

# Build del frontend React
echo "🔨 Compilando frontend React..."
cd "$FRONTEND_DIR"

# Verificar que existen node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias npm..."
    npm install
fi

# Build production
echo "⚙️  Ejecutando build de producción..."
npm run build

# Verificar que se creó el build (Vite genera 'dist', no 'build')
if [ ! -d "dist" ] && [ ! -d "build" ]; then
    echo "❌ Error: No se generó el directorio dist o build"
    exit 1
fi

# Determinar qué directorio usar
if [ -d "dist" ]; then
    BUILD_DIR="dist"
else
    BUILD_DIR="build"
fi

echo "✅ Build completado exitosamente"

# Copiar archivos al nginx
echo "📋 Copiando archivos a nginx/html..."
cd ..
cp -r "$FRONTEND_DIR/$BUILD_DIR/"* "$NGINX_HTML_DIR/"

# Verificar que se copiaron los archivos
if [ ! -f "$NGINX_HTML_DIR/index.html" ]; then
    echo "❌ Error: No se copió index.html correctamente"
    exit 1
fi

echo "✅ Archivos copiados correctamente"

# Listar archivos copiados
echo ""
echo "📦 Archivos en nginx/html:"
ls -lh "$NGINX_HTML_DIR/" | head -10

# Actualizar docker-compose si es necesario
echo ""
echo "🐳 Verificando configuración de Docker Compose..."

# Verificar si nginx está en docker-compose
if grep -q "nginx:" "$DOCKER_COMPOSE_FILE"; then
    echo "✅ Servicio nginx encontrado en docker-compose.yml"
else
    echo "⚠️  Servicio nginx NO encontrado en docker-compose.yml"
    echo "   Necesitas añadir el servicio nginx manualmente"
fi

# Preguntar si reiniciar contenedores
echo ""
read -p "¿Reiniciar contenedores de Docker? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Reiniciando contenedores..."
    
    # Detener nginx si está corriendo
    docker-compose stop nginx 2>/dev/null || true
    
    # Levantar servicios
    docker-compose up -d
    
    echo "✅ Contenedores reiniciados"
    
    # Esperar a que nginx esté listo
    echo "⏳ Esperando a que nginx esté listo..."
    sleep 5
    
    # Test de acceso
    echo "🧪 Probando acceso a la aplicación..."
    if curl -s http://localhost/ | grep -q "<title>"; then
        echo "✅ Frontend accesible en http://localhost/"
    else
        echo "⚠️  Frontend no responde todavía, espera unos segundos"
    fi
    
    # Test API
    if curl -s http://localhost/api/health > /dev/null 2>&1; then
        echo "✅ API accesible en http://localhost/api/"
    else
        echo "⚠️  API no responde, verifica que mcp-forensics-api esté corriendo"
    fi
fi

echo ""
echo "===================================================="
echo "✅ Deployment completado!"
echo ""
echo "🌐 Accesos:"
echo "   Frontend: http://localhost/"
echo "   API:      http://localhost/api/"
echo "   Docs:     http://localhost/docs"
echo "   Health:   http://localhost/api/health"
echo ""
echo "📚 Logs:"
echo "   Frontend: docker-compose logs -f nginx"
echo "   Backend:  docker-compose logs -f mcp-forensics-api"
echo ""
echo "🔧 Troubleshooting:"
echo "   Si ves 'Welcome to nginx', ejecuta:"
echo "   docker-compose restart nginx"
echo "===================================================="
