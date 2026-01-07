/**
 * SEGRD Security - Timeline Service
 * Servicio completo para Timeline con CRUD
 */

import api from './api';

const timelineService = {
  // === MAIN ===
  getAll: () => api.get('/timeline/'),
  getByCase: (caseId) => api.get(`/timeline/${caseId}`),
  getSummary: (caseId) => api.get(`/timeline/${caseId}/summary`),
  
  // === EVENTS ===
  createEvent: (data) => api.post('/timeline/events', data),
  createEventsBulk: (data) => api.post('/timeline/events/bulk', data),
  getEvent: (eventId) => api.get(`/timeline/events/${eventId}`),
  updateEvent: (eventId, data) => api.put(`/timeline/events/${eventId}`, data),
  deleteEvent: (eventId) => api.delete(`/timeline/events/${eventId}`),
  markKeyEvent: (eventId) => api.post(`/timeline/events/${eventId}/key`),
  
  // === CORRELATION ===
  correlate: (data) => api.post('/timeline/correlate', data),
  getCorrelations: (caseId) => api.get(`/timeline/${caseId}/correlations`),
  
  // === GRAPH ===
  getGraph: (caseId) => api.get(`/timeline/${caseId}/graph`),
  
  // === IMPORT/EXPORT ===
  importEvents: (caseId, source, data) => api.post(`/timeline/${caseId}/import/${source}`, data),
  exportTimeline: (caseId, format = 'json') => api.get(`/timeline/${caseId}/export`, { params: { format } }),
};

export default timelineService;
