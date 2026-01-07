/**
 * SEGRD Security - Context Service
 * Servicio para gestión de contexto de caso activo
 */

import api from './api';

const contextService = {
  // === CONTEXT ===
  get: () => api.get('/api/context'),
  getActive: () => api.get('/api/context/active'),
  set: (caseId, data = {}) => api.post('/api/context/set', { case_id: caseId, ...data }),
  clear: () => api.delete('/api/context'),
  cleanup: () => api.post('/api/context/cleanup'),
};

export default contextService;
