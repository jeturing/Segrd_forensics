# 🚀 Instalación y Configuración - PlotlyChart v4.2

## Requisitos Previos

- Node.js >= 18.0.0
- npm >= 9.0.0
- Proyecto React Vite configurado

## 1. Instalación de Dependencias

```bash
cd /home/hack/mcp-kali-forensics/frontend-react

# Instalar nuevas dependencias
npm install plotly.js react-plotly.js

# O actualizar todas las dependencias
npm install
```

## 2. Verificar Instalación

```bash
# Ver que las dependencias están instaladas
npm list plotly.js react-plotly.js

# Resultado esperado:
# ├── plotly.js@2.26.0
# └── react-plotly.js@2.11.2
```

## 3. Estructura de Archivos

```
frontend-react/src/components/
├── Common/
│   ├── PlotlyChart.jsx          ← Componente universal
│   └── index.js                 ← Exporta PlotlyChart
├── Dashboard/
│   ├── Dashboard.jsx            ← Integración principal
│   ├── StatCard.jsx             ← Mini charts
│   ├── ActivityFeed.jsx         ← Items accionables
│   ├── ChartComponents.jsx      ← 9 gráficos
│   └── index.js
└── Investigations/
    ├── Investigations.jsx        ← Integración
    ├── InvestigationCharts.jsx  ← 5 gráficos
    └── index.js
```

## 4. Iniciar Desarrollo

```bash
# Terminal 1: Backend
cd /home/hack/mcp-kali-forensics
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080

# Terminal 2: Frontend
cd frontend-react
npm run dev

# Abrirá en http://localhost:5173
```

## 5. Verificar Funcionalidad

### ✅ Test 1: ActivityFeed Accionable

1. Ir a `http://localhost:5173/dashboard`
2. Scroller a "Actividad Reciente"
3. Clickear en cualquier item de actividad
4. Debe navegar a `/active-investigation?case=IR-XXXX-XXX`

### ✅ Test 2: Stats Cards con Charts

1. Ver las 4 tarjetas KPI (Total, Activos, Agentes, Alertas)
2. Cada una debe mostrar un mini gráfico
3. Clickear en cualquier tarjeta navega a destino correcto

### ✅ Test 3: Dashboard Charts

1. Scrollear down en dashboard
2. Deben aparecer 9 gráficos diferentes:
   - Distribución de Casos (pie)
   - Tendencia de Casos (línea)
   - Alertas por Severidad (barras)
   - Mapa de Actividad (heatmap)
   - Herramientas Más Usadas (barras)
   - Estado de Agentes (scatter)
   - Tasa de Resolución (pie)
   - Tipo de Investigaciones (barras)
   - Análisis Combinado (línea+barras)

### ✅ Test 4: Investigaciones Charts

1. Ir a `/investigations`
2. Deben aparecer 5 gráficos:
   - Casos por Estado
   - Casos por Severidad
   - Timeline de Casos
   - Tasa de Resolución
   - Evolución de Casos

## 6. Troubleshooting

### Error: "Cannot find module 'plotly.js'"

```bash
# Reinstalar plotly.js
npm install --save plotly.js react-plotly.js

# Limpiar cache
rm -rf node_modules/.vite
npm cache clean --force
```

### Error: "PlotlyChart is not defined"

Verificar que está correctamente importado:
```jsx
import { PlotlyChart } from '../Common';
// O
import PlotlyChart from '../Common/PlotlyChart';
```

### Gráficos no aparecen

1. Abrir DevTools (F12)
2. Ver Console para errores
3. Verificar que hay datos disponibles
4. Revisar que el backend está enviando datos

```bash
# Test API
curl http://localhost:8080/api/cases -H "Authorization: Bearer {token}"
```

### Performance lento

- Limitar cantidad de datos mostrados
- Reducir frecuencia de actualizaciones
- Usar `useMemo` en componentes padre

```jsx
const chartData = useMemo(() => {
  // Procesamiento pesado aquí
  return data;
}, [data]);
```

## 7. Personalizar Gráficos

### Cambiar Colores

```jsx
<PlotlyChart
  type="bar"
  chartData={{
    labels: ['A', 'B', 'C'],
    values: [10, 20, 30],
    colors: ['#FF0000', '#00FF00', '#0000FF']  ← Personalizar aquí
  }}
/>
```

### Cambiar Tamaño

```jsx
<PlotlyChart
  chartData={data}
  className="h-96"  ← Cambiar altura
/>
```

### Cambiar Tema

En `PlotlyChart.jsx`, modificar `defaultLayout`:

```jsx
const defaultLayout = {
  paper_bgcolor: '#000000',      ← Fondo
  plot_bgcolor: '#1a1a1a',       ← Área de plot
  font: { color: '#FFFFFF' }     ← Texto
};
```

## 8. Agregar Nuevos Gráficos

### Paso 1: Crear componente

```jsx
// ChartComponents.jsx
export function MiNuevoGrafico({ data }) {
  const chartData = {
    labels: data?.labels || [],
    values: data?.values || []
  };

  return (
    <PlotlyChart
      type="bar"
      chartData={chartData}
      title="Mi Gráfico"
      className="h-80"
    />
  );
}
```

### Paso 2: Importar

```jsx
import { MiNuevoGrafico } from './ChartComponents';
```

### Paso 3: Usar

```jsx
<Card title="📊 Mi Gráfico">
  <MiNuevoGrafico data={{ labels: [...], values: [...] }} />
</Card>
```

## 9. Exportación de Gráficos a PNG

Automático con botón en hover:

1. Hover sobre cualquier gráfico
2. Click en botón de cámara (📷)
3. Se descargará PNG con nombre: `chart_{timestamp}.png`

## 10. Documentación de Referencia

- **Plotly.js:** https://plotly.com/javascript/
- **React-Plotly.js:** https://github.com/plotly/react-plotly.js
- **Tipos de gráficos:** `bar`, `line`, `pie`, `scatter`, `heatmap`, `box`, `histogram`

## 11. Comandos Útiles

```bash
# Desarrollo con hot reload
npm run dev

# Build para producción
npm run build

# Preview de build
npm run preview

# Lint de código
npm run lint

# Fix lint issues
npm run lint:fix

# Format código
npm run format

# Tests
npm run test
```

## 12. Variables de Entorno

Si necesitas personalización por entorno:

```bash
# .env.local
VITE_PLOTLY_MODE=interactive
VITE_CHART_HEIGHT=500
VITE_CHART_COLORS=#3b82f6,#10b981,#f59e0b
```

## 13. Soporte y Contacto

Para problemas o sugerencias:
- Crear issue en GitHub
- Contactar al equipo de desarrollo
- Revisar documentación en `/docs/PLOTLYCHART_IMPLEMENTATION_v4.2.md`

---

**¡Listo para usar PlotlyChart v4.2! 🎉**
