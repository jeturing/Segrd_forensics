/**
 * ToolExecutor - Ejecución híbrida de herramientas v4.1
 * Soporta ejecución local (MCP) y remota (Agents)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PlayIcon,
  StopIcon,
  ServerIcon,
  ComputerDesktopIcon,
  CloudIcon,
  CommandLineIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  QueueListIcon,
  SignalIcon
} from '@heroicons/react/24/outline';

import api from '../../services/api';

// Targets de ejecución
const EXECUTION_TARGETS = [
  { id: 'local', label: 'Local (MCP)', icon: ServerIcon, description: 'Ejecutar en este servidor' },
  { id: 'agent', label: 'Remote Agent', icon: CloudIcon, description: 'Ejecutar en agente remoto' }
];

// Estados de ejecución
const STATUS_CONFIG = {
  queued: { color: 'bg-gray-500', text: 'text-gray-400', label: 'En cola' },
  running: { color: 'bg-blue-500', text: 'text-blue-400', label: 'Ejecutando', animate: true },
  success: { color: 'bg-green-500', text: 'text-green-400', label: 'Completado' },
  completed: { color: 'bg-green-500', text: 'text-green-400', label: 'Completado' },
  failed: { color: 'bg-red-500', text: 'text-red-400', label: 'Fallido' },
  timeout: { color: 'bg-orange-500', text: 'text-orange-400', label: 'Timeout' },
  cancelled: { color: 'bg-gray-500', text: 'text-gray-400', label: 'Cancelado' }
};

export default function ToolExecutor({ toolName, toolParams = [], caseId = null, onComplete }) {
  // Estado de configuración
  const [target, setTarget] = useState('local');
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agents, setAgents] = useState([]);
  const [parameters, setParameters] = useState({});
  const [timeout, setTimeout] = useState(300);
  
  // Estado de ejecución
  const [executionId, setExecutionId] = useState(null);
  const [status, setStatus] = useState(null);
  const [output, setOutput] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  
  // Estado de cola
  const [queue, setQueue] = useState([]);
  const [recentExecutions, setRecentExecutions] = useState([]);
  
  // Estado de UI
  const [isExpanded, setIsExpanded] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  
  const outputRef = useRef(null);
  const pollRef = useRef(null);

  // ============================================================================
  // CARGA DE DATOS
  // ============================================================================

  useEffect(() => {
    loadAgents();
    loadQueue();
    loadRecentExecutions();
    
    // Inicializar parámetros por defecto
    const defaultParams = {};
    toolParams.forEach(param => {
      if (param.default !== undefined) {
        defaultParams[param.name] = param.default;
      }
    });
    setParameters(defaultParams);
  }, [toolParams]);

  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output, autoScroll]);

  useEffect(() => () => stopExecutionPolling(), []);

  const loadAgents = async () => {
    try {
      const { data } = await api.get('/api/v41/agents/', {
        params: { status: 'online' }
      });
      setAgents(data.agents || []);
    } catch (error) {
      console.error('Error loading agents:', error);
    }
  };

  const loadQueue = async () => {
    try {
      const { data } = await api.get('/api/v41/tools/queue');
      setQueue(data.queue || []);
    } catch (error) {
      console.error('Error loading queue:', error);
    }
  };

  const loadRecentExecutions = async () => {
    try {
      const { data } = await api.get('/api/v41/tools/executions', {
        params: { limit: 10 }
      });
      setRecentExecutions(data.executions || []);
    } catch (error) {
      console.error('Error loading executions:', error);
    }
  };

  // ============================================================================
  // WEBSOCKET
  // ============================================================================

  const fetchExecutionOutput = async (execId) => {
    try {
      const { data } = await api.get(`/v41/tools/executions/${execId}/output`);
      if (data.output) {
        const lines = data.output.split('\n').filter(Boolean).map((line) => ({
          stream: 'stdout',
          data: line,
          timestamp: Date.now()
        }));
        setOutput(lines);
      }
    } catch (err) {
      console.error('Error fetching execution output:', err);
    }
  };

  const refreshExecution = async (execId) => {
    try {
      const { data } = await api.get(`/v41/tools/executions/${execId}`, {
        params: { include_output: true }
      });
      const nextStatus = data.status || status;
      setStatus(nextStatus);
      setResult(data);
      
      if (nextStatus && !['queued', 'running'].includes(nextStatus)) {
        stopExecutionPolling();
        await fetchExecutionOutput(execId);
        loadRecentExecutions();
        if (onComplete) onComplete(data);
      }
    } catch (err) {
      console.error('Error checking execution status:', err);
    }
  };

  const startExecutionPolling = (execId) => {
    stopExecutionPolling();
    refreshExecution(execId);
    pollRef.current = setInterval(() => refreshExecution(execId), 3000);
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

  const executeToolRequest = async () => {
    try {
      setStatus('queued');
      setOutput([]);
      setResult(null);
      setError(null);
      setProgress(0);

      const targetValue = parameters.target || parameters.target_host || parameters.domain || parameters.ip || parameters.url || '';
      if (!targetValue) {
        setError('Debes especificar un target o destino para la herramienta.');
        setStatus(null);
        return;
      }

      const selectedAgentInfo = agents.find((a) => a.id === selectedAgent);
      const execTarget = target === 'agent'
        ? `agent_${selectedAgentInfo?.agent_type || 'blue'}`
        : 'mcp_local';
      
      const payload = {
        tool_id: toolName,
        parameters,
        target: targetValue,
        execution_target: execTarget,
        agent_id: target === 'agent' ? selectedAgent : null,
        case_id: caseId,
        timeout
      };
      
      const { data } = await api.post('/api/v41/tools/execute', payload);
      
      if (data.execution_id) {
        setExecutionId(data.execution_id);
        startExecutionPolling(data.execution_id);
      } else {
        throw new Error(data.detail || 'Error al iniciar ejecución');
      }
    } catch (err) {
      setStatus('failed');
      setError(err.message);
    }
  };

  const cancelExecution = async () => {
    if (!executionId) return;
    
    try {
      await api.post(`/v41/tools/executions/${executionId}/cancel`);
      stopExecutionPolling();
      setStatus('cancelled');
    } catch (error) {
      console.error('Error cancelling execution:', error);
    }
  };

  const copyOutput = () => {
    const text = output.map(o => o.data).join('\n');
    navigator.clipboard.writeText(text);
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  const renderParameterInput = (param) => {
    const value = parameters[param.name] || '';
    
    if (param.type === 'boolean' || param.type === 'flag') {
      return (
        <label key={param.name} className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => setParameters(prev => ({ ...prev, [param.name]: e.target.checked }))}
            className="w-4 h-4 rounded bg-gray-700 border-gray-600"
          />
          <span className="text-sm text-gray-300">{param.label || param.name}</span>
          {param.description && (
            <span className="text-xs text-gray-500">({param.description})</span>
          )}
        </label>
      );
    }
    
    if (param.type === 'select' && param.options) {
      return (
        <div key={param.name}>
          <label className="block text-sm text-gray-400 mb-1">{param.label || param.name}</label>
          <select
            value={value}
            onChange={(e) => setParameters(prev => ({ ...prev, [param.name]: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
          >
            <option value="">Seleccionar...</option>
            {param.options.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      );
    }
    
    return (
      <div key={param.name}>
        <label className="block text-sm text-gray-400 mb-1">
          {param.label || param.name}
          {param.required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <input
          type={param.type === 'number' ? 'number' : 'text'}
          value={value}
          placeholder={param.placeholder || param.description}
          onChange={(e) => setParameters(prev => ({ ...prev, [param.name]: e.target.value }))}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500"
        />
      </div>
    );
  };

  const renderOutput = () => (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      {/* Output header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <CommandLineIcon className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-300">Output</span>
          {status && (
            <span className={`px-2 py-0.5 text-xs rounded ${STATUS_CONFIG[status]?.text} ${STATUS_CONFIG[status]?.color}/20`}>
              {STATUS_CONFIG[status]?.label}
              {STATUS_CONFIG[status]?.animate && '...'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {progress > 0 && progress < 100 && (
            <span className="text-xs text-gray-400">{progress}%</span>
          )}
          <button
            onClick={copyOutput}
            className="p-1 hover:bg-gray-700 rounded text-gray-400"
            title="Copiar"
          >
            <DocumentDuplicateIcon className="w-4 h-4" />
          </button>
          <label className="flex items-center gap-1 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="w-3 h-3 rounded"
            />
            Auto-scroll
          </label>
        </div>
      </div>
      
      {/* Output content */}
      <div
        ref={outputRef}
        className="p-3 font-mono text-sm max-h-96 overflow-y-auto"
      >
        {output.length === 0 ? (
          <p className="text-gray-500">Esperando output...</p>
        ) : (
          output.map((line, idx) => (
            <div key={idx} className={`${line.stream === 'stderr' ? 'text-red-400' : 'text-green-400'}`}>
              {line.data}
            </div>
          ))
        )}
        
        {error && (
          <div className="mt-2 p-2 bg-red-500/20 border border-red-500/50 rounded text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>
      
      {/* Progress bar */}
      {status === 'running' && (
        <div className="h-1 bg-gray-800">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-750 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
            <CommandLineIcon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-medium text-white">{toolName}</h3>
            <p className="text-xs text-gray-400">
              Target: {target === 'agent' ? `Agent (${selectedAgent?.slice(0, 8) || 'none'})` : 'Local MCP'}
            </p>
          </div>
        </div>
        <ChevronDownIcon className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
      </div>
      
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Target selection */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Destino de Ejecución</label>
            <div className="grid grid-cols-2 gap-2">
              {EXECUTION_TARGETS.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTarget(t.id)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    target === t.id
                      ? 'bg-blue-500/20 border-blue-500 text-white'
                      : 'bg-gray-700 border-gray-600 text-gray-300 hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <t.icon className="w-5 h-5" />
                    <span className="font-medium">{t.label}</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">{t.description}</p>
                </button>
              ))}
            </div>
          </div>
          
          {/* Agent selection (if remote) */}
          {target === 'agent' && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">Agente Remoto</label>
              <select
                value={selectedAgent || ''}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              >
                <option value="">Seleccionar agente...</option>
                {agents.map(agent => (
                  <option key={agent.id} value={agent.id}>
                    {agent.hostname} ({agent.agent_type}) - {agent.status}
                  </option>
                ))}
              </select>
              {agents.length === 0 && (
                <p className="text-xs text-yellow-400 mt-1">No hay agentes online</p>
              )}
            </div>
          )}
          
          {/* Parameters */}
          {toolParams.length > 0 && (
            <div className="space-y-3">
              <label className="block text-sm text-gray-400">Parámetros</label>
              {toolParams.filter(p => !p.advanced).map(renderParameterInput)}
              
              {toolParams.some(p => p.advanced) && (
                <>
                  <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-sm text-blue-400 flex items-center gap-1"
                  >
                    <Cog6ToothIcon className="w-4 h-4" />
                    {showAdvanced ? 'Ocultar' : 'Mostrar'} opciones avanzadas
                  </button>
                  {showAdvanced && (
                    <div className="space-y-3 pl-4 border-l-2 border-gray-700">
                      {toolParams.filter(p => p.advanced).map(renderParameterInput)}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          
          {/* Timeout */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <ClockIcon className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Timeout:</span>
            </div>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout(parseInt(e.target.value) || 300)}
              className="w-24 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
            />
            <span className="text-sm text-gray-500">segundos</span>
          </div>
          
          {/* Execute button */}
          <div className="flex items-center gap-3">
            {status === 'running' ? (
              <button
                onClick={cancelExecution}
                className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 rounded-lg flex items-center justify-center gap-2 font-medium"
              >
                <StopIcon className="w-5 h-5" />
                Detener
              </button>
            ) : (
              <button
                onClick={executeToolRequest}
                disabled={target === 'agent' && !selectedAgent}
                className="flex-1 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg flex items-center justify-center gap-2 font-medium"
              >
                <PlayIcon className="w-5 h-5" />
                Ejecutar
              </button>
            )}
            <button
              onClick={loadQueue}
              className="p-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg"
              title="Ver cola"
            >
              <QueueListIcon className="w-5 h-5" />
            </button>
          </div>
          
          {/* Output */}
          {(output.length > 0 || status) && renderOutput()}
          
          {/* Result summary */}
          {result && (status === 'success' || status === 'completed') && (
            <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg">
              <h4 className="text-sm font-medium text-green-400 mb-2">Resultado</h4>
              <pre className="text-xs text-gray-300 overflow-x-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
