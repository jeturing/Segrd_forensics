import React from 'react';
import { PlotlyChart } from '../Common';

/**
 * Gráfico de Casos por Estado en Investigaciones
 */
export function CasesByStateChart({ cases }) {
  const statusCount = {
    open: cases.filter(c => c.status?.toLowerCase() === 'open').length,
    'in-progress': cases.filter(c => ['in-progress', 'investigating'].includes(c.status?.toLowerCase())).length,
    resolved: cases.filter(c => c.status?.toLowerCase() === 'resolved').length,
    closed: cases.filter(c => c.status?.toLowerCase() === 'closed').length
  };

  const chartData = {
    labels: Object.keys(statusCount).map(k => k.charAt(0).toUpperCase() + k.slice(1)),
    values: Object.values(statusCount),
    colors: ['#3b82f6', '#f59e0b', '#10b981', '#6b7280']
  };

  return (
    <PlotlyChart
      type="bar"
      chartData={chartData}
      title="Casos por Estado"
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Severidad de Casos en Investigaciones
 */
export function CasesBySeverityChart({ cases }) {
  const severityCount = {
    critical: cases.filter(c => c.severity?.toLowerCase() === 'critical').length,
    high: cases.filter(c => c.severity?.toLowerCase() === 'high').length,
    medium: cases.filter(c => c.severity?.toLowerCase() === 'medium').length,
    low: cases.filter(c => c.severity?.toLowerCase() === 'low').length
  };

  const chartData = {
    labels: ['Crítica', 'Alta', 'Media', 'Baja'],
    values: Object.values(severityCount),
    colors: ['#dc2626', '#ea580c', '#f59e0b', '#3b82f6']
  };

  return (
    <PlotlyChart
      type="pie"
      chartData={chartData}
      title="Severidad de Casos"
      className="w-full h-full"
    />
  );
}

/**
 * Timeline de Casos Recientes
 */
export function RecentCasesTimelineChart({ cases }) {
  const sortedCases = [...cases]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 10);

  const labels = sortedCases.map(c => {
    const date = new Date(c.created_at);
    return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
  });

  const severityValues = sortedCases.map(c => {
    switch (c.severity?.toLowerCase()) {
      case 'critical': return 4;
      case 'high': return 3;
      case 'medium': return 2;
      case 'low': return 1;
      default: return 0;
    }
  });

  const chartData = {
    labels,
    values: severityValues
  };

  return (
    <PlotlyChart
      type="scatter"
      chartData={{
        x: labels,
        y: severityValues,
        labels: sortedCases.map(c => c.id),
        colors: sortedCases.map(c => {
          switch (c.severity?.toLowerCase()) {
            case 'critical': return '#dc2626';
            case 'high': return '#ea580c';
            case 'medium': return '#f59e0b';
            case 'low': return '#3b82f6';
            default: return '#6b7280';
          }
        })
      }}
      title="Timeline de Casos Recientes"
      className="w-full h-full"
    />
  );
}

/**
 * Estadísticas de Resolución
 */
export function ResolutionStatsChart({ cases }) {
  const resolvedCases = cases.filter(c => c.status?.toLowerCase() === 'resolved').length;
  const totalCases = cases.length;
  const resolutionRate = totalCases > 0 ? Math.round((resolvedCases / totalCases) * 100) : 0;

  const chartData = {
    labels: ['Resueltos', 'Pendientes'],
    values: [resolvedCases, totalCases - resolvedCases],
    colors: ['#10b981', '#ef4444']
  };

  return (
    <PlotlyChart
      type="pie"
      chartData={chartData}
      title={`Tasa de Resolución: ${resolutionRate}%`}
      className="w-full h-full"
    />
  );
}

/**
 * Gráfico de Evolución de Casos
 */
export function CasesEvolutionChart({ cases }) {
  // Simular datos de evolución (últimos 7 días)
  const days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return date.toLocaleDateString('es-ES', { weekday: 'short' });
  });

  const casesPerDay = Array.from({ length: 7 }, () => Math.floor(Math.random() * 5) + 1);

  const chartData = {
    labels: days,
    values: casesPerDay
  };

  return (
    <PlotlyChart
      type="line"
      chartData={chartData}
      title="Evolución de Casos (últimos 7 días)"
      className="w-full h-full"
    />
  );
}
