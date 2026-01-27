#!/bin/bash
# ============================================================================
# Script para configurar SMTP dentro del contenedor LXC 154
# Ejecutar con: pct exec 154 -- bash /opt/setup_smtp_lxc.sh
# ============================================================================

set -e

REPO_PATH="/opt/segrd-forensics"

echo "🔧 Configurando SMTP para segrd-forensics (dentro de LXC 154)..."

# Crear o actualizar .env con variables SMTP
if [ ! -f "${REPO_PATH}/.env" ]; then
    echo "Creando .env..."
    touch "${REPO_PATH}/.env"
fi

# Limpiar variables SMTP anteriores si existen
sed -i '/^SMTP_HOST=/d' "${REPO_PATH}/.env" 2>/dev/null || true
sed -i '/^SMTP_PORT=/d' "${REPO_PATH}/.env" 2>/dev/null || true
sed -i '/^SMTP_USER=/d' "${REPO_PATH}/.env" 2>/dev/null || true
sed -i '/^SMTP_PASSWORD=/d' "${REPO_PATH}/.env" 2>/dev/null || true
sed -i '/^SMTP_SSL=/d' "${REPO_PATH}/.env" 2>/dev/null || true
sed -i '/^SMTP_FROM_EMAIL=/d' "${REPO_PATH}/.env" 2>/dev/null || true

# Añadir nuevas variables SMTP
cat >> "${REPO_PATH}/.env" <<EOF

# SMTP Configuration - Security Checklist Email Notifications
SMTP_HOST=mail5010.site4now.net
SMTP_PORT=465
SMTP_USER=no-reply@sajet.us
SMTP_PASSWORD=321Abcd.
SMTP_SSL=True
SMTP_FROM_EMAIL=no-reply@sajet.us

EOF

echo "✅ Variables SMTP añadidas a ${REPO_PATH}/.env"
echo ""
echo "📋 Configuración guardada:"
echo "   SMTP_HOST: mail5010.site4now.net"
echo "   SMTP_PORT: 465 (SSL)"
echo "   SMTP_USER: no-reply@sajet.us"
echo "   SMTP_FROM_EMAIL: no-reply@sajet.us"
echo ""
echo "🔄 Reiniciando contenedor Docker mcp-forensics-api..."

cd "${REPO_PATH}"
docker restart mcp-forensics-api 2>/dev/null || echo "⚠️  No se pudo reiniciar docker-compose, intenta manualmente"

echo "✅ Contenedor reiniciado"
sleep 3

echo ""
echo "🧪 Verificando que SMTP está configurado..."

# Verificar que el endpoint está disponible y SMTP está configurado
RESPONSE=$(curl -s http://localhost:9000/security-checklist/status 2>/dev/null || echo '{"email_configured": false}')

if echo "$RESPONSE" | grep -q '"email_configured": true'; then
    echo "✅ SMTP está correctamente configurado"
    echo ""
    echo "📧 Email configured: YES"
    echo "🌐 Formulario disponible en: https://segrd.com/security-checklist"
    echo "💌 Los reportes se enviarán a: sales@jeturing.com"
    echo ""
    echo "✨ ¡Sistema listo para enviar formularios!"
else
    echo "⚠️  Verificando logs..."
    docker logs mcp-forensics-api --tail 20 | grep -i smtp || echo "No se encontraron logs de SMTP"
    echo ""
    echo "💡 Si ves errores, revisa:"
    echo "   docker logs mcp-forensics-api"
fi

echo ""
echo "📝 Variables de entorno verificadas:"
grep "^SMTP_" "${REPO_PATH}/.env" | grep -v "PASSWORD" || echo "No encontradas"
