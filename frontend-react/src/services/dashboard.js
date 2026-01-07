/**
 * MCP Kali Forensics - Dashboard Service
 * Servicio completo para el Dashboard con CRUD
 */

import api from './api';

const dashboardService = {
  // === STATS ===
  getStats: () => api.get('/api/dashboard/stats'),
  getRecentActivity: () => api.get('/api/dashboard/activity/recent'),
  
  // === CASES ===
  getCases: () => api.get('/api/dashboard/cases/list'),
  getCasesSummary: () => api.get('/api/dashboard/cases/summary'),
  getCase: (caseId) => api.get(`/api/dashboard/cases/${caseId}`),
  createCase: (data) => api.post('/api/dashboard/cases/create', data),
  deleteCase: (caseId) => api.delete(`/api/dashboard/cases/${caseId}`),
  updateCaseStatus: (caseId, status) => api.put(`/api/dashboard/cases/${caseId}/status`, { status }),
  addCaseNote: (caseId, note) => api.post(`/api/dashboard/cases/${caseId}/notes`, { note }),
  
  // === ENDPOINTS ===
  getEndpointsStatus: () => api.get('/api/dashboard/endpoints/status'),
  
  // === EVIDENCE ===
  getEvidenceStats: () => api.get('/api/dashboard/evidence/stats'),
  getEvidenceByCase: (caseId) => api.get(`/api/dashboard/evidence/${caseId}`),
  
  // === IOCs ===
  getIOCStats: () => api.get('/api/dashboard/iocs/stats'),
  getLatestIOCs: () => api.get('/api/dashboard/iocs/latest'),
  getIOC: (iocId) => api.get(`/api/dashboard/iocs/${iocId}`),
  addIOC: (data) => api.post('/api/dashboard/iocs/add', data),
  
  // === M365 ===
  getM365TenantInfo: () => api.get('/api/dashboard/m365/tenant-info'),
  getM365Users: () => api.get('/api/dashboard/m365/users'),
  getM365RiskyUsers: () => api.get('/api/dashboard/m365/risky-users'),
  getM365RiskySignins: () => api.get('/api/dashboard/m365/risky-signins'),
  getM365AuditLogs: () => api.get('/api/dashboard/m365/audit-logs'),
  syncM365: () => api.post('/api/dashboard/m365/sync'),
  
  // === THREATS ===
  getThreatsTimeline: () => api.get('/api/dashboard/threats/timeline'),
  
  // === TOOLS ===
  getToolsStatus: () => api.get('/api/dashboard/tools/status'),
};

export default dashboardService;
