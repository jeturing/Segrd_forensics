#!/bin/bash
# =============================================================================
# Export OpenAPI Spec para API Gravity
# Este script descarga el OpenAPI spec y lo copia/sube a API Gravity
# =============================================================================

set -e

# Configuración
BACKEND_URL="${BACKEND_URL:-http://localhost:9000}"
API_GRAVITY_URL="${API_GRAVITY_URL:-http://10.10.10.9:8084}"
OUTPUT_DIR="./docs/api"

echo "📥 Exportando OpenAPI spec desde $BACKEND_URL"

# Crear directorio si no existe
mkdir -p "$OUTPUT_DIR"

# Descargar OpenAPI spec
curl -s "$BACKEND_URL/openapi.json" > "$OUTPUT_DIR/openapi.json"

if [ $? -eq 0 ] && [ -s "$OUTPUT_DIR/openapi.json" ]; then
    echo "✅ OpenAPI spec guardado en $OUTPUT_DIR/openapi.json"
    
    # Verificar que es JSON válido
    if python3 -c "import json; json.load(open('$OUTPUT_DIR/openapi.json'))" 2>/dev/null; then
        echo "✅ JSON válido"
        
        # Mostrar info básica
        python3 -c "
import json
with open('$OUTPUT_DIR/openapi.json') as f:
    spec = json.load(f)
    print(f'📋 Título: {spec.get(\"info\", {}).get(\"title\", \"N/A\")}')
    print(f'📌 Versión: {spec.get(\"info\", {}).get(\"version\", \"N/A\")}')
    print(f'📐 OpenAPI: {spec.get(\"openapi\", \"N/A\")}')
    print(f'📊 Paths: {len(spec.get(\"paths\", {}))}')
    print(f'🔧 Schemas: {len(spec.get(\"components\", {}).get(\"schemas\", {}))}')
"
    else
        echo "❌ Error: El archivo no es JSON válido"
        exit 1
    fi
else
    echo "❌ Error descargando OpenAPI spec"
    exit 1
fi

# Intentar subir a API Gravity si está disponible
if [ -n "$API_GRAVITY_URL" ]; then
    echo ""
    echo "🚀 Intentando subir a API Gravity ($API_GRAVITY_URL)..."
    
    # Verificar si API Gravity está accesible
    if curl -s --connect-timeout 5 "$API_GRAVITY_URL/health" > /dev/null 2>&1 || \
       curl -s --connect-timeout 5 "$API_GRAVITY_URL" > /dev/null 2>&1; then
        echo "✅ API Gravity está accesible"
        
        # Intentar subir el spec (ajusta el endpoint según la API de API Gravity)
        # Ejemplo para un endpoint hipotético:
        # curl -X POST "$API_GRAVITY_URL/api/specs" \
        #      -H "Content-Type: application/json" \
        #      -d @"$OUTPUT_DIR/openapi.json"
        
        echo "ℹ️  Para subir manualmente a API Gravity:"
        echo "   1. Abre http://10.10.10.9:8085 (UI de documentación)"
        echo "   2. O importa desde: http://TU_IP:80/openapi.json"
        echo "   3. O usa el archivo local: $OUTPUT_DIR/openapi.json"
    else
        echo "⚠️  API Gravity no accesible en $API_GRAVITY_URL"
        echo "   Puedes importar manualmente desde: http://localhost/openapi.json"
    fi
fi

echo ""
echo "📝 URLs disponibles para OpenAPI:"
echo "   - Local (vía nginx): http://localhost/openapi.json"
echo "   - Directo al backend: http://localhost:9000/openapi.json"
echo "   - Swagger UI: http://localhost/docs"
echo "   - ReDoc: http://localhost/redoc"
