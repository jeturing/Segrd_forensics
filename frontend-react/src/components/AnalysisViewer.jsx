/**
 * MCP Kali Forensics - Analysis Viewer Component v4.4.1
 * Visualizador de análisis forenses con streaming de logs en tiempo real
 */

import React, { useState, useEffect, useRef } from 'react';
import { useCaseContext } from '../context/CaseContext';

// Estados de análisis
const ANALYSIS_STATUS = {
  QUEUED: 'queued',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

const STATUS_COLORS = {
  [ANALYSIS_STATUS.QUEUED]: 'bg-yellow-500',
  [ANALYSIS_STATUS.RUNNING]: 'bg-blue-500 animate-pulse',
  [ANALYSIS_STATUS.COMPLETED]: 'bg-green-500',
  [ANALYSIS_STATUS.FAILED]: 'bg-red-500',
  [ANALYSIS_STATUS.CANCELLED]: 'bg-gray-500'
};

const STATUS_ICONS = {
  [ANALYSIS_STATUS.QUEUED]: '⏳',
  [ANALYSIS_STATUS.RUNNING]: '🔄',
  [ANALYSIS_STATUS.COMPLETED]: '✅',
  [ANALYSIS_STATUS.FAILED]: '❌',
  [ANALYSIS_STATUS.CANCELLED]: '🚫'
};

/**
 * Componente principal del visor de análisis
 */
export default function AnalysisViewer({ analysisId }) {
  const { currentCase } = useCaseContext();
  const [analysis, setAnalysis] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  // Cargar datos del análisis
  useEffect(() => {
    if (analysisId) {
      fetchAnalysis();
      connectWebSocket();
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [analysisId]);

  // Auto-scroll de logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchAnalysis = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v41/analyses/${analysisId}`, {
        headers: {
          'X-API-Key': localStorage.getItem('apiKey') || ''
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch analysis');
      
      const data = await response.json();
      setAnalysis(data);
      setLogs(data.logs || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/analysis/${analysisId}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('🔗 WebSocket connected');
        setWsConnected(true);
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'heartbeat') return;
        
        if (data.type === 'log' || data.level) {
          setLogs(prev => [...prev, data]);
        } else if (data.type === 'status') {
          setAnalysis(prev => ({ ...prev, status: data.status }));
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        setWsConnected(false);
      };
      
      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
        setWsConnected(false);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
        <p className="text-red-400">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-900 px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">{STATUS_ICONS[analysis?.status]}</span>
            <div>
              <h3 className="text-lg font-semibold text-white">
                {analysis?.id}
              </h3>
              <p className="text-sm text-gray-400">
                {analysis?.tool_name} - {analysis?.analysis_type}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Status badge */}
            <span className={`px-3 py-1 rounded-full text-xs font-medium text-white ${STATUS_COLORS[analysis?.status]}`}>
              {analysis?.status?.toUpperCase()}
            </span>
            
            {/* WebSocket indicator */}
            <div className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}
                 title={wsConnected ? 'Connected' : 'Disconnected'} />
          </div>
        </div>
      </div>
      
      {/* Info Grid */}
      <div className="grid grid-cols-4 gap-4 p-4 border-b border-gray-700">
        <InfoCard 
          label="Case ID" 
          value={analysis?.case_id || currentCase?.id} 
        />
        <InfoCard 
          label="Started" 
          value={analysis?.started_at ? new Date(analysis.started_at).toLocaleString() : 'Pending'} 
        />
        <InfoCard 
          label="Duration" 
          value={calculateDuration(analysis?.started_at, analysis?.completed_at)} 
        />
        <InfoCard 
          label="Evidence Files" 
          value={analysis?.evidence_files?.length || 0} 
        />
      </div>
      
      {/* Findings Summary */}
      {analysis?.findings && Object.keys(analysis.findings).length > 0 && (
        <div className="p-4 border-b border-gray-700">
          <h4 className="text-sm font-medium text-gray-400 mb-2">Findings</h4>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(analysis.findings).map(([key, value]) => (
              <div key={key} className="bg-gray-900 rounded p-2">
                <span className="text-xs text-gray-500">{key}</span>
                <p className="text-sm text-white font-medium">
                  {typeof value === 'number' ? value : JSON.stringify(value)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Live Logs */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-gray-400">
            Live Logs ({logs.length})
          </h4>
          <button 
            onClick={() => setLogs([])}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Clear
          </button>
        </div>
        
        <div className="bg-gray-900 rounded-lg h-64 overflow-y-auto font-mono text-xs p-2">
          {logs.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No logs yet...</p>
          ) : (
            logs.map((log, index) => (
              <LogEntry key={index} log={log} />
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
      
      {/* Evidence Files */}
      {analysis?.evidence_files?.length > 0 && (
        <div className="p-4 border-t border-gray-700">
          <h4 className="text-sm font-medium text-gray-400 mb-2">
            Evidence Files
          </h4>
          <div className="space-y-1">
            {analysis.evidence_files.map((file, index) => (
              <div key={index} className="flex items-center gap-2 text-sm">
                <span className="text-blue-400">📄</span>
                <span className="text-gray-300">{file}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Componente de tarjeta de información
 */
function InfoCard({ label, value }) {
  return (
    <div className="bg-gray-900 rounded p-3">
      <span className="text-xs text-gray-500">{label}</span>
      <p className="text-sm text-white font-medium truncate">{value}</p>
    </div>
  );
}

/**
 * Componente de entrada de log
 */
function LogEntry({ log }) {
  const levelColors = {
    DEBUG: 'text-gray-500',
    INFO: 'text-blue-400',
    WARNING: 'text-yellow-400',
    ERROR: 'text-red-400'
  };
  
  const timestamp = log.timestamp 
    ? new Date(log.timestamp).toLocaleTimeString() 
    : '';
  
  return (
    <div className="flex gap-2 py-0.5 hover:bg-gray-800">
      <span className="text-gray-600 w-20 flex-shrink-0">{timestamp}</span>
      <span className={`w-16 flex-shrink-0 ${levelColors[log.level] || 'text-gray-400'}`}>
        [{log.level}]
      </span>
      <span className="text-gray-300 flex-1 break-all">{log.message}</span>
    </div>
  );
}

/**
 * Calcular duración del análisis
 */
function calculateDuration(startedAt, completedAt) {
  if (!startedAt) return 'N/A';
  
  const start = new Date(startedAt);
  const end = completedAt ? new Date(completedAt) : new Date();
  const diffMs = end - start;
  
  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}
