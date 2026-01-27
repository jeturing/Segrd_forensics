#!/bin/bash
# ============================================================================
# Script para configurar SMTP en segrd-forensics
# Utiliza el proveedor: mail5010.site4now.net (NO-REPLY@SAJET.US)
# ============================================================================

set -e

REPO_PATH="/opt/segrd-forensics"

echo "🔧 Configurando SMTP para segrd-forensics..."

# Crear o actualizar .env con variables SMTP
cat >> "${REPO_PATH}/.env" <<EOF

# ============================================================================
# SMTP Configuration - Security Checklist Email Notifications
# Proveedor: mail5010.site4now.net
# ============================================================================
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
echo "🔄 Reiniciando servicios Docker..."

# Reiniciar la API para que cargue las nuevas variables
cd "${REPO_PATH}"
docker-compose restart mcp-forensics-api 2>/dev/null || docker restart mcp-forensics-api

echo "✅ Servicios reiniciados"
echo ""
echo "🧪 Verificando que SMTP está configurado..."
sleep 2

# Verificar que el endpoint está disponible
if curl -s http://localhost:9000/security-checklist/status | grep -q '"email_configured": true'; then
    echo "✅ SMTP está correctamente configurado"
    echo ""
    echo "📧 Email configured: YES"
    echo "🌐 Formulario disponible en: /security-checklist"
    echo ""
    echo "✨ ¡Sistema listo para enviar reportes a sales@jeturing.com!"
else
    echo "⚠️  SMTP podría no estar configurado correctamente"
    echo "   Revisa los logs: docker logs mcp-forensics-api"
fi
