/**
 * SEGRD Security - IOC Store Service
 * Servicio completo para gestión de IOCs con CRUD
 * Actualizado para usar el helper api con autenticación
 */

import api from './api';

const iocStoreService = {
  // ============================================================================
  // CRUD OPERATIONS
  // ============================================================================
  
  getIOCs: async (params = {}) => {
    const response = await api.get('/api/iocs/', { params });
    return response.data;
  },

  getIOC: async (iocId) => {
    const response = await api.get(`/api/iocs/${iocId}`);
    return response.data;
  },

  createIOC: async (iocData) => {
    const response = await api.post('/api/iocs/', iocData);
    return response.data;
  },

  updateIOC: async (iocId, updates) => {
    const response = await api.put(`/api/iocs/${iocId}`, updates);
    return response.data;
  },

  deleteIOC: async (iocId) => {
    const response = await api.delete(`/api/iocs/${iocId}`);
    return response.data;
  },

  // ============================================================================
  // BULK OPERATIONS
  // ============================================================================

  bulkCreateIOCs: async (iocs) => {
    const response = await api.post('/api/iocs/bulk', { iocs });
    return response.data;
  },

  bulkDeleteIOCs: async (iocIds) => {
    const response = await api.post('/api/iocs/bulk-delete', { ioc_ids: iocIds });
    return response.data;
  },

  // ============================================================================
  // SEARCH & ANALYTICS
  // ============================================================================

  searchIOCs: async (query) => {
    const response = await api.post('/api/iocs/search', query);
    return response.data;
  },

  getIOCStats: async () => {
    const response = await api.get('/api/iocs/stats');
    return response.data;
  },

  lookupIOC: async (value) => {
    const response = await api.get('/api/iocs/lookup', { params: { value } });
    return response.data;
  },

  getTags: async () => {
    const response = await api.get('/api/iocs/tags');
    return response.data;
  },

  // ============================================================================
  // ENRICHMENT & AI
  // ============================================================================

  enrichIOC: async (iocId, sources = ['virustotal', 'abuseipdb']) => {
    const response = await api.post(`/api/iocs/${iocId}/enrich`, { sources });
    return response.data;
  },

  aiAnalyzeIOC: async (iocId) => {
    const response = await api.post(`/api/iocs/${iocId}/ai-analyze`);
    return response.data;
  },

  aiBulkAnalyze: async (iocIds) => {
    const response = await api.post('/api/iocs/ai-bulk-analyze', { ioc_ids: iocIds });
    return response.data;
  },

  // ============================================================================
  // CASE LINKING
  // ============================================================================

  linkToCase: async (iocId, caseId) => {
    const response = await api.post(`/api/iocs/${iocId}/link-case`, { case_id: caseId });
    return response.data;
  },

  getIOCsByCase: async (caseId) => {
    const response = await api.get(`/api/iocs/cloud/by-case/${caseId}`);
    return response.data;
  },

  getCasesWithIOCs: async () => {
    const response = await api.get('/api/iocs/cloud/cases');
    return response.data;
  },

  extractFromInvestigation: async (investigationId) => {
    const response = await api.post(`/api/iocs/cloud/extract-from-investigation/${investigationId}`);
    return response.data;
  },

  // ============================================================================
  // SIGHTINGS
  // ============================================================================

  addSighting: async (iocId, sightingData) => {
    const response = await api.post(`/api/iocs/${iocId}/sighting`, sightingData);
    return response.data;
  },

  getSightings: async (iocId) => {
    const response = await api.get(`/api/iocs/${iocId}/sightings`);
    return response.data;
  },

  // ============================================================================
  // TAGS
  // ============================================================================

  addTag: async (iocId, tagName) => {
    const response = await api.post(`/api/iocs/${iocId}/tags`, { tag: tagName });
    return response.data;
  },

  removeTag: async (iocId, tagName) => {
    const response = await api.delete(`/api/iocs/${iocId}/tags/${tagName}`);
    return response.data;
  },

  // ============================================================================
  // IMPORT / EXPORT
  // ============================================================================

  importFromMISP: async (mispData) => {
    const response = await api.post('/api/iocs/import/misp', mispData);
    return response.data;
  },

  importFromSTIX: async (stixData) => {
    const response = await api.post('/api/iocs/import/stix', stixData);
    return response.data;
  },

  exportIOCs: async (params = {}) => {
    const response = await api.get('/api/iocs/export', { params });
    return response.data;
  },
};

// Export individual functions for backward compatibility
export const getIOCs = iocStoreService.getIOCs;
export const getIOC = iocStoreService.getIOC;
export const createIOC = iocStoreService.createIOC;
export const updateIOC = iocStoreService.updateIOC;
export const deleteIOC = iocStoreService.deleteIOC;
export const bulkCreateIOCs = iocStoreService.bulkCreateIOCs;
export const bulkDeleteIOCs = iocStoreService.bulkDeleteIOCs;
export const searchIOCs = iocStoreService.searchIOCs;
export const getIOCStats = iocStoreService.getIOCStats;
export const lookupIOC = iocStoreService.lookupIOC;
export const enrichIOC = iocStoreService.enrichIOC;

export default iocStoreService;
