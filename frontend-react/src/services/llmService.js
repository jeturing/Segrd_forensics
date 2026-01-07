import api from './api';

const BASE_URL = '/api/v41/llm';

export const llmService = {
  /**
   * Analiza hallazgos forenses usando LLM
   * @param {Object} params
   * @param {string} params.context - Contexto del análisis (m365, endpoint, credentials, general)
   * @param {Array} params.findings - Lista de hallazgos a analizar
   * @param {string} [params.severity_threshold] - Umbral de severidad (high, medium, low)
   * @param {string} [params.case_id] - ID del caso para análisis contextual profundo
   * @returns {Promise<Object>} Resultado del análisis
   */
  analyzeFindings: async ({ context, findings, severity_threshold = 'medium', case_id }) => {
    const payload = {
      context,
      findings,
      severity_threshold,
      case_id // Optional: triggers deep context analysis in backend
    };
    
    const response = await api.post(`${BASE_URL}/analyze`, payload);
    return response.data;
  },

  /**
   * Obtiene el estado del proveedor LLM actual
   */
  getProviderStatus: async () => {
    const response = await api.get(`${BASE_URL}/provider`);
    return response.data;
  }
};

export default llmService;
