/**
 * SEGRD Security - Live Logs Panel v4.4.1
 * Panel de logs en tiempo real con WebSocket y filtrado
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useCaseContext } from '../context/CaseContext';

// Niveles de log
const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];

const LEVEL_STYLES = {
  DEBUG: { bg: 'bg-gray-700', text: 'text-gray-400', icon: '🔍' },
  INFO: { bg: 'bg-blue-900/50', text: 'text-blue-400', icon: 'ℹ️' },
  WARNING: { bg: 'bg-yellow-900/50', text: 'text-yellow-400', icon: '⚠️' },
  ERROR: { bg: 'bg-red-900/50', text: 'text-red-400', icon: '❌' }
};

/**
 * Panel de logs en tiempo real
 */
export default function LiveLogsPanel({ 
  caseId = null, 
  analysisId = null,
  maxLogs = 500,
  autoScroll = true,
  showFilters = true 
}) {
  const { currentCase } = useCaseContext();
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const [filters, setFilters] = useState({
    levels: new Set(LOG_LEVELS),
    search: ''
  });
  
  const wsRef = useRef(null);
  const logsContainerRef = useRef(null);
  const effectiveCaseId = caseId || currentCase?.id;

  // Conectar WebSocket
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [effectiveCaseId, analysisId]);

  // Aplicar filtros cuando cambien los logs o filtros
  useEffect(() => {
    applyFilters();
  }, [logs, filters]);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && !paused && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll, paused]);

  const connectWebSocket = () => {
    let wsPath;
    
    if (analysisId) {
      wsPath = `/ws/analysis/${analysisId}`;
    } else if (effectiveCaseId) {
      wsPath = `/ws/case/${effectiveCaseId}/live`;
    } else {
      wsPath = '/ws/global/logs';
    }
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${wsPath}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('📡 LiveLogs WebSocket connected:', wsPath);
        setWsConnected(true);
      };
      
      wsRef.current.onmessage = (event) => {
        if (paused) return;
        
        try {
          const data = JSON.parse(event.data);
          
          // Ignorar heartbeats
          if (data.type === 'heartbeat') return;
          
          // Agregar log
          setLogs(prev => {
            const newLogs = [...prev, {
              ...data,
              id: Date.now() + Math.random(),
              timestamp: data.timestamp || new Date().toISOString()
            }];
            
            // Limitar cantidad de logs
            if (newLogs.length > maxLogs) {
              return newLogs.slice(-maxLogs);
            }
            return newLogs;
          });
        } catch (err) {
          console.error('Error parsing log:', err);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('🔌 LiveLogs WebSocket disconnected');
        setWsConnected(false);
        
        // Reconectar después de 3 segundos
        setTimeout(() => {
          if (!paused) connectWebSocket();
        }, 3000);
      };
      
      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
        setWsConnected(false);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  };

  const applyFilters = useCallback(() => {
    let result = logs;
    
    // Filtrar por nivel
    if (filters.levels.size < LOG_LEVELS.length) {
      result = result.filter(log => filters.levels.has(log.level));
    }
    
    // Filtrar por búsqueda
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      result = result.filter(log => 
        log.message?.toLowerCase().includes(searchLower) ||
        log.analysis_id?.toLowerCase().includes(searchLower)
      );
    }
    
    setFilteredLogs(result);
  }, [logs, filters]);

  const toggleLevel = (level) => {
    setFilters(prev => {
      const newLevels = new Set(prev.levels);
      if (newLevels.has(level)) {
        newLevels.delete(level);
      } else {
        newLevels.add(level);
      }
      return { ...prev, levels: newLevels };
    });
  };

  const clearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
  };

  const exportLogs = () => {
    const logText = filteredLogs
      .map(log => `[${log.timestamp}] [${log.level}] ${log.message}`)
      .join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${effectiveCaseId || 'global'}_${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="bg-gray-900 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            📋 Live Logs
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </h3>
          <span className="text-sm text-gray-400">
            {filteredLogs.length} / {logs.length} logs
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Pause/Resume */}
          <button
            onClick={() => setPaused(!paused)}
            className={`px-3 py-1 rounded text-xs font-medium ${
              paused 
                ? 'bg-green-600 hover:bg-green-700 text-white' 
                : 'bg-yellow-600 hover:bg-yellow-700 text-white'
            }`}
          >
            {paused ? '▶️ Resume' : '⏸️ Pause'}
          </button>
          
          {/* Clear */}
          <button
            onClick={clearLogs}
            className="px-3 py-1 rounded text-xs font-medium bg-gray-700 hover:bg-gray-600 text-white"
          >
            🗑️ Clear
          </button>
          
          {/* Export */}
          <button
            onClick={exportLogs}
            className="px-3 py-1 rounded text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white"
          >
            📥 Export
          </button>
        </div>
      </div>
      
      {/* Filters */}
      {showFilters && (
        <div className="px-4 py-2 border-b border-gray-700 flex items-center gap-4">
          {/* Level toggles */}
          <div className="flex items-center gap-1">
            {LOG_LEVELS.map(level => (
              <button
                key={level}
                onClick={() => toggleLevel(level)}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                  filters.levels.has(level)
                    ? `${LEVEL_STYLES[level].bg} ${LEVEL_STYLES[level].text}`
                    : 'bg-gray-700 text-gray-500'
                }`}
              >
                {LEVEL_STYLES[level].icon} {level}
              </button>
            ))}
          </div>
          
          {/* Search */}
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search logs..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="w-full px-3 py-1 rounded bg-gray-900 border border-gray-600 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      )}
      
      {/* Logs container */}
      <div 
        ref={logsContainerRef}
        className="flex-1 overflow-y-auto p-2 font-mono text-xs"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {paused ? '⏸️ Logs paused' : wsConnected ? 'Waiting for logs...' : '⏳ Connecting...'}
          </div>
        ) : (
          filteredLogs.map((log) => (
            <LogLine key={log.id} log={log} />
          ))
        )}
      </div>
      
      {/* Footer status */}
      <div className="px-4 py-2 border-t border-gray-700 text-xs text-gray-500 flex items-center justify-between">
        <span>
          {effectiveCaseId ? `Case: ${effectiveCaseId}` : 'Global logs'}
          {analysisId && ` | Analysis: ${analysisId}`}
        </span>
        <span>
          {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </span>
      </div>
    </div>
  );
}

/**
 * Línea de log individual
 */
function LogLine({ log }) {
  const style = LEVEL_STYLES[log.level] || LEVEL_STYLES.INFO;
  const timestamp = log.timestamp 
    ? new Date(log.timestamp).toLocaleTimeString() 
    : '';
  
  return (
    <div className={`flex gap-2 py-1 px-2 rounded hover:bg-gray-700/50 ${style.bg}`}>
      <span className="text-gray-500 w-20 flex-shrink-0">{timestamp}</span>
      <span className={`w-16 flex-shrink-0 ${style.text}`}>
        {style.icon} {log.level}
      </span>
      {log.analysis_id && (
        <span className="text-purple-400 w-24 flex-shrink-0 truncate">
          {log.analysis_id}
        </span>
      )}
      <span className="text-gray-300 flex-1 break-all">{log.message}</span>
    </div>
  );
}

/**
 * Hook para usar logs en tiempo real
 */
export function useLiveLogs(caseId = null, analysisId = null) {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  
  useEffect(() => {
    let wsPath;
    if (analysisId) {
      wsPath = `/ws/analysis/${analysisId}`;
    } else if (caseId) {
      wsPath = `/ws/case/${caseId}/live`;
    } else {
      wsPath = '/ws/global/logs';
    }
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${wsPath}`;
    
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onopen = () => setConnected(true);
    wsRef.current.onclose = () => setConnected(false);
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== 'heartbeat') {
        setLogs(prev => [...prev.slice(-499), data]);
      }
    };
    
    return () => wsRef.current?.close();
  }, [caseId, analysisId]);
  
  return { logs, connected, clear: () => setLogs([]) };
}
