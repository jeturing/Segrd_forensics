import api from './api';

const DASHBOARD_BASE = '/api/dashboard/m365';
const OAUTH_BASE = '/api/oauth/device-code';

// Tenant info & data
export const getTenantInfo = async () => {
  const { data } = await api.get(`${DASHBOARD_BASE}/tenant-info`);
  return data;
};

export const syncTenant = async () => {
  const { data } = await api.post(`${DASHBOARD_BASE}/sync`);
  return data;
};

export const getRiskySignins = async () => {
  const { data } = await api.get(`${DASHBOARD_BASE}/risky-signins`);
  return data;
};

export const getRiskyUsers = async () => {
  const { data } = await api.get(`${DASHBOARD_BASE}/risky-users`);
  return data;
};

export const getAuditLogs = async (days = 7) => {
  const { data } = await api.get(`${DASHBOARD_BASE}/audit-logs`, { params: { days } });
  return data;
};

// M365 forensic analysis
export const startAnalysis = async ({ tenantId, caseId, scope, targetUsers = [], daysBack = 90, priority = 'medium', investigationId = null }) => {
  const payload = {
    tenant_id: tenantId,
    case_id: caseId,
    scope,
    target_users: targetUsers.length ? targetUsers : null,
    days_back: daysBack,
    priority
  };
  
  // Solo incluir investigation_id si está definido
  if (investigationId) {
    payload.investigation_id = investigationId;
  }
  
  const { data } = await api.post('/forensics/m365/analyze', payload);
  return data;
};

// OAuth device code (Azure Shell / browser)
export const initDeviceCode = async ({ tenantId, scopes }) => {
  const { data } = await api.post(`${OAUTH_BASE}/init`, {
    tenant_id: tenantId,
    scopes
  });
  return data;
};

export const pollDeviceCode = async ({ deviceCode, tenantId }) => {
  const { data } = await api.post(`${OAUTH_BASE}/poll`, {
    device_code: deviceCode,
    tenant_id: tenantId
  });
  return data;
};

export const cancelDeviceCode = async ({ deviceCode, tenantId }) => {
  const { data } = await api.delete(`${OAUTH_BASE}/cancel`, {
    data: { device_code: deviceCode, tenant_id: tenantId }
  });
  return data;
};

export default {
  getTenantInfo,
  syncTenant,
  getRiskySignins,
  getRiskyUsers,
  getAuditLogs,
  startAnalysis,
  initDeviceCode,
  pollDeviceCode,
  cancelDeviceCode
};
