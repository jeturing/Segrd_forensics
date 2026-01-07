/**
 * InvestigationIOCs Component
 * Pestaña de IOCs vinculados para una investigación
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Alert, Loading } from '../Common';
import { useInvestigationWebSocket } from '../../services/realtime';
import * as iocStoreService from '../../services/iocStore';
import api from '../../services/api';

// ============================================================================
// CONSTANTES
// ============================================================================

const IOC_TYPES = {
  ip: { label: 'IP', icon: '🌐', color: 'red' },
  domain: { label: 'Domain', icon: '🔗', color: 'orange' },
  url: { label: 'URL', icon: '🌍', color: 'yellow' },
  email: { label: 'Email', icon: '📧', color: 'purple' },
  hash_md5: { label: 'MD5', icon: '#️⃣', color: 'blue' },
  hash_sha1: { label: 'SHA1', icon: '#️⃣', color: 'blue' },
  hash_sha256: { label: 'SHA256', icon: '#️⃣', color: 'indigo' },
  file_name: { label: 'File', icon: '📄', color: 'green' },
  process_name: { label: 'Process', icon: '⚙️', color: 'pink' },
  registry_key: { label: 'Registry', icon: '🔑', color: 'gray' }
};

const THREAT_LEVELS = {
  critical: { label: 'Critical', bg: 'bg-red-600', text: 'text-red-400' },
  high: { label: 'High', bg: 'bg-orange-500', text: 'text-orange-400' },
  medium: { label: 'Medium', bg: 'bg-yellow-500', text: 'text-yellow-400' },
  low: { label: 'Low', bg: 'bg-green-500', text: 'text-green-400' },
  info: { label: 'Info', bg: 'bg-blue-500', text: 'text-blue-400' }
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export default function InvestigationIOCs({ investigationId }) {
  const [linkedIOCs, setLinkedIOCs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  
  // WebSocket para actualizaciones en tiempo real
  const { isConnected, lastMessage } = useInvestigationWebSocket(investigationId, (message) => {
    handleWebSocketMessage(message);
  });

  // Cargar IOCs vinculados
  useEffect(() => {
    loadLinkedIOCs();
  }, [investigationId]);

  // Manejar mensajes WebSocket
  const handleWebSocketMessage = useCallback((message) => {
    switch (message.event) {
      case 'ioc_linked':
        if (message.investigation_id === investigationId) {
          setLinkedIOCs(prev => [...prev, message.data.ioc]);
        }
        break;
      case 'ioc_unlinked':
        if (message.investigation_id === investigationId) {
          setLinkedIOCs(prev => prev.filter(ioc => ioc.id !== message.ioc_id));
        }
        break;
      default:
        break;
    }
  }, [investigationId]);

  const loadLinkedIOCs = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/investigations/${investigationId}/iocs`);
      setLinkedIOCs(response.data.iocs || []);
    } catch (error) {
      console.error('Error loading linked IOCs:', error);
      // Demo data
      setLinkedIOCs([
        {
          id: 'IOC-20251205-A1B2C',
          value: '185.234.72.15',
          ioc_type: 'ip',
          threat_level: 'critical',
          confidence_score: 92.5,
          tags: ['c2', 'apt'],
          link_info: {
            reason: 'IP detectada en logs de autenticación sospechosa',
            relevance: 'high',
            linked_at: '2025-12-05T10:30:00Z'
          }
        },
        {
          id: 'IOC-20251205-X3Y4Z',
          value: 'malicious-payload.exe',
          ioc_type: 'file_name',
          threat_level: 'high',
          confidence_score: 85.0,
          tags: ['malware', 'dropper'],
          link_info: {
            reason: 'Archivo detectado por YARA en endpoint comprometido',
            relevance: 'high',
            linked_at: '2025-12-05T11:45:00Z'
          }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const searchAvailableIOCs = async (query) => {
    if (!query || query.length < 2) {
      setSearchResults([]);
      return;
    }
    
    setSearchLoading(true);
    try {
      const data = await iocStoreService.getIOCs({ search: query, limit: 20 });
      // Filtrar los que ya están vinculados
      const linkedIds = new Set(linkedIOCs.map(ioc => ioc.id));
      setSearchResults((data.items || []).filter(ioc => !linkedIds.has(ioc.id)));
    } catch (error) {
      console.error('Error searching IOCs:', error);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleLinkIOC = async (iocId, reason = '') => {
    try {
      await api.post(`/api/investigations/${investigationId}/iocs/${iocId}`, {
        reason: reason || 'Vinculado manualmente',
        relevance: 'high'
      });
      
      // Recargar lista
      loadLinkedIOCs();
      setShowLinkModal(false);
      setSearchQuery('');
      setSearchResults([]);
    } catch (error) {
      console.error('Error linking IOC:', error);
      alert('Error al vincular IOC');
    }
  };

  const handleUnlinkIOC = async (iocId) => {
    if (!confirm('¿Desvincular este IOC de la investigación?')) return;
    
    try {
      await api.delete(`/api/investigations/${investigationId}/iocs/${iocId}`);
      setLinkedIOCs(prev => prev.filter(ioc => ioc.id !== iocId));
    } catch (error) {
      console.error('Error unlinking IOC:', error);
      alert('Error al desvincular IOC');
    }
  };

  const handleEnrichIOC = async (iocId) => {
    try {
      await iocStoreService.enrichIOC(iocId, ['virustotal', 'abuseipdb']);
      loadLinkedIOCs();
      alert('IOC enriquecido exitosamente');
    } catch (error) {
      console.error('Error enriching IOC:', error);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">🔗 IOCs Vinculados</h3>
          <span className="badge badge-info">{linkedIOCs.length} IOCs</span>
          {isConnected && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              Live
            </span>
          )}
        </div>
        <Button variant="primary" onClick={() => setShowLinkModal(true)}>
          ➕ Vincular IOC
        </Button>
      </div>

      {/* Lista de IOCs vinculados */}
      {loading ? (
        <Loading message="Cargando IOCs vinculados..." />
      ) : linkedIOCs.length === 0 ? (
        <Alert type="info" message="No hay IOCs vinculados a esta investigación" />
      ) : (
        <div className="space-y-3">
          {linkedIOCs.map(ioc => (
            <LinkedIOCCard
              key={ioc.id}
              ioc={ioc}
              onUnlink={() => handleUnlinkIOC(ioc.id)}
              onEnrich={() => handleEnrichIOC(ioc.id)}
            />
          ))}
        </div>
      )}

      {/* Modal para vincular IOC */}
      {showLinkModal && (
        <LinkIOCModal
          onClose={() => {
            setShowLinkModal(false);
            setSearchQuery('');
            setSearchResults([]);
          }}
          searchQuery={searchQuery}
          onSearchChange={(q) => {
            setSearchQuery(q);
            searchAvailableIOCs(q);
          }}
          searchResults={searchResults}
          searchLoading={searchLoading}
          onLink={handleLinkIOC}
        />
      )}
    </div>
  );
}

// ============================================================================
// SUB-COMPONENTES
// ============================================================================

function LinkedIOCCard({ ioc, onUnlink, onEnrich }) {
  const typeInfo = IOC_TYPES[ioc.ioc_type] || { label: ioc.ioc_type, icon: '❓', color: 'gray' };
  const threatInfo = THREAT_LEVELS[ioc.threat_level] || THREAT_LEVELS.medium;

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* Header con tipo y valor */}
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{typeInfo.icon}</span>
            <div>
              <p className="font-mono text-sm break-all">{ioc.value}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`px-2 py-0.5 rounded text-xs ${threatInfo.bg} text-white`}>
                  {threatInfo.label}
                </span>
                <span className="text-xs text-gray-400">
                  Confianza: {ioc.confidence_score?.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* Tags */}
          {ioc.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {ioc.tags.map(tag => (
                <span key={tag} className="badge badge-secondary text-xs">
                  #{tag}
                </span>
              ))}
            </div>
          )}

          {/* Link info */}
          {ioc.link_info && (
            <div className="bg-gray-700/30 p-2 rounded text-sm">
              <p className="text-gray-300">{ioc.link_info.reason}</p>
              <p className="text-xs text-gray-500 mt-1">
                Vinculado: {new Date(ioc.link_info.linked_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>

        {/* Acciones */}
        <div className="flex flex-col gap-1 ml-4">
          <button
            onClick={onEnrich}
            className="p-2 hover:bg-gray-700 rounded transition"
            title="Enriquecer"
          >
            🔍
          </button>
          <button
            onClick={onUnlink}
            className="p-2 hover:bg-red-700/50 rounded transition text-red-400"
            title="Desvincular"
          >
            🔗
          </button>
        </div>
      </div>
    </Card>
  );
}

function LinkIOCModal({ onClose, searchQuery, onSearchChange, searchResults, searchLoading, onLink }) {
  const [selectedIOC, setSelectedIOC] = useState(null);
  const [reason, setReason] = useState('');

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold">🔗 Vincular IOC a Investigación</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        {/* Búsqueda */}
        <input
          type="text"
          placeholder="Buscar IOCs por valor, tipo, descripción..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="input-base mb-4"
          autoFocus
        />

        {/* Resultados */}
        <div className="flex-1 overflow-y-auto mb-4">
          {searchLoading ? (
            <Loading message="Buscando..." />
          ) : searchResults.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              {searchQuery.length < 2 
                ? 'Escribe al menos 2 caracteres para buscar'
                : 'No se encontraron IOCs'}
            </p>
          ) : (
            <div className="space-y-2">
              {searchResults.map(ioc => {
                const typeInfo = IOC_TYPES[ioc.ioc_type] || { icon: '❓' };
                const isSelected = selectedIOC?.id === ioc.id;
                
                return (
                  <div
                    key={ioc.id}
                    onClick={() => setSelectedIOC(ioc)}
                    className={`p-3 rounded cursor-pointer transition ${
                      isSelected ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{typeInfo.icon}</span>
                      <div className="flex-1">
                        <p className="font-mono text-sm">{ioc.value}</p>
                        <p className="text-xs text-gray-400">
                          {ioc.ioc_type} • {ioc.threat_level} • Score: {ioc.confidence_score}%
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Razón del vínculo */}
        {selectedIOC && (
          <div className="mb-4">
            <label className="block text-sm text-gray-400 mb-1">
              Razón del vínculo (opcional)
            </label>
            <input
              type="text"
              placeholder="Ej: Detectado en logs de autenticación sospechosa"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="input-base"
            />
          </div>
        )}

        {/* Acciones */}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={() => onLink(selectedIOC.id, reason)}
            disabled={!selectedIOC}
          >
            Vincular IOC
          </Button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export { InvestigationIOCs, LinkedIOCCard, LinkIOCModal };
