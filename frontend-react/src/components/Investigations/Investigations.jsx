import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Card, Button, Alert, Loading } from '../Common';
import {
  CasesByStateChart,
  CasesBySeverityChart,
  RecentCasesTimelineChart,
  ResolutionStatsChart,
  CasesEvolutionChart
} from './InvestigationCharts';
import { caseService } from '../../services/cases';

const SEVERITY_COLORS = {
  critical: 'bg-red-900 text-red-200',
  high: 'bg-orange-900 text-orange-200',
  medium: 'bg-yellow-900 text-yellow-200',
  low: 'bg-green-900 text-green-200',
  info: 'bg-blue-900 text-blue-200'
};

const STATUS_COLORS = {
  open: 'bg-blue-900 text-blue-200',
  'in-progress': 'bg-purple-900 text-purple-200',
  investigating: 'bg-purple-900 text-purple-200',
  'on-hold': 'bg-gray-700 text-gray-200',
  resolved: 'bg-green-900 text-green-200',
  closed: 'bg-gray-700 text-gray-200'
};

export default function Investigations() {
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState('loading');
  const [activeTab, setActiveTab] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCase, setSelectedCase] = useState(null);
  const [showNewCaseModal, setShowNewCaseModal] = useState(false);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await caseService.getCases(1, 100);
      setCases(data.items || []);
      setDataSource(data.dataSource || 'real');
      toast.success(`Cargadas ${data.items?.length || 0} investigaciones`);
    } catch (err) {
      console.error('Error loading cases:', err);
      setError('Error conectando con la API');
      setCases([]);
      setDataSource('error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      (c.name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
      (c.id?.toLowerCase() || '').includes(searchTerm.toLowerCase());

    if (activeTab === 'all') return matchesSearch;
    
    const status = c.status?.toLowerCase() || '';
    if (activeTab === 'in-progress') {
      return matchesSearch && (status === 'in-progress' || status === 'investigating');
    }
    return matchesSearch && status === activeTab;
  });

  const handleNewCase = () => {
    setShowNewCaseModal(true);
  };

  const handleCreateCase = async (caseData) => {
    try {
      await caseService.createCase(caseData);
      toast.success('Investigación creada exitosamente');
      setShowNewCaseModal(false);
      loadCases();
    } catch (err) {
      toast.error('Error creando investigación: ' + (err.message || 'Error desconocido'));
    }
  };

  const handleViewGraph = (caseId) => {
    navigate(`/graph?case=${caseId}`);
    toast.info(`Abriendo grafo para ${caseId}`);
  };

  const handleViewIOCs = (caseId) => {
    navigate(`/iocs?case=${caseId}`);
  };

  if (loading && cases.length === 0) {
    return <Loading message="Cargando investigaciones..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold">🔍 Investigaciones</h1>
          <p className="text-gray-400 mt-1">Gestión de casos forenses</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            dataSource === 'real' ? 'bg-green-900 text-green-200' :
            dataSource === 'demo' ? 'bg-yellow-900 text-yellow-200' :
            'bg-red-900 text-red-200'
          }`}>
            {dataSource === 'real' ? '🟢 Real' : 
             dataSource === 'demo' ? '🟡 Demo' : '🔴 Error'}
          </span>
          <button onClick={loadCases} className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">🔄</button>
          <Button variant="primary" onClick={handleNewCase}>➕ Nueva</Button>
        </div>
      </div>

      {error && <Alert type="error" title="Error" message={error} />}

      {/* Search */}
      <div className="flex gap-4 items-center">
        <input
          type="text"
          placeholder="Buscar por ID o nombre..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-base flex-1"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700 overflow-x-auto">
        {['all', 'open', 'in-progress', 'resolved', 'closed'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium border-b-2 transition whitespace-nowrap ${
              activeTab === tab
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab === 'all' ? `Todos (${cases.length})` : 
             tab === 'in-progress' ? 'En Progreso' :
             tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Analytics Charts Row 1 */}
      {cases.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="📊 Casos por Estado">
            <CasesByStateChart cases={cases} />
          </Card>
          <Card title="🚨 Casos por Severidad">
            <CasesBySeverityChart cases={cases} />
          </Card>
        </div>
      )}

      {/* Analytics Charts Row 2 */}
      {cases.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="📈 Timeline de Casos">
            <RecentCasesTimelineChart cases={cases} />
          </Card>
          <Card title="✅ Tasa de Resolución">
            <ResolutionStatsChart cases={cases} />
          </Card>
        </div>
      )}

      {/* Evolution Chart */}
      {cases.length > 0 && (
        <Card title="📊 Evolución de Casos">
          <CasesEvolutionChart cases={cases} />
        </Card>
      )}

      {/* Cases */}
      <div className="space-y-4">
        {filteredCases.length === 0 ? (
          <div className="text-center py-12 bg-gray-800/50 rounded-lg">
            <p className="text-gray-400 text-lg mb-4">
              {cases.length === 0 ? 'No hay investigaciones' : 'Sin resultados'}
            </p>
            <Button variant="primary" onClick={handleNewCase}>➕ Crear Primera</Button>
          </div>
        ) : (
          filteredCases.map((caseItem) => (
            <CaseCard
              key={caseItem.id}
              caseData={caseItem}
              onSelect={() => setSelectedCase(caseItem)}
              onViewGraph={() => handleViewGraph(caseItem.id)}
              onViewIOCs={() => handleViewIOCs(caseItem.id)}
              isSelected={selectedCase?.id === caseItem.id}
            />
          ))
        )}
      </div>

      {selectedCase && (
        <CaseDetailPanel 
          caseData={selectedCase} 
          onClose={() => setSelectedCase(null)}
          onViewGraph={() => handleViewGraph(selectedCase.id)}
          onViewIOCs={() => handleViewIOCs(selectedCase.id)}
        />
      )}

      {showNewCaseModal && (
        <NewCaseModal 
          onClose={() => setShowNewCaseModal(false)}
          onCreate={handleCreateCase}
        />
      )}
    </div>
  );
}

function CaseCard({ caseData, onSelect, onViewGraph, onViewIOCs, isSelected }) {
  const getSeverityIcon = (s) => ({ critical: '🔴', high: '🟠', medium: '🟡', low: '🟢' }[s?.toLowerCase()] || '❓');
  const getStatusIcon = (s) => ({ open: '📂', 'in-progress': '⏳', investigating: '🔍', resolved: '✅', closed: '🗄️' }[s?.toLowerCase()] || '❓');

  return (
    <div onClick={onSelect} className={`card card-hover cursor-pointer ${isSelected ? 'ring-2 ring-blue-500' : ''}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{getStatusIcon(caseData.status)}</span>
            <div>
              <h3 className="font-semibold text-lg">{caseData.id}</h3>
              <p className="text-gray-400">{caseData.name || 'Sin nombre'}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-sm">
            <div><p className="text-gray-500">Severidad</p><p>{getSeverityIcon(caseData.severity)} {caseData.severity?.toUpperCase()}</p></div>
            <div><p className="text-gray-500">Estado</p><span className={`inline-block px-2 py-1 rounded text-xs ${STATUS_COLORS[caseData.status?.toLowerCase()] || 'bg-gray-700'}`}>{caseData.status?.toUpperCase()}</span></div>
            <div><p className="text-gray-500">Asignado</p><p>{caseData.assigned_to || 'N/A'}</p></div>
            <div><p className="text-gray-500">Actualizado</p><p className="text-xs">{caseData.updated_at?.split('T')[0] || 'N/A'}</p></div>
          </div>
        </div>
        <div className="flex flex-col gap-2 ml-4">
          <div className="text-center"><p className="text-2xl font-bold text-blue-400">{caseData.iocs_count || 0}</p><p className="text-xs text-gray-500">IOCs</p></div>
          <div className="flex gap-1">
            <button onClick={(e) => { e.stopPropagation(); onViewGraph(); }} className="px-2 py-1 bg-purple-600 hover:bg-purple-700 rounded text-xs">📊</button>
            <button onClick={(e) => { e.stopPropagation(); onViewIOCs(); }} className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs">🎯</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CaseDetailPanel({ caseData, onClose, onViewGraph, onViewIOCs }) {
  const navigate = useNavigate();
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-700 sticky top-0 bg-gray-800">
          <h2 className="text-2xl font-semibold">{caseData.id}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-700/30 p-4 rounded-lg"><p className="text-gray-500 text-sm">Severidad</p><p className="text-xl font-bold mt-1">{caseData.severity}</p></div>
            <div className="bg-gray-700/30 p-4 rounded-lg"><p className="text-gray-500 text-sm">Estado</p><p className="text-xl font-bold mt-1">{caseData.status}</p></div>
            <div className="bg-gray-700/30 p-4 rounded-lg"><p className="text-gray-500 text-sm">IOCs</p><p className="text-xl font-bold text-blue-400 mt-1">{caseData.iocs_count || 0}</p></div>
            <div className="bg-gray-700/30 p-4 rounded-lg"><p className="text-gray-500 text-sm">Evidencias</p><p className="text-xl font-bold text-green-400 mt-1">{caseData.evidence_count || 0}</p></div>
          </div>
          <Card title="📝 Descripción"><p className="text-gray-300">{caseData.description || 'Sin descripción'}</p></Card>
          <Card title="⚡ Acciones">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Button variant="primary" onClick={() => { navigate('/active-investigation', { state: { caseId: caseData.id } }); onClose(); }}>🎯 Investigar</Button>
              <Button variant="secondary" onClick={onViewGraph}>📊 Grafo</Button>
              <Button variant="secondary" onClick={onViewIOCs}>⚡ IOCs</Button>
              <Button variant="secondary" onClick={() => toast.info('Generando reporte...')}>📄 Reporte</Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function NewCaseModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({ name: '', description: '', severity: 'medium', case_type: 'general' });
  const [creating, setCreating] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) { toast.error('Nombre requerido'); return; }
    setCreating(true);
    try { await onCreate(formData); } finally { setCreating(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-semibold">➕ Nueva Investigación</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">×</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div><label className="block text-sm text-gray-400 mb-1">Nombre *</label><input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="input-base w-full" required /></div>
          <div><label className="block text-sm text-gray-400 mb-1">Descripción</label><textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="input-base w-full h-24" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm text-gray-400 mb-1">Severidad</label><select value={formData.severity} onChange={(e) => setFormData({ ...formData, severity: e.target.value })} className="input-base w-full"><option value="critical">🔴 Crítica</option><option value="high">🟠 Alta</option><option value="medium">🟡 Media</option><option value="low">🟢 Baja</option></select></div>
            <div><label className="block text-sm text-gray-400 mb-1">Tipo</label><select value={formData.case_type} onChange={(e) => setFormData({ ...formData, case_type: e.target.value })} className="input-base w-full"><option value="m365_compromise">M365</option><option value="endpoint_threat">Endpoint</option><option value="phishing">Phishing</option><option value="malware">Malware</option><option value="general">General</option></select></div>
          </div>
          <div className="flex gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onClose} className="flex-1">Cancelar</Button>
            <Button type="submit" variant="primary" className="flex-1" disabled={creating}>{creating ? '⏳...' : '✅ Crear'}</Button>
          </div>
        </form>
      </div>
    </div>
  );
}
