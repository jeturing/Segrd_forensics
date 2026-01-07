/**
 * MCP Kali Forensics - Modules Service
 * Servicio completo para gestión de módulos
 */

import api from './api';

const modulesService = {
  // === LIST ===
  getAll: () => api.get('/modules/'),
  getList: () => api.get('/modules/list'),
  getCategories: () => api.get('/modules/categories'),
  
  // === CRUD ===
  get: (moduleId) => api.get(`/modules/${moduleId}`),
  generate: (moduleId, data) => api.post(`/modules/${moduleId}/generate`, data),
  
  // === ENDPOINTS ===
  getAllEndpoints: () => api.get('/modules/all/endpoints'),
  getEndpoints: (moduleId) => api.get(`/modules/${moduleId}/endpoints`),
  
  // === DEPENDENCIES ===
  getDependencies: (moduleId) => api.get(`/modules/dependencies/${moduleId}`),
  
  // === VALIDATION ===
  validateAll: () => api.get('/modules/validate/all'),
};

export default modulesService;
