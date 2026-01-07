import api from './api';

export const investigationService = {
  // Get all investigations
  getInvestigations: async (page = 1, limit = 50, filters = {}) => {
    const response = await api.get('/investigations', {
      params: { page, limit, ...filters }
    });
    return response.data;
  },

  // Get investigation details
  getInvestigationDetail: async (investigationId) => {
    const response = await api.get(`/investigations/${investigationId}`);
    return response.data;
  },

  // Create investigation
  createInvestigation: async (investigationData) => {
    const response = await api.post('/investigations', investigationData);
    return response.data;
  },

  // Update investigation
  updateInvestigation: async (investigationId, investigationData) => {
    const response = await api.put(`/investigations/${investigationId}`, investigationData);
    return response.data;
  },

  // Close investigation
  closeInvestigation: async (investigationId, reason = '') => {
    const response = await api.post(`/investigations/${investigationId}/close`, { reason });
    return response.data;
  },

  // Get investigation graph (attack graph)
  getInvestigationGraph: async (investigationId) => {
    const response = await api.get(`/investigations/${investigationId}/graph`);
    return response.data;
  },

  // Get investigation evidence
  getInvestigationEvidence: async (investigationId) => {
    const response = await api.get(`/investigations/${investigationId}/evidence`);
    return response.data;
  },

  // Get investigation IOCs
  getInvestigationIOCs: async (investigationId) => {
    const response = await api.get(`/investigations/${investigationId}/iocs`);
    return response.data;
  },

  // Add IOC to investigation
  addIOC: async (investigationId, iocData) => {
    const response = await api.post(`/investigations/${investigationId}/iocs`, iocData);
    return response.data;
  },

  // Get investigation timeline
  getInvestigationTimeline: async (investigationId) => {
    const response = await api.get(`/investigations/${investigationId}/timeline`);
    return response.data;
  },

  // Generate investigation report
  generateReport: async (investigationId, format = 'pdf') => {
    const response = await api.get(`/investigations/${investigationId}/report`, {
      params: { format },
      responseType: format === 'pdf' ? 'blob' : 'json'
    });
    return response.data;
  },

  // Search investigations
  searchInvestigations: async (query) => {
    const response = await api.get('/investigations/search', {
      params: { q: query }
    });
    return response.data;
  },

  // Get investigation status
  getInvestigationStatus: async (investigationId) => {
    const response = await api.get(`/investigations/${investigationId}/status`);
    return response.data;
  }
};
