import api from './api';

export const ragService = {
  // Query RAG
  query: async (caseId, queryText, nResults = 5) => {
    const response = await api.post('/api/rag/query', {
      case_id: caseId,
      query: queryText,
      n_results: nResults
    });
    return response.data;
  },

  // Ingest text
  ingest: async (caseId, text, source) => {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('text', text);
    formData.append('source', source);
    
    const response = await api.post('/api/rag/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  }
};

export default ragService;
