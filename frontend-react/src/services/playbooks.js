import api from './api';

export const playbookService = {
  // List playbooks
  getPlaybooks: async () => {
    const response = await api.get('/api/v41/playbooks');
    return response.data;
  },

  // Get playbook details
  getPlaybook: async (id) => {
    const response = await api.get(`/api/v41/playbooks/${id}`);
    return response.data;
  },

  // Execute playbook
  executePlaybook: async (id, data) => {
    const response = await api.post(`/api/v41/playbooks/${id}/execute`, data);
    return response.data;
  },

  // Get execution status
  getExecution: async (id) => {
    const response = await api.get(`/api/v41/playbooks/executions/${id}`);
    return response.data;
  },

  // Get recommendations (ML)
  getRecommendations: async (caseType, severity, entities) => {
    const response = await api.get('/api/v41/playbooks/recommendations', {
      params: { case_type: caseType, severity, entities }
    });
    return response.data;
  },

  // Predict success (ML)
  predictSuccess: async (playbookId, caseType, severity, entityCount) => {
    const response = await api.post('/api/v41/playbooks/predict', {
      playbook_id: playbookId,
      case_type: caseType,
      severity,
      entity_count: entityCount
    });
    return response.data;
  }
};

export default playbookService;
