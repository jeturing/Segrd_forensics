/**
 * Remote Agents Service v4.5
 * Servicio para gestión de agentes remotos con descarga de scripts
 * y comunicación en tiempo real via WebSocket
 */

import api from './api';

const BASE_URL = '/api/remote-agents';

/**
 * Generar un nuevo token y script de agente
 * @param {Object} params
 * @param {string} params.agent_name - Nombre del agente
 * @param {string} params.os_type - Sistema operativo (windows|linux|mac)
 * @param {string} params.case_id - ID del caso asociado
 * @param {number} params.expires_hours - Horas de validez (default 24)
 */
export const generateAgentScript = async ({ agent_name, os_type, case_id, expires_hours = 24 }) => {
  const response = await api.post(`${BASE_URL}/generate`, {
    agent_name,
    os_type,
    case_id,
    expires_hours
  });
  return response.data;
};

/**
 * Obtener URL de descarga del script
 * @param {string} token - Token del agente
 */
export const getDownloadUrl = (token) => {
  return `${window.location.origin}${BASE_URL}/download/${token}`;
};

/**
 * Descargar script de agente directamente
 * @param {string} token - Token del agente
 * @param {string} agentName - Nombre para el archivo
 * @param {string} osType - Tipo de OS para extensión
 */
export const downloadAgentScript = async (token, agentName, osType) => {
  const response = await api.get(`${BASE_URL}/download/${token}`, {
    responseType: 'blob'
  });
  
  const extension = osType === 'windows' ? 'ps1' : 'sh';
  const filename = `mcp_agent_${agentName}.${extension}`;
  
  // Crear link de descarga
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

/**
 * Listar tokens de agentes activos
 * @param {Object} params
 * @param {string} params.case_id - Filtrar por caso (opcional)
 * @param {boolean} params.only_connected - Solo agentes conectados
 */
export const listAgentTokens = async ({ case_id, only_connected = false } = {}) => {
  const params = new URLSearchParams();
  if (case_id) params.append('case_id', case_id);
  if (only_connected) params.append('only_connected', 'true');
  
  const response = await api.get(`${BASE_URL}/tokens?${params}`);
  return response.data;
};

/**
 * Revocar token de agente
 * @param {string} token - Token completo del agente
 */
export const revokeAgentToken = async (token) => {
  const response = await api.delete(`${BASE_URL}/tokens/${token}`);
  return response.data;
};

/**
 * Enviar comando a agente remoto
 * @param {string} token - Token del agente
 * @param {Object} params
 * @param {string} params.command - Comando a ejecutar
 * @param {number} params.timeout - Timeout en segundos
 * @param {boolean} params.run_as_admin - Ejecutar como admin
 * @param {boolean} params.save_output - Guardar resultado
 */
export const sendCommandToAgent = async (token, { command, timeout = 300, run_as_admin = false, save_output = true }) => {
  const response = await api.post(`${BASE_URL}/send-command/${token}`, {
    command,
    timeout,
    run_as_admin,
    save_output
  });
  return response.data;
};

/**
 * Obtener resultado de un comando
 * @param {string} commandId - ID del comando
 */
export const getCommandResult = async (commandId) => {
  const response = await api.get(`${BASE_URL}/command-result/${commandId}`);
  return response.data;
};

/**
 * Obtener historial de comandos por caso
 * @param {string} caseId - ID del caso
 * @param {number} limit - Límite de resultados
 */
export const getCaseCommandHistory = async (caseId, limit = 50) => {
  const response = await api.get(`${BASE_URL}/history/${caseId}?limit=${limit}`);
  return response.data;
};

/**
 * Obtener estado general del sistema de agentes
 */
export const getRemoteAgentsStatus = async () => {
  const response = await api.get(`${BASE_URL}/status`);
  return response.data;
};

/**
 * Conectar WebSocket para recibir resultados en tiempo real
 * @param {string} token - Token del agente a monitorear
 * @param {Object} handlers - Callbacks para eventos
 */
export const connectAgentWebSocket = (token, handlers = {}) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}${BASE_URL}/ws/${token}`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log('🔌 WebSocket conectado al agente');
    handlers.onConnect?.();
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('📥 Mensaje del agente:', data.type);
      
      switch (data.type) {
        case 'connected':
          handlers.onConnected?.(data);
          break;
        case 'command_result':
          handlers.onCommandResult?.(data);
          break;
        case 'heartbeat':
          handlers.onHeartbeat?.(data);
          break;
        case 'error':
          handlers.onError?.(data);
          break;
        default:
          handlers.onMessage?.(data);
      }
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
    handlers.onError?.({ type: 'websocket_error', error });
  };
  
  ws.onclose = (event) => {
    console.log('🔌 WebSocket cerrado:', event.code, event.reason);
    handlers.onClose?.({ code: event.code, reason: event.reason });
  };
  
  return {
    ws,
    send: (data) => ws.send(JSON.stringify(data)),
    close: () => ws.close(),
    isConnected: () => ws.readyState === WebSocket.OPEN
  };
};

export default {
  generateAgentScript,
  getDownloadUrl,
  downloadAgentScript,
  listAgentTokens,
  revokeAgentToken,
  sendCommandToAgent,
  getCommandResult,
  getCaseCommandHistory,
  getRemoteAgentsStatus,
  connectAgentWebSocket
};
