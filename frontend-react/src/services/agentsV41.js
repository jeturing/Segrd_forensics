/**
 * Agents Service v4.1 - Real Data
 * Conecta con los endpoints v4.1 que usan datos reales de la DB
 */
import api from './api';

const BASE_URL = '/api/v41/agents';

export const agentServiceV41 = {
  // Get all agents (real data or demo fallback)
  getAgents: async (filters = {}) => {
    const response = await api.get(BASE_URL + '/', { params: filters });
    return response.data;
  },

  // Get agent types configuration
  getAgentTypes: async () => {
    const response = await api.get(`${BASE_URL}/types`);
    return response.data;
  },

  // Get agent details
  getAgentDetail: async (agentId) => {
    const response = await api.get(`${BASE_URL}/${agentId}`);
    return response.data;
  },

  // Deploy agent
  deployAgent: async (deployConfig) => {
    const response = await api.post(`${BASE_URL}/deploy`, deployConfig);
    return response.data;
  },

  // Register agent
  registerAgent: async (registrationData) => {
    const response = await api.post(`${BASE_URL}/register`, registrationData);
    return response.data;
  },

  // Execute command on agent
  executeCommand: async (agentId, commandData) => {
    const response = await api.post(`${BASE_URL}/${agentId}/execute`, commandData);
    return response.data;
  },

  // Start packet capture
  startCapture: async (agentId, captureConfig) => {
    const response = await api.post(`${BASE_URL}/${agentId}/capture`, captureConfig);
    return response.data;
  },

  // Get memory dump
  getMemoryDump: async (agentId) => {
    const response = await api.post(`${BASE_URL}/${agentId}/memory`);
    return response.data;
  },

  // List files on agent
  listFiles: async (agentId, path) => {
    const response = await api.get(`${BASE_URL}/${agentId}/files`, { params: { path } });
    return response.data;
  },

  // Run YARA scan on agent
  runYaraScan: async (agentId, yaraScanConfig) => {
    const response = await api.post(`${BASE_URL}/${agentId}/yara`, yaraScanConfig);
    return response.data;
  },

  // Get agent tasks
  getAgentTasks: async (agentId) => {
    const response = await api.get(`${BASE_URL}/${agentId}/tasks`);
    return response.data;
  },

  // Get command templates
  getCommandTemplates: async (osType = 'linux') => {
    const response = await api.get(`${BASE_URL}/commands/templates`, { params: { os_type: osType } });
    return response.data;
  }
};

export default agentServiceV41;
