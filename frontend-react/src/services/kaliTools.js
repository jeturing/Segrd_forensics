/**
 * MCP Kali Forensics - Kali Tools Service
 * Servicio completo para herramientas Kali con CRUD
 */

import api from './api';

const kaliToolsService = {
  // === CATALOG ===
  getStatus: () => api.get('/api/kali-tools/status'),
  getCategories: () => api.get('/api/kali-tools/categories'),
  getExtendedCatalog: () => api.get('/api/kali-tools/extended-catalog'),
  getMetapackages: () => api.get('/api/kali-tools/metapackages'),
  search: (query) => api.get('/api/kali-tools/search', { params: { q: query } }),
  
  // === EXECUTION ===
  execute: (toolId, params) => api.post('/api/kali-tools/execute', { tool_id: toolId, ...params }),
  executeAsync: (toolId, params) => api.post('/api/kali-tools/execute/async', { tool_id: toolId, ...params }),
  preview: (toolId, params) => api.post('/api/kali-tools/preview', { tool_id: toolId, ...params }),
  getExecutions: () => api.get('/api/kali-tools/executions'),
  getExecution: (executionId) => api.get(`/api/kali-tools/executions/${executionId}`),
  
  // === INSTALLATION ===
  install: (data) => api.post('/api/kali-tools/install', data),
  installTool: (toolId) => api.post(`/api/kali-tools/install/${toolId}`),
  getInstallStatus: (executionId) => api.get(`/api/kali-tools/install/status/${executionId}`),
  
  // === QUICK ACTIONS ===
  getQuickActions: () => api.get('/api/kali-tools/quick-actions'),
  executeQuickAction: (actionId, params) => api.post(`/api/kali-tools/quick-actions/${actionId}/execute`, params),
  
  // === PLAYBOOKS ===
  generatePlaybook: (toolId) => api.post(`/api/kali-tools/playbooks/generate/${toolId}`),
  getInvestigationPlaybooks: (investigationType) => api.get(`/api/kali-tools/playbooks/investigation/${investigationType}`),
  
  // === SESSION ===
  getSession: () => api.get('/api/kali-tools/session'),
  
  // === GITHUB ===
  validateGitHub: (repoUrl) => api.get('/api/kali-tools/github/validate', { params: { repo_url: repoUrl } }),
};

export default kaliToolsService;
