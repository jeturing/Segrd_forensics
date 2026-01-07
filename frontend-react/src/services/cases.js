import api from './api';

// Usar endpoints v4.1 con datos reales (baseURL ya incluye /api)
const BASE_URL = '/api/v41/investigations';

export const caseService = {
  // Get all cases/investigations (datos reales)
  getCases: async (page = 1, limit = 50) => {
    try {
      const response = await api.get(`${BASE_URL}/`, {
        params: { page, limit }
      });
      // Adaptar formato para Redux
      return {
        items: response.data.investigations || [],
        pagination: {
          page,
          limit,
          total: response.data.total || 0
        },
        dataSource: response.data.data_source
      };
    } catch (error) {
      console.error('Error fetching cases:', error);
      throw error;
    }
  },

  // Get case details
  getCaseDetail: async (caseId) => {
    const response = await api.get(`${BASE_URL}/${caseId}`);
    return response.data;
  },

  // Create new case
  createCase: async (caseData) => {
    const response = await api.post(`${BASE_URL}/`, caseData);
    return response.data;
  },

  // Update case
  updateCase: async (caseId, caseData) => {
    const response = await api.put(`${BASE_URL}/${caseId}`, caseData);
    return response.data;
  },

  // Close case
  closeCase: async (caseId, resolution = '') => {
    const response = await api.post(`${BASE_URL}/${caseId}/close`, { resolution });
    return response.data;
  },

  // Get case evidence (alias para IOCs)
  getCaseEvidence: async (caseId) => {
    const response = await api.get(`${BASE_URL}/${caseId}/iocs`);
    return response.data;
  },

  // Get case IOCs
  getCaseIOCs: async (caseId) => {
    const response = await api.get(`${BASE_URL}/${caseId}/iocs`);
    return response.data;
  },

  // Get case timeline
  getCaseTimeline: async (caseId) => {
    const response = await api.get(`${BASE_URL}/${caseId}/timeline`);
    return response.data;
  },

  // Get case graph (incluye nodos de Threat Intel)
  getCaseGraph: async (caseId) => {
    try {
      // Primero intenta el endpoint de casos que incluye threat intel
      const response = await api.get(`/api/cases/${caseId}/graph`);
      return response.data;
    } catch (error) {
      // Fallback al endpoint v41
      try {
        const response = await api.get(`${BASE_URL}/${caseId}/graph`);
        return response.data;
      } catch (fallbackError) {
        console.error('Error fetching case graph:', fallbackError);
        return { nodes: [], edges: [] };
      }
    }
  },

  // Get case threat intel analyses
  getCaseThreatIntel: async (caseId) => {
    try {
      const response = await api.get(`/api/cases/${caseId}/threat-intel`);
      return response.data;
    } catch (error) {
      console.error('Error fetching threat intel:', error);
      return { analyses: [], total: 0 };
    }
  },

  // Save threat intel to case
  saveThreatIntelToCase: async (caseId, threatIntelData) => {
    const response = await api.post(`/api/cases/${caseId}/threat-intel`, threatIntelData);
    return response.data;
  },

  // Add node to case graph
  addGraphNode: async (caseId, nodeData) => {
    const response = await api.post(`/api/cases/${caseId}/graph/node`, nodeData);
    return response.data;
  },

  // Enrich graph with AI analysis
  enrichGraphWithAI: async (caseId, options = {}) => {
    try {
      const response = await api.post(`/api/cases/${caseId}/graph/enrich`, {
        analysis_type: options.analysisType || 'full',
        focus_nodes: options.focusNodes || null,
        graph_data: options.graphData || null
      });
      return response.data;
    } catch (error) {
      console.error('Error enriching graph with AI:', error);
      throw error;
    }
  },

  // Get statistics
  getStats: async () => {
    try {
      const response = await api.get(`${BASE_URL}/stats`);
      return response.data;
    } catch {
      // Fallback si el endpoint no existe aún
      return null;
    }
  }
};
