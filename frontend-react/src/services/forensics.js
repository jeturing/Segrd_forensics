/**
 * SEGRD Security - Forensics Service
 * Servicio completo para análisis forense
 */

import api from './api';

const forensicsService = {
  // === EVIDENCE ===
  getEvidenceSummary: (caseId) => api.get(`/api/forensics/evidence/${caseId}/summary`),
  getEvidenceTimeline: (caseId) => api.get(`/api/forensics/evidence/${caseId}/timeline`),
  getEvidenceRaw: (caseId) => api.get(`/api/forensics/evidence/${caseId}/raw`),
  getEvidenceSignins: (caseId) => api.get(`/api/forensics/evidence/${caseId}/signins`),
  getEvidenceUsers: (caseId) => api.get(`/api/forensics/evidence/${caseId}/users`),
  getEvidenceOAuth: (caseId) => api.get(`/api/forensics/evidence/${caseId}/oauth`),
  getEvidenceM365: (caseId) => api.get(`/api/forensics/evidence/${caseId}/m365`),
  getEvidenceRules: (caseId) => api.get(`/api/forensics/evidence/${caseId}/rules`),
  getEvidenceFile: (caseId, filename) => api.get(`/api/forensics/evidence/${caseId}/file/${filename}`),
  downloadEvidence: (caseId, filename) => api.get(`/api/forensics/evidence/${caseId}/download/${filename}`, { responseType: 'blob' }),
  
  // === M365 FORENSICS ===
  analyzeM365: (data) => api.post('/forensics/m365/analyze', data),
  getM365Tenants: () => api.get('/forensics/m365/tenants'),
  getM365Reports: (caseId) => api.get(`/forensics/m365/reports/${caseId}`),
  getM365ReportSummary: (caseId) => api.get(`/forensics/m365/reports/summary/${caseId}`),
  getM365ReportDetail: (reportId) => api.get(`/forensics/m365/reports/detail/${reportId}`),
  generateM365Report: (investigationId) => api.post(`/forensics/m365/investigations/${investigationId}/report`),
  
  // === GRAPH ===
  getGraph: (caseId) => api.get(`/forensics/graph/${caseId}`),
  addNode: (data) => api.post('/forensics/graph/nodes/add', data),
  updateNode: (nodeId, data) => api.put(`/forensics/graph/nodes/${nodeId}`, data),
  deleteNode: (nodeId) => api.delete(`/forensics/graph/nodes/${nodeId}`),
  getCustomNodes: () => api.get('/forensics/graph/nodes/custom'),
  getCustomEdges: () => api.get('/forensics/graph/edges/custom'),
  linkNodesToUsers: (data) => api.post('/forensics/graph/nodes/link-to-users', data),
  linkNodesToDevices: (data) => api.post('/forensics/graph/nodes/link-to-devices', data),
  
  // === TOOLS ===
  getToolsList: () => api.get('/forensics/tools/tools/list'),
  executeTool: (data) => api.post('/forensics/tools/execute', data),
  getToolStatus: (caseId) => api.get(`/forensics/tools/${caseId}/status`),
  
  // === REPORTS ===
  getExecutiveReport: (caseId) => api.get(`/forensics/report/executive/${caseId}`),
  getTechnicalReport: (caseId) => api.get(`/forensics/report/technical/${caseId}`),
};

export default forensicsService;
