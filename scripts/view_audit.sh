#!/bin/bash

#############################################
# Generador de Reporte de Auditoría
# Crea reportes legibles de las auditorías
#############################################

AUDIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/audit-logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -d "$AUDIT_DIR" ]; then
    echo "❌ No hay registros de auditoría"
    exit 1
fi

# Listar auditorías disponibles
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  REGISTROS DE AUDITORÍA DISPONIBLES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

count=1
declare -a files

for file in "$AUDIT_DIR"/setup_audit_*.log; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        date_part=$(echo "$filename" | grep -oP '\d{8}_\d{6}')
        formatted_date=$(echo "$date_part" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
        
        # Contar eventos
        total_lines=$(wc -l < "$file")
        success_count=$(grep -c "\[SUCCESS\]" "$file" 2>/dev/null || echo 0)
        error_count=$(grep -c "\[ERROR\]" "$file" 2>/dev/null || echo 0)
        warning_count=$(grep -c "\[WARNING\]" "$file" 2>/dev/null || echo 0)
        
        echo -e "${GREEN}[$count]${NC} $formatted_date"
        echo "    Archivo: $filename"
        echo "    Eventos: $total_lines líneas | ✅ $success_count | ❌ $error_count | ⚠️  $warning_count"
        echo ""
        
        files[$count]="$file"
        ((count++))
    fi
done

if [ ${#files[@]} -eq 0 ]; then
    echo "No se encontraron registros de auditoría"
    exit 0
fi

# Opción para ver todos o uno específico
echo -e "${YELLOW}Opciones:${NC}"
echo "  [número] - Ver registro específico"
echo "  [a] - Ver todos los registros"
echo "  [s] - Generar resumen estadístico"
echo "  [q] - Salir"
echo ""
read -p "Selecciona una opción: " option

case "$option" in
    [0-9]*)
        if [ -n "${files[$option]}" ]; then
            echo ""
            echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
            echo -e "${BLUE}  VISUALIZANDO REGISTRO #$option${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
            echo ""
            
            # Mostrar con paginación
            less -R "${files[$option]}"
        else
            echo "❌ Opción inválida"
        fi
        ;;
    
    "a"|"A")
        for file in "${files[@]}"; do
            echo ""
            echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
            echo -e "${BLUE}  $(basename "$file")${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
            echo ""
            cat "$file"
            echo ""
        done | less -R
        ;;
    
    "s"|"S")
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}  RESUMEN ESTADÍSTICO DE AUDITORÍAS${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        
        total_setups=${#files[@]}
        total_success=0
        total_errors=0
        total_warnings=0
        
        for file in "${files[@]}"; do
            ((total_success += $(grep -c "\[SUCCESS\]" "$file" 2>/dev/null || echo 0)))
            ((total_errors += $(grep -c "\[ERROR\]" "$file" 2>/dev/null || echo 0)))
            ((total_warnings += $(grep -c "\[WARNING\]" "$file" 2>/dev/null || echo 0)))
        done
        
        echo "Total de configuraciones: $total_setups"
        echo "Total eventos exitosos: $total_success"
        echo "Total errores: $total_errors"
        echo "Total advertencias: $total_warnings"
        echo ""
        
        # Herramientas más instaladas
        echo "Herramientas instaladas con frecuencia:"
        grep -h "instalado" "${files[@]}" 2>/dev/null | sort | uniq -c | sort -rn | head -5
        echo ""
        
        # Errores más comunes
        if [ $total_errors -gt 0 ]; then
            echo "Errores más comunes:"
            grep -h "\[ERROR\]" "${files[@]}" 2>/dev/null | sort | uniq -c | sort -rn | head -5
            echo ""
        fi
        ;;
    
    "q"|"Q")
        echo "Saliendo..."
        exit 0
        ;;
    
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Visualización completada${NC}"
