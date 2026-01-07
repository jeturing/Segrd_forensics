/**
 * Realtime WebSocket Service
 * Servicio para conexiones WebSocket en tiempo real
 */

const rawWsBase = import.meta.env.VITE_WS_URL || 'ws://localhost:9000/ws';
const WS_BASE_URL = rawWsBase.replace(/\/$/, '');
const WS_ROOT = WS_BASE_URL.endsWith('/ws') ? WS_BASE_URL : `${WS_BASE_URL}/ws`;

/**
 * Clase base para gestionar conexiones WebSocket
 */
class WebSocketClient {
  constructor(channel, options = {}) {
    this.channel = channel;
    this.url = `${WS_ROOT}/${channel}`;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 3000;
    this.onMessageCallback = null;
    this.onConnectCallback = null;
    this.onDisconnectCallback = null;
    this.onErrorCallback = null;
    this.pingInterval = null;
    this.isConnecting = false;
  }

  /**
   * Conectar al WebSocket
   */
  connect() {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return this;
    }

    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log(`🔌 WebSocket conectado: ${this.channel}`);
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        
        // Iniciar ping para mantener conexión viva
        this.startPing();
        
        if (this.onConnectCallback) {
          this.onConnectCallback();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Ignorar pong
          if (data.event === 'pong') return;
          
          if (this.onMessageCallback) {
            this.onMessageCallback(data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log(`🔌 WebSocket desconectado: ${this.channel}`, event.code);
        this.isConnecting = false;
        this.stopPing();
        
        if (this.onDisconnectCallback) {
          this.onDisconnectCallback(event);
        }
        
        // Intentar reconexión automática
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`🔄 Reconectando (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
          setTimeout(() => this.connect(), this.reconnectDelay);
        }
      };

      this.ws.onerror = (error) => {
        console.error(`❌ WebSocket error en ${this.channel}:`, error);
        this.isConnecting = false;
        
        if (this.onErrorCallback) {
          this.onErrorCallback(error);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      this.isConnecting = false;
    }

    return this;
  }

  /**
   * Desconectar WebSocket
   */
  disconnect() {
    this.stopPing();
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevenir reconexión
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Enviar mensaje
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }

  /**
   * Registrar callback para mensajes
   */
  onMessage(callback) {
    this.onMessageCallback = callback;
    return this;
  }

  /**
   * Registrar callback para conexión
   */
  onConnect(callback) {
    this.onConnectCallback = callback;
    return this;
  }

  /**
   * Registrar callback para desconexión
   */
  onDisconnect(callback) {
    this.onDisconnectCallback = callback;
    return this;
  }

  /**
   * Registrar callback para errores
   */
  onError(callback) {
    this.onErrorCallback = callback;
    return this;
  }

  /**
   * Iniciar ping periódico
   */
  startPing() {
    this.pingInterval = setInterval(() => {
      this.send('ping');
    }, 30000); // Cada 30 segundos
  }

  /**
   * Detener ping
   */
  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Verificar si está conectado
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// ============================================================================
// FUNCIONES DE CONVENIENCIA PARA CANALES ESPECÍFICOS
// ============================================================================

/**
 * Conectar al canal IOC Store
 * @param {Function} onMessage - Callback para mensajes recibidos
 * @returns {WebSocketClient} - Cliente WebSocket
 */
export function connectIocStoreChannel(onMessage) {
  const client = new WebSocketClient('ioc-store');
  return client.onMessage(onMessage).connect();
}

/**
 * Conectar al canal de investigaciones general
 * @param {Function} onMessage - Callback para mensajes recibidos
 * @returns {WebSocketClient} - Cliente WebSocket
 */
export function connectInvestigationsChannel(onMessage) {
  const client = new WebSocketClient('investigations');
  return client.onMessage(onMessage).connect();
}

/**
 * Conectar al canal de una investigación específica
 * @param {string} investigationId - ID de la investigación
 * @param {Function} onMessage - Callback para mensajes recibidos
 * @returns {WebSocketClient} - Cliente WebSocket
 */
export function connectInvestigationChannel(investigationId, onMessage) {
  const client = new WebSocketClient(`investigation/${investigationId}`);
  return client.onMessage(onMessage).connect();
}

/**
 * Conectar al canal del dashboard
 * @param {Function} onMessage - Callback para mensajes recibidos
 * @returns {WebSocketClient} - Cliente WebSocket
 */
export function connectDashboardChannel(onMessage) {
  const client = new WebSocketClient('dashboard');
  return client.onMessage(onMessage).connect();
}

/**
 * Conectar al canal de agentes móviles
 * @param {Function} onMessage - Callback para mensajes recibidos
 * @returns {WebSocketClient} - Cliente WebSocket
 */
export function connectAgentsChannel(onMessage) {
  const client = new WebSocketClient('agents');
  return client.onMessage(onMessage).connect();
}

// ============================================================================
// HOOKS REACT PARA WEBSOCKET
// ============================================================================

import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Hook para usar WebSocket en componentes React
 * @param {string} channel - Canal WebSocket
 * @param {Object} options - Opciones de configuración
 * @returns {Object} - Estado y funciones del WebSocket
 */
export function useWebSocket(channel, options = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);
  const clientRef = useRef(null);

  const connect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }

    const client = new WebSocketClient(channel, options);
    
    client
      .onConnect(() => {
        setIsConnected(true);
        setError(null);
      })
      .onMessage((data) => {
        setLastMessage(data);
        if (options.onMessage) {
          options.onMessage(data);
        }
      })
      .onDisconnect(() => {
        setIsConnected(false);
      })
      .onError((err) => {
        setError(err);
        if (options.onError) {
          options.onError(err);
        }
      })
      .connect();

    clientRef.current = client;
  }, [channel, options]);

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      clientRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const send = useCallback((message) => {
    if (clientRef.current) {
      clientRef.current.send(message);
    }
  }, []);

  useEffect(() => {
    if (options.autoConnect !== false) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [channel]);

  return {
    isConnected,
    lastMessage,
    error,
    connect,
    disconnect,
    send
  };
}

/**
 * Hook específico para IOC Store
 * @param {Function} onEvent - Callback para eventos del IOC Store
 * @returns {Object} - Estado del WebSocket
 */
export function useIocStoreWebSocket(onEvent) {
  return useWebSocket('ioc-store', {
    onMessage: onEvent
  });
}

/**
 * Hook específico para una investigación
 * @param {string} investigationId - ID de la investigación
 * @param {Function} onEvent - Callback para eventos
 * @returns {Object} - Estado del WebSocket
 */
export function useInvestigationWebSocket(investigationId, onEvent) {
  return useWebSocket(`investigation/${investigationId}`, {
    onMessage: onEvent
  });
}

// ============================================================================
// EXPORT DEFAULT
// ============================================================================

export default {
  WebSocketClient,
  connectIocStoreChannel,
  connectInvestigationsChannel,
  connectInvestigationChannel,
  connectDashboardChannel,
  connectAgentsChannel,
  useWebSocket,
  useIocStoreWebSocket,
  useInvestigationWebSocket
};

export { WS_ROOT as WS_BASE_URL };
