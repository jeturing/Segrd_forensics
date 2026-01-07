import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import api, { API_BASE_URL } from '../../services/api';
import ConfigurationPanel from '../Maintenance/ConfigurationPanel';

// ============================================================================
// COMPONENTES COMUNES
// ============================================================================

const Card = ({ title, children, className = '', actions }) => (
  <div className={`bg-gray-800 rounded-xl border border-gray-700 shadow-lg ${className}`}>
    {title && (
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100">{title}</h3>
        {actions && <div className="flex gap-2">{actions}</div>}
      </div>
    )}
    <div className="p-6">{children}</div>
  </div>
);

const Badge = ({ color = 'gray', children }) => {
  const colors = {
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${colors[color]}`}>
      {children}
    </span>
  );
};

const Loading = ({ message = 'Cargando...' }) => (
  <div className="flex flex-col items-center justify-center py-12">
    <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
    <p className="text-gray-400">{message}</p>
  </div>
);

const Tabs = ({ tabs, activeTab, onChange }) => (
  <div className="flex border-b border-gray-700 mb-6 overflow-x-auto">
    {tabs.map((tab) => (
      <button
        key={tab.id}
        onClick={() => onChange(tab.id)}
        className={`px-6 py-3 text-sm font-medium whitespace-nowrap transition-all ${
          activeTab === tab.id
            ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/10'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
        }`}
      >
        <span className="mr-2">{tab.icon}</span>
        {tab.label}
      </button>
    ))}
  </div>
);

const EditProviderModal = ({ provider, containers = [], onClose, onSave }) => {
  const [config, setConfig] = useState({
    base_url: provider.base_url || '',
    api_key: provider.api_key || '',
    enabled: provider.enabled !== false
  });
  const [pullModelName, setPullModelName] = useState('');
  const [pullAsRoot, setPullAsRoot] = useState(false);
  const [selectedContainerId, setSelectedContainerId] = useState('');
  const [containerModels, setContainerModels] = useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(provider.type, config);
  };

  // Fetch models when container is selected
  useEffect(() => {
    if (selectedContainerId) {
      const fetchModels = async () => {
        try {
          const res = await api.get(`/api/v41/docker/containers/${selectedContainerId}/models`);
          setContainerModels(res.data || []);
        } catch (e) {
          console.error("Error fetching container models", e);
        }
      };
      fetchModels();
    } else {
      setContainerModels([]);
    }
  }, [selectedContainerId]);

  const handlePullModel = async () => {
      if (!pullModelName) return toast.error("Nombre de modelo requerido");
      // Use selected container or try to find one
      const containerId = selectedContainerId || containers.find(c => c.image.includes('ollama'))?.id;
      
      if (!containerId) return toast.error("Seleccione un contenedor o asegúrese de que hay uno de Ollama activo");

      try {
          await api.post(`/api/v41/docker/containers/${containerId}/pull`, {
              model_name: pullModelName,
              as_root: pullAsRoot
          });
          toast.success(`Iniciando descarga de ${pullModelName}...`);
          setPullModelName('');
      } catch(e) {
          console.error(e);
          toast.error("Error al iniciar descarga");
      }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 w-full max-w-md shadow-2xl">
        <h3 className="text-xl font-semibold mb-4 text-gray-100">Configurar {provider.name}</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          
          {/* Container Selection */}
          {(provider.type === 'local' || provider.type === 'ollama') && containers.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Seleccionar Contenedor Docker</label>
              <select
                value={selectedContainerId}
                onChange={(e) => {
                  const cid = e.target.value;
                  setSelectedContainerId(cid);
                  const container = containers.find(c => c.id === cid);
                  if (container) {
                    // Try to guess port from ports string "0.0.0.0:11434->11434/tcp"
                    const portMatch = container.ports.match(/:(\d+)->/);
                    const port = portMatch ? portMatch[1] : '11434';
                    setConfig({...config, base_url: `http://localhost:${port}`});
                  }
                }}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none text-sm"
              >
                <option value="">-- Seleccionar contenedor --</option>
                {containers.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.image})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Base URL</label>
            <input
              type="text"
              value={config.base_url}
              onChange={e => setConfig({...config, base_url: e.target.value})}
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              placeholder="http://localhost:1234/v1"
            />
          </div>
          {provider.has_api_key && (
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">API Key</label>
              <input
                type="password"
                value={config.api_key}
                onChange={e => setConfig({...config, api_key: e.target.value})}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
                placeholder="sk-..."
              />
            </div>
          )}
          
          {/* Pull Model Section */}
          {(provider.type === 'local' || provider.type === 'ollama') && (
             <div className="border-t border-gray-700 pt-4 mt-2">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Inicializar Modelo (Docker)</h4>
                
                {/* Available Models List */}
                {containerModels.length > 0 && (
                  <div className="mb-3">
                    <label className="block text-xs text-gray-400 mb-1">Modelos disponibles en contenedor:</label>
                    <div className="flex flex-wrap gap-2">
                      {containerModels.map(model => (
                        <span 
                          key={model} 
                          onClick={() => setPullModelName(model)}
                          className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-200 cursor-pointer border border-gray-600"
                        >
                          {model}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                   <input 
                     type="text" 
                     value={pullModelName}
                     onChange={e => setPullModelName(e.target.value)}
                     placeholder="Nombre del modelo (ej: phi4)"
                     className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
                   />
                   <div className="flex items-center justify-between">
                       <div className="flex items-center gap-2">
                          <input 
                            type="checkbox" 
                            id="as-root" 
                            checked={pullAsRoot}
                            onChange={e => setPullAsRoot(e.target.checked)}
                            className="rounded bg-gray-900 border-gray-700 text-blue-500"
                          />
                          <label htmlFor="as-root" className="text-xs text-gray-400">Inicializar como Root</label>
                       </div>
                       <button 
                         type="button"
                         onClick={handlePullModel}
                         className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-xs text-white transition-colors"
                       >
                         Descargar / Inicializar
                       </button>
                   </div>
                </div>
             </div>
          )}

          <div className="flex items-center gap-2 mt-4">
            <input
              type="checkbox"
              checked={config.enabled}
              onChange={e => setConfig({...config, enabled: e.target.checked})}
              id="enabled"
              className="rounded bg-gray-900 border-gray-700 text-blue-500 focus:ring-blue-500"
            />
            <label htmlFor="enabled" className="text-gray-300">Habilitado</label>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button type="button" onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors">Cancelar</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors">Guardar</button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================================================
// COMPONENTE PRINCIPAL: MAINTENANCE PANEL
// ============================================================================

export default function MaintenancePanel() {
  const [activeTab, setActiveTab] = useState('llm');
  const [loading, setLoading] = useState(true);
  
  // Estados para LLM
  const [llmStatus, setLlmStatus] = useState(null);
  const [llmHealth, setLlmHealth] = useState(null);
  const [llmStats, setLlmStats] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);
  const [activeModelId, setActiveModelId] = useState(null);
  const [loadingModels, setLoadingModels] = useState(false);
  const [editingProvider, setEditingProvider] = useState(null);
  const [containers, setContainers] = useState([]);
  
  // Estados para System
  const [systemInfo, setSystemInfo] = useState(null);
  
  // Estados para Tools
  const [toolsStatus, setToolsStatus] = useState(null);
  
  // Estados para Database
  const [dbStats, setDbStats] = useState(null);
  const [dbEnv, setDbEnv] = useState(null);
  const [dbCleaning, setDbCleaning] = useState(false);
  const [dbMode, setDbMode] = useState('sqlite');
  const [dbSwitching, setDbSwitching] = useState(false);
  const [dbMigrating, setDbMigrating] = useState(false);
  
  // Estado para Logs
  const [logLevel, setLogLevel] = useState('INFO');
  
  // Estados para Config
  const [config, setConfig] = useState({
    llm_provider: 'llm_studio',
    llm_studio_url: 'http://100.101.115.5:2714/v1/completions',
    max_tokens: 512,
    temperature: 0.4,
    timeout: 40,
    auto_fallback: true,
    debug_mode: false
  });

  const tabs = [
    { id: 'llm', label: 'LLM / IA', icon: '🧠' },
    { id: 'providers', label: 'Proveedores', icon: '🔌' },
    { id: 'models', label: 'Modelos', icon: '🤖' },
    { id: 'tools', label: 'Herramientas', icon: '🔧' },
    { id: 'apis', label: 'APIs & Keys', icon: '🔑' },
    { id: 'system', label: 'Sistema', icon: '⚙️' },
    { id: 'database', label: 'Base de Datos', icon: '💾' },
    { id: 'logs', label: 'Logs', icon: '📜' }
  ];

  // ============================================================================
  // CARGA DE DATOS
  // ============================================================================

  const loadLLMData = useCallback(async () => {
    try {
      const [statusRes, healthRes, modelsRes] = await Promise.all([
        api.get('/api/v41/llm/status').catch(() => ({ data: { data: null } })),
        api.get('/api/v41/llm/health').catch(() => ({ data: null })),
        api.get('/api/v41/llm/models').catch(() => ({ data: { models: [], active_model_id: null } }))
      ]);
      setLlmStatus(statusRes.data?.data);
      setLlmHealth(healthRes.data);
      setAvailableModels(modelsRes.data?.models || []);
      setActiveModelId(modelsRes.data?.active_model_id);
    } catch (error) {
      console.error('Error loading LLM data:', error);
    }
  }, []);

  const loadContainers = useCallback(async () => {
    try {
      const res = await api.get('/api/v41/docker/containers');
      setContainers(res.data);
    } catch (error) {
      console.error('Error loading containers:', error);
    }
  }, []);

  const loadSystemInfo = useCallback(async () => {
    try {
      const res = await api.get('/api/health').catch(() => ({ data: null }));
      setSystemInfo(res.data);
    } catch (error) {
      console.error('Error loading system info:', error);
    }
  }, []);

  const loadToolsStatus = useCallback(async () => {
    try {
      const res = await api.get('/api/v41/tools/status').catch(() => ({ 
        data: { tools: [] } 
      }));
      setToolsStatus(res.data);
    } catch (error) {
      console.error('Error loading tools status:', error);
    }
  }, []);

  const loadDatabaseStats = useCallback(async () => {
    try {
      const [statsRes, envRes, modeRes] = await Promise.all([
        api.get('/api/v41/system/db-stats'),
        api.get('/api/v41/system/environment'),
        api.get('/api/v41/system/db-mode').catch(() => ({ data: { mode: 'sqlite' } })),
      ]);
      setDbStats(statsRes.data);
      setDbEnv(envRes.data);
      if (modeRes?.data?.mode) setDbMode(modeRes.data.mode);
    } catch (error) {
      console.error('Error loading DB stats:', error);
      setDbStats(null);
    }
  }, []);

  const loadAllData = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      loadLLMData(),
      loadSystemInfo(),
      loadToolsStatus(),
      loadDatabaseStats(),
      loadContainers()
    ]);
    setLoading(false);
  }, [loadLLMData, loadSystemInfo, loadToolsStatus, loadDatabaseStats, loadContainers]);

  const optimizeDatabase = async () => {
    setDbCleaning(true);
    try {
      await api.post('/api/v41/system/db-clean', { confirm: true, optimize_only: true });
      toast.success('Vacuum ejecutado');
      await loadDatabaseStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo optimizar la BD');
    } finally {
      setDbCleaning(false);
    }
  };

  const resetDatabase = async () => {
    if (!window.confirm('⚠️ Esto eliminará datos de desarrollo en SQLite. ¿Continuar?')) return;
    setDbCleaning(true);
    try {
      await api.post('/api/v41/system/db-clean', { confirm: true });
      toast.success('BD limpiada (desarrollo)');
      await loadDatabaseStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo limpiar la BD');
    } finally {
      setDbCleaning(false);
    }
  };

  const changeDbMode = async (mode) => {
    setDbSwitching(true);
    try {
      const payload = { mode };
      if (mode === 'postgrest') {
        payload.postgrest_url = dbEnv?.postgrest_url || 'http://localhost:3000';
        payload.database_url = dbEnv?.database || 'postgresql://root:.@localhost:5433/forensics_db';
      }
      const res = await api.post('/api/v41/system/db-mode', payload);
      if (res.data?.success) {
        setDbMode(res.data.mode);
        toast.success(`Modo BD cambiado a ${res.data.mode}`);
        await loadDatabaseStats();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo cambiar el modo de BD');
    } finally {
      setDbSwitching(false);
    }
  };

  const migrateDb = async () => {
    if (!window.confirm('Migrar SQLite -> Postgres? Asegúrate de que Postgres/PostgREST estén corriendo.')) return;
    setDbMigrating(true);
    try {
      const res = await api.post('/api/v41/system/db-migrate', {
        target_url: dbEnv?.database || 'postgresql://root:.@localhost:5433/forensics_db'
      });
      if (res.data?.success) {
        toast.success('Migración completada');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error en migración');
    } finally {
      setDbMigrating(false);
    }
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 60000);
    return () => clearInterval(interval);
  }, [loadAllData]);

  // ============================================================================
  // ACCIONES LLM
  // ============================================================================

  const setActiveModel = async (modelId) => {
    try {
      const res = await api.post('/api/v41/llm/models/active', { model_id: modelId });
      if (res.data?.success) {
        toast.success(`Modelo activo: ${modelId}`);
        setActiveModelId(modelId);
        await loadLLMData();
      } else {
        toast.error('Error cambiando modelo');
      }
    } catch (error) {
      toast.error('Error cambiando modelo');
    }
  };

  const refreshModels = async () => {
    setLoadingModels(true);
    try {
      const res = await api.post('/api/v41/llm/refresh');
      if (res.data?.success) {
        toast.success(`${res.data.total_models} modelos detectados`);
        await loadLLMData();
      }
    } catch (error) {
      toast.error('Error refrescando modelos');
    } finally {
      setLoadingModels(false);
    }
  };

  const setProvider = async (provider) => {
    try {
      await api.post('/api/v41/llm/provider', {
        provider,
        reason: 'Cambio desde panel de mantenimiento'
      });
      toast.success(`Proveedor cambiado a ${provider}`);
      await loadLLMData();
    } catch (error) {
      toast.error('Error cambiando proveedor');
    }
  };

  const handleSaveProvider = async (type, config) => {
    try {
      await api.put(`/api/v41/llm/providers/${type}`, {
        ...config,
        provider_type: type
      });
      toast.success('Configuración guardada');
      setEditingProvider(null);
      await loadLLMData();
    } catch (error) {
      toast.error('Error guardando configuración');
    }
  };

  const testLLM = async () => {
    try {
      toast.info('Probando conexión LLM...');
      const res = await api.post('/api/v41/llm/test', {
        prompt: 'Test de conectividad: responde OK si funcionas correctamente.'
      });
      if (res.data?.success) {
        toast.success(`✅ ${res.data.model_used || 'LLM'} respondió en ${res.data.response_time_seconds}s`);
      } else {
        toast.warning('LLM respondió en modo offline');
      }
    } catch (error) {
      toast.error('Error en test LLM');
    }
  };

  const resetLLMStats = async () => {
    if (!window.confirm('¿Reiniciar estadísticas LLM?')) return;
    try {
      await api.post('/api/v41/llm/reset-stats');
      toast.success('Estadísticas reiniciadas');
      await loadLLMData();
    } catch (error) {
      toast.error('Error reiniciando estadísticas');
    }
  };

  const saveConfig = async () => {
    try {
      await api.post('/api/v41/system/config', config);
      toast.success('Configuración guardada');
    } catch (error) {
      toast.error('Error guardando configuración');
    }
  };

  // ============================================================================
  // RENDER TABS
  // ============================================================================

  const renderLLMTab = () => (
    <div className="space-y-6">
      {/* Estado General */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">Modelo Activo</div>
          <div className="text-lg font-bold text-blue-400 truncate" title={activeModelId || 'N/A'}>
            {activeModelId ? (
              <>🤖 {activeModelId.split('/').pop()}</>
            ) : (
              <span className="text-yellow-400">⚠️ Sin modelo</span>
            )}
          </div>
        </Card>

        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">Estado</div>
          <div className={`text-xl font-bold flex items-center gap-2 ${
            llmHealth?.healthy ? 'text-green-400' : 'text-yellow-400'
          }`}>
            {llmHealth?.healthy ? '🟢 Saludable' : '🟡 Degradado'}
          </div>
        </Card>

        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">Modelos Detectados</div>
          <div className="text-xl font-bold text-purple-400">
            {availableModels.length}
          </div>
        </Card>

        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">Errores</div>
          <div className="text-xl font-bold text-red-400">
            {Object.values(llmStats?.llm_statistics || {}).reduce((sum, s) => sum + (s?.errors || 0), 0)}
          </div>
        </Card>
      </div>

      {/* Acciones Rápidas */}
      <Card title="⚡ Acciones Rápidas">
        <div className="flex flex-wrap gap-3">
          <button
            onClick={testLLM}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition"
          >
            🧪 Test Conexión
          </button>
          <button
            onClick={resetLLMStats}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm font-medium transition"
          >
            📊 Reset Stats
          </button>
          <button
            onClick={loadLLMData}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm font-medium transition"
          >
            🔄 Actualizar
          </button>
        </div>
      </Card>

      {/* Estadísticas por Proveedor */}
      <Card title="📈 Estadísticas por Proveedor">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Proveedor</th>
                <th className="pb-3 font-medium">Requests</th>
                <th className="pb-3 font-medium">Errores</th>
                <th className="pb-3 font-medium">Latencia Prom.</th>
                <th className="pb-3 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {Object.entries(llmStats?.llm_statistics || {}).map(([provider, stats]) => (
                <tr key={provider} className="border-b border-gray-700/50">
                  <td className="py-3 font-medium">
                    {provider === 'llm_studio' && '☁️ LLM Studio'}
                    {provider === 'phi4_local' && '💻 Phi-4 Local'}
                    {provider === 'offline' && '📋 Offline'}
                  </td>
                  <td className="py-3">{stats?.requests || 0}</td>
                  <td className="py-3 text-red-400">{stats?.errors || 0}</td>
                  <td className="py-3">{(stats?.avg_latency || 0).toFixed(2)}s</td>
                  <td className="py-3">
                    <Badge color={llmHealth?.providers?.[provider]?.status === 'healthy' ? 'green' : 'yellow'}>
                      {llmHealth?.providers?.[provider]?.status || 'unknown'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );

  const renderProvidersTab = () => (
    <div className="space-y-6">
      <Card title="🔌 Proveedores Disponibles">
        <div className="space-y-4">
          {/* LLM Studio */}
          <div className={`p-4 rounded-lg border-2 transition ${
            llmStatus?.active_provider === 'lm_studio' 
              ? 'border-blue-500 bg-blue-500/10' 
              : 'border-gray-700 hover:border-gray-600'
          }`}>
            <div className="flex items-center justify-between cursor-pointer" onClick={() => setProvider('lm_studio')}>
              <div className="flex items-center gap-3">
                <span className="text-3xl">☁️</span>
                <div>
                  <h4 className="font-semibold text-gray-100">LLM Studio (Jeturing AI)</h4>
                  <p className="text-sm text-gray-400">Proveedor principal - API OpenAI compatible</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge color={llmHealth?.providers?.lm_studio?.status === 'healthy' ? 'green' : 'yellow'}>
                  {llmHealth?.providers?.lm_studio?.status || 'checking'}
                </Badge>
                {llmStatus?.active_provider === 'lm_studio' && (
                  <Badge color="blue">ACTIVO</Badge>
                )}
              </div>
            </div>
            <div className="mt-3 flex justify-between items-center">
              <div className="text-xs text-gray-500">
                URL: {config.llm_studio_url || 'http://localhost:1234/v1'}
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); setEditingProvider({ type: 'lm_studio', name: 'LLM Studio', base_url: config.llm_studio_url }); }}
                className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded text-gray-300 transition-colors"
              >
                ⚙️ Configurar
              </button>
            </div>
          </div>

          {/* Phi-4 Local (mapped to 'local') */}
          <div className={`p-4 rounded-lg border-2 transition ${
            llmStatus?.active_provider === 'local' 
              ? 'border-green-500 bg-green-500/10' 
              : 'border-gray-700 hover:border-gray-600'
          }`}>
            <div className="flex items-center justify-between cursor-pointer" onClick={() => setProvider('local')}>
              <div className="flex items-center gap-3">
                <span className="text-3xl">💻</span>
                <div>
                  <h4 className="font-semibold text-gray-100">Phi-4 Local</h4>
                  <p className="text-sm text-gray-400">Motor local - Fallback automático</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge color="green">available</Badge>
                {llmStatus?.active_provider === 'local' && (
                  <Badge color="blue">ACTIVO</Badge>
                )}
              </div>
            </div>
             <div className="mt-3 flex justify-between items-center">
              <div className="text-xs text-gray-500">
                 {/* Local provider might not have URL exposed in config object directly, need to check */}
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); setEditingProvider({ type: 'local', name: 'Phi-4 Local' }); }}
                className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded text-gray-300 transition-colors"
              >
                ⚙️ Configurar
              </button>
            </div>
          </div>

          {/* Offline */}
          <div className={`p-4 rounded-lg border-2 transition cursor-pointer ${
            llmStatus?.active_provider === 'offline' 
              ? 'border-purple-500 bg-purple-500/10' 
              : 'border-gray-700 hover:border-gray-600'
          }`}
          onClick={() => setProvider('offline')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-3xl">📋</span>
                <div>
                  <h4 className="font-semibold text-gray-100">Modo Offline</h4>
                  <p className="text-sm text-gray-400">Reglas estáticas - Sin IA</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge color="green">available</Badge>
                {llmStatus?.active_provider === 'offline' && (
                  <Badge color="blue">ACTIVO</Badge>
                )}
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );

  const renderModelsTab = () => (
    <div className="space-y-6">
      {/* Modelo Activo */}
      <Card title="🎯 Modelo Activo" actions={
        <button
          onClick={refreshModels}
          disabled={loadingModels}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
        >
          {loadingModels ? '⏳ Detectando...' : '🔄 Refrescar Modelos'}
        </button>
      }>
        {activeModelId ? (
          <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-lg border border-blue-500/30">
            <span className="text-3xl">🤖</span>
            <div>
              <div className="text-lg font-bold text-blue-400">{activeModelId}</div>
              <div className="text-sm text-gray-400">
                Proveedor: {llmStatus?.active_model?.provider || 'lm_studio'} • 
                Cargado: {llmStatus?.active_model?.loaded ? '✅ Sí' : '⏳ No'}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <div className="flex items-center gap-2 text-yellow-400">
              <span>⚠️</span>
              <span>No hay modelo activo. Carga un modelo en LM Studio u Ollama.</span>
            </div>
          </div>
        )}
      </Card>

      {/* Lista de Modelos Disponibles */}
      <Card title={`📦 Modelos Disponibles (${availableModels.length})`}>
        {availableModels.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {availableModels.map((model) => (
              <div 
                key={model.id} 
                className={`flex items-center justify-between p-3 rounded-lg transition cursor-pointer ${
                  model.id === activeModelId 
                    ? 'bg-blue-600/20 border border-blue-500/50' 
                    : 'bg-gray-700/50 hover:bg-gray-700 border border-transparent'
                }`}
                onClick={() => model.id !== activeModelId && setActiveModel(model.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">
                    {model.name?.includes('phi') ? '🧠' : 
                     model.name?.includes('llama') ? '🦙' : 
                     model.name?.includes('qwen') ? '💎' : 
                     model.name?.includes('deepseek') ? '🌊' : 
                     model.name?.includes('mistral') ? '🌪️' : '🤖'}
                  </span>
                  <div>
                    <div className="font-medium text-gray-200">{model.name || model.id}</div>
                    <div className="text-xs text-gray-400">
                      {model.provider} • Context: {model.context_length || 4096}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {model.loaded && <Badge color="green">Cargado</Badge>}
                  {model.id === activeModelId && <Badge color="blue">Activo</Badge>}
                  {model.id !== activeModelId && (
                    <button 
                      onClick={(e) => { e.stopPropagation(); setActiveModel(model.id); }}
                      className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-500 rounded transition"
                    >
                      Usar
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            <div className="text-4xl mb-3">📭</div>
            <p>No se detectaron modelos.</p>
            <p className="text-sm">Asegúrate de que LM Studio u Ollama estén corriendo.</p>
            <button
              onClick={refreshModels}
              className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
            >
              🔄 Buscar Modelos
            </button>
          </div>
        )}
      </Card>

      {/* Configuración de Generación */}
      <Card title="⚙️ Parámetros de Generación">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Max Tokens</label>
            <input
              type="number"
              value={config.max_tokens}
              onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Temperature</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={config.temperature}
              onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Timeout (segundos)</label>
            <input
              type="number"
              value={config.timeout}
              onChange={(e) => setConfig({ ...config, timeout: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm"
            />
          </div>
        </div>

        <div className="mt-4">
          <button
            onClick={saveConfig}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition"
          >
            💾 Guardar Parámetros
          </button>
        </div>
      </Card>
    </div>
  );

  const renderToolsTab = () => (
    <div className="space-y-6">
      <Card title="🔧 Estado de Herramientas Forenses">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { name: 'Sparrow', icon: '🦅', status: 'installed', version: '1.2.0' },
            { name: 'Hawk', icon: '🦅', status: 'installed', version: '2.1.0' },
            { name: 'O365 Extractor', icon: '📦', status: 'installed', version: '1.0.0' },
            { name: 'Loki', icon: '🔍', status: 'installed', version: '0.50.0' },
            { name: 'YARA Rules', icon: '📋', status: 'installed', version: 'latest' },
            { name: 'ROADtools', icon: '🛣️', status: 'not_installed', version: '-' },
            { name: 'AADInternals', icon: '🔐', status: 'installed', version: '0.9.0' },
            { name: 'Monkey365', icon: '🐒', status: 'not_installed', version: '-' },
            { name: 'Volatility', icon: '💾', status: 'installed', version: '3.0' }
          ].map((tool) => (
            <div key={tool.name} className="p-4 bg-gray-700/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{tool.icon}</span>
                  <span className="font-medium text-gray-200">{tool.name}</span>
                </div>
                <Badge color={tool.status === 'installed' ? 'green' : 'gray'}>
                  {tool.status === 'installed' ? 'OK' : 'N/A'}
                </Badge>
              </div>
              <div className="text-xs text-gray-400">v{tool.version}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="📥 Instalar Herramientas">
        <div className="flex flex-wrap gap-3">
          <button className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium transition">
            🔄 Actualizar Todas
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition">
            📥 Instalar ROADtools
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition">
            📥 Instalar Monkey365
          </button>
        </div>
      </Card>
    </div>
  );

  const renderSystemTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">API Status</div>
          <div className="text-xl font-bold text-green-400">🟢 Online</div>
        </Card>
        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">Versión</div>
          <div className="text-xl font-bold text-blue-400">{systemInfo?.version || 'v4.5.0'}</div>
        </Card>
        <Card className="!p-4">
          <div className="text-sm text-gray-400 mb-1">Uptime</div>
          <div className="text-xl font-bold text-purple-400">
            {systemInfo?.uptime || '...'} 
          </div>
        </Card>
      </div>

      <Card title="📊 Información del Sistema">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Sistema Operativo</span>
              <span className="text-gray-200">Kali Linux</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Python</span>
              <span className="text-gray-200">3.11.x</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">FastAPI</span>
              <span className="text-gray-200">0.104.x</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Base de Datos</span>
              <span className="text-gray-200">{dbEnv?.engine || 'SQLite'}</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Puerto API</span>
              <span className="text-gray-200">{dbEnv?.api_port || (() => {
                try {
                  return new URL(API_BASE_URL).port || '9000';
                } catch {
                  return '9000';
                }
              })()}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Puerto Frontend</span>
              <span className="text-gray-200">{window.location.port || '3000'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Modo</span>
              <span className="text-gray-200">{dbEnv?.mode || 'Desarrollo'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-700">
              <span className="text-gray-400">Evidence Path</span>
              <span className="text-gray-200 text-xs">{dbEnv?.evidence_dir || '~/forensics-evidence'}</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );

  const renderDatabaseTab = () => (
    <div className="space-y-6">
      <Card title="💾 Estadísticas de Base de Datos">
        {dbStats?.database && (
          <div className="text-sm text-gray-400 mb-3">
            Motor: {dbEnv?.engine || 'sqlite'} • Archivo: {dbStats.database} • Tamaño: {(((dbStats?.size_bytes || 0) / 1024)).toFixed(1)} KB
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Tabla</th>
                <th className="pb-3 font-medium">Registros</th>
                <th className="pb-3 font-medium">Fuente</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {(dbStats?.tables || []).map((table) => (
                <tr key={table.name} className="border-b border-gray-700/50">
                  <td className="py-3 font-mono text-blue-400">{table.name}</td>
                  <td className="py-3">{table.rows}</td>
                  <td className="py-3 text-gray-500">sqlite://{dbStats?.database || 'forensics.db'}</td>
                </tr>
              ))}
              {(!dbStats?.tables || dbStats?.tables.length === 0) && (
                <tr>
                  <td className="py-3 text-gray-400" colSpan={3}>Sin datos de tablas</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="🔧 Acciones de Mantenimiento">
        <div className="flex flex-wrap gap-3">
          <button
            onClick={optimizeDatabase}
            disabled={dbCleaning}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            🔄 Optimizar (VACUUM)
          </button>
          <button
            onClick={() => changeDbMode('sqlite')}
            disabled={dbSwitching || dbMode === 'sqlite'}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            🗄️ Usar SQLite local
          </button>
          <button
            onClick={() => changeDbMode('postgrest')}
            disabled={dbSwitching || dbMode === 'postgrest'}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            🌐 Usar PostgREST (PG)
          </button>
          <button
            onClick={migrateDb}
            disabled={dbMigrating}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            🚚 Migrar SQLite → PG
          </button>
          <button
            onClick={resetDatabase}
            disabled={dbCleaning}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            ⚠️ Reset (Dev Only)
          </button>
        </div>
      </Card>
    </div>
  );

  const renderLogsTab = () => (
    <div className="space-y-6">
      <Card title="📜 Logs del Sistema" actions={
        <button className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          🔄 Actualizar
        </button>
      }>
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-xs text-gray-300 h-96 overflow-y-auto">
          <div className="text-green-400">[2025-12-07 10:30:15] ✅ LLM Provider Manager initialized - Active: llm_studio</div>
          <div className="text-blue-400">[2025-12-07 10:30:16] 🧠 SOAR Intelligence Engine started</div>
          <div className="text-blue-400">[2025-12-07 10:30:17] ⚡ AgentQueue initialized (max: 10)</div>
          <div className="text-gray-400">[2025-12-07 10:31:00] 📡 Health check: all systems operational</div>
          <div className="text-yellow-400">[2025-12-07 10:32:45] ⏱️ LLM Studio latency: 1.2s</div>
          <div className="text-green-400">[2025-12-07 10:33:00] ✅ M365 Analysis completed for IR-2025-001</div>
          <div className="text-gray-400">[2025-12-07 10:35:00] 📊 Stats update: 45 requests, 2 errors</div>
          <div className="text-blue-400">[2025-12-07 10:36:12] 🔄 Provider switched to phi4_local</div>
          <div className="text-green-400">[2025-12-07 10:36:15] ✅ Fallback successful</div>
          <div className="text-gray-400">[2025-12-07 10:40:00] 📡 Health check: all systems operational</div>
        </div>
      </Card>

      <Card title="⚙️ Configuración de Logs">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Nivel de Log</label>
            <select
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm"
           >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Retención (días)</label>
            <input
              type="number"
              defaultValue={30}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Tamaño máximo (MB)</label>
            <input
              type="number"
              defaultValue={100}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 text-sm"
            />
          </div>
        </div>
      </Card>
    </div>
  );

  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 p-6">
        <Loading message="Cargando panel de mantenimiento..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-3">
            <span className="text-3xl">🛠️</span>
            Panel de Mantenimiento
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Gestión de LLM, proveedores, modelos, herramientas y sistema v4.5
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadAllData}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition flex items-center gap-2"
          >
            🔄 Actualizar Todo
          </button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Content */}
      <div className="animate-fadeIn">
        {activeTab === 'llm' && renderLLMTab()}
        {activeTab === 'providers' && renderProvidersTab()}
        {activeTab === 'models' && renderModelsTab()}
        {activeTab === 'tools' && renderToolsTab()}
        {activeTab === 'apis' && <ConfigurationPanel />}
        {activeTab === 'system' && renderSystemTab()}
        {activeTab === 'database' && renderDatabaseTab()}
        {activeTab === 'logs' && renderLogsTab()}
      </div>

      {/* Modals */}
      {editingProvider && (
        <EditProviderModal
          provider={editingProvider}
          containers={containers}
          onClose={() => setEditingProvider(null)}
          onSave={handleSaveProvider}
        />
      )}
    </div>
  );
}
