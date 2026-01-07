/**
 * SEGRD Security - Threat Hunting Service
 * Servicio completo para Threat Hunting con CRUD
 */

import api from './api';

const huntingService = {
  // === MAIN ===
  getAll: () => api.get('/hunting/'),
  getCategories: () => api.get('/hunting/categories'),
  getMitre: () => api.get('/hunting/mitre'),
  
  // === QUERIES ===
  getQueries: () => api.get('/hunting/queries'),
  getQuery: (queryId) => api.get(`/hunting/queries/${queryId}`),
  saveQuery: (data) => api.post('/hunting/queries/save', data),
  
  // === EXECUTION ===
  execute: (data) => api.post('/hunting/execute', data),
  executeCustom: (data) => api.post('/hunting/execute/custom', data),
  executeBatch: (data) => api.post('/hunting/batch', data),
  
  // === RESULTS ===
  getResults: (caseId) => api.get(`/hunting/results/${caseId}`),
  getResult: (caseId, huntId) => api.get(`/hunting/results/${caseId}/${huntId}`),
  deleteResult: (caseId, huntId) => api.delete(`/hunting/results/${caseId}/${huntId}`),
};

export default huntingService;
