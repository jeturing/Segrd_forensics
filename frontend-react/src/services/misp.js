/**
 * MISP API Service
 * Integración con Malware Information Sharing Platform
 * v4.5
 */

const API_BASE = '/api/misp';

/**
 * Obtener estado de conexión con MISP
 */
export async function getStatus() {
  const response = await fetch(`${API_BASE}/status`);
  return response.json();
}

/**
 * Obtener estadísticas de MISP
 */
export async function getStatistics() {
  const response = await fetch(`${API_BASE}/statistics`);
  if (!response.ok) {
    throw new Error('Error obteniendo estadísticas de MISP');
  }
  return response.json();
}

/**
 * Buscar IOC en MISP
 * @param {string} value - Valor del IOC
 * @param {string} [type] - Tipo: ip-src, ip-dst, domain, md5, sha256, email, url
 * @param {number} [limit=50] - Límite de resultados
 */
export async function searchIOC(value, type = null, limit = 50) {
  const response = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value, type, limit })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error en búsqueda');
  }
  return response.json();
}

/**
 * Búsqueda rápida de IP
 */
export async function searchIP(ip, limit = 50) {
  const response = await fetch(`${API_BASE}/search/ip/${encodeURIComponent(ip)}?limit=${limit}`);
  if (!response.ok) throw new Error('Error buscando IP');
  return response.json();
}

/**
 * Búsqueda rápida de dominio
 */
export async function searchDomain(domain, limit = 50) {
  const response = await fetch(`${API_BASE}/search/domain/${encodeURIComponent(domain)}?limit=${limit}`);
  if (!response.ok) throw new Error('Error buscando dominio');
  return response.json();
}

/**
 * Búsqueda rápida de hash
 */
export async function searchHash(hash, limit = 50) {
  const response = await fetch(`${API_BASE}/search/hash/${encodeURIComponent(hash)}?limit=${limit}`);
  if (!response.ok) throw new Error('Error buscando hash');
  return response.json();
}

/**
 * Búsqueda rápida de email
 */
export async function searchEmail(email, limit = 50) {
  const response = await fetch(`${API_BASE}/search/email/${encodeURIComponent(email)}?limit=${limit}`);
  if (!response.ok) throw new Error('Error buscando email');
  return response.json();
}

/**
 * Listar eventos de MISP
 */
export async function getEvents(params = {}) {
  const query = new URLSearchParams();
  if (params.limit) query.set('limit', params.limit);
  if (params.page) query.set('page', params.page);
  if (params.from_date) query.set('from_date', params.from_date);
  if (params.to_date) query.set('to_date', params.to_date);
  if (params.threat_level) query.set('threat_level', params.threat_level);
  if (params.tags) query.set('tags', params.tags);
  if (params.published !== undefined) query.set('published', params.published);

  const response = await fetch(`${API_BASE}/events?${query.toString()}`);
  if (!response.ok) throw new Error('Error obteniendo eventos');
  return response.json();
}

/**
 * Obtener evento específico
 */
export async function getEvent(eventId) {
  const response = await fetch(`${API_BASE}/events/${eventId}`);
  if (!response.ok) throw new Error('Error obteniendo evento');
  return response.json();
}

/**
 * Listar feeds de MISP
 */
export async function getFeeds() {
  const response = await fetch(`${API_BASE}/feeds`);
  if (!response.ok) throw new Error('Error obteniendo feeds');
  return response.json();
}

/**
 * Forzar actualización de feed
 */
export async function fetchFeed(feedId) {
  const response = await fetch(`${API_BASE}/feeds/${feedId}/fetch`, { method: 'POST' });
  if (!response.ok) throw new Error('Error actualizando feed');
  return response.json();
}

/**
 * Listar galaxies (ATT&CK, etc)
 */
export async function getGalaxies() {
  const response = await fetch(`${API_BASE}/galaxies`);
  if (!response.ok) throw new Error('Error obteniendo galaxies');
  return response.json();
}

/**
 * Listar taxonomías
 */
export async function getTaxonomies() {
  const response = await fetch(`${API_BASE}/taxonomies`);
  if (!response.ok) throw new Error('Error obteniendo taxonomías');
  return response.json();
}

/**
 * Exportar caso a MISP
 */
export async function exportCaseToMISP(caseId, iocs, eventInfo = null, threatLevel = 2, tags = []) {
  const response = await fetch(`${API_BASE}/export-case`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      case_id: caseId,
      iocs,
      event_info: eventInfo,
      threat_level: threatLevel,
      tags
    })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error exportando a MISP');
  }
  return response.json();
}

/**
 * Importar evento MISP a caso
 */
export async function importEventToCase(eventId, caseId) {
  const response = await fetch(`${API_BASE}/import-event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_id: eventId, case_id: caseId })
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error importando de MISP');
  }
  return response.json();
}

/**
 * Lookup rápido de IP (formato simplificado)
 */
export async function quickLookupIP(ip) {
  const response = await fetch(`${API_BASE}/lookup/ip/${encodeURIComponent(ip)}`);
  return response.json();
}

/**
 * Lookup rápido de dominio (formato simplificado)
 */
export async function quickLookupDomain(domain) {
  const response = await fetch(`${API_BASE}/lookup/domain/${encodeURIComponent(domain)}`);
  return response.json();
}

export default {
  getStatus,
  getStatistics,
  searchIOC,
  searchIP,
  searchDomain,
  searchHash,
  searchEmail,
  getEvents,
  getEvent,
  getFeeds,
  fetchFeed,
  getGalaxies,
  getTaxonomies,
  exportCaseToMISP,
  importEventToCase,
  quickLookupIP,
  quickLookupDomain
};
