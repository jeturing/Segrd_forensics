import api from './api';

// Usar endpoints v4.1 con datos reales
const BASE_URL = '/api/v41/agents';

export const agentService = {
  // Get all agents (datos reales o demo)
  getAgents: async (filters = {}) => {
    try {
      const response = await api.get(`${BASE_URL}/`, { params: filters });
      return {
        agents: response.data.agents || [],
        total: response.data.total || 0,
        dataSource: response.data.data_source
      };
    } catch (error) {
      console.error('Error fetching agents:', error);
      throw error;
    }
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
  deployAgent: async (agentData) => {
    const response = await api.post(`${BASE_URL}/deploy`, agentData);
    return response.data;
  },

  // Register agent
  registerAgent: async (registrationData) => {
    const response = await api.post(`${BASE_URL}/register`, registrationData);
    return response.data;
  },

  // Execute command on agent
  executeCommand: async (agentId, command, osType = 'linux') => {
    const response = await api.post(`${BASE_URL}/${agentId}/execute`, {
      command,
      os_type: osType
    });
    return response.data;
  },

  // Get agent tasks
  getAgentTasks: async (agentId) => {
    const response = await api.get(`${BASE_URL}/${agentId}/tasks`);
    return response.data;
  },

  // Start network capture
  startNetworkCapture: async (agentId, config = {}) => {
    const response = await api.post(`${BASE_URL}/${agentId}/capture`, config);
    return response.data;
  },

  // Get memory dump
  getMemoryDump: async (agentId) => {
    const response = await api.post(`${BASE_URL}/${agentId}/memory`);
    return response.data;
  },

  // List files
  listFiles: async (agentId, path = '/') => {
    const response = await api.get(`${BASE_URL}/${agentId}/files`, { params: { path } });
    return response.data;
  },

  // Run YARA scan
  runYaraScan: async (agentId, config = {}) => {
    const response = await api.post(`${BASE_URL}/${agentId}/yara`, config);
    return response.data;
  },

  // Get command templates
  getCommandTemplates: async (osType = 'linux') => {
    const response = await api.get(`${BASE_URL}/commands/templates`, { params: { os_type: osType } });
    return response.data;
  }
};
