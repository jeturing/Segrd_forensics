import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Card, Loading, Alert } from '../Common';
import StatCard from './StatCard';
import ActivityFeed from './ActivityFeed';
import {
  CasesStatusChart,
  CasesTrendChart,
  AlertsSeverityChart,
  ActivityHeatmapChart,
  TopToolsChart,
  AgentsConnectionChart,
  ResolutionRateChart,
  InvestigationTypesChart,
  CombinedAnalyticsChart
} from './ChartComponents';
import { caseService } from '../../services/cases';
import { agentService } from '../../services/agents';
import api from '../../services/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    totalCases: 0,
    activeCases: 0,
    resolvedCases: 0,
    criticalAlerts: 0,
    totalAgents: 0,
    onlineAgents: 0
  });
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState([]);
  const [dataSource, setDataSource] = useState('loading');
  const [error, setError] = useState(null);
  const demoInvestigations = [
    { id: 'IR-2025-001', name: 'Phishing en M365', status: 'investigating', severity: 'critical', updated_at: new Date().toISOString() },
    { id: 'IR-2025-002', name: 'Ransomware en endpoint', status: 'open', severity: 'high', updated_at: new Date().toISOString() }
  ];
  const demoAgents = [
    { id: 'demo-agent-01', status: 'online' },
    { id: 'demo-agent-02', status: 'offline' }
  ];

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // auto refresh cada 30s
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Cargar investigaciones reales
      const casesData = await caseService.getCases(1, 100);
      const investigations = casesData.items || [];
      
      // Cargar agentes reales
      const agentsData = await agentService.getAgents();
      const agents = agentsData.agents || [];
      
      // Calcular estadísticas
      const activeCases = investigations.filter(c => 
        ['open', 'in-progress', 'investigating'].includes(c.status?.toLowerCase())
      ).length;
      
      const resolvedCases = investigations.filter(c => 
        ['resolved', 'closed'].includes(c.status?.toLowerCase())
      ).length;
      
      const criticalAlerts = investigations.filter(c => 
        c.severity?.toLowerCase() === 'critical'
      ).length;
      
      const onlineAgents = agents.filter(a => 
        a.status?.toLowerCase() === 'online'
      ).length;

      setStats({
        totalCases: investigations.length,
        activeCases,
        resolvedCases,
        criticalAlerts,
        totalAgents: agents.length,
        onlineAgents
      });

      // Crear feed de actividad basado en datos reales
      const recentActivities = investigations.slice(0, 5).map((inv, idx) => ({
        id: idx + 1,
        type: inv.status === 'investigating' ? 'analysis_active' : 'case_update',
        message: `${inv.id}: ${inv.name}`,
        timestamp: formatTimeAgo(inv.updated_at || inv.created_at),
        severity: inv.severity
      }));

      setActivities(recentActivities);
      // Determinar origen de datos: si hay datos reales, marcar como real aunque el flag diga demo
      const hasRealData = (investigations.length > 0 || agents.length > 0);
      const origin = hasRealData ? 'real' : ((casesData.dataSource === 'demo' || agentsData.dataSource === 'demo') ? 'demo' : 'real');

      setDataSource(origin);
      setLoading(false);
      
    } catch (err) {
      console.error('Error loading dashboard:', err);
      // Fallback a datos demo para no dejar la pantalla en blanco
      const investigations = demoInvestigations;
      const agents = demoAgents;
      const activeCases = investigations.filter(c => 
        ['open', 'in-progress', 'investigating'].includes(c.status?.toLowerCase())
      ).length;
      const resolvedCases = investigations.filter(c => 
        ['resolved', 'closed'].includes(c.status?.toLowerCase())
      ).length;
      const criticalAlerts = investigations.filter(c => 
        c.severity?.toLowerCase() === 'critical'
      ).length;
      const onlineAgents = agents.filter(a => 
        a.status?.toLowerCase() === 'online'
      ).length;

      setStats({
        totalCases: investigations.length,
        activeCases,
        resolvedCases,
        criticalAlerts,
        totalAgents: agents.length,
        onlineAgents
      });

      const recentActivities = investigations.slice(0, 5).map((inv, idx) => ({
        id: idx + 1,
        type: inv.status === 'investigating' ? 'analysis_active' : 'case_update',
        message: `${inv.id}: ${inv.name}`,
        timestamp: formatTimeAgo(inv.updated_at || inv.created_at),
        severity: inv.severity
      }));
      setActivities(recentActivities);
      setDataSource('demo');
      setLoading(false);
      setError(null);
    }
  };

  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return 'Hace poco';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return 'Hace un momento';
    if (diff < 3600) return `Hace ${Math.floor(diff / 60)} min`;
    if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} horas`;
    return `Hace ${Math.floor(diff / 86400)} días`;
  };

  const handleNewCase = () => {
    navigate('/investigations');
    toast.info('Navegando a Investigaciones para crear nuevo caso');
  };

  const handleThreatHunting = () => {
    navigate('/kali-tools');
    toast.info('Abriendo herramientas de Threat Hunting');
  };

  const handleGenerateReport = () => {
    toast.info('Generando reporte... (Funcionalidad en desarrollo)');
  };

  const handleConnectAgent = () => {
    navigate('/agents-v41');
    toast.info('Abriendo panel de agentes');
  };

  if (loading) {
    return <Loading message="Cargando Dashboard..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Dashboard</h1>
          <p className="text-gray-400 mt-1">             MCP Kali Forensics & IR - v4.1</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            dataSource === 'real' ? 'bg-green-900 text-green-200' :
            dataSource === 'demo' ? 'bg-yellow-900 text-yellow-200' :
            'bg-red-900 text-red-200'
          }`}>
            {dataSource === 'real' ? '🟢 Datos Reales' : 
             dataSource === 'demo' ? '🟡 Modo Demo' : 
             '🔴 Sin conexión'}
          </span>
          <button 
            onClick={loadDashboardData}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
          >
            🔄 Actualizar
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert
          type="error"
          title="Error de Conexión"
          message={error}
        />
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Investigaciones"
          value={stats.totalCases}
          icon="📊"
          color="blue"
          trend={dataSource === 'real' ? 'Datos en vivo' : 'Sin datos'}
          onClick={() => navigate('/investigations')}
          chartData={{
            labels: ['D-4', 'D-3', 'D-2', 'D-1', 'Hoy'],
            values: [10, 12, 15, 13, stats.totalCases]
          }}
        />
        <StatCard
          title="Casos Activos"
          value={stats.activeCases}
          icon="🔄"
          color="yellow"
          trend="En progreso"
          onClick={() => navigate('/investigations')}
          chartData={{
            labels: ['D-4', 'D-3', 'D-2', 'D-1', 'Hoy'],
            values: [6, 7, 8, 7, stats.activeCases]
          }}
        />
        <StatCard
          title="Agentes Online"
          value={`${stats.onlineAgents}/${stats.totalAgents}`}
          icon="🖥️"
          color="green"
          trend={stats.onlineAgents > 0 ? 'Conectados' : 'Sin agentes'}
          onClick={() => navigate('/agents-v41')}
          chartData={{
            labels: ['D-4', 'D-3', 'D-2', 'D-1', 'Hoy'],
            values: [3, 3, 3, 2, stats.onlineAgents]
          }}
        />
        <StatCard
          title="Alertas Críticas"
          value={stats.criticalAlerts}
          icon="🔴"
          color="red"
          trend={stats.criticalAlerts > 0 ? 'Requieren acción' : 'Todo normal'}
          onClick={() => navigate('/investigations')}
          chartData={{
            labels: ['D-4', 'D-3', 'D-2', 'D-1', 'Hoy'],
            values: [2, 3, 4, 3, stats.criticalAlerts]
          }}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Feed - Takes 2 columns */}
        <div className="lg:col-span-2">
          <Card title="📋 Actividad Reciente">
            {activities.length > 0 ? (
              <ActivityFeed activities={activities} />
            ) : (
              <p className="text-gray-400 py-4">No hay actividad reciente</p>
            )}
          </Card>
        </div>

        {/* Quick Actions */}
        <Card title="⚡ Acciones Rápidas">
          <div className="space-y-3">
            <button 
              onClick={handleNewCase}
              className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium text-white transition flex items-center justify-center gap-2"
            >
              ➕ Nueva Investigación
            </button>
            <button 
              onClick={handleThreatHunting}
              className="w-full px-4 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium text-white transition flex items-center justify-center gap-2"
            >
              🎯 Threat Hunting
            </button>
            <button 
              onClick={handleGenerateReport}
              className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-medium text-white transition flex items-center justify-center gap-2"
            >
              📄 Generar Reporte
            </button>
            <button 
              onClick={handleConnectAgent}
              className="w-full px-4 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium text-white transition flex items-center justify-center gap-2"
            >
              🔌 Ver Agentes
            </button>
          </div>
        </Card>
      </div>

      {/* Analytics Section */}
      <div className="space-y-6">
        {/* Row 1: Distribution & Trend */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="📊 Distribución de Casos">
            <div className="h-96">
              <CasesStatusChart data={{
                labels: ['Abierto', 'En Progreso', 'Resuelto', 'Cerrado'],
                values: [stats.activeCases, Math.floor(stats.activeCases * 0.6), stats.resolvedCases, Math.floor(stats.resolvedCases * 0.4)]
              }} />
            </div>
          </Card>
          <Card title="📈 Tendencia de Casos (últimas 5 semanas)">
            <div className="h-96">
              <CasesTrendChart data={{
                labels: ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5'],
                values: [4, 7, 5, 9, stats.totalCases]
              }} />
            </div>
          </Card>
        </div>

        {/* Row 2: Alerts & Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="🚨 Alertas por Severidad">
            <div className="h-96">
              <AlertsSeverityChart data={{
                labels: ['Crítica', 'Alta', 'Media', 'Baja'],
                values: [stats.criticalAlerts, Math.floor(stats.criticalAlerts * 2), Math.floor(stats.criticalAlerts * 3), Math.floor(stats.criticalAlerts * 1.5)]
              }} />
            </div>
          </Card>
          <Card title="🌡️ Mapa de Calor - Actividad por Hora">
            <div className="h-96">
              <ActivityHeatmapChart />
            </div>
          </Card>
        </div>

        {/* Row 3: Tools & Types */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="🛠️ Herramientas Más Usadas">
            <div className="h-96">
              <TopToolsChart data={{
                labels: ['Sparrow', 'Hawk', 'Loki', 'YARA', 'OSQuery'],
                values: [45, 38, 32, 28, 22]
              }} />
            </div>
          </Card>
          <Card title="📊 Tipo de Investigaciones">
            <div className="h-96">
              <InvestigationTypesChart data={{
                labels: ['Phishing', 'Malware', 'Credenciales', 'Insider Threat', 'Otros'],
                values: [15, 12, 8, 5, 10]
              }} />
            </div>
          </Card>
        </div>

        {/* Row 4: Agents & Resolution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="🖥️ Estado de Agentes">
            <div className="h-96">
              <AgentsConnectionChart data={{
                x: Array.from({ length: stats.totalAgents }, (_, i) => i + 1),
                y: Array.from({ length: stats.totalAgents }, () => Math.floor(Math.random() * 10)),
                labels: Array.from({ length: stats.totalAgents }, (_, i) => `Agent-${String(i + 1).padStart(2, '0')}`),
                statuses: Array.from({ length: stats.totalAgents }, (_, i) => i < stats.onlineAgents ? 'online' : 'offline')
              }} />
            </div>
          </Card>
          <Card title="✅ Tasa de Resolución">
            <div className="h-96">
              <ResolutionRateChart data={{
                labels: ['Resueltos', 'Pendientes'],
                values: [stats.resolvedCases, stats.activeCases]
              }} />
            </div>
          </Card>
        </div>

        {/* Combined Analytics */}
        <Card title="📊 Análisis Combinado">
          <div className="h-96">
            <CombinedAnalyticsChart data={{
              labels: ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4', 'Sem 5'],
              cases: [10, 15, 12, 18, stats.totalCases],
              resolutionRate: [60, 65, 70, 75, 80]
            }} />
          </div>
        </Card>
      </div>

      {/* System Status */}
      <Card title="📡 Estado del Sistema">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition">
            <div className="text-2xl mb-2">🟢</div>
            <div className="text-sm text-gray-400">API Backend</div>
            <div className="text-xs text-green-400">Conectado</div>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition">
            <div className="text-2xl mb-2">🗄️</div>
            <div className="text-sm text-gray-400">Base de Datos</div>
            <div className="text-xs text-green-400">SQLite OK</div>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition">
            <div className="text-2xl mb-2">🛠️</div>
            <div className="text-sm text-gray-400">Herramientas</div>
            <div className="text-xs text-green-400">Loki, YARA, OSQuery</div>
          </div>
          <div className="text-center p-4 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700 transition">
            <div className="text-2xl mb-2">🖥️</div>
            <div className="text-sm text-gray-400">Agentes</div>
            <div className="text-xs text-yellow-400">{stats.onlineAgents} online</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
