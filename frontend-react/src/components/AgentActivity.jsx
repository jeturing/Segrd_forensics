/**
 * MCP Kali Forensics - Agent Activity Component v4.4.1
 * Monitor de actividad de agentes Blue/Red/Purple en tiempo real
 */

import React, { useState, useEffect, useRef } from 'react';
import { useCaseContext } from '../context/CaseContext';

// Tipos de agentes
const AGENT_TYPES = {
  BLUE: { 
    name: 'Blue Team', 
    color: 'blue', 
    icon: '🛡️',
    description: 'Defensive operations'
  },
  RED: { 
    name: 'Red Team', 
    color: 'red', 
    icon: '⚔️',
    description: 'Offensive operations'
  },
  PURPLE: { 
    name: 'Purple Team', 
    color: 'purple', 
    icon: '🔮',
    description: 'Collaborative testing'
  }
};

// Estados de agentes
const AGENT_STATUS = {
  IDLE: { label: 'Idle', color: 'gray', icon: '💤' },
  RUNNING: { label: 'Running', color: 'blue', icon: '🔄' },
  SUCCESS: { label: 'Success', color: 'green', icon: '✅' },
  ERROR: { label: 'Error', color: 'red', icon: '❌' },
  WAITING: { label: 'Waiting', color: 'yellow', icon: '⏳' }
};

/**
 * Componente principal de actividad de agentes
 */
export default function AgentActivity({ caseId = null }) {
  const { currentCase } = useCaseContext();
  const [agents, setAgents] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const wsRef = useRef(null);
  
  const effectiveCaseId = caseId || currentCase?.id;

  useEffect(() => {
    fetchAgents();
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [effectiveCaseId]);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/agents', {
        headers: {
          'X-API-Key': localStorage.getItem('apiKey') || ''
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setAgents(data.agents || []);
      } else {
        // Demo agents si falla
        setAgents(generateDemoAgents());
      }
    } catch (err) {
      console.error('Error fetching agents:', err);
      setAgents(generateDemoAgents());
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const wsPath = effectiveCaseId 
      ? `/ws/case/${effectiveCaseId}/live`
      : '/ws/global/logs';
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${wsPath}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('🤖 AgentActivity WebSocket connected');
        setWsConnected(true);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'heartbeat') return;
          
          // Filtrar actividades de agentes
          if (data.source?.startsWith('agent:') || data.agent_id) {
            setActivities(prev => [
              {
                ...data,
                id: Date.now() + Math.random(),
                timestamp: data.timestamp || new Date().toISOString()
              },
              ...prev.slice(0, 99) // Mantener últimas 100
            ]);
            
            // Actualizar estado del agente
            if (data.agent_id) {
              setAgents(prev => prev.map(agent => 
                agent.id === data.agent_id 
                  ? { ...agent, status: data.status || agent.status, lastActivity: data.timestamp }
                  : agent
              ));
            }
          }
        } catch (err) {
          console.error('Error parsing agent activity:', err);
        }
      };
      
      wsRef.current.onclose = () => {
        setWsConnected(false);
        setTimeout(() => connectWebSocket(), 3000);
      };
      
      wsRef.current.onerror = () => {
        setWsConnected(false);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  };

  const filteredAgents = filter === 'ALL' 
    ? agents 
    : agents.filter(a => a.type === filter);

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
        <p className="text-gray-400 mt-2">Loading agents...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-900 px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            🤖 Agent Activity
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </h3>
          
          {/* Filter */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setFilter('ALL')}
              className={`px-3 py-1 rounded text-xs font-medium ${
                filter === 'ALL' ? 'bg-gray-600 text-white' : 'bg-gray-700 text-gray-400'
              }`}
            >
              All
            </button>
            {Object.entries(AGENT_TYPES).map(([key, type]) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1 rounded text-xs font-medium ${
                  filter === key 
                    ? `bg-${type.color}-600 text-white` 
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {type.icon} {type.name}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* Agents Grid */}
      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAgents.map(agent => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
        
        {filteredAgents.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No agents found
          </div>
        )}
      </div>
      
      {/* Recent Activity */}
      <div className="border-t border-gray-700 p-4">
        <h4 className="text-sm font-medium text-gray-400 mb-3">
          Recent Activity ({activities.length})
        </h4>
        
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {activities.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">
              No recent activity
            </p>
          ) : (
            activities.slice(0, 20).map(activity => (
              <ActivityItem key={activity.id} activity={activity} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Tarjeta de agente individual
 */
function AgentCard({ agent }) {
  const type = AGENT_TYPES[agent.type] || AGENT_TYPES.BLUE;
  const status = AGENT_STATUS[agent.status] || AGENT_STATUS.IDLE;
  
  return (
    <div className={`bg-gray-900 rounded-lg border border-${type.color}-500/30 p-4`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{type.icon}</span>
          <div>
            <h4 className="text-white font-medium">{agent.name}</h4>
            <p className="text-xs text-gray-500">{agent.id}</p>
          </div>
        </div>
        
        <span className={`px-2 py-1 rounded text-xs bg-${status.color}-900/50 text-${status.color}-400`}>
          {status.icon} {status.label}
        </span>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center">
          <p className="text-lg font-bold text-white">{agent.tasksCompleted || 0}</p>
          <p className="text-xs text-gray-500">Completed</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-white">{agent.tasksRunning || 0}</p>
          <p className="text-xs text-gray-500">Running</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-white">{agent.tasksFailed || 0}</p>
          <p className="text-xs text-gray-500">Failed</p>
        </div>
      </div>
      
      {/* Current task */}
      {agent.currentTask && (
        <div className="bg-gray-800 rounded p-2 text-xs">
          <span className="text-gray-500">Current:</span>
          <span className="text-gray-300 ml-1">{agent.currentTask}</span>
        </div>
      )}
      
      {/* Last activity */}
      {agent.lastActivity && (
        <p className="text-xs text-gray-500 mt-2">
          Last: {new Date(agent.lastActivity).toLocaleString()}
        </p>
      )}
      
      {/* Actions */}
      <div className="flex gap-2 mt-3">
        <button className="flex-1 px-2 py-1 rounded text-xs bg-blue-600 hover:bg-blue-700 text-white">
          📋 View Logs
        </button>
        <button className="flex-1 px-2 py-1 rounded text-xs bg-gray-700 hover:bg-gray-600 text-white">
          ⚙️ Configure
        </button>
      </div>
    </div>
  );
}

/**
 * Item de actividad
 */
function ActivityItem({ activity }) {
  const timestamp = activity.timestamp 
    ? new Date(activity.timestamp).toLocaleTimeString() 
    : '';
  
  const levelColors = {
    DEBUG: 'text-gray-500',
    INFO: 'text-blue-400',
    WARNING: 'text-yellow-400',
    ERROR: 'text-red-400',
    SUCCESS: 'text-green-400'
  };
  
  return (
    <div className="flex items-center gap-2 text-xs bg-gray-900 rounded px-2 py-1">
      <span className="text-gray-500 w-16">{timestamp}</span>
      {activity.agent_id && (
        <span className="text-purple-400 w-20 truncate">{activity.agent_id}</span>
      )}
      <span className={`flex-1 ${levelColors[activity.level] || 'text-gray-400'}`}>
        {activity.message}
      </span>
    </div>
  );
}

/**
 * Generar agentes demo
 */
function generateDemoAgents() {
  return [
    {
      id: 'AGENT-BLUE-001',
      name: 'Defender',
      type: 'BLUE',
      status: 'RUNNING',
      tasksCompleted: 45,
      tasksRunning: 2,
      tasksFailed: 1,
      currentTask: 'Scanning endpoints for IOCs',
      lastActivity: new Date().toISOString()
    },
    {
      id: 'AGENT-BLUE-002',
      name: 'Monitor',
      type: 'BLUE',
      status: 'IDLE',
      tasksCompleted: 120,
      tasksRunning: 0,
      tasksFailed: 3,
      currentTask: null,
      lastActivity: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: 'AGENT-RED-001',
      name: 'Attacker',
      type: 'RED',
      status: 'WAITING',
      tasksCompleted: 15,
      tasksRunning: 0,
      tasksFailed: 2,
      currentTask: 'Awaiting authorization',
      lastActivity: new Date(Date.now() - 1800000).toISOString()
    },
    {
      id: 'AGENT-PURPLE-001',
      name: 'Validator',
      type: 'PURPLE',
      status: 'SUCCESS',
      tasksCompleted: 30,
      tasksRunning: 0,
      tasksFailed: 0,
      currentTask: null,
      lastActivity: new Date(Date.now() - 600000).toISOString()
    }
  ];
}

/**
 * Hook para monitorear agentes
 */
export function useAgentMonitor() {
  const [agents, setAgents] = useState([]);
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch('/api/agents');
        if (response.ok) {
          const data = await response.json();
          setAgents(data.agents || []);
        }
      } catch (err) {
        console.error('Error fetching agents:', err);
      }
    };
    
    fetchAgents();
    const interval = setInterval(fetchAgents, 10000); // Refresh cada 10s
    
    return () => clearInterval(interval);
  }, []);
  
  return {
    agents,
    connected,
    blueAgents: agents.filter(a => a.type === 'BLUE'),
    redAgents: agents.filter(a => a.type === 'RED'),
    purpleAgents: agents.filter(a => a.type === 'PURPLE'),
    runningAgents: agents.filter(a => a.status === 'RUNNING')
  };
}
