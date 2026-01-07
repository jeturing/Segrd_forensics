/**
 * Monkey365 API Service
 * M365 Cloud Security Assessment
 * v4.5
 */

const API_BASE = '/api/monkey365';

/**
 * Get Monkey365 installation status and available collectors
 */
export async function getStatus() {
  const response = await fetch(`${API_BASE}/status`);
  if (!response.ok) {
    throw new Error('Failed to get Monkey365 status');
  }
  return response.json();
}

/**
 * Start a new security scan
 * @param {Object} params - Scan parameters
 * @param {string} params.tenant_id - Microsoft 365 Tenant ID
 * @param {string} params.case_id - Case ID to associate results
 * @param {string} params.instance - Instance type (Microsoft365, Azure, EntraID)
 * @param {string[]} params.collectors - Collectors to run
 * @param {string} params.output_format - Output format (html, json, csv)
 */
export async function startScan(params) {
  const response = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(params)
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start scan');
  }
  return response.json();
}

/**
 * Get list of available scans/reports
 */
export async function getScans() {
  const response = await fetch(`${API_BASE}/scans`);
  if (!response.ok) {
    throw new Error('Failed to get scans');
  }
  return response.json();
}

/**
 * Get HTML report content for a specific scan
 * @param {string} scanId - Scan ID
 */
export async function getReport(scanId) {
  const response = await fetch(`${API_BASE}/report/${scanId}`);
  if (!response.ok) {
    throw new Error('Failed to get report');
  }
  return response.json();
}

/**
 * Import scan results to a case
 * @param {string} scanId - Scan ID to import
 * @param {string} caseId - Target case ID
 */
export async function importToCase(scanId, caseId) {
  const response = await fetch(`${API_BASE}/import/${scanId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ case_id: caseId })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to import to case');
  }
  return response.json();
}

/**
 * Get scan progress/status
 * @param {string} scanId - Scan ID
 */
export async function getScanStatus(scanId) {
  const response = await fetch(`${API_BASE}/scan/${scanId}/status`);
  if (!response.ok) {
    throw new Error('Failed to get scan status');
  }
  return response.json();
}

export default {
  getStatus,
  startScan,
  getScans,
  getReport,
  importToCase,
  getScanStatus
};
