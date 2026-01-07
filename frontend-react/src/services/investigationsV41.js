/**
 * Investigation Service v4.1 - Real Data
 * Conecta con los endpoints v4.1 que usan datos reales de la DB
 */
import api from './api';

const BASE_URL = '/api/v41/investigations';

export const investigationServiceV41 = {
  // Get all investigations (real data)
  getInvestigations: async (filters = {}) => {
    const response = await api.get(BASE_URL + '/', { params: filters });
    return response.data;
  },

  // Get investigation details
  getInvestigationDetail: async (investigationId) => {
    const response = await api.get(`${BASE_URL}/${investigationId}`);
    return response.data;
  },

  // Create investigation
  createInvestigation: async (investigationData) => {
    const response = await api.post(BASE_URL, investigationData);
    return response.data;
  },

  // Update investigation
  updateInvestigation: async (investigationId, investigationData) => {
    const response = await api.put(`${BASE_URL}/${investigationId}`, investigationData);
    return response.data;
  },

  // Close investigation
  closeInvestigation: async (investigationId, resolution = '') => {
    const response = await api.post(`${BASE_URL}/${investigationId}/close`, { resolution });
    return response.data;
  },

  // Get investigation graph
  getInvestigationGraph: async (investigationId) => {
    const response = await api.get(`${BASE_URL}/${investigationId}/graph`);
    return response.data;
  },

  // Get investigation timeline
  getInvestigationTimeline: async (investigationId) => {
    const response = await api.get(`${BASE_URL}/${investigationId}/timeline`);
    return response.data;
  },

  // Get investigation IOCs
  getInvestigationIOCs: async (investigationId) => {
    const response = await api.get(`${BASE_URL}/${investigationId}/iocs`);
    return response.data;
  },

  // Add IOC to investigation
  addIOC: async (investigationId, iocData) => {
    const response = await api.post(`${BASE_URL}/${investigationId}/iocs`, iocData);
    return response.data;
  },

  // Statistics
  getStats: async () => {
    const response = await api.get(`${BASE_URL}/stats`);
    return response.data;
  }
};

export default investigationServiceV41;
