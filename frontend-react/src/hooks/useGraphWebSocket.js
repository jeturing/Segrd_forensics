/**
 * useGraphWebSocket v4.5.0
 * ========================
 * Hook para conexión WebSocket con actualizaciones en tiempo real
 * del grafo de ataque durante análisis activos.
 * 
 * Features:
 * - Auto-conexión/reconexión
 * - Heartbeat para mantener conexión viva
 * - Manejo de eventos: new_node, new_edge, update_node, analysis_complete
 * - Buffer de actualizaciones para batch rendering
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// Tipos de eventos del WebSocket
export const GRAPH_WS_EVENTS = {
  NEW_NODE: 'graph:new_node',
  NEW_EDGE: 'graph:new_edge',
  UPDATE_NODE: 'graph:update_node',
  DELETE_NODE: 'graph:delete_node',
  ANALYSIS_PROGRESS: 'graph:analysis_progress',
  ANALYSIS_COMPLETE: 'graph:analysis_complete',
  ERROR: 'graph:error'
};

// Estados de conexión
export const CONNECTION_STATE = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error'
};

/**
 * Hook principal para WebSocket del grafo
 * 
 * @param {string} caseId - ID del caso para suscribirse
 * @param {Object} options - Opciones de configuración
 * @returns {Object} Estado y funciones de control
 */
export function useGraphWebSocket(caseId, options = {}) {
  const {
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    batchUpdates = true,
    batchDelay = 100, // ms para acumular updates antes de aplicar
    onNodeAdded = null,
    onEdgeAdded = null,
    onNodeUpdated = null,
    onAnalysisComplete = null,
    onError = null
  } = options;

  // Estado
  const [connectionState, setConnectionState] = useState(CONNECTION_STATE.DISCONNECTED);
  const [lastMessage, setLastMessage] = useState(null);
  const [pendingUpdates, setPendingUpdates] = useState({ nodes: [], edges: [] });
  const [analysisProgress, setAnalysisProgress] = useState(0);
  
  // Refs
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatRef = useRef(null);
  const batchTimeoutRef = useRef(null);
  const updateBufferRef = useRef({ nodes: [], edges: [] });

  // Construir URL del WebSocket
  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || window.location.host;
    return `${protocol}//${host}/ws/graph/${caseId}`;
  }, [caseId]);

  // Limpiar timeouts
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current);
      batchTimeoutRef.current = null;
    }
  }, []);

  // Procesar buffer de actualizaciones
  const flushUpdateBuffer = useCallback(() => {
    const buffer = updateBufferRef.current;
    
    if (buffer.nodes.length > 0 || buffer.edges.length > 0) {
      setPendingUpdates({
        nodes: [...buffer.nodes],
        edges: [...buffer.edges]
      });
      
      // Limpiar buffer
      updateBufferRef.current = { nodes: [], edges: [] };
    }
    
    batchTimeoutRef.current = null;
  }, []);

  // Agregar update al buffer
  const bufferUpdate = useCallback((type, data) => {
    if (type === 'node') {
      updateBufferRef.current.nodes.push(data);
    } else if (type === 'edge') {
      updateBufferRef.current.edges.push(data);
    }

    // Programar flush si no está programado
    if (batchUpdates && !batchTimeoutRef.current) {
      batchTimeoutRef.current = setTimeout(flushUpdateBuffer, batchDelay);
    } else if (!batchUpdates) {
      flushUpdateBuffer();
    }
  }, [batchUpdates, batchDelay, flushUpdateBuffer]);

  // Manejar mensajes entrantes
  const handleMessage = useCallback((event) => {
    try {
      const message = JSON.parse(event.data);
      setLastMessage(message);

      switch (message.type) {
        case GRAPH_WS_EVENTS.NEW_NODE:
          bufferUpdate('node', { action: 'add', data: message.payload });
          onNodeAdded?.(message.payload);
          break;

        case GRAPH_WS_EVENTS.NEW_EDGE:
          bufferUpdate('edge', { action: 'add', data: message.payload });
          onEdgeAdded?.(message.payload);
          break;

        case GRAPH_WS_EVENTS.UPDATE_NODE:
          bufferUpdate('node', { action: 'update', data: message.payload });
          onNodeUpdated?.(message.payload);
          break;

        case GRAPH_WS_EVENTS.DELETE_NODE:
          bufferUpdate('node', { action: 'delete', data: message.payload });
          break;

        case GRAPH_WS_EVENTS.ANALYSIS_PROGRESS:
          setAnalysisProgress(message.payload.progress || 0);
          break;

        case GRAPH_WS_EVENTS.ANALYSIS_COMPLETE:
          setAnalysisProgress(100);
          onAnalysisComplete?.(message.payload);
          break;

        case GRAPH_WS_EVENTS.ERROR:
          console.error('Graph WS Error:', message.payload);
          onError?.(message.payload);
          break;

        case 'pong':
          // Heartbeat response - conexión viva
          break;

        default:
          console.log('Unknown graph message type:', message.type);
      }
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  }, [bufferUpdate, onNodeAdded, onEdgeAdded, onNodeUpdated, onAnalysisComplete, onError]);

  // Conectar WebSocket
  const connect = useCallback(() => {
    if (!caseId) {
      console.warn('useGraphWebSocket: No caseId provided');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    cleanup();
    setConnectionState(CONNECTION_STATE.CONNECTING);

    try {
      const url = getWsUrl();
      console.log(`🔌 Connecting to graph WebSocket: ${url}`);
      
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        console.log('✅ Graph WebSocket connected');
        setConnectionState(CONNECTION_STATE.CONNECTED);
        reconnectCountRef.current = 0;

        // Iniciar heartbeat
        heartbeatRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, heartbeatInterval);

        // Suscribirse a updates del caso
        wsRef.current.send(JSON.stringify({
          type: 'subscribe',
          payload: { case_id: caseId, channel: 'graph_updates' }
        }));
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onclose = (event) => {
        console.log(`WebSocket closed: code=${event.code}, reason=${event.reason}`);
        setConnectionState(CONNECTION_STATE.DISCONNECTED);
        cleanup();

        // Intentar reconectar si no fue cierre intencional
        if (event.code !== 1000 && reconnectCountRef.current < reconnectAttempts) {
          setConnectionState(CONNECTION_STATE.RECONNECTING);
          reconnectCountRef.current++;
          
          console.log(`🔄 Reconnecting (${reconnectCountRef.current}/${reconnectAttempts})...`);
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionState(CONNECTION_STATE.ERROR);
        onError?.(error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionState(CONNECTION_STATE.ERROR);
    }
  }, [caseId, getWsUrl, cleanup, handleMessage, heartbeatInterval, reconnectAttempts, reconnectInterval, onError]);

  // Desconectar WebSocket
  const disconnect = useCallback(() => {
    cleanup();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    
    setConnectionState(CONNECTION_STATE.DISCONNECTED);
    reconnectCountRef.current = 0;
  }, [cleanup]);

  // Enviar mensaje
  const send = useCallback((type, payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
      return true;
    }
    console.warn('WebSocket not connected, cannot send message');
    return false;
  }, []);

  // Limpiar updates pendientes (después de aplicarlos al grafo)
  const clearPendingUpdates = useCallback(() => {
    setPendingUpdates({ nodes: [], edges: [] });
  }, []);

  // Auto-conexión
  useEffect(() => {
    if (autoConnect && caseId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, caseId]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // Estado
    connectionState,
    isConnected: connectionState === CONNECTION_STATE.CONNECTED,
    lastMessage,
    pendingUpdates,
    analysisProgress,
    
    // Acciones
    connect,
    disconnect,
    send,
    clearPendingUpdates,
    
    // Helpers
    requestFullRefresh: () => send('request_full_graph', { case_id: caseId })
  };
}

/**
 * Hook simplificado para solo escuchar updates
 */
export function useGraphUpdates(caseId, onUpdate) {
  const { pendingUpdates, clearPendingUpdates, isConnected } = useGraphWebSocket(caseId);

  useEffect(() => {
    if (pendingUpdates.nodes.length > 0 || pendingUpdates.edges.length > 0) {
      onUpdate?.(pendingUpdates);
      clearPendingUpdates();
    }
  }, [pendingUpdates, onUpdate, clearPendingUpdates]);

  return { isConnected };
}

export default useGraphWebSocket;
