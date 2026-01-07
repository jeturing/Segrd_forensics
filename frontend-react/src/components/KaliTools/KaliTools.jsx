/**
 * KaliTools - Panel de herramientas de seguridad de Kali Linux
 * Permite explorar, configurar y ejecutar herramientas organizadas por categoría
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  MagnifyingGlassIcon,
  PlayIcon,
  StopIcon,
  DocumentDuplicateIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  CommandLineIcon,
  ClockIcon,
  Cog6ToothIcon,
  BoltIcon,
  ShieldExclamationIcon,
  ArrowPathIcon,
  InformationCircleIcon,
  WifiIcon,
  SparklesIcon,
  UserGroupIcon,
  RocketLaunchIcon,
  AdjustmentsHorizontalIcon,
  CheckBadgeIcon
} from '@heroicons/react/24/outline';

import api from '../../services/api';
import { Button } from '../Common';
import { useCaseContext } from '../../context/CaseContext';
import MetaPackageInstaller from './MetaPackageInstaller';

const KALI_BASE = '/api/kali-tools';

// Iconos por categoría
const CATEGORY_ICONS = {
  reconnaissance: '🔍',
  scanning: '📡',
  enumeration: '📋',
  vulnerability: '🔓',
  exploitation: '💥',
  password: '🔑',
  wireless: '📶',
  forensics: '🔬',
  web: '🌐',
  network: '🔌',
  osint: '🕵️',
  crypto: '🔐',
  reporting: '📊'
};

// Colores por categoría
const CATEGORY_COLORS = {
  reconnaissance: 'from-blue-500 to-blue-600',
  scanning: 'from-purple-500 to-purple-600',
  enumeration: 'from-green-500 to-green-600',
  vulnerability: 'from-red-500 to-red-600',
  exploitation: 'from-orange-500 to-orange-600',
  password: 'from-yellow-500 to-yellow-600',
  wireless: 'from-cyan-500 to-cyan-600',
  forensics: 'from-indigo-500 to-indigo-600',
  web: 'from-teal-500 to-teal-600',
  network: 'from-pink-500 to-pink-600',
  osint: 'from-violet-500 to-violet-600',
  crypto: 'from-emerald-500 to-emerald-600',
  reporting: 'from-slate-500 to-slate-600'
};

// Perfiles de rol → metapaquetes sugeridos
const ROLE_PROFILES = {
  blue: {
    label: 'Blue Team / DFIR',
    packages: ['kali-linux-forensic', 'kali-tools-forensics', 'kali-tools-top10', 'kali-tools-crypto']
  },
  red: {
    label: 'Red Team / Pentest',
    packages: ['kali-linux-default', 'kali-linux-wireless', 'kali-linux-web', 'kali-tools-passwords', 'kali-tools-exploitation']
  },
  purple: {
    label: 'Purple / Hybrid',
    packages: ['kali-linux-top10', 'kali-linux-wireless', 'kali-tools-forensics', 'kali-tools-web', 'kali-tools-crypto']
  },
  hybrid: {
    label: 'Híbrido Personalizado',
    packages: ['kali-linux-default', 'kali-tools-top10', 'kali-tools-forensics', 'kali-tools-passwords']
  },
  custom: {
    label: 'Custom',
    packages: []
  }
};

const OPTIONAL_PACKAGES = [
  { id: 'kali-linux-everything', label: 'Full (Everything)', desc: 'Instala todo el catálogo' },
  { id: 'kali-linux-large', label: 'Large', desc: 'Paquetes extendidos' },
  { id: 'kali-tools-sdr', label: 'SDR', desc: 'Radio definida por software' },
  { id: 'kali-tools-voip', label: 'VoIP', desc: 'Telefonía y voz' },
  { id: 'kali-tools-gpu', label: 'GPU', desc: 'Cracking con GPU' }
];

const INSTALL_STEPS = ['Rol', 'Preferencias', 'Metapaquetes', 'Instalar'];

export default function KaliTools() {
  // Estado principal
  const [categories, setCategories] = useState([]);
  const [tools, setTools] = useState([]);
  const [toolsStatus, setToolsStatus] = useState({});
  const [extendedCatalog, setExtendedCatalog] = useState({});
  const [baseCatalog, setBaseCatalog] = useState({});
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedTool, setSelectedTool] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [quickActions, setQuickActions] = useState([]);
  const [error, setError] = useState(null);
  // Instalación guiada
  const [installStep, setInstallStep] = useState(0);
  const [selectedRole, setSelectedRole] = useState('blue');
  const [selectedPackages, setSelectedPackages] = useState(ROLE_PROFILES.blue.packages);
  const [preferences, setPreferences] = useState({
    focus: 'cloud',
    environment: 'lab',
    telemetry: 'network'
  });
  const [installing, setInstalling] = useState(false);
  const [installResult, setInstallResult] = useState(null);
  const nextStep = () => setInstallStep((s) => Math.min(INSTALL_STEPS.length - 1, s + 1));
  const prevStep = () => setInstallStep((s) => Math.max(0, s - 1));
  
  // Estado de ejecución
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [params, setParams] = useState({});
  const [commandPreview, setCommandPreview] = useState('');
  
  // Estado de UI
  const [activeTab, setActiveTab] = useState('categories'); // categories, tools, execution, autoInvestigate
  const [showInstaller, setShowInstaller] = useState(false);
  const [showDangerWarning, setShowDangerWarning] = useState(false);
  
  // Estado de investigación automatizada
  const [autoInvestigateIOCs, setAutoInvestigateIOCs] = useState('');
  const [autoInvestigateType, setAutoInvestigateType] = useState('full');
  const [autoInvestigateAgents, setAutoInvestigateAgents] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [investigationProfiles, setInvestigationProfiles] = useState({});
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationResult, setInvestigationResult] = useState(null);
  const [sessionInfo, setSessionInfo] = useState({ user: '', hostname: '', shell: '', cwd: '' });
  const [loadingSession, setLoadingSession] = useState(true);
  const [catalogReady, setCatalogReady] = useState(false);
  const [quickModal, setQuickModal] = useState({ open: false, action: null, keys: [], values: {} });

  // Contexto de caso
  const { currentCase, hasActiveCase, caseList = [], selectCase } = useCaseContext();
  
  const outputRef = useRef(null);

  const getPrompt = (userValue, hostValue) => {
    const u = userValue || sessionInfo.user || 'local';
    const h = hostValue || sessionInfo.hostname || 'host';
    return `${u}@${h}$`;
  };

  // ============================================================================
  // INSTALACIÓN GUIADA (ROLES)
  // ============================================================================

  const buildPackagesFromPreferences = (roleValue, prefs) => {
    const base = new Set(ROLE_PROFILES[roleValue]?.packages || []);
    if (prefs.focus === 'network') base.add('kali-linux-wireless');
    if (prefs.focus === 'web') base.add('kali-linux-web');
    if (prefs.focus === 'cloud') base.add('kali-linux-top10');
    if (prefs.telemetry === 'endpoints') base.add('kali-tools-forensics');
    if (prefs.telemetry === 'network') base.add('kali-tools-sniffing-spoofing');
    if (prefs.environment === 'prod') base.add('kali-linux-default');
    return Array.from(base);
  };

  const handlePreferenceChange = (key, value) => {
    const next = { ...preferences, [key]: value };
    setPreferences(next);
    setSelectedPackages(buildPackagesFromPreferences(selectedRole, next));
  };

  const togglePackage = (pkg) => {
    setSelectedPackages((prev) =>
      prev.includes(pkg) ? prev.filter((p) => p !== pkg) : [...prev, pkg]
    );
  };

  const generateInstallCommand = () => {
    if (!selectedPackages.length) return 'Seleccione al menos un metapaquete';
    return `sudo apt-get update && sudo apt-get install -y ${selectedPackages.join(' ')}`;
  };

  const installMetapackages = async () => {
    if (!selectedPackages.length) {
      setError('Selecciona al menos un metapaquete');
      return;
    }
    try {
      setInstalling(true);
      setInstallResult(null);
      setError(null);
      const { data } = await api.post(`${KALI_BASE}/install`, {
        role: selectedRole,
        packages: selectedPackages
      });
      setInstallResult(data);
    } catch (err) {
      console.error('Error instalando metapaquetes:', err);
      setError('Error instalando metapaquetes. Revisa permisos/root.');
    } finally {
      setInstalling(false);
    }
  };

  // ============================================================================
  // CARGA DE DATOS
  // ============================================================================

  const loadSessionInfo = useCallback(async () => {
    try {
      const { data } = await api.get(`${KALI_BASE}/session`);
      setSessionInfo({
        user: data?.user || '',
        hostname: data?.hostname || '',
        shell: data?.shell || '',
        cwd: data?.cwd || ''
      });
    } catch (error) {
      console.error('Error obteniendo sesión OS:', error);
      setSessionInfo({ user: '', hostname: '', shell: '', cwd: '' });
    } finally {
      setLoadingSession(false);
    }
  }, []);

  useEffect(() => {
    loadQuickActions();
    loadToolsStatus();
    loadAgents();
    loadInvestigationProfiles();
    loadSessionInfo();
  }, []);

  useEffect(() => {
    setSelectedPackages(buildPackagesFromPreferences(selectedRole, preferences));
  }, [selectedRole]);

  useEffect(() => {
    if (selectedCategory) {
      loadToolsByCategory(selectedCategory);
    }
  }, [selectedCategory]);

  useEffect(() => {
    if (!selectedCategory && categories.length > 0) {
      const first = categories[0];
      const nextId = first.id || first.name || first.category || first;
      setSelectedCategory(nextId);
      loadToolsByCategory(nextId);
      setCatalogReady(true);
    }
  }, [categories, selectedCategory]);

  useEffect(() => {
    if (selectedTool && Object.keys(params).length > 0) {
      previewCommand();
    }
  }, [params, selectedTool]);

  const loadToolsByCategory = async (category) => {
    try {
      setError(null);
      // Si el catálogo extendido tiene esta categoría, úsalo localmente
      if (extendedCatalog[category]) {
        setTools(extendedCatalog[category]);
        return;
      }
      if (baseCatalog[category]) {
        setTools(baseCatalog[category]);
        return;
      }

      const { data } = await api.get(`${KALI_BASE}/tools`, {
        params: { category }
      });
      setTools(data);
    } catch (error) {
      console.error('Error loading tools:', error);
      setTools([]);
      setError('No se pudieron cargar las herramientas para la categoría seleccionada.');
    }
  };

  const loadQuickActions = async () => {
    try {
      setError(null);
      const { data } = await api.get(`${KALI_BASE}/quick-actions`);
      setQuickActions(data);
    } catch (error) {
      console.error('Error loading quick actions:', error);
      setError('No se pudieron cargar las acciones rápidas.');
    }
  };

  const loadToolsStatus = async () => {
    try {
      setError(null);
      // Intentar cargar catálogo extendido primero
      try {
        // Backend expone /api/kali-tools/extended-catalog
        const { data } = await api.get(`${KALI_BASE}/extended-catalog`);

        // Procesar catálogo extendido
        const statusMap = {};
        const catalogCategories = data.categories || data; // endpoint puede devolver {categories:{...}} o {cat:[...]}
        const extendedCategories = Object.entries(catalogCategories || {}).map(([id, catOrList]) => {
          const toolsList = Array.isArray(catOrList) ? catOrList : (catOrList.tools || []);
          toolsList.forEach((tool) => {
            statusMap[tool.id] = tool.installed ? 'available' : 'not_installed';
          });
          return {
            id,
            name: catOrList.name || id,
            count: toolsList.length,
            icon: getCategoryIcon(id)
          };
        });
        setToolsStatus(statusMap);
        setCategories(extendedCategories);
        // Guardar catálogo extendido para usarlo localmente (evita 400 en categorías no nativas)
        setExtendedCatalog(
          Object.entries(catalogCategories || {}).reduce((acc, [id, catOrList]) => {
            acc[id] = Array.isArray(catOrList) ? catOrList : (catOrList.tools || []);
            return acc;
          }, {})
        );

        // Cargar catálogo base (herramientas nativas instaladas)
        try {
          const baseResp = await api.get(`${KALI_BASE}/tools`);
          const grouped = baseResp.data.reduce((acc, tool) => {
            const cat = tool.category || 'misc';
            acc[cat] = acc[cat] || [];
            acc[cat].push(tool);
            return acc;
          }, {});
          setBaseCatalog(grouped);

          const baseCategories = Object.entries(grouped).map(([id, list]) => ({
            id,
            name: id,
            count: list.length,
            icon: getCategoryIcon(id)
          }));

          // Unir categorías extendidas + base (evitar duplicados por id)
          const merged = [...extendedCategories];
          baseCategories.forEach((bcat) => {
            if (!merged.find((c) => c.id === bcat.id)) {
              merged.push(bcat);
            }
          });
          setCategories(merged);
        } catch (baseErr) {
          console.warn('No se pudo cargar catálogo base:', baseErr.message);
        }
      } catch (extError) {
        // Fallback a endpoint normal
        console.log('Extended catalog not available, using standard');
        const { data } = await api.get(`${KALI_BASE}/status`);
        setToolsStatus(data);
        // Si el endpoint de status no trae categorías, usa /categories
        if (!categories.length) {
          const catResp = await api.get(`${KALI_BASE}/categories`);
          setCategories(catResp.data);
        }
      }
    } catch (error) {
      console.error('Error loading tools status:', error);
      setError('No se pudo obtener el estado de las herramientas.');
    }
  };

  const getCategoryIcon = (categoryId) => {
    const icons = {
      reconnaissance: '🔍',
      exploitation: '💣',
      m365_forensics: '☁️',
      m365_recon: '🔐',
      threat_hunting: '🎯',
      log_analysis: '📊',
      metapackage: '📦',
      edr: '🛡️',
      malware: '🦠',
      network: '🌐'
    };
    return icons[categoryId] || '🛠️';
  };

  const loadAgents = async () => {
    try {
      const { data } = await api.get('/api/v41/agents/');
      setAutoInvestigateAgents(data.agents || []);
    } catch (error) {
      console.error('Error loading agents:', error);
    }
  };

  const loadInvestigationProfiles = async () => {
    try {
      const { data } = await api.get('/api/v41/agents/investigate/profiles');
      setInvestigationProfiles(data);
    } catch (error) {
      console.error('Error loading investigation profiles:', error);
    }
  };

  const startAutomatedInvestigation = async () => {
    if (!autoInvestigateIOCs.trim()) {
      setError('Por favor ingresa al menos un IOC para investigar');
      return;
    }

    setIsInvestigating(true);
    setInvestigationResult(null);
    setError(null);

    try {
      const iocsList = autoInvestigateIOCs.split('\n').filter(ioc => ioc.trim());
      
      const { data } = await api.post('/api/v41/agents/investigate', {
        investigation_type: autoInvestigateType,
        iocs: iocsList,
        target_agent: selectedAgentId || null,
        priority: 'normal',
        timeout_minutes: 30
      });

      setInvestigationResult(data);
    } catch (error) {
      console.error('Error starting investigation:', error);
      setError('Error al iniciar la investigación: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsInvestigating(false);
    }
  };

  const searchTools = async (query) => {
    if (!query.trim()) {
      if (selectedCategory) {
        await loadToolsByCategory(selectedCategory);
      } else {
        setTools([]);
      }
      return;
    }
    try {
      const { data } = await api.get(`${KALI_BASE}/search`, {
        params: { q: query }
      });
      setTools(data.tools);
    } catch (error) {
      console.error('Error searching tools:', error);
      setError('Búsqueda fallida. Verifica la API.');
    }
  };
  // ============================================================================
  // EJECUCIÓN DE HERRAMIENTAS
  // ============================================================================

  const previewCommand = async () => {
    if (!hasActiveCase()) {
      setError('Selecciona un caso antes de previsualizar comandos.');
      return;
    }
    if (!selectedTool) return;
    
    try {
      const { data } = await api.post(`${KALI_BASE}/preview`, {
        tool_id: selectedTool.id,
        params
      });
      setCommandPreview(data.command || '');
    } catch (error) {
      console.error('Error previewing command:', error);
    }
  };

  const executeTool = async () => {
    if (!hasActiveCase()) {
      setError('Selecciona un caso antes de ejecutar herramientas.');
      return;
    }
    if (!selectedTool) return;
    
    // Verificar si la herramienta está instalada
    const toolStatus = toolsStatus[selectedTool.id];
    if (toolStatus && toolStatus !== 'available') {
      if (window.confirm(`La herramienta ${selectedTool.name} no está disponible (${toolStatus}). ¿Desea instalarla?`)) {
        await installTool(selectedTool.id);
      }
      return;
    }
    
    // Verificar herramienta peligrosa
    if (selectedTool.dangerous && !showDangerWarning) {
      setShowDangerWarning(true);
      return;
    }
    
    setIsExecuting(true);
    setExecutionResult(null);
    setShowDangerWarning(false);
    setActiveTab('execution');
    
    try {
      const { data } = await api.post(`${KALI_BASE}/execute`, {
        tool_id: selectedTool.id,
        params,
        case_id: currentCase?.case_id
      });
      setExecutionResult(data);
      
      // Scroll al final del output
      if (outputRef.current) {
        outputRef.current.scrollTop = outputRef.current.scrollHeight;
      }
    } catch (error) {
      setExecutionResult({
        success: false,
        error: error.message,
        tool_name: selectedTool.name
      });
      setError('La ejecución falló. Revisa la consola/logs.');
    } finally {
      setIsExecuting(false);
    }
  };

  const installTool = async (toolId) => {
    if (!window.confirm(`¿Instalar ${toolId}? Esto puede tomar varios minutos.`)) {
      return;
    }
    
    setIsExecuting(true);
    setExecutionResult({
      success: null,
      output: `Instalando ${toolId}...\n`,
      tool_name: toolId
    });
    
    try {
      const { data } = await api.post(`${KALI_BASE}/install/${toolId}`);
      const executionId = data.execution_id;
      
      // Polling para verificar estado de instalación
      const pollInterval = setInterval(async () => {
        try {
          const { data: status } = await api.get(`${KALI_BASE}/install/status/${executionId}`);
          
          setExecutionResult(prev => ({
            ...prev,
            output: prev.output + (status.result?.output || ''),
            success: status.status === 'completed'
          }));
          
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval);
            setIsExecuting(false);
            
            if (status.status === 'completed') {
              // Recargar estado de herramientas
              loadToolsStatus();
              setError(null);
            } else {
              setError(`Instalación fallida: ${status.result?.error}`);
            }
          }
        } catch (pollError) {
          console.error('Error polling install status:', pollError);
          clearInterval(pollInterval);
          setIsExecuting(false);
        }
      }, 2000);
      
      // Timeout de 10 minutos
      setTimeout(() => {
        clearInterval(pollInterval);
        setIsExecuting(false);
        setError('Timeout de instalación (10 min)');
      }, 600000);
      
    } catch (error) {
      setIsExecuting(false);
      setExecutionResult({
        success: false,
        error: error.response?.data?.detail || error.message,
        tool_name: toolId
      });
      setError('Error al iniciar instalación');
    }
  };

  const executeQuickAction = async (action) => {
    const paramKeys = Object.values(action.params_template || {})
      .filter((v) => v.startsWith('{') && v.endsWith('}'))
      .map((v) => v.slice(1, -1));

    if (paramKeys.length > 0) {
      setQuickModal({
        open: true,
        action,
        keys: paramKeys,
        values: paramKeys.reduce((acc, k) => ({ ...acc, [k]: '' }), {})
      });
      return;
    }

    await runQuickAction(action, {});
  };

  const runQuickAction = async (action, actionParams) => {
    setIsExecuting(true);
    setActiveTab('execution');

    try {
      const { data } = await api.post(`${KALI_BASE}/quick-actions/${action.id}/execute`, actionParams);
      setExecutionResult({
        success: true,
        tool_name: action.name,
        output: data.results
          .map((r) => `\n=== ${r.tool_name} ===\n${r.output || r.error || 'No output'}`)
          .join('\n'),
        duration_seconds: data.results.reduce((sum, r) => sum + (r.duration_seconds || 0), 0)
      });
    } catch (error) {
      setExecutionResult({
        success: false,
        error: error.message,
        tool_name: action.name
      });
      setError('La ejecución de la acción rápida falló.');
    } finally {
      setIsExecuting(false);
      setQuickModal({ open: false, action: null, keys: [], values: {} });
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  // ============================================================================
  // COMPONENTES DE UI
  // ============================================================================

  const StatusBadge = ({ status }) => {
    const styles = {
      available: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      not_installed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      requires_root: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      running: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
    };
    
    const labels = {
      available: 'Disponible',
      not_installed: 'No instalado',
      requires_root: 'Requiere root',
      running: 'Ejecutando'
    };
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status] || styles.not_installed}`}>
        {labels[status] || status}
      </span>
    );
  };

  const CategoryCard = ({ category }) => (
    <div
      onClick={() => {
        setSelectedCategory(category.id);
        setActiveTab('tools');
      }}
      className={`
        relative overflow-hidden rounded-xl p-4 cursor-pointer
        bg-gradient-to-br ${CATEGORY_COLORS[category.id] || 'from-gray-500 to-gray-600'}
        hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl
      `}
    >
      <div className="flex items-center justify-between">
        <div>
          <span className="text-3xl">{CATEGORY_ICONS[category.id] || '🔧'}</span>
          <h3 className="mt-2 text-lg font-bold text-white">{category.name}</h3>
          <p className="text-white/80 text-sm">{category.count} herramientas</p>
        </div>
        <ChevronRightIcon className="w-6 h-6 text-white/60" />
      </div>
    </div>
  );

  const ToolCard = ({ tool }) => (
    <div
      onClick={() => {
        setSelectedTool(tool);
        setParams({});
        setCommandPreview('');
        setExecutionResult(null);
      }}
      className={`
        p-4 rounded-lg border cursor-pointer transition-all duration-200
        ${selectedTool?.id === tool.id 
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
          : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600'}
        ${tool.status === 'not_installed' ? 'opacity-60' : ''}
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{tool.icon}</span>
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white">{tool.name}</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{tool.description}</p>
          </div>
        </div>
        <StatusBadge status={tool.status || toolsStatus[tool.id]} />
      </div>
      
      <div className="mt-3 flex items-center gap-2">
        {tool.requires_root && (
          <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 rounded">
            🔒 Root
          </span>
        )}
        {tool.dangerous && (
          <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded">
            ⚠️ Peligroso
          </span>
        )}
      </div>
    </div>
  );

  const ParameterInput = ({ param, value, onChange }) => {
    const baseClasses = "w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent";
    
    if (param.type === 'select') {
      return (
        <select
          value={value || param.default || ''}
          onChange={(e) => onChange(e.target.value)}
          className={baseClasses}
        >
          <option value="">Seleccionar...</option>
          {param.options.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    }
    
    if (param.type === 'boolean') {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={value || param.default || false}
            onChange={(e) => onChange(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-gray-700 dark:text-gray-300">Activar</span>
        </label>
      );
    }
    
    if (param.type === 'number') {
      return (
        <input
          type="number"
          value={value || param.default || ''}
          onChange={(e) => onChange(parseInt(e.target.value) || 0)}
          placeholder={param.placeholder}
          className={baseClasses}
        />
      );
    }
    
    return (
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={param.placeholder}
        className={baseClasses}
      />
    );
  };

  const QuickActionCard = ({ action }) => (
    <div
      onClick={() => executeQuickAction(action)}
      className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500 cursor-pointer transition-all bg-white dark:bg-gray-800 hover:shadow-md"
    >
      <div className="flex items-center gap-3">
        <BoltIcon className="w-8 h-8 text-yellow-500" />
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-white">{action.name}</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">{action.description}</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {(action.tools || []).map(t => (
              <span key={t} className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const QuickModal = () => {
    if (!quickModal.open) return null;
    return (
      <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center px-4">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg shadow-2xl space-y-4">
          <h3 className="text-xl font-semibold text-white">Parámetros requeridos</h3>
          <p className="text-sm text-gray-400">
            Acción rápida: <span className="text-blue-300 font-semibold">{quickModal.action?.name}</span>
          </p>
          <div className="space-y-3">
            {quickModal.keys.map((k) => (
              <div key={k} className="space-y-1">
                <label className="text-sm text-gray-300">{k}</label>
                <input
                  type="text"
                  value={quickModal.values[k]}
                  onChange={(e) =>
                    setQuickModal((prev) => ({
                      ...prev,
                      values: { ...prev.values, [k]: e.target.value }
                    }))
                  }
                  className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white"
                  placeholder={`Ingrese ${k}`}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setQuickModal({ open: false, action: null, keys: [], values: {} })}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200"
            >
              Cancelar
            </button>
            <button
              onClick={() => runQuickAction(quickModal.action, quickModal.values)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              Ejecutar
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================

  const showInstallerButton = true;

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-red-500 to-orange-500 rounded-lg">
            <CommandLineIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Kali Tools</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Herramientas de seguridad organizadas por investigación
            </p>
            {currentCase ? (
              <div className="text-xs text-blue-300 mt-1">
                Caso activo: <span className="font-semibold">{currentCase.case_id}</span> — {currentCase.name || ''}
              </div>
            ) : (
              <div className="text-xs text-yellow-300 mt-1">Selecciona un caso para registrar evidencia y comandos.</div>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          {showInstallerButton && (
            <button
              onClick={() => setShowInstaller(true)}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg shadow hover:scale-[1.01] transition flex items-center gap-2"
            >
              <SparklesIcon className="w-5 h-5" />
              Configurar rol Kali + instalar
            </button>
          )}
          {/* Selector de caso activo */}
          <div className="relative">
            <select
              className="pl-3 pr-6 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
              value={currentCase?.case_id || ''}
              onChange={(e) => {
                const selected = caseList.find((c) => c.case_id === e.target.value);
                if (selected) {
                  selectCase(selected);
                }
              }}
            >
              <option value="">Selecciona caso activo</option>
              {caseList.map((c) => (
                <option key={c.case_id} value={c.case_id}>
                  {c.case_id} — {c.name || c.description || ''}
                </option>
              ))}
            </select>
          </div>
        </div>
          
          {/* Búsqueda */}
          <div className="relative w-80">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar herramientas..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                searchTools(e.target.value);
                if (e.target.value) {
                  setActiveTab('tools');
                  setSelectedCategory(null);
                }
              }}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <span className="px-3 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-600">
            {loadingSession
              ? 'Detectando usuario del sistema...'
              : `Autenticado con cuenta OS: ${sessionInfo.user || 'local'}@${sessionInfo.hostname || 'host'}`}
          </span>
          {sessionInfo.shell && (
            <span className="px-2 py-1 rounded bg-gray-800 text-gray-100 text-xs border border-gray-700">
              Shell: {sessionInfo.shell}
            </span>
          )}
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-500/10 border border-red-500/40 text-red-200 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Tabs de navegación */}
        <div className="mt-4 flex gap-2">
          <button
            onClick={() => {
              setActiveTab('categories');
              setSelectedCategory(null);
              setSelectedTool(null);
            }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'categories'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            📁 Categorías
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'tools'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            🔧 Herramientas {selectedCategory && `(${selectedCategory})`}
          </button>
          <button
            onClick={() => setActiveTab('execution')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'execution'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            ⚡ Ejecución
          </button>
          <button
            onClick={() => setActiveTab('quick')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'quick'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            ⚡ Acciones Rápidas
          </button>
          <button
            onClick={() => setActiveTab('autoInvestigate')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'autoInvestigate'
                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            🤖 Investigación Auto
          </button>
        </div>
      </div>
      <QuickModal />

      {/* Contenido principal */}
      <div className="flex-1 overflow-hidden flex">
        {/* Panel izquierdo: Categorías o Lista de herramientas */}
        <div className="w-1/2 border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-4">
          {activeTab === 'categories' && (
            categories.length === 0 ? (
              <div className="text-gray-500 text-sm">No hay categorías disponibles. Verifica el catálogo o instala metapaquetes.</div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {categories.map(cat => (
                  <CategoryCard key={cat.id || cat.name} category={cat} />
                ))}
              </div>
            )
          )}
          
          {activeTab === 'tools' && (
            <div className="space-y-3">
              {selectedCategory && (
                <div className="flex items-center gap-2 mb-4">
                  <button
                    onClick={() => {
                      setSelectedCategory(null);
                      setActiveTab('categories');
                    }}
                    className="text-blue-600 hover:text-blue-800 dark:text-blue-400"
                  >
                    ← Volver
                  </button>
                  <span className="text-2xl">{CATEGORY_ICONS[selectedCategory]}</span>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white capitalize">
                    {selectedCategory.replace('_', ' ')}
                  </h2>
                </div>
              )}
              
              {tools.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {searchQuery 
                    ? 'No se encontraron herramientas' 
                    : 'Selecciona una categoría para ver herramientas'}
                </div>
              ) : (
                tools.map(tool => (
                  <ToolCard key={tool.id} tool={tool} />
                ))
              )}
            </div>
          )}
          
          {activeTab === 'quick' && (
            <div className="space-y-3">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                ⚡ Acciones Rápidas
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Ejecuta múltiples herramientas con un solo clic para investigaciones comunes.
              </p>
              {quickActions.map(action => (
                <QuickActionCard key={action.id} action={action} />
              ))}
            </div>
          )}

          {activeTab === 'autoInvestigate' && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                🤖 Investigación Automatizada
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Ingresa IOCs y deja que los agentes investiguen automáticamente usando las herramientas apropiadas.
              </p>

              {/* IOCs Input */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  IOCs a investigar (uno por línea)
                </label>
                <textarea
                  value={autoInvestigateIOCs}
                  onChange={(e) => setAutoInvestigateIOCs(e.target.value)}
                  placeholder={"192.168.1.100\nexample.com\nmalware.exe\nuser@email.com\n5d41402abc4b2a76b9719d911017c592"}
                  className="w-full h-40 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-mono focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Soporta: IPs, dominios, URLs, hashes (MD5/SHA1/SHA256), emails, paths de archivos
                </p>
              </div>

              {/* Tipo de investigación */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tipo de Investigación
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'quick', label: '⚡ Rápida', desc: 'Solo herramientas básicas (5 min)' },
                    { id: 'full', label: '🔍 Completa', desc: 'Todas las herramientas (30 min)' },
                    { id: 'targeted', label: '🎯 Dirigida', desc: 'Herramientas específicas' }
                  ].map(type => (
                    <button
                      key={type.id}
                      onClick={() => setAutoInvestigateType(type.id)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        autoInvestigateType === type.id
                          ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30'
                          : 'border-gray-300 dark:border-gray-600 hover:border-purple-300'
                      }`}
                    >
                      <div className="font-medium text-gray-900 dark:text-white">{type.label}</div>
                      <div className="text-xs text-gray-500">{type.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Selección de agente */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Agente de Ejecución
                </label>
                <select
                  value={selectedAgentId}
                  onChange={(e) => setSelectedAgentId(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                >
                  <option value="">🤖 Auto-selección (mejor agente disponible)</option>
                  <option value="local-mcp">💻 Local (MCP Server)</option>
                  {autoInvestigateAgents.filter(a => a.status === 'online').map(agent => (
                    <option key={agent.id} value={agent.id}>
                      {agent.agent_type === 'blue' ? '🔵' : agent.agent_type === 'red' ? '🔴' : '🟣'} {agent.name} ({agent.hostname})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Agentes online: {autoInvestigateAgents.filter(a => a.status === 'online').length}
                </p>
              </div>

              {/* Botón de ejecución */}
              <button
                onClick={startAutomatedInvestigation}
                disabled={isInvestigating || !autoInvestigateIOCs.trim()}
                className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 ${
                  isInvestigating || !autoInvestigateIOCs.trim()
                    ? 'bg-gray-400 cursor-not-allowed text-white'
                    : 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl'
                } transition-all`}
              >
                {isInvestigating ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Investigando...
                  </>
                ) : (
                  <>
                    <BoltIcon className="w-5 h-5" />
                    Iniciar Investigación Automatizada
                  </>
                )}
              </button>

              {/* Resultado de investigación */}
              {investigationResult && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="px-4 py-3 bg-purple-100 dark:bg-purple-900/30 border-b border-purple-200 dark:border-purple-800">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircleIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                        <span className="font-medium text-purple-900 dark:text-purple-100">
                          Investigación Iniciada
                        </span>
                      </div>
                      <span className="text-sm text-purple-600 dark:text-purple-400">
                        ID: {investigationResult.investigation_id}
                      </span>
                    </div>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <div className="text-xs text-gray-500 mb-1">Tareas Encoladas</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">
                          {investigationResult.tasks_queued}
                        </div>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <div className="text-xs text-gray-500 mb-1">Agente Asignado</div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {investigationResult.agent_id}
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-xs text-gray-500 mb-2">IOCs Clasificados</div>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(investigationResult.classified_iocs || {}).map(([type, count]) => (
                          <span key={type} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                            {type}: {count}
                          </span>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-xs text-gray-500 mb-2">Herramientas Seleccionadas</div>
                      <div className="flex flex-wrap gap-1">
                        {(investigationResult.tools_selected || []).map((tool, i) => (
                          <span key={i} className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded text-xs">
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>

                    {investigationResult.tasks && investigationResult.tasks.length > 0 && (
                      <div>
                        <div className="text-xs text-gray-500 mb-2">Primeras Tareas</div>
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                          {investigationResult.tasks.map((task, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs bg-gray-50 dark:bg-gray-900 rounded px-2 py-1">
                              <span className="font-mono text-purple-600">{task.tool}</span>
                              <span className="text-gray-500">→</span>
                              <span className="font-mono text-gray-700 dark:text-gray-300 truncate">{task.target}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'execution' && !selectedTool && (
            <div className="text-center py-12 text-gray-500">
              <CommandLineIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>Selecciona una herramienta para ejecutar</p>
            </div>
          )}
        </div>

        {/* Panel derecho: Configuración y ejecución */}
        <div className="w-1/2 overflow-y-auto p-4">
          {selectedTool ? (
            <div className="space-y-6">
              {/* Header de herramienta */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-4xl">{selectedTool.icon}</span>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                        {selectedTool.name}
                      </h2>
                      <p className="text-gray-600 dark:text-gray-400">{selectedTool.description}</p>
                    </div>
                  </div>
                  <StatusBadge status={selectedTool.status || toolsStatus[selectedTool.id]} />
                </div>
                
                {selectedTool.examples && selectedTool.examples.length > 0 && (
                  <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <p className="text-xs text-gray-500 mb-1">Ejemplos:</p>
                    {selectedTool.examples.map((ex, i) => (
                      <code key={i} className="block text-sm text-gray-700 dark:text-gray-300">
                        $ {ex}
                      </code>
                    ))}
                  </div>
                )}
              </div>

              {/* Parámetros */}
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Cog6ToothIcon className="w-5 h-5" />
                  Parámetros
                </h3>
                
                <div className="space-y-4">
                  {selectedTool.parameters?.map(param => (
                    <div key={param.name}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {param.name}
                        {param.required && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      <ParameterInput
                        param={param}
                        value={params[param.name]}
                        onChange={(val) => setParams({ ...params, [param.name]: val })}
                      />
                      <p className="mt-1 text-xs text-gray-500">{param.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Preview del comando */}
              {commandPreview && (
                <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-400">Comando a ejecutar:</span>
                    <button
                      onClick={() => copyToClipboard(commandPreview)}
                      className="text-gray-400 hover:text-white"
                    >
                      <DocumentDuplicateIcon className="w-4 h-4" />
                    </button>
                  </div>
                  <code className="text-green-400 text-sm font-mono">
                    {getPrompt() + ' ' + commandPreview}
                  </code>
                </div>
              )}

              {/* Warning para herramientas peligrosas */}
              {showDangerWarning && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0" />
                    <div>
                      <h4 className="font-semibold text-red-800 dark:text-red-400">
                        ⚠️ Herramienta Potencialmente Peligrosa
                      </h4>
                      <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                        Esta herramienta puede ser detectada como intrusiva o causar interrupciones.
                        Asegúrese de tener autorización antes de ejecutarla.
                      </p>
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={executeTool}
                          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                        >
                          Entiendo, ejecutar
                        </button>
                        <button
                          onClick={() => setShowDangerWarning(false)}
                          className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Botón de ejecución */}
              {!showDangerWarning && (
                <button
                  onClick={executeTool}
                  disabled={isExecuting || selectedTool.status === 'not_installed'}
                  className={`
                    w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2
                    ${isExecuting 
                      ? 'bg-gray-400 cursor-not-allowed' 
                      : selectedTool.status === 'not_installed'
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl'}
                    transition-all
                  `}
                >
                  {isExecuting ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Ejecutando...
                    </>
                  ) : (
                    <>
                      <PlayIcon className="w-5 h-5" />
                      Ejecutar {selectedTool.name}
                    </>
                  )}
                </button>
              )}

              {/* Resultado de ejecución */}
              {executionResult && (
                <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
                  <div className={`px-4 py-2 flex items-center justify-between ${
                    executionResult.success 
                      ? 'bg-green-900/50 border-b border-green-800' 
                      : 'bg-red-900/50 border-b border-red-800'
                  }`}>
                    <div className="flex items-center gap-2">
                      {executionResult.success ? (
                        <CheckCircleIcon className="w-5 h-5 text-green-400" />
                      ) : (
                        <XCircleIcon className="w-5 h-5 text-red-400" />
                      )}
                      <span className="font-medium text-white">
                        {executionResult.success ? 'Ejecución exitosa' : 'Error en ejecución'}
                      </span>
                    </div>
                    {executionResult.duration_seconds && (
                      <div className="flex items-center gap-1 text-gray-400 text-sm">
                        <ClockIcon className="w-4 h-4" />
                        {executionResult.duration_seconds.toFixed(2)}s
                      </div>
                    )}
                  </div>
                  
                  <div 
                    ref={outputRef}
                    className="p-4 max-h-96 overflow-y-auto font-mono text-sm"
                  >
                    {executionResult.command && (
                      <div className="text-gray-400 mb-2">
                        {`${getPrompt(executionResult.run_as, executionResult.hostname)} ${executionResult.command}`}
                        {executionResult.shell && (
                          <span className="text-xs text-gray-500 ml-2">({executionResult.shell})</span>
                        )}
                      </div>
                    )}
                    <pre className="text-gray-300 whitespace-pre-wrap">
                      {executionResult.output || executionResult.error || 'Sin output'}
                    </pre>
                    {executionResult.stderr && (
                      <pre className="text-red-400 whitespace-pre-wrap mt-2">
                        {executionResult.stderr}
                      </pre>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <div className="text-center">
                <ShieldExclamationIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">Selecciona una herramienta</p>
                <p className="text-sm">Elige una categoría y herramienta para comenzar</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Instalador guiado */}
      {showInstaller && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center px-4 py-8">
          <div className="relative w-full max-w-5xl bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/10 to-emerald-500/10 pointer-events-none" />
            <div className="relative p-6 space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-blue-300 text-sm">
                    <RocketLaunchIcon className="w-5 h-5" />
                    Instalación guiada de Kali (metapaquetes oficiales)
                  </div>
                  <h3 className="text-2xl font-bold text-white mt-1">Configura tu rol y despliega las herramientas</h3>
                  <p className="text-gray-400 text-sm">
                    Elegimos los metapaquetes adecuados según el tipo de equipo y las preferencias de investigación.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowInstaller(false)}
                    className="px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 hover:bg-gray-700"
                  >
                    Cerrar
                  </button>
                </div>
              </div>

              {/* Progreso */}
              <div className="flex items-center gap-2">
                {INSTALL_STEPS.map((label, idx) => (
                  <div key={label} className="flex items-center gap-2">
                    <div
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1 transition ${
                        installStep >= idx
                          ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                          : 'bg-gray-800 text-gray-400'
                      }`}
                    >
                      <CheckBadgeIcon className="w-4 h-4" />
                      {label}
                    </div>
                    {idx < INSTALL_STEPS.length - 1 && (
                      <div className="w-8 h-px bg-gradient-to-r from-blue-500/60 to-purple-500/60" />
                    )}
                  </div>
                ))}
              </div>

              {/* Step content */}
              {installStep === 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Object.entries(ROLE_PROFILES).map(([key, profile]) => (
                    <button
                      key={key}
                      onClick={() => setSelectedRole(key)}
                      className={`p-4 rounded-xl border text-left transition transform hover:-translate-y-0.5 ${
                        selectedRole === key
                          ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20'
                          : 'border-gray-700 bg-gray-800 hover:border-blue-500/50'
                      }`}
                    >
                      <div className="flex items-center gap-2 text-sm text-gray-300 mb-2">
                        <UserGroupIcon className="w-5 h-5" />
                        {profile.label}
                      </div>
                      <div className="text-xs text-gray-400">
                        {profile.packages.length === 0 ? 'Define tus propios metapaquetes' : 'Incluye:'}
                        {profile.packages.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {profile.packages.map((pkg) => (
                              <span key={pkg} className="px-2 py-1 bg-gray-900 border border-gray-700 rounded text-[11px] text-blue-200">
                                {pkg}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {installStep === 1 && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/60">
                    <div className="flex items-center gap-2 text-gray-200 font-semibold mb-2">
                      <AdjustmentsHorizontalIcon className="w-5 h-5" />
                      Enfoque principal
                    </div>
                    {['cloud', 'network', 'web'].map((opt) => (
                      <button
                        key={opt}
                        onClick={() => handlePreferenceChange('focus', opt)}
                        className={`w-full text-left px-3 py-2 rounded-lg mb-2 border transition ${
                          preferences.focus === opt
                            ? 'border-blue-500 bg-blue-500/10 text-white'
                            : 'border-gray-700 text-gray-300 hover:border-blue-500/50'
                        }`}
                      >
                        {opt === 'cloud' && 'Cloud / SaaS'}
                        {opt === 'network' && 'Red / Wireless'}
                        {opt === 'web' && 'Web / Apps'}
                      </button>
                    ))}
                  </div>

                  <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/60">
                    <div className="flex items-center gap-2 text-gray-200 font-semibold mb-2">
                      <ShieldExclamationIcon className="w-5 h-5" />
                      Entorno
                    </div>
                    {['lab', 'prod'].map((opt) => (
                      <button
                        key={opt}
                        onClick={() => handlePreferenceChange('environment', opt)}
                        className={`w-full text-left px-3 py-2 rounded-lg mb-2 border transition ${
                          preferences.environment === opt
                            ? 'border-purple-500 bg-purple-500/10 text-white'
                            : 'border-gray-700 text-gray-300 hover:border-purple-500/50'
                        }`}
                      >
                        {opt === 'lab' ? 'Lab / Demo' : 'Producción controlada'}
                      </button>
                    ))}
                  </div>

                  <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/60">
                    <div className="flex items-center gap-2 text-gray-200 font-semibold mb-2">
                      <WifiIcon className="w-5 h-5" />
                      Telemetría
                    </div>
                    {['network', 'endpoints'].map((opt) => (
                      <button
                        key={opt}
                        onClick={() => handlePreferenceChange('telemetry', opt)}
                        className={`w-full text-left px-3 py-2 rounded-lg mb-2 border transition ${
                          preferences.telemetry === opt
                            ? 'border-emerald-500 bg-emerald-500/10 text-white'
                            : 'border-gray-700 text-gray-300 hover:border-emerald-500/50'
                        }`}
                      >
                        {opt === 'network' ? 'Red / Capturas' : 'Endpoints / DFIR'}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {installStep === 2 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/70">
                    <h4 className="text-sm text-gray-200 font-semibold mb-2">Metapaquetes sugeridos</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {selectedPackages.map((pkg) => (
                        <label key={pkg} className="flex items-center gap-3 bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2">
                          <input
                            type="checkbox"
                            checked={true}
                            onChange={() => togglePackage(pkg)}
                            className="accent-blue-500 w-4 h-4"
                          />
                          <span className="text-gray-100 text-sm">{pkg}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/70">
                    <h4 className="text-sm text-gray-200 font-semibold mb-2">Opcionales</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {OPTIONAL_PACKAGES.map((pkg) => (
                        <label key={pkg.id} className="flex items-start gap-3 bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2">
                          <input
                            type="checkbox"
                            checked={selectedPackages.includes(pkg.id)}
                            onChange={() => togglePackage(pkg.id)}
                            className="accent-blue-500 w-4 h-4 mt-1"
                          />
                          <div>
                            <p className="text-gray-100 text-sm font-semibold">{pkg.label}</p>
                            <p className="text-gray-400 text-xs">{pkg.desc}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {installStep === 3 && (
                <div className="space-y-3">
                  <div className="bg-gray-800/70 border border-gray-700 rounded-lg p-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-300">Comando a ejecutar</p>
                      <code className="text-xs text-blue-200 break-all">{generateInstallCommand()}</code>
                    </div>
                    <Button
                      variant="secondary"
                      onClick={() => navigator.clipboard.writeText(generateInstallCommand())}
                    >
                      Copiar
                    </Button>
                  </div>
                  <div className="flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-5 h-5 text-yellow-400" />
                    <p className="text-sm text-gray-300">
                      Requiere permisos root. Se usa whitelist de metapaquetes oficiales de Kali.
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={installMetapackages}
                      disabled={installing}
                      className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-lg flex items-center gap-2 shadow-lg hover:shadow-xl disabled:opacity-60"
                    >
                      {installing ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <PlayIcon className="w-5 h-5" />}
                      {installing ? 'Instalando...' : 'Instalar metapaquetes'}
                    </button>
                    {installResult && (
                      <span className={`text-sm ${installResult.success ? 'text-green-400' : 'text-red-400'}`}>
                        {installResult.success ? 'Instalación completada' : 'Falló la instalación'}
                      </span>
                    )}
                  </div>
                  {installResult && (
                    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs text-gray-200 max-h-60 overflow-y-auto">
                      <p className="text-gray-400 mb-1">Resumen</p>
                      <pre className="whitespace-pre-wrap">{JSON.stringify(installResult, null, 2)}</pre>
                    </div>
                  )}
                </div>
              )}

              {/* Controles */}
              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={prevStep}
                  disabled={installStep === 0}
                  className="px-4 py-2 rounded-lg border border-gray-700 text-gray-200 hover:border-blue-500 disabled:opacity-40"
                >
                  Atrás
                </button>
                <div className="flex items-center gap-2">
                  <div className="text-xs text-gray-400">
                    Paso {installStep + 1} / {INSTALL_STEPS.length}
                  </div>
                  <button
                    onClick={installStep >= INSTALL_STEPS.length - 1 ? installMetapackages : nextStep}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 shadow-lg"
                  >
                    {installStep >= INSTALL_STEPS.length - 1 ? 'Instalar ahora' : 'Siguiente'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
