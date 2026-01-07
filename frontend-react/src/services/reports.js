/**
 * MCP Kali Forensics - Reports Service
 * Servicio completo para reportes con CRUD
 */

import api from './api';

const reportsService = {
  // === LIST ===
  getAll: () => api.get('/reports/'),
  getByCase: (caseId) => api.get(`/reports/case/${caseId}`),
  
  // === CRUD ===
  get: (reportId) => api.get(`/reports/${reportId}`),
  delete: (reportId) => api.delete(`/reports/${reportId}`),
  getStatus: (reportId) => api.get(`/reports/${reportId}/status`),
  
  // === GENERATION ===
  generate: (data) => api.post('/reports/generate', data),
  preview: (data) => api.post('/reports/preview', data),
  regenerate: (reportId) => api.post(`/reports/${reportId}/regenerate`),
  batch: (data) => api.post('/reports/batch', data),
  
  // === DOWNLOAD ===
  download: (reportId) => api.get(`/reports/${reportId}/download`, { responseType: 'blob' }),
  
  // === TEMPLATES ===
  getTemplates: () => api.get('/reports/templates'),
  createTemplate: (data) => api.post('/reports/templates', data),
  getTemplate: (templateId) => api.get(`/reports/templates/${templateId}`),
  deleteTemplate: (templateId) => api.delete(`/reports/templates/${templateId}`),
  
  // === SECTIONS ===
  getSections: () => api.get('/reports/sections'),
  
  // === FORENSICS REPORTS ===
  getExecutiveReport: (caseId) => api.get(`/forensics/report/executive/${caseId}`),
  getTechnicalReport: (caseId) => api.get(`/forensics/report/technical/${caseId}`),
};

export default reportsService;
