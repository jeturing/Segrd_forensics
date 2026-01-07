/**
 * SEGRD Security - Security Tools Service
 * Servicio completo para herramientas Kali con CRUD
 */

import api from './api';

const kaliToolsService = {
  // === CATALOG ===
  getStatus: () => api.get('/api/security-tools/status'),
  getCategories: () => api.get('/api/security-tools/categories'),
  getExtendedCatalog: () => api.get('/api/security-tools/extended-catalog'),
  getMetapackages: () => api.get('/api/security-tools/metapackages'),
  search: (query) => api.get('/api/security-tools/search', { params: { q: query } }),
  
  // === EXECUTION ===
  execute: (toolId, params) => api.post('/api/security-tools/execute', { tool_id: toolId, ...params }),
  executeAsync: (toolId, params) => api.post('/api/security-tools/execute/async', { tool_id: toolId, ...params }),
  preview: (toolId, params) => api.post('/api/security-tools/preview', { tool_id: toolId, ...params }),
  getExecutions: () => api.get('/api/security-tools/executions'),
  getExecution: (executionId) => api.get(`/api/security-tools/executions/${executionId}`),
  
  // === INSTALLATION ===
  install: (data) => api.post('/api/security-tools/install', data),
  installTool: (toolId) => api.post(`/api/security-tools/install/${toolId}`),
  getInstallStatus: (executionId) => api.get(`/api/security-tools/install/status/${executionId}`),
  
  // === QUICK ACTIONS ===
  getQuickActions: () => api.get('/api/security-tools/quick-actions'),
  executeQuickAction: (actionId, params) => api.post(`/api/security-tools/quick-actions/${actionId}/execute`, params),
  
  // === PLAYBOOKS ===
  generatePlaybook: (toolId) => api.post(`/api/security-tools/playbooks/generate/${toolId}`),
  getInvestigationPlaybooks: (investigationType) => api.get(`/api/security-tools/playbooks/investigation/${investigationType}`),
  
  // === SESSION ===
  getSession: () => api.get('/api/security-tools/session'),
  
  // === GITHUB ===
  validateGitHub: (repoUrl) => api.get('/api/security-tools/github/validate', { params: { repo_url: repoUrl } }),
};

export default kaliToolsService;
