/**
 * Threat Hunting Page - v4.4
 * Ejecuta queries de hunting contra M365, endpoints y SIEM
 * 
 * v4.4: Integración con CaseContext - case_id obligatorio
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Crosshair, Play, Search, Filter, Shield, AlertTriangle, 
  Clock, ChevronRight, Database, Terminal, FileCode, Brain,
  RefreshCw, Save, Trash2, Eye, BarChart3
} from 'lucide-react';
import api from '../../services/api';
import { useCaseContext } from '../../context/CaseContext';
import CaseHeader from '../CaseHeader';

// Mapeo de severidad a colores
const severityColors = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/50',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  info: 'bg-gray-500/20 text-gray-400 border-gray-500/50'
};

// Iconos por tipo de query
const queryTypeIcons = {
  kql: Database,
  osquery: Terminal,
  sigma: FileCode,
  yara: Shield,
  graph: BarChart3
};

const ThreatHuntingPage = () => {
  // v4.4: Usar contexto de caso
  const { currentCase, hasActiveCase, getCaseId, registerActivity } = useCaseContext();
  
  const [queries, setQueries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedQuery, setSelectedQuery] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCustomQuery, setShowCustomQuery] = useState(false);
  const [customQuery, setCustomQuery] = useState({
    name: '',
    query_type: 'kql',
    query: '',
    case_id: ''  // v4.4: Se llenará del contexto
  });

  // v4.4: Actualizar case_id en customQuery cuando cambie el caso
  useEffect(() => {
    if (currentCase) {
      setCustomQuery(prev => ({ ...prev, case_id: currentCase.case_id }));
    }
  }, [currentCase]);

  // Cargar queries disponibles
  const loadQueries = useCallback(async () => {
    try {
      setLoading(true);
      const [queriesRes, categoriesRes] = await Promise.all([
        api.get('/hunting/queries'),
        api.get('/hunting/categories')
      ]);
      setQueries(queriesRes.data.queries || []);
      setCategories(categoriesRes.data.categories || {});
    } catch (error) {
      console.error('Error loading queries:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueries();
  }, [loadQueries]);

  // Ejecutar hunt - v4.4: Usa case_id del contexto
  const executeHunt = async (queryId) => {
    // v4.4: Validar caso activo
    if (!hasActiveCase()) {
      console.error('❌ No active case selected');
      return;
    }
    
    try {
      setExecuting(true);
      setResults(null);
      
      // v4.4: Registrar actividad
      registerActivity('hunt_executed', { query_id: queryId });
      
      const response = await api.post('/hunting/execute', {
        hunt_id: queryId,
        case_id: getCaseId(),  // v4.4: Usar case_id del contexto
        use_llm_analysis: true
      });
      
      setResults({
        status: 'queued',
        message: response.data.message,
        execution_id: response.data.execution_id
      });
      
      // Poll for results - v4.4: Usa case_id del contexto
      setTimeout(async () => {
        try {
          const resultsRes = await api.get(`/hunting/results/${getCaseId()}`);
          if (resultsRes.data.results?.length > 0) {
            setResults(resultsRes.data.results[0]);
          }
        } catch (e) {
          console.error('Error fetching results:', e);
        }
      }, 3000);
      
    } catch (error) {
      console.error('Error executing hunt:', error);
      setResults({ status: 'error', error: error.message });
    } finally {
      setExecuting(false);
    }
  };

  // Ejecutar query personalizada - v4.4: Usa case_id del contexto
  const executeCustomHunt = async () => {
    if (!customQuery.name || !customQuery.query) return;
    
    // v4.4: Validar caso activo
    if (!hasActiveCase()) {
      console.error('❌ No active case selected');
      return;
    }
    
    try {
      setExecuting(true);
      
      // v4.4: Registrar actividad
      registerActivity('custom_hunt_executed', { query_name: customQuery.name });
      
      const response = await api.post('/hunting/execute/custom', {
        ...customQuery,
        case_id: getCaseId()  // v4.4: Asegurar case_id del contexto
      });
      setResults({
        status: 'queued',
        message: `Custom hunt '${customQuery.name}' iniciado`,
        execution_id: response.data.execution_id
      });
    } catch (error) {
      console.error('Error executing custom hunt:', error);
      setResults({ status: 'error', error: error.message });
    } finally {
      setExecuting(false);
    }
  };

  // Filtrar queries
  const filteredQueries = queries.filter(q => {
    const matchesSearch = q.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          q.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !selectedCategory || q.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* v4.4: Case Header con selector */}
      <CaseHeader 
        title="Threat Hunting"
        subtitle={`${queries.length} queries disponibles • MITRE ATT&CK Coverage`}
        icon="🎯"
      />
      
      {/* v4.4: Solo mostrar contenido si hay caso activo */}
      {!hasActiveCase() ? (
        <div className="flex items-center justify-center h-64 text-gray-500">
          Selecciona un caso para iniciar Threat Hunting
        </div>
      ) : (
      <>
      {/* Header (original, ahora dentro del conditional) */}
      <div className="flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Crosshair className="w-8 h-8 text-purple-500" />
          <div>
            <h1 className="text-2xl font-bold text-white">Threat Hunting</h1>
            <p className="text-gray-400 text-sm">
              Caso: <span className="text-blue-400">{getCaseId()}</span> • {queries.length} queries
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCustomQuery(!showCustomQuery)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
          >
            <Terminal className="w-4 h-4" />
            Query Personalizada
          </button>
          <button
            onClick={loadQueries}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refrescar
          </button>
        </div>
      </div>

      {/* Custom Query Panel */}
      {showCustomQuery && (
        <div className="bg-gray-800 rounded-lg p-6 border border-purple-500/30">
          <h3 className="text-lg font-semibold text-white mb-4">Query Personalizada</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Nombre</label>
              <input
                type="text"
                value={customQuery.name}
                onChange={(e) => setCustomQuery({...customQuery, name: e.target.value})}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                placeholder="Nombre de la query"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Tipo</label>
              <select
                value={customQuery.query_type}
                onChange={(e) => setCustomQuery({...customQuery, query_type: e.target.value})}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              >
                <option value="kql">KQL (Azure Sentinel)</option>
                <option value="osquery">OSQuery</option>
                <option value="sigma">Sigma Rule</option>
                <option value="yara">YARA</option>
              </select>
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-sm text-gray-400 mb-1">Query</label>
            <textarea
              value={customQuery.query}
              onChange={(e) => setCustomQuery({...customQuery, query: e.target.value})}
              className="w-full h-32 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white font-mono text-sm"
              placeholder="Escribe tu query aquí..."
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={executeCustomHunt}
              disabled={executing || !customQuery.name || !customQuery.query}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              <Play className="w-4 h-4" />
              Ejecutar
            </button>
            <button
              onClick={() => setShowCustomQuery(false)}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Filters & Search */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar queries..."
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-2 rounded-lg transition-colors ${
              !selectedCategory ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Todas
          </button>
          {Object.keys(categories).slice(0, 5).map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
              className={`px-3 py-2 rounded-lg transition-colors capitalize ${
                selectedCategory === cat ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {cat.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Queries List */}
        <div className="col-span-2 space-y-3">
          {filteredQueries.map((query) => {
            const IconComponent = queryTypeIcons[query.query_type] || Database;
            return (
              <div
                key={query.id}
                onClick={() => setSelectedQuery(query)}
                className={`bg-gray-800 rounded-lg p-4 cursor-pointer border transition-all ${
                  selectedQuery?.id === query.id 
                    ? 'border-purple-500 ring-1 ring-purple-500' 
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-gray-700 rounded-lg">
                      <IconComponent className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{query.name}</h3>
                      <p className="text-sm text-gray-400 mt-1">{query.description}</p>
                      <div className="flex gap-2 mt-2">
                        <span className={`px-2 py-0.5 text-xs rounded border ${severityColors[query.severity]}`}>
                          {query.severity}
                        </span>
                        <span className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded">
                          {query.query_type?.toUpperCase()}
                        </span>
                        {query.mitre?.map(t => (
                          <span key={t} className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      executeHunt(query.id);
                    }}
                    disabled={executing}
                    className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded-lg text-sm transition-colors"
                  >
                    {executing && selectedQuery?.id === query.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Ejecutar
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Results Panel */}
        <div className="space-y-4">
          {/* Query Details */}
          {selectedQuery && (
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <h3 className="font-semibold text-white mb-3">Detalles de Query</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Categoría:</span>
                  <span className="text-white capitalize">{selectedQuery.category?.replace('_', ' ')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Tipo:</span>
                  <span className="text-white">{selectedQuery.query_type?.toUpperCase()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Severidad:</span>
                  <span className={`px-2 py-0.5 rounded ${severityColors[selectedQuery.severity]}`}>
                    {selectedQuery.severity}
                  </span>
                </div>
                {selectedQuery.mitre?.length > 0 && (
                  <div>
                    <span className="text-gray-400">MITRE ATT&CK:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedQuery.mitre.map(t => (
                        <span key={t} className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Execution Results */}
          {results && (
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                {results.status === 'queued' && <Clock className="w-4 h-4 text-yellow-400" />}
                {results.status === 'completed' && <Shield className="w-4 h-4 text-green-400" />}
                {results.status === 'error' && <AlertTriangle className="w-4 h-4 text-red-400" />}
                Resultados
              </h3>
              
              {results.status === 'queued' && (
                <div className="flex items-center gap-2 text-yellow-400">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>{results.message}</span>
                </div>
              )}
              
              {results.status === 'error' && (
                <div className="text-red-400">{results.error}</div>
              )}
              
              {results.total_hits !== undefined && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Hits encontrados:</span>
                    <span className="text-white font-bold">{results.total_hits}</span>
                  </div>
                  {results.llm_analysis && (
                    <div className="mt-3 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                      <div className="flex items-center gap-2 text-purple-400 mb-2">
                        <Brain className="w-4 h-4" />
                        <span className="text-sm font-medium">Análisis LLM</span>
                      </div>
                      <p className="text-sm text-gray-300">{results.llm_analysis.analysis}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* MITRE Coverage */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="font-semibold text-white mb-3">Cobertura MITRE</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {['initial_access', 'persistence', 'privilege_escalation', 'defense_evasion', 
                'credential_access', 'lateral_movement', 'exfiltration', 'command_control'].map(tactic => (
                <div key={tactic} className="flex items-center gap-2 p-2 bg-gray-700 rounded">
                  <div className={`w-2 h-2 rounded-full ${
                    Object.values(categories).some(c => c.queries?.includes(tactic)) 
                      ? 'bg-green-400' 
                      : 'bg-gray-500'
                  }`} />
                  <span className="text-gray-300 capitalize">{tactic.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      </>
      )}
    </div>
  );
};

export default ThreatHuntingPage;
