/**
 * MCP Kali Forensics - Tenants Service
 * Servicio completo para gestión de tenants M365 con CRUD
 */

import api from './api';

const tenantsService = {
  // ============================================================================
  // CRUD OPERATIONS
  // ============================================================================

  getAll: async (includeInactive = false) => {
    const response = await api.get('/tenants/', { params: includeInactive ? { include_inactive: true } : {} });
    return response.data;
  },

  get: async (tenantId) => {
    const response = await api.get(`/tenants/${tenantId}`);
    return response.data;
  },

  update: async (tenantId, data) => {
    const response = await api.put(`/tenants/${tenantId}`, data);
    return response.data;
  },

  delete: async (tenantId) => {
    const response = await api.delete(`/tenants/${tenantId}`);
    return response.data;
  },

  // ============================================================================
  // ACTIVE TENANT
  // ============================================================================

  getActive: async () => {
    const response = await api.get('/tenants/active');
    return response.data;
  },

  switch: async (tenantId) => {
    const response = await api.post(`/tenants/${tenantId}/switch`);
    return response.data;
  },

  // ============================================================================
  // ONBOARDING
  // ============================================================================

  onboard: async (data) => {
    const response = await api.post('/tenants/onboard', data);
    return response.data;
  },

  // Device Code Flow
  initDeviceAuth: async (tenantId) => {
    const response = await api.post('/tenants/device-code/init', { tenant_id: tenantId });
    return response.data;
  },

  pollDeviceToken: async (tenantId, deviceCode) => {
    const response = await api.post('/tenants/device-code/poll', { tenant_id: tenantId, device_code: deviceCode });
    return response.data;
  },

  onboardWithDeviceCode: async (tenantId, accessToken, name = null) => {
    const response = await api.post('/tenants/device-code/onboard', { 
      tenant_id: tenantId, 
      access_token: accessToken,
      name 
    });
    return response.data;
  },

  // ============================================================================
  // SYNC
  // ============================================================================

  sync: async (tenantId, accessToken = null) => {
    const body = accessToken ? { access_token: accessToken } : {};
    const response = await api.post(`/tenants/${tenantId}/sync`, body);
    return response.data;
  },

  syncAll: async () => {
    const response = await api.post('/tenants/sync-all');
    return response.data;
  },

  // ============================================================================
  // ANALYSIS
  // ============================================================================

  analyze: async (tenantId, data = {}) => {
    const response = await api.post(`/tenants/${tenantId}/analyze`, data);
    return response.data;
  },

  // ============================================================================
  // TENANT DATA
  // ============================================================================

  getStats: async (tenantId) => {
    const response = await api.get(`/tenants/${tenantId}/stats`);
    return response.data;
  },

  getCases: async (tenantId) => {
    const response = await api.get(`/tenants/${tenantId}/cases`);
    return response.data;
  },

  getUsers: async (tenantId) => {
    const response = await api.get(`/tenants/${tenantId}/users`);
    return response.data;
  },

  getActivity: async (tenantId) => {
    const response = await api.get(`/tenants/${tenantId}/activity`);
    return response.data;
  },
};

// Export individual functions for backward compatibility
export const listTenants = tenantsService.getAll;
export const getActiveTenant = tenantsService.getActive;
export const switchTenant = tenantsService.switch;
export const syncTenant = tenantsService.sync;
export const initDeviceAuth = tenantsService.initDeviceAuth;
export const pollDeviceToken = tenantsService.pollDeviceToken;
export const onboardTenantWithDeviceCode = tenantsService.onboardWithDeviceCode;

export default tenantsService;
