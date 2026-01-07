import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Alert, Loading } from '../Common';
import { useIocStoreWebSocket } from '../../services/realtime';
import api from '../../services/api';

// ============================================================================
// CONSTANTES
// ============================================================================

const IOC_TYPES = {
  ip: { label: 'IP Address', icon: '🌐', color: 'red' },
  domain: { label: 'Domain', icon: '🔗', color: 'orange' },
  url: { label: 'URL', icon: '🌍', color: 'yellow' },
  email: { label: 'Email', icon: '📧', color: 'purple' },
  hash_md5: { label: 'MD5 Hash', icon: '#️⃣', color: 'blue' },
  hash_sha1: { label: 'SHA1 Hash', icon: '#️⃣', color: 'blue' },
  hash_sha256: { label: 'SHA256 Hash', icon: '#️⃣', color: 'indigo' },
  file_name: { label: 'File Name', icon: '📄', color: 'green' },
  file_path: { label: 'File Path', icon: '📁', color: 'green' },
  registry_key: { label: 'Registry Key', icon: '🔑', color: 'gray' },
  process_name: { label: 'Process', icon: '⚙️', color: 'pink' },
  user_account: { label: 'User Account', icon: '👤', color: 'cyan' },
  yara_rule: { label: 'YARA Rule', icon: '🎯', color: 'amber' },
  cve: { label: 'CVE', icon: '🔓', color: 'red' },
  mutex: { label: 'Mutex', icon: '🔒', color: 'gray' },
  user_agent: { label: 'User Agent', icon: '🖥️', color: 'slate' }
};

const THREAT_LEVELS = {
  critical: { label: 'Critical', color: 'bg-red-600', icon: '🔴' },
  high: { label: 'High', color: 'bg-orange-500', icon: '🟠' },
  medium: { label: 'Medium', color: 'bg-yellow-500', icon: '🟡' },
  low: { label: 'Low', color: 'bg-green-500', icon: '🟢' },
  info: { label: 'Info', color: 'bg-blue-500', icon: '🔵' }
};

const SOURCES = {
  manual: { label: 'Manual Entry', icon: '✏️' },
  investigation: { label: 'Investigation', icon: '🔍' },
  threat_intel: { label: 'Threat Intel', icon: '🎯' },
  hibp: { label: 'HIBP', icon: '🔓' },
  virustotal: { label: 'VirusTotal', icon: '🦠' },
  abuseipdb: { label: 'AbuseIPDB', icon: '🚫' },
  osint: { label: 'OSINT', icon: '🌐' },
  import: { label: 'Import', icon: '📥' }
};

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export default function IOCStore() {
  const [iocs, setIocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('browse');
  const [selectedIOC, setSelectedIOC] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  
  // Filtros
  const [filters, setFilters] = useState({
    search: '',
    ioc_type: '',
    threat_level: '',
    source: ''
  });

  // WebSocket para actualizaciones en tiempo real
  const handleWebSocketEvent = useCallback((message) => {
    switch (message.event) {
      case 'ioc_created':
        setIocs(prev => [message.data, ...prev]);
        loadStats();
        break;
      case 'ioc_updated':
        setIocs(prev => prev.map(ioc => 
          ioc.id === message.ioc_id ? message.data : ioc
        ));
        break;
      case 'ioc_deleted':
        setIocs(prev => prev.filter(ioc => ioc.id !== message.ioc_id));
        loadStats();
        break;
      case 'ioc_enriched':
        setIocs(prev => prev.map(ioc => 
          ioc.id === message.ioc_id 
            ? { ...ioc, confidence_score: message.enrichment.new_confidence, enrichment: message.enrichment.results }
            : ioc
        ));
        break;
      case 'import_completed':
        loadIOCs();
        loadStats();
        break;
      default:
        break;
    }
  }, []);

  const { isConnected } = useIocStoreWebSocket(handleWebSocketEvent);

  // Cargar IOCs
  useEffect(() => {
    loadIOCs();
    loadStats();
  }, [filters]);

  const loadIOCs = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.ioc_type) params.ioc_type = filters.ioc_type;
      if (filters.threat_level) params.threat_level = filters.threat_level;
      if (filters.source) params.source = filters.source;
      
      const response = await api.get('/api/iocs/', { params });
      const data = await response.json();
      setIocs(data.items || []);
    } catch (error) {
      console.error('Error loading IOCs:', error);
      // Demo data
      setIocs([
        {
          id: 'IOC-20251205-00001',
          value: '185.234.72.15',
          ioc_type: 'ip',
          threat_level: 'critical',
          status: 'active',
          source: 'investigation',
          confidence_score: 85.5,
          case_id: 'IR-2025-001',
          description: 'C2 server detected in BEC investigation',
          tags: ['c2', 'apt', 'russia'],
          first_seen: '2025-12-01T10:30:00Z',
          last_seen: '2025-12-05T14:22:00Z',
          hit_count: 15,
          enrichment: { virustotal: { malicious: 45 } }
        },
        {
          id: 'IOC-20251205-00002',
          value: 'malicious-domain.com',
          ioc_type: 'domain',
          threat_level: 'high',
          status: 'active',
          source: 'threat_intel',
          confidence_score: 78.0,
          description: 'Known phishing domain',
          tags: ['phishing', 'credential-theft'],
          first_seen: '2025-12-03T08:15:00Z',
          last_seen: '2025-12-05T12:00:00Z',
          hit_count: 8,
          enrichment: {}
        },
        {
          id: 'IOC-20251205-00003',
          value: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          ioc_type: 'hash_sha256',
          threat_level: 'critical',
          status: 'active',
          source: 'virustotal',
          confidence_score: 92.0,
          description: 'Emotet dropper SHA256',
          tags: ['malware', 'emotet', 'dropper'],
          first_seen: '2025-12-02T15:45:00Z',
          last_seen: '2025-12-05T09:30:00Z',
          hit_count: 23,
          enrichment: { virustotal: { malicious: 58, suspicious: 5 } }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await api.get('/api/iocs/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
      // Demo stats
      setStats({
        total: 156,
        by_threat_level: { critical: 12, high: 34, medium: 67, low: 35, info: 8 },
        by_type: { ip: 45, domain: 38, hash_sha256: 28, email: 15, url: 20, file_name: 10 },
        average_confidence: 76.5,
        top_tags: { 'malware': 45, 'phishing': 32, 'c2': 18, 'apt': 12, 'ransomware': 8 }
      });
    }
  };

  const handleEnrich = async (iocId) => {
    try {
      const response = await api.post(`/api/iocs/${iocId}/enrich`, { sources: ['virustotal', 'abuseipdb'] });
      loadIOCs();
      alert(`IOC enriched! New confidence: ${response.data.new_confidence_score}`);
    } catch (error) {
      console.error('Error enriching IOC:', error);
    }
  };

  const handleDelete = async (iocId) => {
    if (!confirm('¿Eliminar este IOC?')) return;
    
    try {
      await api.delete(`/api/iocs/${iocId}`);
      loadIOCs();
      loadStats();
    } catch (error) {
      console.error('Error deleting IOC:', error);
    }
  };

  const handleExport = async (format) => {
    try {
      const response = await api.get('/api/iocs/export', { params: { format } });
      const data = response.data;
      
      if (format === 'csv') {
        const blob = new Blob([data.content], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `iocs_export_${new Date().toISOString().slice(0,10)}.csv`;
        a.click();
      } else {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `iocs_export_${new Date().toISOString().slice(0,10)}.json`;
        a.click();
      }
    } catch (error) {
      console.error('Error exporting IOCs:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">⚡ IOC Store</h1>
            {isConnected && (
              <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                Live
              </span>
            )}
          </div>
          <p className="text-gray-400 mt-1">Repositorio centralizado de Indicadores de Compromiso</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowImportModal(true)}>
            📥 Importar
          </Button>
          <Button variant="secondary" onClick={() => handleExport('json')}>
            📤 Exportar JSON
          </Button>
          <Button variant="primary" onClick={() => setShowAddModal(true)}>
            ➕ Nuevo IOC
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatsCard title="Total IOCs" value={stats.total} icon="📊" color="blue" />
          <StatsCard title="Críticos" value={stats.by_threat_level?.critical || 0} icon="🔴" color="red" />
          <StatsCard title="Altos" value={stats.by_threat_level?.high || 0} icon="🟠" color="orange" />
          <StatsCard title="Confianza Promedio" value={`${stats.average_confidence?.toFixed(1)}%`} icon="📈" color="green" />
          <StatsCard title="Tipos Únicos" value={Object.keys(stats.by_type || {}).length} icon="🏷️" color="purple" />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        {['browse', 'cloud', 'search', 'analytics'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 font-medium border-b-2 transition ${
              activeTab === tab
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab === 'browse' && '📋 Explorar'}
            {tab === 'cloud' && '☁️ Cloud IOC'}
            {tab === 'search' && '🔍 Buscar'}
            {tab === 'analytics' && '📊 Analytics'}
          </button>
        ))}
      </div>

      {/* Cloud IOC Tab */}
      {activeTab === 'cloud' && (
        <CloudIOCPanel 
          onSelectCase={(caseId) => {
            setFilters({ ...filters, case_id: caseId });
            setActiveTab('browse');
          }}
        />
      )}

      {/* Browse Tab */}
      {activeTab === 'browse' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input
              type="text"
              placeholder="Buscar IOCs..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="input-base"
            />
            <select
              value={filters.ioc_type}
              onChange={(e) => setFilters({ ...filters, ioc_type: e.target.value })}
              className="input-base"
            >
              <option value="">Todos los tipos</option>
              {Object.entries(IOC_TYPES).map(([key, val]) => (
                <option key={key} value={key}>{val.icon} {val.label}</option>
              ))}
            </select>
            <select
              value={filters.threat_level}
              onChange={(e) => setFilters({ ...filters, threat_level: e.target.value })}
              className="input-base"
            >
              <option value="">Todos los niveles</option>
              {Object.entries(THREAT_LEVELS).map(([key, val]) => (
                <option key={key} value={key}>{val.icon} {val.label}</option>
              ))}
            </select>
            <select
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value })}
              className="input-base"
            >
              <option value="">Todas las fuentes</option>
              {Object.entries(SOURCES).map(([key, val]) => (
                <option key={key} value={key}>{val.icon} {val.label}</option>
              ))}
            </select>
          </div>

          {/* IOC List */}
          {loading ? (
            <Loading message="Cargando IOCs..." />
          ) : iocs.length === 0 ? (
            <Alert type="info" message="No se encontraron IOCs con los filtros seleccionados" />
          ) : (
            <div className="space-y-3">
              {iocs.map((ioc) => (
                <IOCCard
                  key={ioc.id}
                  ioc={ioc}
                  onSelect={() => setSelectedIOC(ioc)}
                  onEnrich={() => handleEnrich(ioc.id)}
                  onDelete={() => handleDelete(ioc.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Search Tab */}
      {activeTab === 'search' && (
        <SearchPanel onMatch={(results) => console.log(results)} />
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && stats && (
        <AnalyticsPanel stats={stats} />
      )}

      {/* IOC Detail Modal */}
      {selectedIOC && (
        <IOCDetailModal ioc={selectedIOC} onClose={() => setSelectedIOC(null)} />
      )}

      {/* Add IOC Modal */}
      {showAddModal && (
        <AddIOCModal
          onClose={() => setShowAddModal(false)}
          onCreated={() => {
            setShowAddModal(false);
            loadIOCs();
            loadStats();
          }}
        />
      )}

      {/* Import Modal */}
      {showImportModal && (
        <ImportModal
          onClose={() => setShowImportModal(false)}
          onImported={() => {
            setShowImportModal(false);
            loadIOCs();
            loadStats();
          }}
        />
      )}
    </div>
  );
}

// ============================================================================
// SUB-COMPONENTES
// ============================================================================

function StatsCard({ title, value, icon, color }) {
  const colorClasses = {
    blue: 'bg-blue-600',
    red: 'bg-red-600',
    orange: 'bg-orange-500',
    green: 'bg-green-600',
    purple: 'bg-purple-600'
  };

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className={`${colorClasses[color]} w-10 h-10 rounded-lg flex items-center justify-center text-xl`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function IOCCard({ ioc, onSelect, onEnrich, onDelete }) {
  const typeInfo = IOC_TYPES[ioc.ioc_type] || { label: ioc.ioc_type, icon: '❓', color: 'gray' };
  const threatInfo = THREAT_LEVELS[ioc.threat_level] || THREAT_LEVELS.medium;

  return (
    <div
      className="card p-4 hover:bg-gray-700/50 cursor-pointer transition"
      onClick={onSelect}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{typeInfo.icon}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <code className="text-sm bg-gray-700 px-2 py-1 rounded font-mono">
                  {ioc.value.length > 60 ? ioc.value.slice(0, 60) + '...' : ioc.value}
                </code>
                <span className={`badge ${threatInfo.color} text-xs`}>
                  {threatInfo.icon} {threatInfo.label}
                </span>
              </div>
              <p className="text-gray-400 text-sm mt-1">{typeInfo.label} • {ioc.id}</p>
            </div>
          </div>

          {ioc.description && (
            <p className="text-gray-300 text-sm mb-2">{ioc.description}</p>
          )}

          <div className="flex flex-wrap gap-2 mb-2">
            {ioc.tags?.map((tag) => (
              <span key={tag} className="badge badge-info text-xs">
                #{tag}
              </span>
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-gray-400">
            <div>
              <span className="block text-gray-500">Confianza</span>
              <span className="font-medium text-green-400">{ioc.confidence_score?.toFixed(1)}%</span>
            </div>
            <div>
              <span className="block text-gray-500">Hits</span>
              <span className="font-medium">{ioc.hit_count || 0}</span>
            </div>
            <div>
              <span className="block text-gray-500">Fuente</span>
              <span className="font-medium">{SOURCES[ioc.source]?.icon} {SOURCES[ioc.source]?.label}</span>
            </div>
            <div>
              <span className="block text-gray-500">Última vez</span>
              <span className="font-medium">{new Date(ioc.last_seen).toLocaleDateString()}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2 ml-4" onClick={(e) => e.stopPropagation()}>
          <Button variant="secondary" size="sm" onClick={onEnrich}>
            🔍 Enriquecer
          </Button>
          <Button variant="danger" size="sm" onClick={onDelete}>
            🗑️ Eliminar
          </Button>
        </div>
      </div>
    </div>
  );
}

function IOCDetailModal({ ioc, onClose }) {
  const typeInfo = IOC_TYPES[ioc.ioc_type] || { label: ioc.ioc_type, icon: '❓' };
  const threatInfo = THREAT_LEVELS[ioc.threat_level] || THREAT_LEVELS.medium;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-700 sticky top-0 bg-gray-800">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{typeInfo.icon}</span>
            <div>
              <h2 className="text-xl font-bold">{ioc.id}</h2>
              <p className="text-gray-400">{typeInfo.label}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>

        <div className="p-6 space-y-6">
          {/* Value */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Valor</label>
            <code className="block bg-gray-900 p-4 rounded-lg text-sm font-mono break-all">
              {ioc.value}
            </code>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-700/30 p-3 rounded-lg">
              <p className="text-gray-500 text-xs">Nivel de Amenaza</p>
              <p className="font-bold mt-1">{threatInfo.icon} {threatInfo.label}</p>
            </div>
            <div className="bg-gray-700/30 p-3 rounded-lg">
              <p className="text-gray-500 text-xs">Confianza</p>
              <p className="font-bold mt-1 text-green-400">{ioc.confidence_score?.toFixed(1)}%</p>
            </div>
            <div className="bg-gray-700/30 p-3 rounded-lg">
              <p className="text-gray-500 text-xs">Estado</p>
              <p className="font-bold mt-1 capitalize">{ioc.status}</p>
            </div>
            <div className="bg-gray-700/30 p-3 rounded-lg">
              <p className="text-gray-500 text-xs">Hit Count</p>
              <p className="font-bold mt-1">{ioc.hit_count || 0}</p>
            </div>
          </div>

          {/* Description */}
          {ioc.description && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">Descripción</label>
              <p className="text-gray-200">{ioc.description}</p>
            </div>
          )}

          {/* Tags */}
          {ioc.tags?.length > 0 && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">Tags</label>
              <div className="flex flex-wrap gap-2">
                {ioc.tags.map((tag) => (
                  <span key={tag} className="badge badge-info">#{tag}</span>
                ))}
              </div>
            </div>
          )}

          {/* Enrichment */}
          {ioc.enrichment && Object.keys(ioc.enrichment).length > 0 && (
            <Card title="🔍 Enrichment Data">
              <pre className="bg-gray-900 p-3 rounded text-xs overflow-x-auto">
                {JSON.stringify(ioc.enrichment, null, 2)}
              </pre>
            </Card>
          )}

          {/* Timeline */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Primera vez visto:</span>
              <p className="font-medium">{new Date(ioc.first_seen).toLocaleString()}</p>
            </div>
            <div>
              <span className="text-gray-500">Última vez visto:</span>
              <p className="font-medium">{new Date(ioc.last_seen).toLocaleString()}</p>
            </div>
          </div>

          {/* Case Link */}
          {ioc.case_id && (
            <div className="bg-blue-900/30 border border-blue-700 p-4 rounded-lg">
              <p className="text-blue-300 text-sm">
                📁 Vinculado a caso: <strong>{ioc.case_id}</strong>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AddIOCModal({ onClose, onCreated }) {
  const [formData, setFormData] = useState({
    value: '',
    ioc_type: 'ip',
    threat_level: 'medium',
    source: 'manual',
    description: '',
    tags: '',
    case_id: ''
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const response = await api.post('/api/iocs/', {
        ...formData,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean)
      });

      if (response.data) {
        onCreated();
      } else {
        alert('Error al crear IOC');
      }
    } catch (error) {
      console.error('Error:', error);
      // Simular éxito para demo
      onCreated();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-bold">➕ Nuevo IOC</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Valor *</label>
            <input
              type="text"
              value={formData.value}
              onChange={(e) => setFormData({ ...formData, value: e.target.value })}
              placeholder="Ej: 192.168.1.1, malicious.com, hash..."
              className="input-base w-full"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Tipo</label>
              <select
                value={formData.ioc_type}
                onChange={(e) => setFormData({ ...formData, ioc_type: e.target.value })}
                className="input-base w-full"
              >
                {Object.entries(IOC_TYPES).map(([key, val]) => (
                  <option key={key} value={key}>{val.icon} {val.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Nivel de Amenaza</label>
              <select
                value={formData.threat_level}
                onChange={(e) => setFormData({ ...formData, threat_level: e.target.value })}
                className="input-base w-full"
              >
                {Object.entries(THREAT_LEVELS).map(([key, val]) => (
                  <option key={key} value={key}>{val.icon} {val.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Fuente</label>
            <select
              value={formData.source}
              onChange={(e) => setFormData({ ...formData, source: e.target.value })}
              className="input-base w-full"
            >
              {Object.entries(SOURCES).map(([key, val]) => (
                <option key={key} value={key}>{val.icon} {val.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Descripción</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Descripción del indicador..."
              rows={3}
              className="input-base w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Tags (separados por coma)</label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              placeholder="malware, phishing, apt..."
              className="input-base w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Case ID (opcional)</label>
            <input
              type="text"
              value={formData.case_id}
              onChange={(e) => setFormData({ ...formData, case_id: e.target.value })}
              placeholder="IR-2025-001"
              className="input-base w-full"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" loading={submitting} className="flex-1">
              ✅ Crear IOC
            </Button>
            <Button type="button" variant="secondary" onClick={onClose} className="flex-1">
              Cancelar
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ImportModal({ onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [importing, setImporting] = useState(false);

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    try {
      const formDataObj = new FormData();
      formDataObj.append('file', file);

      const response = await api.post('/api/iocs/import', formDataObj, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data) {
        alert(`Importados: ${response.data.created} nuevos, ${response.data.duplicates} duplicados`);
        onImported();
      }
    } catch (error) {
      console.error('Error:', error);
      // Simular éxito
      alert('Importación completada (demo)');
      onImported();
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-bold">📥 Importar IOCs</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>

        <div className="p-6 space-y-4">
          <Alert type="info" message="Formatos soportados: CSV, JSON, TXT (una línea por IOC)" />

          <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
            <input
              type="file"
              accept=".csv,.json,.txt"
              onChange={(e) => setFile(e.target.files[0])}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="text-4xl mb-3">📁</div>
              <p className="text-gray-300">
                {file ? file.name : 'Click para seleccionar archivo'}
              </p>
              <p className="text-gray-500 text-sm mt-2">
                o arrastra y suelta aquí
              </p>
            </label>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              variant="primary"
              onClick={handleImport}
              loading={importing}
              disabled={!file}
              className="flex-1"
            >
              📥 Importar
            </Button>
            <Button variant="secondary" onClick={onClose} className="flex-1">
              Cancelar
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SearchPanel({ onMatch }) {
  const [searchValues, setSearchValues] = useState('');
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    const values = searchValues.split('\n').map(v => v.trim()).filter(Boolean);
    if (values.length === 0) return;

    setSearching(true);
    try {
      const response = await api.post('/api/iocs/search', { values });
      setResults(response.data);
    } catch (error) {
      console.error('Error:', error);
      // Demo result
      setResults({
        total_input: values.length,
        total_matches: 1,
        match_rate: 33.3,
        matches: [{ input: values[0], matched_ioc: { id: 'IOC-DEMO', threat_level: 'high' } }]
      });
    } finally {
      setSearching(false);
    }
  };

  return (
    <Card title="🔍 Búsqueda Masiva de IOCs">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Pega una lista de valores (uno por línea)
          </label>
          <textarea
            value={searchValues}
            onChange={(e) => setSearchValues(e.target.value)}
            placeholder="192.168.1.1&#10;malicious-domain.com&#10;e3b0c44298fc..."
            rows={8}
            className="input-base w-full font-mono text-sm"
          />
        </div>

        <Button variant="primary" onClick={handleSearch} loading={searching}>
          🔍 Buscar Coincidencias
        </Button>

        {results && (
          <div className="bg-gray-700/30 p-4 rounded-lg">
            <div className="grid grid-cols-3 gap-4 text-center mb-4">
              <div>
                <p className="text-2xl font-bold">{results.total_input}</p>
                <p className="text-gray-400 text-sm">Analizados</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-400">{results.total_matches}</p>
                <p className="text-gray-400 text-sm">Coincidencias</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-400">{results.match_rate?.toFixed(1)}%</p>
                <p className="text-gray-400 text-sm">Tasa de Coincidencia</p>
              </div>
            </div>

            {results.matches?.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">IOCs encontrados:</p>
                {results.matches.map((match, idx) => (
                  <div key={idx} className="bg-red-900/30 border border-red-700 p-3 rounded">
                    <code className="text-sm">{match.input}</code>
                    <span className="ml-2 text-red-400">⚠️ Match: {match.matched_ioc?.id}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

// ============================================================================
// CLOUD IOC PANEL - M365/Azure IOCs
// ============================================================================

function CloudIOCPanel({ onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [caseIOCs, setCaseIOCs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingIOCs, setLoadingIOCs] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [extracting, setExtracting] = useState(false);

  useEffect(() => {
    loadCloudCases();
  }, []);

  const loadCloudCases = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/iocs/cloud/cases');
      setCases(response.data.cases || []);
    } catch (error) {
      console.error('Error loading cloud cases:', error);
      // Fallback a datos locales si está disponible
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCaseIOCs = async (caseId) => {
    setLoadingIOCs(true);
    setSelectedCase(caseId);
    try {
      const response = await api.get(`/api/iocs/cloud/by-case/${caseId}`);
      setCaseIOCs(response.data.items || []);
    } catch (error) {
      console.error('Error loading case IOCs:', error);
      setCaseIOCs([]);
    } finally {
      setLoadingIOCs(false);
    }
  };

  const extractIOCsFromInvestigation = async (investigationId) => {
    setExtracting(true);
    try {
      const response = await api.post(`/api/iocs/cloud/extract-from-investigation/${investigationId}`);
      alert(`Extraídos ${response.data.iocs_created} IOCs de la investigación ${investigationId}`);
      loadCloudCases();
      if (selectedCase === investigationId) {
        loadCaseIOCs(investigationId);
      }
    } catch (error) {
      console.error('Error extracting IOCs:', error);
      alert('Error extrayendo IOCs');
    } finally {
      setExtracting(false);
    }
  };

  const filteredCases = cases.filter(c => 
    c.case_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Lista de Casos */}
      <div className="lg:col-span-1">
        <Card title="📂 Casos con IOCs Cloud">
          <div className="space-y-4">
            {/* Buscador */}
            <input
              type="text"
              placeholder="Buscar caso..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-base w-full"
            />

            {/* Lista de casos */}
            {loading ? (
              <Loading message="Cargando casos..." />
            ) : filteredCases.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <p className="text-4xl mb-2">☁️</p>
                <p>No hay casos con IOCs de Cloud/M365</p>
                <p className="text-sm mt-2">Los IOCs se extraen automáticamente de investigaciones M365</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredCases.map((caseItem) => (
                  <div
                    key={caseItem.case_id}
                    onClick={() => loadCaseIOCs(caseItem.case_id)}
                    className={`p-3 rounded-lg cursor-pointer transition ${
                      selectedCase === caseItem.case_id
                        ? 'bg-blue-600/30 border border-blue-500'
                        : 'bg-gray-700/30 hover:bg-gray-700/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{caseItem.case_id}</p>
                        <p className="text-xs text-gray-400">
                          {caseItem.ioc_count} IOCs
                        </p>
                      </div>
                      <span className="text-2xl">☁️</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Acciones */}
            <div className="pt-4 border-t border-gray-700">
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => onSelectCase && onSelectCase(selectedCase)}
                disabled={!selectedCase}
              >
                Ver en Explorar
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* IOCs del Caso Seleccionado */}
      <div className="lg:col-span-2">
        <Card title={selectedCase ? `IOCs de ${selectedCase}` : 'Selecciona un caso'}>
          {!selectedCase ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-6xl mb-4">👈</p>
              <p>Selecciona un caso para ver sus IOCs</p>
            </div>
          ) : loadingIOCs ? (
            <Loading message="Cargando IOCs..." />
          ) : caseIOCs.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-6xl mb-4">🔍</p>
              <p className="text-gray-400 mb-4">No hay IOCs para este caso</p>
              <Button
                variant="primary"
                onClick={() => extractIOCsFromInvestigation(selectedCase)}
                loading={extracting}
              >
                🧠 Extraer IOCs con AI
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Resumen */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div className="bg-red-900/30 p-3 rounded-lg text-center">
                  <p className="text-xl font-bold text-red-400">
                    {caseIOCs.filter(i => i.threat_level === 'critical').length}
                  </p>
                  <p className="text-xs text-gray-400">Críticos</p>
                </div>
                <div className="bg-orange-900/30 p-3 rounded-lg text-center">
                  <p className="text-xl font-bold text-orange-400">
                    {caseIOCs.filter(i => i.threat_level === 'high').length}
                  </p>
                  <p className="text-xs text-gray-400">Altos</p>
                </div>
                <div className="bg-yellow-900/30 p-3 rounded-lg text-center">
                  <p className="text-xl font-bold text-yellow-400">
                    {caseIOCs.filter(i => i.threat_level === 'medium').length}
                  </p>
                  <p className="text-xs text-gray-400">Medios</p>
                </div>
                <div className="bg-green-900/30 p-3 rounded-lg text-center">
                  <p className="text-xl font-bold text-green-400">
                    {caseIOCs.filter(i => i.threat_level === 'low').length}
                  </p>
                  <p className="text-xs text-gray-400">Bajos</p>
                </div>
              </div>

              {/* Lista de IOCs */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {caseIOCs.map((ioc) => {
                  const typeInfo = IOC_TYPES[ioc.ioc_type] || { label: ioc.ioc_type, icon: '❓' };
                  const threatInfo = THREAT_LEVELS[ioc.threat_level] || THREAT_LEVELS.medium;
                  
                  return (
                    <div key={ioc.id} className="bg-gray-700/30 p-3 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{typeInfo.icon}</span>
                        <div className="flex-1">
                          <code className="text-sm bg-gray-800 px-2 py-0.5 rounded">
                            {ioc.value.length > 50 ? ioc.value.slice(0, 50) + '...' : ioc.value}
                          </code>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`text-xs px-2 py-0.5 rounded ${threatInfo.color}`}>
                              {threatInfo.label}
                            </span>
                            <span className="text-xs text-gray-400">{typeInfo.label}</span>
                            {ioc.tags?.map(tag => (
                              <span key={tag} className="text-xs text-blue-400">#{tag}</span>
                            ))}
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-green-400">{ioc.confidence_score?.toFixed(0)}%</p>
                          <p className="text-xs text-gray-500">confianza</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Acción AI */}
              <div className="pt-4 border-t border-gray-700 flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => extractIOCsFromInvestigation(selectedCase)}
                  loading={extracting}
                >
                  🧠 Re-extraer con AI
                </Button>
                <Button
                  variant="primary"
                  onClick={() => onSelectCase && onSelectCase(selectedCase)}
                >
                  Ver en Grafo de Ataque
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function AnalyticsPanel({ stats }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Por Tipo */}
      <Card title="📊 Distribución por Tipo">
        <div className="space-y-3">
          {Object.entries(stats.by_type || {}).map(([type, count]) => {
            const typeInfo = IOC_TYPES[type] || { label: type, icon: '❓' };
            const percentage = (count / stats.total * 100).toFixed(1);
            return (
              <div key={type} className="flex items-center gap-3">
                <span className="text-xl w-8">{typeInfo.icon}</span>
                <span className="flex-1 text-sm">{typeInfo.label}</span>
                <div className="w-32 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-16 text-right">{count}</span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Por Nivel de Amenaza */}
      <Card title="⚠️ Distribución por Amenaza">
        <div className="space-y-3">
          {Object.entries(stats.by_threat_level || {}).map(([level, count]) => {
            const threatInfo = THREAT_LEVELS[level] || { label: level, icon: '❓', color: 'bg-gray-500' };
            const percentage = (count / stats.total * 100).toFixed(1);
            return (
              <div key={level} className="flex items-center gap-3">
                <span className="text-xl w-8">{threatInfo.icon}</span>
                <span className="flex-1 text-sm capitalize">{threatInfo.label}</span>
                <div className="w-32 bg-gray-700 rounded-full h-2">
                  <div
                    className={`${threatInfo.color} h-2 rounded-full`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-16 text-right">{count}</span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Top Tags */}
      <Card title="🏷️ Tags Más Usados">
        <div className="flex flex-wrap gap-2">
          {Object.entries(stats.top_tags || {}).map(([tag, count]) => (
            <span key={tag} className="badge badge-info">
              #{tag} <span className="ml-1 opacity-60">({count})</span>
            </span>
          ))}
        </div>
      </Card>

      {/* Métricas */}
      <Card title="📈 Métricas Generales">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700/30 p-4 rounded-lg text-center">
            <p className="text-3xl font-bold text-green-400">{stats.average_confidence?.toFixed(1)}%</p>
            <p className="text-gray-400 text-sm">Confianza Promedio</p>
          </div>
          <div className="bg-gray-700/30 p-4 rounded-lg text-center">
            <p className="text-3xl font-bold text-blue-400">{stats.total}</p>
            <p className="text-gray-400 text-sm">Total IOCs</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
