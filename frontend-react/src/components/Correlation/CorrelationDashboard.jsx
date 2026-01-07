/**
 * CorrelationDashboard - Panel de correlación y alertas
 * v4.1 - Motor de detección con Sigma + ML
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  BellAlertIcon,
  ShieldExclamationIcon,
  ChartBarIcon,
  AdjustmentsHorizontalIcon,
  EyeIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  FunnelIcon,
  ArrowPathIcon,
  PlusIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

import api from '../../services/api';

// Colores por severidad
const SEVERITY_CONFIG = {
  critical: { color: 'bg-red-500', text: 'text-red-400', bg: 'bg-red-500/20', label: 'Crítica' },
  high: { color: 'bg-orange-500', text: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Alta' },
  medium: { color: 'bg-yellow-500', text: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Media' },
  low: { color: 'bg-blue-500', text: 'text-blue-400', bg: 'bg-blue-500/20', label: 'Baja' },
  info: { color: 'bg-gray-500', text: 'text-gray-400', bg: 'bg-gray-500/20', label: 'Info' }
};

// Tipos de detección
const DETECTION_TYPES = {
  sigma: { icon: '📋', label: 'Sigma Rule' },
  ml_anomaly: { icon: '🤖', label: 'ML Anomaly' },
  threshold: { icon: '📊', label: 'Threshold' },
  pattern: { icon: '🔍', label: 'Pattern Match' }
};

export default function CorrelationDashboard() {
  // Estado principal
  const [alerts, setAlerts] = useState([]);
  const [rules, setRules] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  
  // Estado de filtros
  const [severityFilter, setSeverityFilter] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [timeRange, setTimeRange] = useState('24h');
  
  // Estado de UI
  const [activeTab, setActiveTab] = useState('alerts'); // alerts, rules, analytics
  const [isLoading, setIsLoading] = useState(false);
  const [showRuleEditor, setShowRuleEditor] = useState(false);
  
  const alertsRef = useRef(null);

  // ============================================================================
  // CARGA DE DATOS
  // ============================================================================

  useEffect(() => {
    loadAlerts();
    loadRules();
    loadStatistics();
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [severityFilter, statusFilter, timeRange]);

  const loadAlerts = async () => {
    try {
      setIsLoading(true);
      const params = { limit: 50 };
      if (severityFilter.length > 0) {
        params.severity = severityFilter.join(',');
      }
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      
      const { data } = await api.get('/api/v41/correlation/alerts', { params });
      setAlerts(data.alerts || []);
    } catch (error) {
      console.error('Error loading alerts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadRules = async () => {
    try {
      const { data } = await api.get('/api/v41/correlation/rules');
      setRules(data.rules || []);
    } catch (error) {
      console.error('Error loading rules:', error);
    }
  };

  const loadStatistics = async () => {
    try {
      const { data } = await api.get('/api/v41/correlation/stats');
      setStatistics(data);
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  const playAlertSound = () => {
    // Sonido de alerta (opcional)
    try {
      const audio = new Audio('/alert.mp3');
      audio.volume = 0.3;
      audio.play().catch(() => {});
    } catch (e) {}
  };

  // ============================================================================
  // ACCIONES
  // ============================================================================

  const updateAlertStatus = async (alertId, newStatus) => {
    try {
      await api.patch(`/v41/correlation/alerts/${alertId}`, { status: newStatus });
      loadAlerts();
    } catch (error) {
      console.error('Error updating alert:', error);
    }
  };

  const toggleRule = async (ruleId, enabled) => {
    try {
      const action = enabled ? 'enable' : 'disable';
      await api.patch(`/v41/correlation/rules/${ruleId}/${action}`);
      loadRules();
    } catch (error) {
      console.error('Error toggling rule:', error);
    }
  };

  // ============================================================================
  // ESTADÍSTICAS CALCULADAS
  // ============================================================================

  const alertStats = useMemo(() => {
    const bySeverity = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    const byStatus = { new: 0, investigating: 0, resolved: 0, false_positive: 0 };
    
    alerts.forEach(alert => {
      if (bySeverity[alert.severity] !== undefined) bySeverity[alert.severity]++;
      if (byStatus[alert.status] !== undefined) byStatus[alert.status]++;
    });
    
    return { bySeverity, byStatus };
  }, [alerts]);

  // ============================================================================
  // RENDER
  // ============================================================================

  const renderAlertCard = (alert) => {
    const severity = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
    const detection = DETECTION_TYPES[alert.detection_type] || DETECTION_TYPES.sigma;
    
    return (
      <div
        key={alert.id}
        className={`bg-gray-800 rounded-lg border-l-4 ${severity.color.replace('bg-', 'border-')} hover:bg-gray-750 cursor-pointer transition-all`}
        onClick={() => setSelectedAlert(alert)}
      >
        <div className="p-4">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs rounded ${severity.bg} ${severity.text}`}>
                {severity.label}
              </span>
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <span>{detection.icon}</span>
                {detection.label}
              </span>
            </div>
            <span className="text-xs text-gray-500">
              {new Date(alert.created_at).toLocaleString()}
            </span>
          </div>
          
          <h3 className="font-medium text-white mb-1">{alert.rule_name || alert.title}</h3>
          <p className="text-sm text-gray-400 line-clamp-2">{alert.description}</p>
          
          {/* Indicadores */}
          {alert.indicators && alert.indicators.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {alert.indicators.slice(0, 3).map((indicator, idx) => (
                <span key={idx} className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300">
                  {indicator}
                </span>
              ))}
              {alert.indicators.length > 3 && (
                <span className="text-xs text-gray-500">+{alert.indicators.length - 3}</span>
              )}
            </div>
          )}
          
          {/* Footer */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-700">
            <span className={`text-xs px-2 py-0.5 rounded ${
              alert.status === 'new' ? 'bg-blue-500/20 text-blue-400' :
              alert.status === 'investigating' ? 'bg-yellow-500/20 text-yellow-400' :
              alert.status === 'resolved' ? 'bg-green-500/20 text-green-400' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {alert.status}
            </span>
            <div className="flex gap-1">
              <button
                onClick={(e) => { e.stopPropagation(); updateAlertStatus(alert.id, 'investigating'); }}
                className="p-1 hover:bg-yellow-500/20 rounded text-yellow-400"
                title="Investigar"
              >
                <EyeIcon className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); updateAlertStatus(alert.id, 'resolved'); }}
                className="p-1 hover:bg-green-500/20 rounded text-green-400"
                title="Resolver"
              >
                <CheckCircleIcon className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); updateAlertStatus(alert.id, 'false_positive'); }}
                className="p-1 hover:bg-gray-500/20 rounded text-gray-400"
                title="Falso positivo"
              >
                <XCircleIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderStatCards = () => (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      {Object.entries(SEVERITY_CONFIG).map(([key, config]) => (
        <div key={key} className={`${config.bg} rounded-lg p-4`}>
          <div className="flex items-center justify-between">
            <span className={`text-2xl font-bold ${config.text}`}>
              {alertStats.bySeverity[key] || 0}
            </span>
            <ShieldExclamationIcon className={`w-8 h-8 ${config.text} opacity-50`} />
          </div>
          <p className="text-sm text-gray-400 mt-1">{config.label}</p>
        </div>
      ))}
    </div>
  );

  const renderRulesTab = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-300">Reglas de Correlación</h3>
        <button
          onClick={() => setShowRuleEditor(true)}
          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-lg flex items-center gap-2 text-sm"
        >
          <PlusIcon className="w-4 h-4" />
          Nueva Regla
        </button>
      </div>
      
      {rules.map(rule => (
        <div key={rule.id} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h4 className="font-medium text-white">{rule.name}</h4>
                <span className={`px-2 py-0.5 text-xs rounded ${
                  SEVERITY_CONFIG[rule.severity]?.bg || 'bg-gray-500/20'
                } ${SEVERITY_CONFIG[rule.severity]?.text || 'text-gray-400'}`}>
                  {SEVERITY_CONFIG[rule.severity]?.label || rule.severity}
                </span>
              </div>
              <p className="text-sm text-gray-400">{rule.description}</p>
              
              {/* Rule type & conditions */}
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <DocumentTextIcon className="w-3 h-3" />
                  {rule.rule_type}
                </span>
                {rule.mitre_tactics && (
                  <span>MITRE: {rule.mitre_tactics.join(', ')}</span>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">
                {rule.match_count || 0} matches
              </span>
              <button
                onClick={() => toggleRule(rule.id, !rule.is_enabled)}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  rule.is_enabled ? 'bg-green-500' : 'bg-gray-600'
                }`}
              >
                <span className={`absolute top-0.5 ${rule.is_enabled ? 'right-0.5' : 'left-0.5'} w-4 h-4 bg-white rounded-full transition-all`} />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  const renderAnalytics = () => (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Total Alertas (24h)</p>
          <p className="text-2xl font-bold text-white">{statistics?.total_alerts_24h || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Reglas Activas</p>
          <p className="text-2xl font-bold text-white">{statistics?.active_rules || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Eventos Procesados</p>
          <p className="text-2xl font-bold text-white">{statistics?.events_processed || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-400">Tasa de Detección</p>
          <p className="text-2xl font-bold text-green-400">{statistics?.detection_rate || 0}%</p>
        </div>
      </div>
      
      {/* Top rules */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h4 className="font-medium text-white mb-4">Top Reglas Disparadas</h4>
        {(statistics?.top_rules || []).map((rule, idx) => (
          <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
            <span className="text-sm text-gray-300">{rule.name}</span>
            <span className="text-sm font-medium text-blue-400">{rule.count}</span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-600 rounded-lg flex items-center justify-center">
              <BellAlertIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Correlation Engine</h1>
              <p className="text-sm text-gray-400">Detección de Amenazas con Sigma + ML</p>
            </div>
          </div>
          
          {/* Live indicator */}
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-400">En vivo</span>
          </div>
        </div>
        
        {/* Tabs y filtros */}
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            {[
              { id: 'alerts', label: 'Alertas', icon: BellAlertIcon },
              { id: 'rules', label: 'Reglas', icon: AdjustmentsHorizontalIcon },
              { id: 'analytics', label: 'Analytics', icon: ChartBarIcon }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                  activeTab === tab.id
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
          
          {activeTab === 'alerts' && (
            <div className="flex items-center gap-2">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm"
              >
                <option value="1h">Última hora</option>
                <option value="24h">24 horas</option>
                <option value="7d">7 días</option>
                <option value="30d">30 días</option>
              </select>
              <button
                onClick={loadAlerts}
                className="p-2 hover:bg-gray-800 rounded-lg"
              >
                <ArrowPathIcon className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4" ref={alertsRef}>
        {activeTab === 'alerts' && (
          <>
            {renderStatCards()}
            <div className="space-y-4">
              {alerts.map(renderAlertCard)}
              {alerts.length === 0 && !isLoading && (
                <div className="text-center py-12 text-gray-500">
                  <ShieldExclamationIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No hay alertas en este período</p>
                </div>
              )}
            </div>
          </>
        )}
        
        {activeTab === 'rules' && renderRulesTab()}
        
        {activeTab === 'analytics' && renderAnalytics()}
      </div>
      
      {/* Alert Detail Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setSelectedAlert(null)}>
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-white">{selectedAlert.rule_name || selectedAlert.title}</h2>
                <p className="text-sm text-gray-400">ID: {selectedAlert.id}</p>
              </div>
              <button onClick={() => setSelectedAlert(null)} className="text-gray-400 hover:text-white">
                <XCircleIcon className="w-6 h-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-1">Descripción</h4>
                <p className="text-gray-200">{selectedAlert.description}</p>
              </div>
              
              {selectedAlert.indicators && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Indicadores</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedAlert.indicators.map((ind, idx) => (
                      <span key={idx} className="px-2 py-1 bg-gray-700 rounded text-sm">{ind}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedAlert.raw_data && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Datos Raw</h4>
                  <pre className="bg-gray-900 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedAlert.raw_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
