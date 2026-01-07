/**
 * MCP Kali Forensics - Processes Service
 * Servicio completo para gestión de procesos
 */

import api from './api';

const processesService = {
  // === MAIN ===
  getAll: (caseId = null) => api.get('/processes', { params: caseId ? { case_id: caseId } : {} }),
  get: (processId) => api.get(`/processes/${processId}`),
  cancel: (processId) => api.delete(`/processes/${processId}`),
};

export default processesService;
