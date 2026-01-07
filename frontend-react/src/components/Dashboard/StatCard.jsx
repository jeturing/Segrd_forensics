import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';

const colorMap = {
  blue: 'bg-blue-600',
  green: 'bg-green-600',
  yellow: 'bg-yellow-600',
  red: 'bg-red-600',
  purple: 'bg-purple-600'
};

const colorPlotly = {
  blue: '#3b82f6',
  green: '#10b981',
  yellow: '#f59e0b',
  red: '#ef4444',
  purple: '#8b5cf6'
};

export default function StatCard({
  title,
  value,
  icon,
  color = 'blue',
  trend,
  onClick,
  chartData = null // { labels: [], values: [] }
}) {
  const [miniChartData, setMiniChartData] = useState([]);

  useEffect(() => {
    if (chartData && chartData.labels && chartData.values) {
      setMiniChartData([
        {
          x: chartData.labels.slice(0, 7), // Últimos 7 puntos
          y: chartData.values.slice(0, 7),
          type: 'scatter',
          mode: 'lines+markers',
          line: { color: colorPlotly[color], width: 2 },
          marker: { size: 4 },
          fill: 'tozeroy',
          fillcolor: `${colorPlotly[color]}33`,
          hovertemplate: '%{x}: %{y}<extra></extra>'
        }
      ]);
    }
  }, [chartData, color]);

  return (
    <div 
      className={`card ${onClick ? 'cursor-pointer hover:bg-gray-700/50 transition' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <p className="text-gray-400 text-sm mb-2">{title}</p>
          <p className="text-3xl font-bold text-gray-100">{value}</p>
          {trend && <p className="text-xs text-gray-500 mt-2">{trend}</p>}
        </div>
        <div className={`${colorMap[color]} w-12 h-12 rounded-lg flex items-center justify-center text-2xl`}>
          {icon}
        </div>
      </div>
      
      {/* Mini Chart */}
      {miniChartData.length > 0 && (
        <div className="mt-4 -mx-2 -mb-2">
          <Plot
            data={miniChartData}
            layout={{
              width: 300,
              height: 80,
              margin: { l: 20, r: 20, t: 10, b: 20 },
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              font: { size: 10, color: '#9ca3af' },
              xaxis: {
                showgrid: false,
                zeroline: false,
                showticklabels: false
              },
              yaxis: {
                showgrid: true,
                gridcolor: '#374151',
                showticklabels: false
              },
              hovermode: 'x unified',
              showlegend: false
            }}
            config={{
              displayModeBar: false,
              responsive: true,
              staticPlot: false
            }}
            style={{ width: '100%' }}
          />
        </div>
      )}
      {miniChartData.length > 0 && !Plot && (
        <div className="mt-4 h-20 bg-gray-700 rounded animate-pulse flex items-center justify-center text-xs text-gray-400">
          Cargando gráfico...
        </div>
      )}
    </div>
  );
}
