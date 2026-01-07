/**
 * PlaybookRunner - Gestión y ejecución de playbooks SOAR
 * v4.1 - Automatización de respuesta a incidentes
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  PlayIcon,
  StopIcon,
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  ClockIcon,
  BoltIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ChevronRightIcon,
  Cog6ToothIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  EyeIcon,
  CommandLineIcon
} from '@heroicons/react/24/outline';

import api from '../../services/api';

// Colores por tipo de trigger
const TRIGGER_COLORS = {
  manual: 'from-blue-500 to-blue-600',
  scheduled: 'from-purple-500 to-purple-600',
  threshold: 'from-orange-500 to-orange-600',
  pattern: 'from-red-500 to-red-600'
};

// Iconos por tipo de acción
const ACTION_ICONS = {
  execute_tool: '🔧',
  create_alert: '🚨',
  send_notification: '📧',
  isolate_host: '🔒',
  block_ip: '🚫',
  collect_evidence: '📦',
  update_case: '📝',
  escalate: '⬆️',
  enrich_ioc: '🔍',
  create_ticket: '🎫'
};

export default function PlaybookRunner() {
  // Estado principal
  const [playbooks, setPlaybooks] = useState([]);
  const [selectedPlaybook, setSelectedPlaybook] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [activeExecution, setActiveExecution] = useState(null);
  
  // Estado de UI
  const [activeTab, setActiveTab] = useState('library'); // library, execution, create
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // Estado de ejecución en tiempo real
  const [executionSteps, setExecutionSteps] = useState([]);
  const [executionLogs, setExecutionLogs] = useState([]);
  
  // WebSocket para updates en tiempo real
  const pollRef = useRef(null);

  // ============================================================================
  // CARGA DE DATOS
  // ============================================================================

  useEffect(() => {
    loadPlaybooks();
    loadExecutions();
  }, []);

  useEffect(() => {
    if (activeExecution) {
      startExecutionPolling(activeExecution.id);
    }
    return () => {
      stopExecutionPolling();
    };
  }, [activeExecution]);

  const loadPlaybooks = async () => {
    try {
      setIsLoading(true);
      const { data } = await api.get('/api/v41/playbooks');
      setPlaybooks(data.playbooks || []);
    } catch (error) {
      console.error('Error loading playbooks:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadExecutions = async () => {
    try {
      const { data } = await api.get('/api/v41/playbooks/executions', {
        params: { limit: 20 }
      });
      setExecutions(data.executions || []);
    } catch (error) {
      console.error('Error loading executions:', error);
    }
  };

  const refreshExecution = async (executionId) => {
    try {
      const { data } = await api.get(`/v41/playbooks/executions/${executionId}`);
      setActiveExecution((prev) => prev ? { ...prev, status: data.status } : { id: executionId, status: data.status });
      setExecutionSteps(data.steps || []);
      
      if (data.status && data.status !== 'running') {
        stopExecutionPolling();
        loadExecutions();
      }
    } catch (error) {
      console.error('Error fetching execution status:', error);
    }
  };

  const startExecutionPolling = (executionId) => {
    stopExecutionPolling();
    refreshExecution(executionId);
    pollRef.current = setInterval(() => refreshExecution(executionId), 3000);
  };

  const stopExecutionPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  // ============================================================================
  // ACCIONES
  // ============================================================================

  const executePlaybook = async (playbookId, context = {}) => {
    try {
      setIsLoading(true);
      const { data } = await api.post(`/v41/playbooks/${playbookId}/execute`, {
        input_data: context
      });
      
      if (data.execution_id) {
        setActiveExecution({ id: data.execution_id, status: data.status || 'running', playbook_id: playbookId });
        setExecutionSteps([]);
        setExecutionLogs([]);
        setActiveTab('execution');
      }
    } catch (error) {
      console.error('Error executing playbook:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const stopPlaybook = async (executionId) => {
    try {
      await api.post(`/v41/playbooks/executions/${executionId}/cancel`);
      loadExecutions();
    } catch (error) {
      console.error('Error stopping playbook:', error);
    }
  };

  const deletePlaybook = async (playbookId) => {
    if (!confirm('¿Eliminar este playbook?')) return;
    
    try {
      await api.delete(`/v41/playbooks/${playbookId}`);
      loadPlaybooks();
    } catch (error) {
      console.error('Error deleting playbook:', error);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  const renderPlaybookCard = (playbook) => (
    <div
      key={playbook.id}
      className="bg-gray-800 rounded-lg border border-gray-700 hover:border-blue-500 transition-all cursor-pointer overflow-hidden"
      onClick={() => setSelectedPlaybook(playbook)}
    >
      {/* Header */}
      <div className={`h-2 bg-gradient-to-r ${TRIGGER_COLORS[playbook.trigger_type] || TRIGGER_COLORS.manual}`} />
      
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="font-semibold text-white">{playbook.name}</h3>
            <p className="text-sm text-gray-400 line-clamp-2">{playbook.description}</p>
          </div>
          <span className={`px-2 py-1 text-xs rounded ${playbook.is_enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'}`}>
            {playbook.is_enabled ? 'Activo' : 'Inactivo'}
          </span>
        </div>
        
        {/* Steps preview */}
        <div className="flex items-center gap-1 my-3">
          {(playbook.steps || []).slice(0, 5).map((step, idx) => (
            <React.Fragment key={idx}>
              <span className="w-8 h-8 flex items-center justify-center bg-gray-700 rounded text-sm">
                {ACTION_ICONS[step.action_type] || '⚡'}
              </span>
              {idx < Math.min(playbook.steps?.length - 1, 4) && (
                <ChevronRightIcon className="w-3 h-3 text-gray-500" />
              )}
            </React.Fragment>
          ))}
          {playbook.steps?.length > 5 && (
            <span className="text-xs text-gray-500">+{playbook.steps.length - 5}</span>
          )}
        </div>
        
        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <BoltIcon className="w-3 h-3" />
            {playbook.trigger_type}
          </span>
          <div className="flex gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); executePlaybook(playbook.id); }}
              className="p-1 hover:bg-green-500/20 rounded text-green-400"
              title="Ejecutar"
            >
              <PlayIcon className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); deletePlaybook(playbook.id); }}
              className="p-1 hover:bg-red-500/20 rounded text-red-400"
              title="Eliminar"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderExecutionMonitor = () => (
    <div className="space-y-4">
      {/* Header de ejecución */}
      {activeExecution && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-white">Ejecución: {activeExecution.id?.slice(0, 8)}</h3>
              <p className="text-sm text-gray-400">Estado: {activeExecution.status}</p>
            </div>
            {activeExecution.status === 'running' && (
              <button
                onClick={() => stopPlaybook(activeExecution.id)}
                className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg flex items-center gap-2 hover:bg-red-500/30"
              >
                <StopIcon className="w-4 h-4" />
                Detener
              </button>
            )}
          </div>
          
          {/* Progress steps */}
          <div className="space-y-2">
            {executionSteps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-3 p-2 bg-gray-700/50 rounded">
                <span className="w-6 h-6 flex items-center justify-center rounded-full text-sm bg-gray-600">
                  {step.status === 'running' ? (
                    <ArrowPathIcon className="w-4 h-4 animate-spin text-blue-400" />
                  ) : step.status === 'completed' ? (
                    <CheckCircleIcon className="w-4 h-4 text-green-400" />
                  ) : step.status === 'failed' ? (
                    <XCircleIcon className="w-4 h-4 text-red-400" />
                  ) : (
                    idx + 1
                  )}
                </span>
                <div className="flex-1">
                  <p className="text-sm text-white">{step.action}</p>
                  {step.result && (
                    <p className="text-xs text-gray-400">{JSON.stringify(step.result).slice(0, 100)}</p>
                  )}
                </div>
                <span className="text-xs text-gray-500">
                  {step.startedAt && new Date(step.startedAt).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Logs */}
      <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm max-h-64 overflow-y-auto">
        {executionLogs.length === 0 ? (
          <p className="text-gray-500">Esperando logs...</p>
        ) : (
          executionLogs.map((log, idx) => (
            <div key={idx} className="text-gray-300">{log}</div>
          ))
        )}
      </div>
    </div>
  );

  const renderExecutionHistory = () => (
    <div className="space-y-2">
      <h3 className="font-medium text-gray-300 mb-3">Historial de Ejecuciones</h3>
      {executions.map((exec) => (
        <div
          key={exec.id}
          className="flex items-center justify-between p-3 bg-gray-800 rounded-lg hover:bg-gray-700 cursor-pointer"
          onClick={() => setActiveExecution(exec)}
        >
          <div className="flex items-center gap-3">
            <span className={`w-2 h-2 rounded-full ${
              exec.status === 'completed' ? 'bg-green-500' :
              exec.status === 'failed' ? 'bg-red-500' :
              exec.status === 'running' ? 'bg-blue-500 animate-pulse' :
              'bg-gray-500'
            }`} />
            <div>
              <p className="text-sm text-white">{exec.playbook_name || exec.playbook_id?.slice(0, 8)}</p>
              <p className="text-xs text-gray-500">
                {new Date(exec.started_at).toLocaleString()}
              </p>
            </div>
          </div>
          <span className={`text-xs px-2 py-1 rounded ${
            exec.status === 'completed' ? 'bg-green-500/20 text-green-400' :
            exec.status === 'failed' ? 'bg-red-500/20 text-red-400' :
            'bg-blue-500/20 text-blue-400'
          }`}>
            {exec.status}
          </span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
              <BoltIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">SOAR Playbooks</h1>
              <p className="text-sm text-gray-400">Automatización de Respuesta a Incidentes</p>
            </div>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg flex items-center gap-2"
          >
            <PlusIcon className="w-5 h-5" />
            Nuevo Playbook
          </button>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2">
          {[
            { id: 'library', label: 'Biblioteca', icon: DocumentTextIcon },
            { id: 'execution', label: 'Ejecución', icon: PlayIcon },
            { id: 'history', label: 'Historial', icon: ClockIcon }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'library' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {playbooks.map(renderPlaybookCard)}
            {playbooks.length === 0 && !isLoading && (
              <div className="col-span-full text-center py-12 text-gray-500">
                <DocumentTextIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No hay playbooks configurados</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 text-purple-400 hover:text-purple-300"
                >
                  Crear el primero
                </button>
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'execution' && renderExecutionMonitor()}
        
        {activeTab === 'history' && renderExecutionHistory()}
      </div>
    </div>
  );
}
