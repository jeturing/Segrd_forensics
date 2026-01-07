import React from 'react';
import { PlotlyChart } from '../Common';

/**
 * Gráfico de Casos por Estado
 */
export function CasesStatusChart({ data }) {
  const chartData = {
    labels: data?.labels || ['Abierto', 'En Progreso', 'Resuelto', 'Cerrado'],
    values: data?.values || [12, 8, 5, 3],
    colors: ['#ef4444', '#f59e0b', '#10b981', '#6b7280']
  };

  return (
    <PlotlyChart
      type="pie"
      chartData={chartData}
      title="Distribución de Casos"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Tendencia de Casos
 */
export function CasesTrendChart({ data }) {
  const chartData = {
    labels: data?.labels || ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5'],
    values: data?.values || [4, 7, 5, 9, 12]
  };

  return (
    <PlotlyChart
      type="line"
      chartData={chartData}
      title="Tendencia de Casos (últimas 5 semanas)"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Severidad de Alertas
 */
export function AlertsSeverityChart({ data }) {
  const chartData = {
    labels: data?.labels || ['Crítica', 'Alta', 'Media', 'Baja'],
    values: data?.values || [5, 12, 18, 8],
    colors: ['#dc2626', '#ea580c', '#f59e0b', '#3b82f6']
  };

  return (
    <PlotlyChart
      type="bar"
      chartData={chartData}
      title="Alertas por Severidad"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Actividad por Hora
 */
export function ActivityHeatmapChart({ data }) {
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  const days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

  // Generar matriz de actividad
  const matrix = days.map(() =>
    hours.map(() => Math.floor(Math.random() * 100))
  );

  const chartData = {
    matrix,
    xLabels: hours,
    yLabels: days
  };

  return (
    <PlotlyChart
      type="heatmap"
      chartData={chartData}
      title="Mapa de Calor - Actividad por Hora"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Herramientas Más Usadas
 */
export function TopToolsChart({ data }) {
  const chartData = {
    labels: data?.labels || ['Sparrow', 'Hawk', 'Loki', 'YARA', 'OSQuery'],
    values: data?.values || [45, 38, 32, 28, 22]
  };

  return (
    <PlotlyChart
      type="bar"
      chartData={chartData}
      title="Herramientas Más Utilizadas"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Agentes Conectados (Scatter)
 */
export function AgentsConnectionChart({ data }) {
  const chartData = {
    x: data?.x || [1, 2, 3, 4, 5, 6, 7, 8],
    y: data?.y || [4, 7, 2, 9, 6, 3, 8, 5],
    labels: data?.labels || ['Agent-01', 'Agent-02', 'Agent-03', 'Agent-04', 'Agent-05', 'Agent-06', 'Agent-07', 'Agent-08'],
    colors: data?.statuses?.map(s => s === 'online' ? '#10b981' : '#6b7280') || '#3b82f6'
  };

  return (
    <PlotlyChart
      type="scatter"
      chartData={chartData}
      title="Estado de Agentes"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Tasa de Resolución
 */
export function ResolutionRateChart({ data }) {
  const chartData = {
    labels: data?.labels || ['Resueltos', 'Aún Pendientes'],
    values: data?.values || [42, 18],
    colors: ['#10b981', '#ef4444']
  };

  return (
    <PlotlyChart
      type="pie"
      chartData={chartData}
      title="Tasa de Resolución (%)"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Investigaciones por Tipo
 */
export function InvestigationTypesChart({ data }) {
  const chartData = {
    labels: data?.labels || ['Phishing', 'Malware', 'Compromiso de Credenciales', 'Insider Threat', 'Otros'],
    values: data?.values || [15, 12, 8, 5, 10]
  };

  return (
    <PlotlyChart
      type="bar"
      chartData={chartData}
      title="Investigaciones por Tipo"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico Combinado de Línea y Barra
 */
export function CombinedAnalyticsChart({ data }) {
  const layout = {
    title: 'Análisis Combinado - Casos vs Resoluciones',
    xaxis: {
      title: 'Período'
    },
    yaxis: {
      title: 'Cantidad de Casos'
    },
    yaxis2: {
      title: 'Tasa de Resolución (%)',
      overlaying: 'y',
      side: 'right'
    }
  };

  const chartDataCombined = [
    {
      x: data?.labels || ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5'],
      y: data?.cases || [10, 15, 12, 18, 22],
      type: 'bar',
      name: 'Casos Nuevos',
      marker: { color: '#3b82f6' }
    },
    {
      x: data?.labels || ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5'],
      y: data?.resolutionRate || [60, 65, 70, 75, 80],
      type: 'scatter',
      mode: 'lines+markers',
      name: 'Tasa de Resolución',
      line: { color: '#10b981', width: 3 },
      yaxis: 'y2'
    }
  ];

  return (
    <PlotlyChart
      data={chartDataCombined}
      layout={layout}
      title=""
      className="w-full h-full"
    />
  );
}
