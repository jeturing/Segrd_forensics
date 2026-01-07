/**
 * AgentsDashboard - Panel de gestión de agentes Red/Blue/Purple
 * v4.1 - Agentes distribuidos para IR
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  ServerStackIcon,
  ComputerDesktopIcon,
  SignalIcon,
  SignalSlashIcon,
  PlayIcon,
  StopIcon,
  PlusIcon,
  TrashIcon,
  ChevronRightIcon,
  ArrowPathIcon,
  ClipboardDocumentListIcon,
  ShieldCheckIcon,
  BugAntIcon,
  SparklesIcon,
  CpuChipIcon,
  ClockIcon,
  MapPinIcon,
  WifiIcon
} from '@heroicons/react/24/outline';

import api from '../../services/api';
import { WS_BASE_URL } from '../../services/realtime';

const AGENTS_API_BASE = '/api/v41/agents';

// Configuración de tipos de agente
const AGENT_TYPES = {
  blue: { 
    label: 'Blue Team', 
    icon: ShieldCheckIcon, 
    color: 'from-blue-500 to-blue-600',
    bg: 'bg-blue-500/20',
    text: 'text-blue-400',
    description: 'Defensa y monitoreo'
  },
  red: { 
    label: 'Red Team', 
    icon: BugAntIcon, 
    color: 'from-red-500 to-red-600',
    bg: 'bg-red-500/20',
    text: 'text-red-400',
    description: 'Simulación de ataques'
  },
  purple: { 
    label: 'Purple Team', 
    icon: SparklesIcon, 
    color: 'from-purple-500 to-purple-600',
    bg: 'bg-purple-500/20',
    text: 'text-purple-400',
    description: 'Colaboración y mejora'
  }
};

// Estados de agente
const STATUS_CONFIG = {
  online: { color: 'bg-green-500', text: 'text-green-400', label: 'Online' },
  offline: { color: 'bg-gray-500', text: 'text-gray-400', label: 'Offline' },
  busy: { color: 'bg-yellow-500', text: 'text-yellow-400', label: 'Busy' },
  error: { color: 'bg-red-500', text: 'text-red-400', label: 'Error' }
};

export default function AgentsDashboard() {
  // Estado principal
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentTasks, setAgentTasks] = useState([]);
  const [agentTelemetry, setAgentTelemetry] = useState(null);
  
  // Estado de filtros
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Estado de UI
  const [activeTab, setActiveTab] = useState('overview'); // overview, tasks, telemetry
  const [isLoading, setIsLoading] = useState(false);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  
  // WebSocket
  const wsRef = useRef(null);

  // ============================================================================
  // CARGA DE DATOS
  // ============================================================================

  useEffect(() => {
    loadAgents();
    connectWebSocket();
    
    // Refresh cada 30s
    const interval = setInterval(loadAgents, 30000);
    
    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      loadAgentTasks(selectedAgent.id);
    }
  }, [selectedAgent]);

  const loadAgents = async () => {
    try {
      setIsLoading(true);
      const params = {};
      if (typeFilter !== 'all') params.agent_type = typeFilter;
      if (statusFilter !== 'all') params.status = statusFilter;

      const { data } = await api.get(`${AGENTS_API_BASE}/`, { params });
      setAgents(data.agents || []);
    } catch (error) {
      console.error('Error loading agents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAgentTasks = async (agentId) => {
    try {
      const { data } = await api.get(`${AGENTS_API_BASE}/${agentId}/tasks`, {
        params: { limit: 20 }
      });
      setAgentTasks(data.tasks || []);
    } catch (error) {
      console.error('Error loading tasks:', error);
    }
  };

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(`${WS_BASE_URL}/agents_v41`);
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.event === 'agent_registered' || data.event === 'agent_heartbeat') {
          loadAgents();
        } else if (data.event === 'task_completed' && selectedAgent?.id === data.agent_id) {
          loadAgentTasks(selectedAgent.id);
        } else if (data.event === 'agent_offline') {
          setAgents(prev => prev.map(a => 
            a.id === data.agent_id ? { ...a, status: 'offline' } : a
          ));
        }
      };
      
      ws.onerror = () => ws.close();
      wsRef.current = ws;
    } catch (error) {
      console.error('Error connecting websocket agents_v41:', error);
    }
  };

  // ============================================================================
  // ACCIONES
  // ============================================================================

  const dispatchTask = async (agentId, taskType, config = {}) => {
    try {
      await api.post(`${AGENTS_API_BASE}/${agentId}/task`, {
        tool: taskType,
        parameters: config
      });
      loadAgentTasks(agentId);
    } catch (error) {
      console.error('Error dispatching task:', error);
    }
  };

  const removeAgent = async (agentId) => {
    if (!confirm('¿Eliminar este agente?')) return;
    
    try {
      await api.delete(`${AGENTS_API_BASE}/${agentId}`);
      loadAgents();
      setSelectedAgent(null);
    } catch (error) {
      console.error('Error removing agent:', error);
    }
  };

  // ============================================================================
  // ESTADÍSTICAS
  // ============================================================================

  const stats = React.useMemo(() => {
    const byType = { blue: 0, red: 0, purple: 0 };
    const byStatus = { online: 0, offline: 0, busy: 0, error: 0 };
    
    agents.forEach(agent => {
      if (byType[agent.agent_type] !== undefined) byType[agent.agent_type]++;
      if (byStatus[agent.status] !== undefined) byStatus[agent.status]++;
    });
    
    return { total: agents.length, byType, byStatus };
  }, [agents]);

  // ============================================================================
  // FILTRADO
  // ============================================================================

  const filteredAgents = React.useMemo(() => {
    return agents.filter(agent => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!agent.hostname?.toLowerCase().includes(query) &&
            !agent.ip_address?.toLowerCase().includes(query)) {
          return false;
        }
      }
      return true;
    });
  }, [agents, searchQuery]);

  // ============================================================================
  // RENDER
  // ============================================================================

  const renderStatCards = () => (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
      {/* Total */}
      <div className="bg-gray-800 rounded-lg p-3">
        <div className="flex items-center justify-between">
          <ServerStackIcon className="w-6 h-6 text-gray-400" />
          <span className="text-2xl font-bold text-white">{stats.total}</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">Total Agentes</p>
      </div>
      
      {/* By type */}
      {Object.entries(AGENT_TYPES).map(([type, config]) => (
        <div key={type} className={`${config.bg} rounded-lg p-3`}>
          <div className="flex items-center justify-between">
            <config.icon className={`w-6 h-6 ${config.text}`} />
            <span className={`text-2xl font-bold ${config.text}`}>{stats.byType[type]}</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">{config.label}</p>
        </div>
      ))}
      
      {/* Online/Offline */}
      <div className="bg-green-500/20 rounded-lg p-3">
        <div className="flex items-center justify-between">
          <SignalIcon className="w-6 h-6 text-green-400" />
          <span className="text-2xl font-bold text-green-400">{stats.byStatus.online}</span>
        </div>
        <p className="text-xs text-gray-400 mt-1">Online</p>
      </div>
      
      <div className="bg-gray-700/50 rounded-lg p-3">
        <div className="flex items-center justify-between">
          <SignalSlashIcon className="w-6 h-6 text-gray-400" />
          <span className="text-2xl font-bold text-gray-400">{stats.byStatus.offline}</span>
        </div>
        <p className="text-xs text-gray-400 mt-1">Offline</p>
      </div>
    </div>
  );

  const renderAgentCard = (agent) => {
    const typeConfig = AGENT_TYPES[agent.agent_type] || AGENT_TYPES.blue;
    const statusConfig = STATUS_CONFIG[agent.status] || STATUS_CONFIG.offline;
    
    return (
      <div
        key={agent.id}
        className={`bg-gray-800 rounded-lg border ${selectedAgent?.id === agent.id ? 'border-blue-500' : 'border-gray-700'} hover:border-gray-600 cursor-pointer transition-all`}
        onClick={() => setSelectedAgent(agent)}
      >
        {/* Type indicator */}
        <div className={`h-1 rounded-t-lg bg-gradient-to-r ${typeConfig.color}`} />
        
        <div className="p-4">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-lg ${typeConfig.bg} flex items-center justify-center`}>
                <typeConfig.icon className={`w-5 h-5 ${typeConfig.text}`} />
              </div>
              <div>
                <h3 className="font-medium text-white">{agent.hostname || agent.name || agent.id}</h3>
                <p className="text-xs text-gray-500">{agent.ip_address || 'IP no disponible'}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${statusConfig.color} ${agent.status === 'online' ? 'animate-pulse' : ''}`} />
              <span className={`text-xs ${statusConfig.text}`}>{statusConfig.label}</span>
            </div>
          </div>
          
          {/* Capabilities */}
          <div className="flex flex-wrap gap-1 mb-3">
            {(agent.capabilities || []).slice(0, 3).map((cap, idx) => (
              <span key={idx} className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300">
                {cap}
              </span>
            ))}
            {(agent.capabilities?.length || 0) > 3 && (
              <span className="text-xs text-gray-500">+{agent.capabilities.length - 3}</span>
            )}
          </div>
          
          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <ClockIcon className="w-3 h-3" />
              {agent.last_seen || agent.last_heartbeat ? new Date(agent.last_seen || agent.last_heartbeat).toLocaleTimeString() : 'N/A'}
            </span>
            <span className="flex items-center gap-1">
              <CpuChipIcon className="w-3 h-3" />
              {agent.os_version || agent.platform || 'Unknown'}
            </span>
          </div>
        </div>
      </div>
    );
  };

  const renderAgentDetail = () => {
    if (!selectedAgent) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <ServerStackIcon className="w-16 h-16 mb-4 opacity-30" />
          <p>Selecciona un agente para ver detalles</p>
        </div>
      );
    }
    
    const typeConfig = AGENT_TYPES[selectedAgent.agent_type] || AGENT_TYPES.blue;
    const statusConfig = STATUS_CONFIG[selectedAgent.status] || STATUS_CONFIG.offline;
    
    return (
      <div className="space-y-4">
        {/* Agent header */}
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${typeConfig.color} flex items-center justify-center`}>
                <typeConfig.icon className="w-7 h-7 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{selectedAgent.hostname || selectedAgent.name || selectedAgent.id}</h2>
                <p className="text-sm text-gray-400">
                  {selectedAgent.ip_address || 'N/A'} • {selectedAgent.os_version || selectedAgent.platform || 'N/A'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded ${statusConfig.color}/20 ${statusConfig.text}`}>
                {statusConfig.label}
              </span>
              <button
                onClick={() => removeAgent(selectedAgent.id)}
                className="p-2 hover:bg-red-500/20 rounded text-red-400"
              >
                <TrashIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
          
          {/* Quick actions */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => dispatchTask(selectedAgent.id, 'health_check')}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 text-sm"
            >
              <WifiIcon className="w-4 h-4" />
              Health Check
            </button>
            <button
              onClick={() => dispatchTask(selectedAgent.id, 'collect_logs')}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 text-sm"
            >
              <ClipboardDocumentListIcon className="w-4 h-4" />
              Collect Logs
            </button>
            <button
              onClick={() => dispatchTask(selectedAgent.id, 'scan_iocs')}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 text-sm"
            >
              <PlayIcon className="w-4 h-4" />
              Scan IOCs
            </button>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 border-b border-gray-700 pb-2">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'tasks', label: 'Tasks' },
            { id: 'telemetry', label: 'Telemetry' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                activeTab === tab.id
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        
        {/* Tab content */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Información</h4>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">ID</dt>
                  <dd className="text-gray-300 font-mono">{selectedAgent.id?.slice(0, 12)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Tipo</dt>
                  <dd className={typeConfig.text}>{typeConfig.label}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Versión</dt>
                  <dd className="text-gray-300">{selectedAgent.agent_version || selectedAgent.version || 'N/A'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Registrado</dt>
                  <dd className="text-gray-300">
                    {selectedAgent.created_at
                      ? new Date(selectedAgent.created_at).toLocaleDateString()
                      : selectedAgent.last_seen
                        ? new Date(selectedAgent.last_seen).toLocaleDateString()
                        : 'N/A'}
                  </dd>
                </div>
              </dl>
            </div>
            
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Capabilities</h4>
              <div className="flex flex-wrap gap-2">
                {(selectedAgent.capabilities || []).map((cap, idx) => (
                  <span key={idx} className="px-2 py-1 bg-gray-700 rounded text-sm text-gray-300">
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'tasks' && (
          <div className="space-y-2">
            {agentTasks.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay tareas recientes</p>
            ) : (
              agentTasks.map(task => (
                <div key={task.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className={`w-2 h-2 rounded-full ${
                      task.status === 'completed' ? 'bg-green-500' :
                      task.status === 'running' ? 'bg-blue-500 animate-pulse' :
                      task.status === 'failed' ? 'bg-red-500' :
                      'bg-gray-500'
                    }`} />
                    <div>
                      <p className="text-sm text-white">{task.task_type || task.tool || 'Tarea'}</p>
                      <p className="text-xs text-gray-500">
                        {task.created_at ? new Date(task.created_at).toLocaleString() : 'Sin timestamp'}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">{task.status || 'pending'}</span>
                </div>
              ))
            )}
          </div>
        )}
        
        {activeTab === 'telemetry' && (
          agentTelemetry ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-blue-400">{agentTelemetry.cpu_usage || 0}%</p>
                <p className="text-xs text-gray-500">CPU Usage</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-green-400">{agentTelemetry.memory_usage || 0}%</p>
                <p className="text-xs text-gray-500">Memory</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-yellow-400">{agentTelemetry.disk_usage || 0}%</p>
                <p className="text-xs text-gray-500">Disk</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-purple-400">{agentTelemetry.tasks_completed || 0}</p>
                <p className="text-xs text-gray-500">Tasks Done</p>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">Telemetría no disponible para este agente.</p>
          )
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
              <ServerStackIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Agents Dashboard</h1>
              <p className="text-sm text-gray-400">Gestión de Agentes Red/Blue/Purple</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadAgents}
              className="p-2 hover:bg-gray-800 rounded-lg"
            >
              <ArrowPathIcon className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setShowRegisterModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-2"
            >
              <PlusIcon className="w-5 h-5" />
              Registrar Agente
            </button>
          </div>
        </div>
        
        {/* Filters */}
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Buscar por hostname o IP..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500"
          />
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); loadAgents(); }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="all">Todos los tipos</option>
            <option value="blue">Blue Team</option>
            <option value="red">Red Team</option>
            <option value="purple">Purple Team</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); loadAgents(); }}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="all">Todos los estados</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="busy">Busy</option>
          </select>
        </div>
      </div>
      
      {/* Stats */}
      <div className="p-4">
        {renderStatCards()}
      </div>
      
      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Agents list */}
        <div className="w-1/2 border-r border-gray-700 overflow-y-auto p-4">
          <div className="grid grid-cols-1 gap-3">
            {filteredAgents.map(renderAgentCard)}
            {filteredAgents.length === 0 && !isLoading && (
              <div className="text-center py-12 text-gray-500">
                <ServerStackIcon className="w-12 h-12 mx-auto mb-4 opacity-30" />
                <p>No hay agentes registrados</p>
              </div>
            )}
          </div>
        </div>
        
        {/* Agent detail */}
        <div className="w-1/2 overflow-y-auto p-4">
          {renderAgentDetail()}
        </div>
      </div>
      
      {/* Modal de Registro de Agente */}
      {showRegisterModal && (
        <RegisterAgentModal 
          onClose={() => setShowRegisterModal(false)}
          onSuccess={() => {
            setShowRegisterModal(false);
            loadAgents();
          }}
        />
      )}
    </div>
  );
}

// ============================================================================
// COMPONENTE: RegisterAgentModal
// ============================================================================

function RegisterAgentModal({ onClose, onSuccess }) {
  const [agentType, setAgentType] = useState('blue');
  const [platform, setPlatform] = useState('linux');
  const [agentName, setAgentName] = useState('');
  const [deployScript, setDeployScript] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [step, setStep] = useState(1); // 1: config, 2: script
  const [registrationToken, setRegistrationToken] = useState('');

  const PLATFORMS = {
    linux: { label: 'Linux', icon: '🐧', description: 'Ubuntu, Debian, RHEL, Kali' },
    windows: { label: 'Windows', icon: '🪟', description: 'Windows 10/11, Server 2019+' },
    macos: { label: 'macOS', icon: '🍎', description: 'macOS 12+' }
  };

  const generateScript = async () => {
    setIsGenerating(true);
    try {
      const response = await api.get(`${AGENTS_API_BASE}/deploy/script/${agentType}`, {
        params: { 
          platform,
          agent_name: agentName || `agent-${Date.now()}`
        }
      });
      
      setDeployScript(response.data.script);
      setRegistrationToken(response.data.registration_token || '');
      setStep(2);
    } catch (error) {
      console.error('Error generating script:', error);
      // Fallback: generar script localmente
      const fallbackScript = generateLocalScript(agentType, platform, agentName);
      setDeployScript(fallbackScript);
      setStep(2);
    } finally {
      setIsGenerating(false);
    }
  };

  const generateLocalScript = (type, plat, name) => {
    const mcpUrl = window.location.origin.replace(':3000', ':9000').replace(':3001', ':9000');
    const agentId = `agent-${type}-${Date.now()}`;
    
    if (plat === 'linux') {
      return `#!/bin/bash
# JETURING MCP - Agent Deployment Script
# Type: ${type.toUpperCase()} | Platform: Linux
# Generated: ${new Date().toISOString()}

set -e

echo "🚀 Installing JETURING ${type.toUpperCase()} Agent..."

# Variables
AGENT_ID="${agentId}"
AGENT_NAME="${name || agentId}"
MCP_URL="${mcpUrl}"
AGENT_TYPE="${type}"
INSTALL_DIR="/opt/jeturing-agent"

# Create install directory
sudo mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Install dependencies
sudo apt-get update && sudo apt-get install -y python3 python3-pip curl jq

# Create agent script
cat > agent.py << 'AGENT_EOF'
#!/usr/bin/env python3
"""JETURING Agent - Connects to MCP for task execution"""
import os, sys, json, time, subprocess, platform, requests, socket

AGENT_ID = os.getenv("AGENT_ID", "${agentId}")
AGENT_NAME = os.getenv("AGENT_NAME", "${name || agentId}")
MCP_URL = os.getenv("MCP_URL", "${mcpUrl}")
AGENT_TYPE = os.getenv("AGENT_TYPE", "${type}")

def get_system_info():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "version": platform.version(),
        "cpu_count": os.cpu_count(),
        "ip": socket.gethostbyname(socket.gethostname())
    }

def register():
    try:
        resp = requests.post(f"{MCP_URL}/api/v41/agents/", json={
            "agent_id": AGENT_ID,
            "agent_type": AGENT_TYPE,
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "capabilities": ["yara", "loki", "osquery"] if AGENT_TYPE == "blue" else ["recon", "exploit"],
            "status": "online"
        }, timeout=10)
        print(f"✅ Registered: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Registration failed: {e}")

def heartbeat():
    try:
        requests.post(f"{MCP_URL}/api/v41/agents/{AGENT_ID}/heartbeat", 
            json=get_system_info(), timeout=5)
    except: pass

def get_tasks():
    try:
        resp = requests.get(f"{MCP_URL}/api/v41/agents/{AGENT_ID}/pending-tasks", timeout=5)
        return resp.json() if resp.ok else []
    except: return []

def execute_task(task):
    try:
        if task.get("task_type") == "yara_scan":
            result = subprocess.run(["yara", "-r", task.get("rules", "/etc/yara/rules"), task.get("path", "/tmp")],
                capture_output=True, text=True, timeout=300)
            return {"output": result.stdout, "matches": len(result.stdout.splitlines())}
        elif task.get("task_type") == "loki_scan":
            result = subprocess.run(["python3", "/opt/Loki/loki.py", "--path", task.get("path", "/tmp")],
                capture_output=True, text=True, timeout=600)
            return {"output": result.stdout}
        return {"status": "unsupported_task"}
    except Exception as e:
        return {"error": str(e)}

def report_task(task_id, result):
    try:
        requests.post(f"{MCP_URL}/api/v41/agents/task/{task_id}/complete",
            json={"result": result, "status": "completed"}, timeout=10)
    except: pass

def main():
    print(f"🔷 JETURING Agent starting - {AGENT_TYPE.upper()} mode")
    register()
    while True:
        try:
            heartbeat()
            for task in get_tasks():
                print(f"📋 Executing task: {task.get('id')}")
                result = execute_task(task)
                report_task(task.get("id"), result)
            time.sleep(10)
        except KeyboardInterrupt:
            print("Agent stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
AGENT_EOF

# Install Python dependencies
pip3 install requests

# Create systemd service
sudo tee /etc/systemd/system/jeturing-agent.service << SERVICE_EOF
[Unit]
Description=JETURING ${type.toUpperCase()} Agent
After=network.target

[Service]
Type=simple
User=root
Environment="AGENT_ID=${agentId}"
Environment="AGENT_NAME=${name || agentId}"
Environment="MCP_URL=${mcpUrl}"
Environment="AGENT_TYPE=${type}"
ExecStart=/usr/bin/python3 /opt/jeturing-agent/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable jeturing-agent
sudo systemctl start jeturing-agent

echo "✅ Agent installed and running!"
echo "📊 Check status: sudo systemctl status jeturing-agent"
echo "📜 View logs: sudo journalctl -u jeturing-agent -f"
`;
    } else if (plat === 'windows') {
      return `# JETURING MCP - Agent Deployment Script (PowerShell)
# Type: ${type.toUpperCase()} | Platform: Windows
# Generated: ${new Date().toISOString()}
# Run as Administrator

$ErrorActionPreference = "Stop"

Write-Host "🚀 Installing JETURING ${type.toUpperCase()} Agent..." -ForegroundColor Cyan

# Variables
$AgentId = "${agentId}"
$AgentName = "${name || agentId}"
$McpUrl = "${mcpUrl}"
$AgentType = "${type}"
$InstallDir = "C:\\ProgramData\\JeturingAgent"

# Create install directory
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir

# Create agent script
@'
# JETURING Agent for Windows
param([string]$McpUrl, [string]$AgentId, [string]$AgentType)

function Register-Agent {
    $body = @{
        agent_id = $AgentId
        agent_type = $AgentType
        hostname = $env:COMPUTERNAME
        ip_address = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*"} | Select-Object -First 1).IPAddress
        capabilities = @("defender", "sysmon", "eventlog")
        status = "online"
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "$McpUrl/api/v41/agents/" -Method POST -Body $body -ContentType "application/json"
        Write-Host "✅ Agent registered" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Registration failed: $_" -ForegroundColor Yellow
    }
}

function Send-Heartbeat {
    $info = @{
        hostname = $env:COMPUTERNAME
        cpu_usage = (Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
        memory_usage = [math]::Round((1 - (Get-WmiObject Win32_OperatingSystem).FreePhysicalMemory / (Get-WmiObject Win32_OperatingSystem).TotalVisibleMemorySize) * 100)
    } | ConvertTo-Json
    
    try { Invoke-RestMethod -Uri "$McpUrl/api/v41/agents/$AgentId/heartbeat" -Method POST -Body $info -ContentType "application/json" -TimeoutSec 5 } catch {}
}

Register-Agent
while ($true) {
    Send-Heartbeat
    Start-Sleep -Seconds 10
}
'@ | Out-File -FilePath "$InstallDir\\agent.ps1" -Encoding UTF8

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File $InstallDir\\agent.ps1 -McpUrl $McpUrl -AgentId $AgentId -AgentType $AgentType"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 3
Register-ScheduledTask -TaskName "JeturingAgent" -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM" -RunLevel Highest -Force

# Start immediately
Start-ScheduledTask -TaskName "JeturingAgent"

Write-Host "✅ Agent installed and running!" -ForegroundColor Green
Write-Host "📊 Check status: Get-ScheduledTask -TaskName JeturingAgent" -ForegroundColor Cyan
`;
    } else {
      // macOS
      return `#!/bin/bash
# JETURING MCP - Agent Deployment Script
# Type: ${type.toUpperCase()} | Platform: macOS
# Generated: ${new Date().toISOString()}

set -e

echo "🚀 Installing JETURING ${type.toUpperCase()} Agent..."

# Variables
AGENT_ID="${agentId}"
AGENT_NAME="${name || agentId}"
MCP_URL="${mcpUrl}"
AGENT_TYPE="${type}"
INSTALL_DIR="/usr/local/jeturing-agent"

# Create install directory
sudo mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Install Python if needed
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    brew install python3
fi

pip3 install requests

# Create agent script (same as Linux)
cat > agent.py << 'AGENT_EOF'
#!/usr/bin/env python3
import os, sys, json, time, requests, socket, platform

AGENT_ID = os.getenv("AGENT_ID", "${agentId}")
MCP_URL = os.getenv("MCP_URL", "${mcpUrl}")
AGENT_TYPE = os.getenv("AGENT_TYPE", "${type}")

def register():
    try:
        requests.post(f"{MCP_URL}/api/v41/agents/", json={
            "agent_id": AGENT_ID,
            "agent_type": AGENT_TYPE,
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "capabilities": ["santa", "osquery"],
            "status": "online"
        }, timeout=10)
        print("✅ Registered")
    except Exception as e:
        print(f"⚠️ Failed: {e}")

def heartbeat():
    try:
        requests.post(f"{MCP_URL}/api/v41/agents/{AGENT_ID}/heartbeat", timeout=5)
    except: pass

def main():
    print(f"🔷 JETURING Agent starting - {AGENT_TYPE.upper()}")
    register()
    while True:
        heartbeat()
        time.sleep(10)

if __name__ == "__main__":
    main()
AGENT_EOF

# Create LaunchDaemon
sudo tee /Library/LaunchDaemons/com.jeturing.agent.plist << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jeturing.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/usr/local/jeturing-agent/agent.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>AGENT_ID</key>
        <string>${agentId}</string>
        <key>MCP_URL</key>
        <string>${mcpUrl}</string>
        <key>AGENT_TYPE</key>
        <string>${type}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
PLIST_EOF

# Load and start
sudo launchctl load /Library/LaunchDaemons/com.jeturing.agent.plist

echo "✅ Agent installed and running!"
echo "📊 Check: sudo launchctl list | grep jeturing"
`;
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(deployScript);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const getOneLiner = () => {
    const mcpUrl = window.location.origin.replace(':3000', ':9000').replace(':3001', ':9000');
    if (platform === 'linux') {
      return `curl -sSL ${mcpUrl}/api/v41/agents/deploy/script/${agentType}?platform=linux | sudo bash`;
    } else if (platform === 'windows') {
      return `irm "${mcpUrl}/api/v41/agents/deploy/script/${agentType}?platform=windows" | iex`;
    } else {
      return `curl -sSL ${mcpUrl}/api/v41/agents/deploy/script/${agentType}?platform=macos | sudo bash`;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
              <PlusIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Registrar Nuevo Agente</h2>
              <p className="text-sm text-gray-400">Paso {step} de 2</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 1 ? (
            <div className="space-y-6">
              {/* Agent Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Nombre del Agente (opcional)
                </label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="ej: server-web-01, endpoint-finanzas"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500"
                />
              </div>

              {/* Agent Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Tipo de Agente
                </label>
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(AGENT_TYPES).map(([type, config]) => {
                    const Icon = config.icon;
                    return (
                      <button
                        key={type}
                        onClick={() => setAgentType(type)}
                        className={`p-4 rounded-xl border-2 transition-all ${
                          agentType === type
                            ? 'border-indigo-500 bg-indigo-500/20'
                            : 'border-gray-600 hover:border-gray-500 bg-gray-700/50'
                        }`}
                      >
                        <div className={`w-12 h-12 mx-auto rounded-lg bg-gradient-to-br ${config.color} flex items-center justify-center mb-3`}>
                          <Icon className="w-6 h-6 text-white" />
                        </div>
                        <p className="font-medium text-white">{config.label}</p>
                        <p className="text-xs text-gray-400 mt-1">{config.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Platform Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Plataforma de Destino
                </label>
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(PLATFORMS).map(([plat, config]) => (
                    <button
                      key={plat}
                      onClick={() => setPlatform(plat)}
                      className={`p-4 rounded-xl border-2 transition-all ${
                        platform === plat
                          ? 'border-indigo-500 bg-indigo-500/20'
                          : 'border-gray-600 hover:border-gray-500 bg-gray-700/50'
                      }`}
                    >
                      <div className="text-3xl mb-2">{config.icon}</div>
                      <p className="font-medium text-white">{config.label}</p>
                      <p className="text-xs text-gray-400 mt-1">{config.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* One-liner */}
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-300">🚀 Instalación Rápida (One-liner)</span>
                </div>
                <div className="bg-black rounded p-3 font-mono text-sm text-green-400 overflow-x-auto">
                  {getOneLiner()}
                </div>
              </div>

              {/* Full Script */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-300">📜 Script Completo</span>
                  <button
                    onClick={copyToClipboard}
                    className={`px-3 py-1 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                      copied 
                        ? 'bg-green-600 text-white' 
                        : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                    }`}
                  >
                    {copied ? '✓ Copiado!' : '📋 Copiar'}
                  </button>
                </div>
                <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
                  <pre className="font-mono text-xs text-gray-300 whitespace-pre-wrap">
                    {deployScript}
                  </pre>
                </div>
              </div>

              {/* Instructions */}
              <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
                <h4 className="font-medium text-blue-300 mb-2">📌 Instrucciones</h4>
                <ul className="text-sm text-blue-200 space-y-1">
                  <li>1. Copia el script o usa el one-liner en el nodo remoto</li>
                  <li>2. Ejecuta con privilegios de administrador/root</li>
                  <li>3. El agente se registrará automáticamente en el MCP</li>
                  <li>4. Verifica la conexión en este dashboard</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 flex justify-between">
          {step === 2 && (
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
            >
              ← Volver
            </button>
          )}
          <div className="flex-1" />
          {step === 1 ? (
            <button
              onClick={generateScript}
              disabled={isGenerating}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-white flex items-center gap-2 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  Generando...
                </>
              ) : (
                <>
                  Generar Script
                  <ChevronRightIcon className="w-5 h-5" />
                </>
              )}
            </button>
          ) : (
            <button
              onClick={onSuccess}
              className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white"
            >
              ✓ Listo
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
