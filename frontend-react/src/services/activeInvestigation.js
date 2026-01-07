import api from './api';

const BASE_URL = '/api/active-investigation';

// Command execution
export const executeCommand = async ({ agentId, command, osType = 'windows', timeout = 300, caseId = null }) => {
  const payload = {
    agent_id: agentId,
    command,
    os_type: osType,
    timeout,
    case_id: caseId
  };
  const response = await api.post(`${BASE_URL}/execute`, payload);
  return response.data;
};

export const getCommandHistory = async (agentId, { limit = 50, caseId = null } = {}) => {
  const response = await api.get(`${BASE_URL}/command-history/${agentId}`, {
    params: {
      limit,
      case_id: caseId
    }
  });
  return response.data;
};

export const getCommandTemplates = async (osType = 'windows') => {
  const response = await api.get(`${BASE_URL}/templates`, { params: { os_type: osType } });
  return response.data;
};

// Network capture
export const startCapture = async ({ agentId, filter = null, caseId = null } = {}) => {
  const response = await api.post(`${BASE_URL}/network-capture/start`, null, {
    params: { agent_id: agentId, filter, case_id: caseId }
  });
  return response.data;
};

export const stopCapture = async (captureId) => {
  const response = await api.post(`${BASE_URL}/network-capture/stop`, null, {
    params: { capture_id: captureId }
  });
  return response.data;
};

export const getCapturePackets = async (captureId, { limit = 50, offset = 0 } = {}) => {
  const response = await api.get(`${BASE_URL}/network-capture/${captureId}`, {
    params: { limit, offset }
  });
  return response.data;
};

export const downloadCapture = async (captureId) => {
  const response = await api.get(`${BASE_URL}/network-capture/${captureId}/download`);
  return response.data;
};

// Memory dump
export const requestMemoryDump = async ({ agentId, caseId = null, format = 'raw' }) => {
  const response = await api.post(`${BASE_URL}/memory-dump/request`, {
    agent_id: agentId,
    case_id: caseId,
    format
  });
  return response.data;
};

export const getMemoryDumpStatus = async (dumpId) => {
  const response = await api.get(`${BASE_URL}/memory-dump/${dumpId}/status`);
  return response.data;
};

export const downloadMemoryDump = async (dumpId) => {
  const response = await api.get(`${BASE_URL}/memory-dump/${dumpId}/download`);
  return response.data;
};

// File transfer
export const uploadFile = async (agentId, destination) => {
  const response = await api.post(`${BASE_URL}/file-upload/${agentId}`, null, {
    params: { destination }
  });
  return response.data;
};

export const downloadFile = async (agentId, source) => {
  const response = await api.get(`${BASE_URL}/file-download/${agentId}`, {
    params: { source }
  });
  return response.data;
};

export default {
  executeCommand,
  getCommandHistory,
  getCommandTemplates,
  startCapture,
  stopCapture,
  getCapturePackets,
  downloadCapture,
  requestMemoryDump,
  getMemoryDumpStatus,
  downloadMemoryDump,
  uploadFile,
  downloadFile
};
