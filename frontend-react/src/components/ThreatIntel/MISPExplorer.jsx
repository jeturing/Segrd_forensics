/**
 * MISP Explorer Component
 * Panel de integración con MISP para Threat Intelligence
 * v4.5
 */

import React, { useState, useEffect } from 'react';
import {
  Shield,
  Search,
  Database,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ExternalLink,
  Download,
  Upload,
  Tag,
  Globe,
  Hash,
  Mail,
  Calendar,
  Clock,
  Filter,
  ChevronDown,
  ChevronUp,
  Layers
} from 'lucide-react';
import mispService from '../../services/misp';

const MISPExplorer = ({ onSelectIOC, caseId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('auto');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [feeds, setFeeds] = useState([]);
  const [galaxies, setGalaxies] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [activeTab, setActiveTab] = useState('search');
  const [error, setError] = useState(null);
  const [eventFilters, setEventFilters] = useState({
    threatLevel: '',
    published: true,
    limit: 25
  });

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const statusData = await mispService.getStatus();
      setStatus(statusData);
      
      if (statusData.connected) {
        // Cargar datos adicionales en paralelo
        const [statsData, eventsData] = await Promise.all([
          mispService.getStatistics().catch(() => null),
          mispService.getEvents({ limit: 10, published: true }).catch(() => null)
        ]);
        
        if (statsData) setStatistics(statsData);
        if (eventsData?.events) setEvents(eventsData.events);
      }
    } catch (err) {
      console.error('Error loading MISP status:', err);
      setError('Error conectando con MISP');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setSearching(true);
    setError(null);
    setSearchResults(null);
    
    try {
      let result;
      
      // Auto-detectar tipo si es 'auto'
      if (searchType === 'auto') {
        // Detectar tipo basado en patrón
        if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(searchQuery)) {
          result = await mispService.searchIP(searchQuery);
        } else if (/^[a-f0-9]{32}$/i.test(searchQuery)) {
          result = await mispService.searchHash(searchQuery);
        } else if (/^[a-f0-9]{40}$/i.test(searchQuery)) {
          result = await mispService.searchHash(searchQuery);
        } else if (/^[a-f0-9]{64}$/i.test(searchQuery)) {
          result = await mispService.searchHash(searchQuery);
        } else if (/@/.test(searchQuery)) {
          result = await mispService.searchEmail(searchQuery);
        } else if (/^https?:\/\//.test(searchQuery)) {
          result = await mispService.searchIOC(searchQuery, 'url');
        } else {
          result = await mispService.searchDomain(searchQuery);
        }
      } else {
        result = await mispService.searchIOC(searchQuery, searchType);
      }
      
      setSearchResults(result);
    } catch (err) {
      setError(err.message || 'Error en búsqueda');
    } finally {
      setSearching(false);
    }
  };

  const loadEvents = async () => {
    try {
      const params = {
        limit: eventFilters.limit,
        published: eventFilters.published
      };
      if (eventFilters.threatLevel) {
        params.threat_level = parseInt(eventFilters.threatLevel);
      }
      
      const result = await mispService.getEvents(params);
      setEvents(result.events || []);
    } catch (err) {
      setError('Error cargando eventos');
    }
  };

  const loadEventDetails = async (eventId) => {
    try {
      const result = await mispService.getEvent(eventId);
      setSelectedEvent(result.event);
    } catch (err) {
      setError('Error cargando evento');
    }
  };

  const loadFeeds = async () => {
    try {
      const result = await mispService.getFeeds();
      setFeeds(result.feeds || []);
    } catch (err) {
      setError('Error cargando feeds');
    }
  };

  const loadGalaxies = async () => {
    try {
      const result = await mispService.getGalaxies();
      setGalaxies(result.galaxies || []);
    } catch (err) {
      setError('Error cargando galaxies');
    }
  };

  const importToCase = async (ioc) => {
    if (onSelectIOC) {
      onSelectIOC({
        type: ioc.type,
        value: ioc.value,
        source: 'misp',
        event_id: ioc.event_id,
        tags: ioc.tags,
        comment: ioc.comment
      });
    }
  };

  const getThreatLevelBadge = (level) => {
    const colors = {
      high: 'bg-red-500/20 text-red-400 border-red-500/30',
      medium: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      low: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      undefined: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    };
    return colors[level] || colors.undefined;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-purple-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-400">Conectando con MISP...</p>
        </div>
      </div>
    );
  }

  if (!status?.configured) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-purple-500/20 rounded-lg">
            <Shield className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">MISP No Configurado</h3>
            <p className="text-gray-400 text-sm">Configura las variables de entorno para conectar</p>
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm">
          <p className="text-gray-500"># Variables requeridas en .env</p>
          <p className="text-green-400">MISP_URL=https://misp.ejemplo.com</p>
          <p className="text-green-400">MISP_API_KEY=tu_api_key</p>
          <p className="text-green-400">MISP_VERIFY_SSL=true</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gradient-to-r from-purple-900/50 to-gray-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Shield className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">MISP Integration</h3>
              <p className="text-sm text-gray-400">Malware Information Sharing Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {status?.connected ? (
              <span className="flex items-center gap-2 px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                <CheckCircle className="w-4 h-4" />
                Conectado
              </span>
            ) : (
              <span className="flex items-center gap-2 px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm">
                <XCircle className="w-4 h-4" />
                Desconectado
              </span>
            )}
            <button
              onClick={loadStatus}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Stats */}
        {statistics && (
          <div className="grid grid-cols-4 gap-4 mt-4">
            <div className="bg-gray-900/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-purple-400">{statistics.events_count?.toLocaleString() || 0}</p>
              <p className="text-xs text-gray-500">Eventos</p>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-blue-400">{statistics.attributes_count?.toLocaleString() || 0}</p>
              <p className="text-xs text-gray-500">Atributos</p>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-green-400">{statistics.orgs_count || 0}</p>
              <p className="text-xs text-gray-500">Organizaciones</p>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-orange-400">{statistics.correlation_count?.toLocaleString() || 0}</p>
              <p className="text-xs text-gray-500">Correlaciones</p>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {[
          { id: 'search', label: 'Búsqueda', icon: Search },
          { id: 'events', label: 'Eventos', icon: Database },
          { id: 'feeds', label: 'Feeds', icon: RefreshCw },
          { id: 'galaxies', label: 'Galaxies', icon: Layers }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id);
              if (tab.id === 'events') loadEvents();
              if (tab.id === 'feeds') loadFeeds();
              if (tab.id === 'galaxies') loadGalaxies();
            }}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-purple-400 border-b-2 border-purple-400 bg-purple-500/10'
                : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-5 h-5" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">×</button>
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="flex-1">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Buscar IP, dominio, hash, email, URL..."
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg focus:border-purple-500 focus:outline-none text-white"
                />
              </div>
              <select
                value={searchType}
                onChange={(e) => setSearchType(e.target.value)}
                className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg text-gray-300"
              >
                <option value="auto">Auto-detectar</option>
                <option value="ip-src">IP (source)</option>
                <option value="ip-dst">IP (dest)</option>
                <option value="domain">Dominio</option>
                <option value="md5">MD5</option>
                <option value="sha256">SHA256</option>
                <option value="email">Email</option>
                <option value="url">URL</option>
              </select>
              <button
                onClick={handleSearch}
                disabled={searching || !searchQuery.trim()}
                className="px-6 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-lg font-medium flex items-center gap-2"
              >
                {searching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Buscar
              </button>
            </div>

            {/* Search Results */}
            {searchResults && (
              <div className="bg-gray-900 rounded-lg border border-gray-700">
                <div className="p-3 border-b border-gray-700 flex items-center justify-between">
                  <span className="font-medium">
                    {searchResults.found ? (
                      <span className="text-green-400">✓ {searchResults.count} resultados encontrados</span>
                    ) : (
                      <span className="text-gray-400">No se encontraron resultados</span>
                    )}
                  </span>
                  <span className="text-sm text-gray-500">Query: {searchResults.query}</span>
                </div>
                
                {searchResults.results?.length > 0 && (
                  <div className="divide-y divide-gray-800 max-h-96 overflow-y-auto">
                    {searchResults.results.map((result, idx) => (
                      <div key={idx} className="p-3 hover:bg-gray-800/50 transition-colors">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs font-medium">
                                {result.type}
                              </span>
                              <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getThreatLevelBadge(result.event_threat_level)}`}>
                                {result.event_threat_level || 'unknown'}
                              </span>
                            </div>
                            <p className="font-mono text-white break-all">{result.value}</p>
                            {result.event_info && (
                              <p className="text-sm text-gray-400 mt-1">Evento: {result.event_info}</p>
                            )}
                            {result.tags?.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {result.tags.slice(0, 5).map((tag, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => importToCase(result)}
                            className="p-2 text-gray-400 hover:text-purple-400 hover:bg-purple-500/10 rounded-lg"
                            title="Importar a caso"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Events Tab */}
        {activeTab === 'events' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex gap-3 items-center">
              <select
                value={eventFilters.threatLevel}
                onChange={(e) => setEventFilters({ ...eventFilters, threatLevel: e.target.value })}
                className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg text-gray-300"
              >
                <option value="">Todos los niveles</option>
                <option value="1">High</option>
                <option value="2">Medium</option>
                <option value="3">Low</option>
              </select>
              <label className="flex items-center gap-2 text-sm text-gray-400">
                <input
                  type="checkbox"
                  checked={eventFilters.published}
                  onChange={(e) => setEventFilters({ ...eventFilters, published: e.target.checked })}
                  className="rounded bg-gray-700 border-gray-600"
                />
                Solo publicados
              </label>
              <button
                onClick={loadEvents}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Actualizar
              </button>
            </div>

            {/* Events List */}
            <div className="space-y-2">
              {events.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No hay eventos para mostrar</p>
              ) : (
                events.map((event) => (
                  <div
                    key={event.id}
                    className="bg-gray-900 border border-gray-700 rounded-lg p-4 hover:border-purple-500/50 transition-colors cursor-pointer"
                    onClick={() => loadEventDetails(event.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase border ${getThreatLevelBadge(event.threat_level)}`}>
                            {event.threat_level}
                          </span>
                          <span className="text-gray-500 text-sm">#{event.id}</span>
                        </div>
                        <h4 className="font-medium text-white mb-1">{event.info}</h4>
                        <div className="flex items-center gap-4 text-sm text-gray-400">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {event.date}
                          </span>
                          <span className="flex items-center gap-1">
                            <Database className="w-3 h-3" />
                            {event.attribute_count} atributos
                          </span>
                          <span>{event.org}</span>
                        </div>
                        {event.tags?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {event.tags.slice(0, 5).map((tag, i) => (
                              <span key={i} className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Feeds Tab */}
        {activeTab === 'feeds' && (
          <div className="space-y-3">
            {feeds.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No hay feeds configurados</p>
            ) : (
              feeds.map((feed) => (
                <div key={feed.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-white">{feed.name}</h4>
                    <p className="text-sm text-gray-400">{feed.provider}</p>
                    <p className="text-xs text-gray-500 mt-1">{feed.url}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs ${feed.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                      {feed.enabled ? 'Activo' : 'Inactivo'}
                    </span>
                    <button
                      onClick={() => mispService.fetchFeed(feed.id)}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
                      title="Actualizar feed"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Galaxies Tab */}
        {activeTab === 'galaxies' && (
          <div className="grid grid-cols-2 gap-3">
            {galaxies.length === 0 ? (
              <p className="col-span-2 text-center text-gray-500 py-8">Cargando galaxies...</p>
            ) : (
              galaxies.slice(0, 20).map((galaxy) => (
                <div key={galaxy.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4">
                  <h4 className="font-medium text-white mb-1">{galaxy.name}</h4>
                  <p className="text-xs text-gray-500 mb-2">{galaxy.type}</p>
                  <p className="text-sm text-gray-400 line-clamp-2">{galaxy.description}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Event Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl w-full max-w-4xl max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Evento #{selectedEvent.id}</h3>
                <p className="text-sm text-gray-400">{selectedEvent.info}</p>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="p-2 hover:bg-gray-700 rounded-lg"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-96">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <span className="text-gray-500 text-sm">Nivel de amenaza</span>
                  <p className={`font-bold uppercase ${
                    selectedEvent.threat_level === 'high' ? 'text-red-400' :
                    selectedEvent.threat_level === 'medium' ? 'text-orange-400' : 'text-gray-400'
                  }`}>{selectedEvent.threat_level}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-sm">Organización</span>
                  <p className="font-medium">{selectedEvent.org}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-sm">Fecha</span>
                  <p>{selectedEvent.date}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-sm">Estado</span>
                  <p>{selectedEvent.analysis}</p>
                </div>
              </div>

              {selectedEvent.attributes?.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-2">Atributos ({selectedEvent.attributes.length})</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {selectedEvent.attributes.map((attr, idx) => (
                      <div key={idx} className="bg-gray-900 rounded p-2 flex items-center justify-between">
                        <div>
                          <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs mr-2">
                            {attr.type}
                          </span>
                          <span className="font-mono text-sm">{attr.value}</span>
                        </div>
                        <button
                          onClick={() => importToCase(attr)}
                          className="p-1 text-gray-400 hover:text-purple-400"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => window.open(`${status?.url}/events/view/${selectedEvent.id}`, '_blank')}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Ver en MISP
              </button>
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MISPExplorer;
