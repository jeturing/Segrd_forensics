import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

/**
 * Componente PlotlyChart reutilizable
 * Proporciona gráficos interactivos con Plotly
 * 
 * @param {Object} props
 * @param {Array} props.data - Array de objetos de datos para Plotly
 * @param {Object} props.layout - Configuración del layout de Plotly
 * @param {Object} props.config - Configuración adicional de Plotly
 * @param {string} props.type - Tipo de gráfico: 'bar', 'line', 'pie', 'scatter', 'heatmap'
 * @param {Object} props.chartData - Datos específicos del gráfico
 * @param {string} props.title - Título del gráfico
 * @param {boolean} props.onClick - Si se puede hacer clic en los datos
 * @param {Function} props.onPointClick - Callback cuando se hace clic en un punto
 * @param {string} props.className - Clases CSS adicionales
 */
export default function PlotlyChart({
  data,
  layout,
  config = {},
  type = 'bar',
  chartData = null,
  title = '',
  onClick = false,
  onPointClick = null,
  className = ''
}) {
  const defaultConfig = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    toImageButtonOptions: {
      format: 'png',
      filename: `chart_${Date.now()}`,
      height: 600,
      width: 800,
      scale: 2
    }
  };

  const mergedConfig = { ...defaultConfig, ...config };

  const defaultLayout = {
    autosize: true,
    margin: { l: 50, r: 20, t: title ? 40 : 20, b: 40 },
    paper_bgcolor: '#1f2937',
    plot_bgcolor: '#111827',
    font: { color: '#e5e7eb', family: 'system-ui', size: 11 },
    hovermode: 'closest',
    showlegend: true,
    legend: {
      bgcolor: '#1f2937',
      bordercolor: '#374151',
      borderwidth: 1,
      font: { size: 10 }
    },
    xaxis: {
      gridcolor: '#374151',
      tickfont: { color: '#9ca3af', size: 10 }
    },
    yaxis: {
      gridcolor: '#374151',
      tickfont: { color: '#9ca3af', size: 10 }
    },
    title: title ? {
      text: title,
      x: 0.5,
      xanchor: 'center',
      font: { size: 14, color: '#f3f4f6' }
    } : undefined
  };

  const mergedLayout = { ...defaultLayout, ...layout };

  // Generar datos automáticamente basados en chartData
  const chartDataProcessed = useMemo(() => {
    if (data && data.length > 0) {
      return data;
    }

    if (!chartData) return [];

    switch (type) {
      case 'bar':
        return [
          {
            x: chartData.labels || [],
            y: chartData.values || [],
            type: 'bar',
            marker: { color: '#3b82f6' },
            hovertemplate: '<b>%{x}</b><br>%{y}<extra></extra>'
          }
        ];

      case 'line':
        return [
          {
            x: chartData.labels || [],
            y: chartData.values || [],
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#3b82f6', width: 2 },
            marker: { size: 6, color: '#60a5fa' },
            fill: 'tozeroy',
            fillcolor: 'rgba(59, 130, 246, 0.1)',
            hovertemplate: '<b>%{x}</b><br>%{y}<extra></extra>'
          }
        ];

      case 'pie':
        return [
          {
            labels: chartData.labels || [],
            values: chartData.values || [],
            type: 'pie',
            marker: {
              colors: chartData.colors || [
                '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
                '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'
              ]
            },
            hovertemplate: '<b>%{label}</b><br>%{value}<extra></extra>'
          }
        ];

      case 'scatter':
        return [
          {
            x: chartData.x || [],
            y: chartData.y || [],
            type: 'scatter',
            mode: 'markers',
            marker: {
              size: chartData.sizes || 8,
              color: chartData.colors || '#3b82f6',
              opacity: 0.7
            },
            text: chartData.labels || [],
            hovertemplate: '<b>%{text}</b><br>X: %{x}<br>Y: %{y}<extra></extra>'
          }
        ];

      case 'heatmap':
        return [
          {
            z: chartData.matrix || [],
            x: chartData.xLabels || [],
            y: chartData.yLabels || [],
            type: 'heatmap',
            colorscale: 'Viridis',
            hovertemplate: 'X: %{x}<br>Y: %{y}<br>Value: %{z}<extra></extra>'
          }
        ];

      default:
        return [];
    }
  }, [data, chartData, type]);

  const handleClick = (event) => {
    if (onPointClick && event.points && event.points.length > 0) {
      onPointClick(event.points[0]);
    }
  };

  return (
    <div className={`w-full h-full ${className}`}>
      <Plot
        data={chartDataProcessed}
        layout={mergedLayout}
        config={mergedConfig}
        onClick={onClick ? handleClick : null}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
      />
    </div>
  );
}
