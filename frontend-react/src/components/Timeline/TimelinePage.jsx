/**
 * Timeline Page - v4.4
 * Línea de tiempo forense con correlación de eventos
 * 
 * v4.4: Integración con CaseContext - case_id obligatorio
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock, Calendar, Filter, Plus, Link2, Download, Upload,
  AlertTriangle, Shield, User, Globe, Server, Mail, File,
  ChevronDown, ChevronUp, Eye, Trash2, Star, RefreshCw,
  ZoomIn, ZoomOut, Maximize2
} from 'lucide-react';
import api from '../../services/api';
import { useCaseContext } from '../../context/CaseContext';
import CaseHeader from '../CaseHeader';

// Iconos por tipo de evento
const eventTypeIcons = {
  authentication: User,
  file_access: File,
  email: Mail,
  network: Globe,
  process: Server,
  lateral_movement: Link2,
  persistence: Shield,
  indicator: AlertTriangle,
  custom: Star
};

// Colores por severidad
const severityStyles = {
  critical: { bg: 'bg-red-500', border: 'border-red-500', text: 'text-red-400', dot: 'bg-red-500' },
  high: { bg: 'bg-orange-500', border: 'border-orange-500', text: 'text-orange-400', dot: 'bg-orange-500' },
  medium: { bg: 'bg-yellow-500', border: 'border-yellow-500', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  low: { bg: 'bg-blue-500', border: 'border-blue-500', text: 'text-blue-400', dot: 'bg-blue-500' },
  info: { bg: 'bg-gray-500', border: 'border-gray-500', text: 'text-gray-400', dot: 'bg-gray-500' }
};

const TimelinePage = () => {
  // v4.4: Usar contexto de caso
  const { currentCase, hasActiveCase, getCaseId, registerActivity } = useCaseContext();
  
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    eventTypes: [],
    severity: null,
    keyEventsOnly: false
  });
  const [showAddEvent, setShowAddEvent] = useState(false);
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [newEvent, setNewEvent] = useState({
    title: '',
    event_type: 'custom',
    source: 'manual',
    severity: 'info',
    description: '',
    event_time: new Date().toISOString().slice(0, 16)
  });

  // v4.4: Cargar timeline cuando cambie el caso
  const loadTimeline = useCallback(async () => {
    if (!hasActiveCase()) return;
    
    const caseId = getCaseId();
    
    try {
      setLoading(true);
      registerActivity('timeline_loaded', { case_id: caseId });
      
      const [timelineRes, summaryRes] = await Promise.all([
        api.get(`/timeline/${caseId}`, { params: filters }),
        api.get(`/timeline/${caseId}/summary`)
      ]);
      setEvents(timelineRes.data.events || []);
      setSummary(summaryRes.data);
    } catch (error) {
      console.error('Error loading timeline:', error);
      // Datos de ejemplo si el API falla
      setEvents([
        {
          event_id: 'evt_001',
          event_time: '2025-12-07T10:30:00Z',
          event_type: 'authentication',
          title: 'Login sospechoso desde IP externa',
          severity: 'high',
          source: 'm365_audit',
          is_key_event: true
        },
        {
          event_id: 'evt_002',
          event_time: '2025-12-07T10:45:00Z',
          event_type: 'email',
          title: 'Regla de reenvío creada',
          severity: 'critical',
          source: 'm365_audit',
          is_key_event: true
        },
        {
          event_id: 'evt_003',
          event_time: '2025-12-07T11:00:00Z',
          event_type: 'file_access',
          title: 'Descarga masiva de archivos (847 archivos)',
          severity: 'high',
          source: 'm365_audit',
          is_key_event: false
        }
      ]);
    } finally {
      setLoading(false);
    }
  }, [hasActiveCase, getCaseId, registerActivity, filters]);

  // v4.4: Recargar cuando cambie el caso
  useEffect(() => {
    if (hasActiveCase()) {
      loadTimeline();
    }
  }, [currentCase, loadTimeline, hasActiveCase]);

  // Agregar evento - v4.4: Usa case_id del contexto
  const addEvent = async () => {
    if (!newEvent.title || !hasActiveCase()) return;
    
    const caseId = getCaseId();
    
    try {
      registerActivity('event_added', { title: newEvent.title });
      
      await api.post('/timeline/events', {
        case_id: caseId,
        ...newEvent,
        event_time: new Date(newEvent.event_time).toISOString()
      });
      setShowAddEvent(false);
      setNewEvent({
        title: '',
        event_type: 'custom',
        source: 'manual',
        severity: 'info',
        description: '',
        event_time: new Date().toISOString().slice(0, 16)
      });
      loadTimeline();
    } catch (error) {
      console.error('Error adding event:', error);
    }
  };

  // Correlacionar eventos seleccionados
  const correlateEvents = async () => {
    if (selectedEvents.length < 2) return;
    
    try {
      const name = prompt('Nombre de la correlación:');
      if (!name) return;
      
      await api.post('/timeline/correlate', {
        case_id: getCaseId(),  // v4.4
        event_ids: selectedEvents,
        correlation_name: name,
        correlation_type: 'manual'
      });
      setSelectedEvents([]);
      loadTimeline();
    } catch (error) {
      console.error('Error correlating events:', error);
    }
  };

  // Marcar como evento clave
  const toggleKeyEvent = async (eventId, isKey) => {
    try {
      await api.post(`/timeline/events/${eventId}/key`, null, {
        params: { is_key: !isKey }
      });
      loadTimeline();
    } catch (error) {
      console.error('Error toggling key event:', error);
    }
  };

  // Eliminar evento
  const deleteEvent = async (eventId) => {
    if (!confirm('¿Eliminar este evento?')) return;
    
    try {
      await api.delete(`/timeline/events/${eventId}`);
      loadTimeline();
    } catch (error) {
      console.error('Error deleting event:', error);
    }
  };

  // Exportar timeline - v4.4: Usa case_id del contexto
  const exportTimeline = async (format = 'json') => {
    if (!hasActiveCase()) return;
    
    try {
      const response = await api.get(`/timeline/${getCaseId()}/export`, {
        params: { format }
      });
      
      if (response.data.download_url) {
        window.open(response.data.download_url, '_blank');
      }
    } catch (error) {
      console.error('Error exporting timeline:', error);
    }
  };

  // Formatear fecha
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('es-ES', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading && hasActiveCase()) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* v4.4: Case Header */}
      <CaseHeader 
        title="Timeline Forense"
        subtitle={hasActiveCase() ? `${events.length} eventos` : 'Selecciona un caso'}
        icon="⏱️"
      />
      
      {/* v4.4: Solo mostrar contenido si hay caso */}
      {!hasActiveCase() ? (
        <div className="flex items-center justify-center h-64 text-gray-500">
          Selecciona un caso para ver el timeline
        </div>
      ) : (
      <>
      {/* Header con acciones */}
      <div className="flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Clock className="w-8 h-8 text-green-500" />
          <div>
            <h1 className="text-2xl font-bold text-white">Timeline Forense</h1>
            <p className="text-gray-400 text-sm">
              Caso: <span className="text-green-400">{getCaseId()}</span> • {events.length} eventos
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAddEvent(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Agregar Evento
          </button>
          {selectedEvents.length >= 2 && (
            <button
              onClick={correlateEvents}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
            >
              <Link2 className="w-4 h-4" />
              Correlacionar ({selectedEvents.length})
            </button>
          )}
          <div className="relative group">
            <button className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors">
              <Download className="w-4 h-4" />
              Exportar
            </button>
            <div className="absolute right-0 mt-2 py-2 w-40 bg-gray-800 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => exportTimeline('json')}
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700"
              >
                JSON
              </button>
              <button
                onClick={() => exportTimeline('csv')}
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700"
              >
                CSV
              </button>
              <button
                onClick={() => exportTimeline('html')}
                className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700"
              >
                HTML
              </button>
            </div>
          </div>
          <button
            onClick={loadTimeline}
            className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Add Event Modal */}
      {showAddEvent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold text-white mb-4">Agregar Evento</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Título</label>
                <input
                  type="text"
                  value={newEvent.title}
                  onChange={(e) => setNewEvent({...newEvent, title: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  placeholder="Descripción del evento"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Fecha/Hora</label>
                  <input
                    type="datetime-local"
                    value={newEvent.event_time}
                    onChange={(e) => setNewEvent({...newEvent, event_time: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Tipo</label>
                  <select
                    value={newEvent.event_type}
                    onChange={(e) => setNewEvent({...newEvent, event_type: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="authentication">Autenticación</option>
                    <option value="file_access">Acceso a archivo</option>
                    <option value="email">Email</option>
                    <option value="network">Red</option>
                    <option value="process">Proceso</option>
                    <option value="lateral_movement">Mov. Lateral</option>
                    <option value="persistence">Persistencia</option>
                    <option value="indicator">Indicador</option>
                    <option value="custom">Personalizado</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Severidad</label>
                  <select
                    value={newEvent.severity}
                    onChange={(e) => setNewEvent({...newEvent, severity: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="info">Info</option>
                    <option value="low">Baja</option>
                    <option value="medium">Media</option>
                    <option value="high">Alta</option>
                    <option value="critical">Crítica</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Fuente</label>
                  <select
                    value={newEvent.source}
                    onChange={(e) => setNewEvent({...newEvent, source: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="manual">Manual</option>
                    <option value="m365_audit">M365 Audit</option>
                    <option value="azure_ad">Azure AD</option>
                    <option value="endpoint_loki">Loki</option>
                    <option value="endpoint_yara">YARA</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Descripción</label>
                <textarea
                  value={newEvent.description}
                  onChange={(e) => setNewEvent({...newEvent, description: e.target.value})}
                  className="w-full h-20 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                  placeholder="Descripción detallada..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowAddEvent(false)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={addEvent}
                disabled={!newEvent.title}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                Agregar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="text-2xl font-bold text-white">{summary.total_events || events.length}</div>
            <div className="text-sm text-gray-400">Total Eventos</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="text-2xl font-bold text-red-400">{summary.suspicious_events || 0}</div>
            <div className="text-sm text-gray-400">Sospechosos</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="text-2xl font-bold text-purple-400">{summary.total_correlations || 0}</div>
            <div className="text-sm text-gray-400">Correlaciones</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="text-2xl font-bold text-green-400">
              {summary.timeframe?.start ? formatDate(summary.timeframe.start) : '-'}
            </div>
            <div className="text-sm text-gray-400">Inicio</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="text-2xl font-bold text-green-400">
              {summary.timeframe?.end ? formatDate(summary.timeframe.end) : '-'}
            </div>
            <div className="text-sm text-gray-400">Fin</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <Filter className="w-5 h-5 text-gray-400" />
        <div className="flex gap-2">
          {['critical', 'high', 'medium', 'low', 'info'].map(sev => (
            <button
              key={sev}
              onClick={() => setFilters({
                ...filters,
                severity: filters.severity === sev ? null : sev
              })}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                filters.severity === sev 
                  ? `${severityStyles[sev].bg} text-white` 
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.keyEventsOnly}
            onChange={(e) => setFilters({...filters, keyEventsOnly: e.target.checked})}
            className="rounded bg-gray-700 border-gray-600"
          />
          Solo eventos clave
        </label>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-700"></div>

        {/* Events */}
        <div className="space-y-4">
          {events
            .filter(e => !filters.severity || e.severity === filters.severity)
            .filter(e => !filters.keyEventsOnly || e.is_key_event)
            .map((event) => {
              const IconComponent = eventTypeIcons[event.event_type] || Star;
              const style = severityStyles[event.severity] || severityStyles.info;
              const isSelected = selectedEvents.includes(event.event_id);
              const isExpanded = expandedEvent === event.event_id;

              return (
                <div
                  key={event.event_id}
                  className={`relative pl-16 group ${
                    isSelected ? 'ring-2 ring-purple-500 rounded-lg' : ''
                  }`}
                >
                  {/* Event dot */}
                  <div
                    className={`absolute left-4 w-5 h-5 rounded-full ${style.dot} border-4 border-gray-900 z-10 cursor-pointer`}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedEvents(selectedEvents.filter(id => id !== event.event_id));
                      } else {
                        setSelectedEvents([...selectedEvents, event.event_id]);
                      }
                    }}
                  />

                  {/* Event card */}
                  <div
                    className={`bg-gray-800 rounded-lg p-4 border ${style.border}/30 hover:border-opacity-60 transition-colors`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${style.bg}/20`}>
                          <IconComponent className={`w-5 h-5 ${style.text}`} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-white">{event.title}</h3>
                            {event.is_key_event && (
                              <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-1 text-sm text-gray-400">
                            <Calendar className="w-4 h-4" />
                            <span>{formatDate(event.event_time)}</span>
                            <span>•</span>
                            <span className="capitalize">{event.source?.replace('_', ' ')}</span>
                            <span className={`px-2 py-0.5 rounded ${style.bg}/20 ${style.text}`}>
                              {event.severity}
                            </span>
                          </div>
                          {event.description && isExpanded && (
                            <p className="mt-2 text-sm text-gray-300">{event.description}</p>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setExpandedEvent(isExpanded ? null : event.event_id)}
                          className="p-1.5 hover:bg-gray-700 rounded"
                          title="Ver detalles"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          )}
                        </button>
                        <button
                          onClick={() => toggleKeyEvent(event.event_id, event.is_key_event)}
                          className="p-1.5 hover:bg-gray-700 rounded"
                          title="Marcar como clave"
                        >
                          <Star className={`w-4 h-4 ${event.is_key_event ? 'text-yellow-400 fill-yellow-400' : 'text-gray-400'}`} />
                        </button>
                        <button
                          onClick={() => deleteEvent(event.event_id)}
                          className="p-1.5 hover:bg-gray-700 rounded"
                          title="Eliminar"
                        >
                          <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
      </>
      )}
    </div>
  );
};

export default TimelinePage;
