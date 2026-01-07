import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheckIcon,
  CloudIcon,
  ArrowPathIcon,
  LockClosedIcon,
  KeyIcon,
  ArrowTopRightOnSquareIcon,
  ClipboardIcon,
  PlayIcon,
  BoltIcon,
  ServerIcon,
  ChartBarSquareIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  UserGroupIcon,
  BuildingOfficeIcon,
  CommandLineIcon
} from '@heroicons/react/24/outline';
import { Card, Button, Alert, Loading } from '../Common';
import api from '../../services/api';
import {
  getTenantInfo,
  syncTenant,
  getRiskySignins,
  getRiskyUsers,
  getAuditLogs,
  startAnalysis,
  initDeviceCode,
  pollDeviceCode,
  cancelDeviceCode
} from '../../services/m365';

const DEFAULT_SCOPES = [
  'User.Read',                // Perfil básico
  'Directory.Read.All',       // Directorio (solo lectura)
  'AuditLog.Read.All',        // Logs de auditoría
  'IdentityRiskEvent.Read.All', // Eventos de riesgo
  'Reports.Read.All',         // Informes (sign-ins, usage)
  'SecurityEvents.Read.All'   // Eventos de seguridad (solo lectura)
];

const TOOL_OPTIONS = [
  // ====== BÁSICO (3) ======
  { id: 'sparrow', label: 'Sparrow', desc: 'Tokens abusados y apps OAuth', icon: '🦅', category: 'BÁSICO' },
  { id: 'hawk', label: 'Hawk', desc: 'Reglas maliciosas, delegaciones y Teams', icon: '🦅', category: 'BÁSICO' },
  { id: 'o365_extractor', label: 'O365', desc: 'Unified Audit Logs completos', icon: '📦', category: 'BÁSICO' },
  
  // ====== RECONOCIMIENTO (3) ======
  { id: 'azurehound', label: 'AzureHound', desc: 'Attack paths BloodHound', icon: '🐕', category: 'RECONOCIMIENTO' },
  { id: 'roadtools', label: 'ROADtools', desc: 'Reconocimiento completo de Azure AD', icon: '🗺️', category: 'RECONOCIMIENTO' },
  { id: 'aadinternals', label: 'AADInternals', desc: 'Red Team Azure AD', icon: '🔓', category: 'RECONOCIMIENTO' },
  
  // ====== AUDITORÍA (3) ======
  { id: 'monkey365', label: 'Monkey365', desc: '300+ checks de seguridad M365', icon: '🐵', category: 'AUDITORÍA' },
  { id: 'crowdstrike_crt', label: 'CrowdStrike', desc: 'Análisis de riesgos Azure/M365', icon: '🦅', category: 'AUDITORÍA' },
  { id: 'maester', label: 'Maester', desc: 'Security testing framework M365', icon: '🎯', category: 'AUDITORÍA' },
  
  // ====== FORENSE (3) ======
  { id: 'm365_extractor', label: 'M365 Extractor', desc: 'Forense Exchange/Teams/OneDrive', icon: '📧', category: 'FORENSE' },
  { id: 'graph', label: 'Graph', desc: 'Microsoft Graph API queries', icon: '📈', category: 'FORENSE' },
  { id: 'cloud_katana', label: 'Cloud', desc: 'IR automation', icon: '⚔️', category: 'FORENSE' }
];

export default function M365() {
  const [tenantInfo, setTenantInfo] = useState(null);
  const [loadingTenant, setLoadingTenant] = useState(true);
  const [riskySignins, setRiskySignins] = useState([]);
  const [riskyUsers, setRiskyUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [analysisForm, setAnalysisForm] = useState(() => ({
    tenantId: '',
    caseId: `IR-M365-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`,
    scope: ['sparrow', 'hawk'],
    daysBack: 90,
    targetUsers: '',
    priority: 'medium'
  }));

  // Multi-tenant y modal de usuarios
  const [tenants, setTenants] = useState([]);
  const [availableCases, setAvailableCases] = useState([]);
  const [m365Users, setM365Users] = useState([]);
  const [showUsersModal, setShowUsersModal] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [showCasesDropdown, setShowCasesDropdown] = useState(false);
  const [caseSearchTerm, setCaseSearchTerm] = useState('');
  const [userSearchTerm, setUserSearchTerm] = useState('');

  const [deviceFlow, setDeviceFlow] = useState(null);
  const [polling, setPolling] = useState(false);
  const pollRef = React.useRef(null);
  const pollAttempts = React.useRef(0);
  
  // Estado de progreso del análisis
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const analysisPollingRef = useRef(null);
  const consoleRef = useRef(null);
  
  // Estado de consola interactiva y opciones de extracción
  const [executionLog, setExecutionLog] = useState([]);
  const [pendingDecision, setPendingDecision] = useState(null);
  const [extractionOptions, setExtractionOptions] = useState({
    includeInactive: false,
    includeExternal: false,
    includeArchived: false,
    includeDeleted: false
  });

  // Auto-scroll de consola cuando se agrega un nuevo log
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [executionLog]);

  const navigate = useNavigate();

  const resolvedTenantId = analysisForm.tenantId || tenantInfo?.tenant_id || '';

  const storedToken = useMemo(() => {
    if (!resolvedTenantId) return null;
    return localStorage.getItem(`azure_token_${resolvedTenantId}`) || null;
  }, [resolvedTenantId]);

  const loadTenant = useCallback(async () => {
    setLoadingTenant(true);
    try {
      const info = await getTenantInfo();
      setTenantInfo(info);
      setAnalysisForm((prev) => ({
        ...prev,
        tenantId: prev.tenantId || info?.tenant_id || ''
      }));
      
      // Validar si hay token almacenado para este tenant
      if (info?.tenant_id) {
        const storedToken = localStorage.getItem(`azure_token_${info.tenant_id}`);
        if (storedToken) {
          const tokenExp = localStorage.getItem(`azure_token_exp_${info.tenant_id}`);
          if (tokenExp && Date.now() < Number(tokenExp)) {
            toast.success('✅ Token Azure AD válido detectado', { autoClose: 2000 });
          } else {
            toast.warn('⚠️ Token expirado - Inicia Device Code nuevamente');
          }
        }
      }
    } catch (error) {
      console.error('Error loading tenant info', error);
      toast.error('No se pudo cargar información de Microsoft 365');
    } finally {
      setLoadingTenant(false);
    }
  }, []);

  const loadSignals = useCallback(async () => {
    try {
      const [signins, users, audits] = await Promise.all([
        getRiskySignins(),
        getRiskyUsers(),
        getAuditLogs(7)
      ]);
      setRiskySignins(signins.signins || []);
      setRiskyUsers(users.users || []);
      setAuditLogs(audits.logs || []);
    } catch (error) {
      console.error('Error loading M365 signals', error);
    }
  }, []);

  useEffect(() => {
    loadTenant();
    loadSignals();
    loadTenants();
    loadCases();
    loadM365Users();
  }, [loadTenant, loadSignals]);

  // Cargar tenants disponibles
  const loadTenants = async () => {
    try {
      const { data } = await api.get('/tenants/');
      setTenants(data.tenants || []);
    } catch (error) {
      console.error('Error loading tenants:', error);
      setTenants([]);
    }
  };

  // Cargar casos disponibles
  const loadCases = async () => {
    try {
      const { data } = await api.get('/api/v41/investigations');
      // Mapear id -> case_id para compatibilidad
      const cases = (data.investigations || []).map(c => ({
        ...c,
        case_id: c.id || c.case_id,
        title: c.name || c.title
      }));
      setAvailableCases(cases);
    } catch (error) {
      console.error('Error loading cases:', error);
    }
  };

  // Cargar usuarios de M365
  const loadM365Users = async () => {
    try {
      const { data } = await api.get('/dashboard/m365/users');
      setM365Users(data.users || []);
    } catch (error) {
      console.error('Error loading M365 users:', error);
    }
  };

  // Poll estado del análisis activo (GLOBAL - persiste entre páginas)
  useEffect(() => {
    if (!activeAnalysis) return;
    
    const pollAnalysisStatus = async () => {
      try {
        const { data } = await api.get(`/forensics/case/${activeAnalysis.case_id}/status`);
        setAnalysisStatus(data);
        
        if (data.status === 'completed' || data.status === 'failed') {
          setAnalysisRunning(false);
          if (analysisPollingRef.current) {
            clearInterval(analysisPollingRef.current);
            analysisPollingRef.current = null;
          }
          
          if (data.status === 'completed') {
            // Notificación persistente con sonido
            const notification = new Notification('✅ Análisis M365 Completado', {
              body: `El caso ${activeAnalysis.caseId} ha finalizado exitosamente`,
              icon: '/favicon.ico',
              requireInteraction: true,
              tag: activeAnalysis.caseId
            });
            
            notification.onclick = () => {
              window.focus();
              navigate(`/graph?case=${activeAnalysis.caseId}`);
            };
            
            toast.success(`✅ Análisis M365 completado - ${activeAnalysis.caseId}`, {
              autoClose: false,
              onClick: () => navigate(`/graph?case=${activeAnalysis.caseId}`)
            });
          } else {
            toast.error('❌ El análisis falló: ' + (data.error || 'Error desconocido'), {
              autoClose: false
            });
          }
        }
      } catch (error) {
        console.error('Error polling analysis status:', error);
      }
    };
    
    // Solicitar permiso para notificaciones
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    
    pollAnalysisStatus(); // Ejecutar inmediatamente
    analysisPollingRef.current = setInterval(pollAnalysisStatus, 3000); // Cada 3 segundos
    
    return () => {
      if (analysisPollingRef.current) {
        clearInterval(analysisPollingRef.current);
      }
    };
  }, [activeAnalysis]);

  // Poll device code
  useEffect(() => {
    if (!polling || !deviceFlow) return;
    if (pollRef.current) {
      clearInterval(pollRef.current);
    }
    pollAttempts.current = 0;

    const interval = setInterval(async () => {
      try {
        pollAttempts.current += 1;
        // Limitar intentos para evitar bucles infinitos
        if (pollAttempts.current > 12) { // ~1 min si interval=5s
          toast.warn('Timeout esperando autenticación. Inicia el flujo de nuevo.');
          clearInterval(interval);
          pollRef.current = null;
          setPolling(false);
          setDeviceFlow(null);
          return;
        }

        const resp = await pollDeviceCode({
          deviceCode: deviceFlow.device_code,
          tenantId: resolvedTenantId
        });

        if (resp.status === 'pending') {
          return;
        }

        if (resp.status === 'success') {
          localStorage.setItem(`azure_token_${resolvedTenantId}`, resp.access_token);
          if (resp.refresh_token) {
            localStorage.setItem(`azure_refresh_${resolvedTenantId}`, resp.refresh_token);
          }
          const expiresAt = Date.now() + (resp.expires_in || 3600) * 1000;
          localStorage.setItem(`azure_token_exp_${resolvedTenantId}`, String(expiresAt));
          toast.success('Autenticación M365 completada');
          // Limpieza de polling
          clearInterval(interval);
          pollRef.current = null;
          setPolling(false);
          setDeviceFlow(null);
        }
      } catch (error) {
        const detail = error.response?.data?.detail || error.message;
        if (error.response?.status === 410) {
          toast.warn('Código expirado, inicia de nuevo');
        } else {
          toast.error(`Error autenticando: ${detail || 'timeout/polling'}`);
        }
        clearInterval(interval);
        pollRef.current = null;
        setPolling(false);
        setDeviceFlow(null);
      }
    }, (deviceFlow.interval || 5) * 1000);

    pollRef.current = interval;
    return () => {
      clearInterval(interval);
      pollRef.current = null;
    };
  }, [polling, deviceFlow, resolvedTenantId]);

  const handleSync = async () => {
    try {
      const res = await syncTenant();
      toast.success('Tenant sincronizado');
      setTenantInfo((prev) => ({
        ...prev,
        last_sync: new Date().toISOString(),
        tenant_sync: res.tenant_sync,
        users_sync: res.users_sync
      }));
    } catch (error) {
      toast.error('Sync falló, revisa credenciales');
    }
  };

  const handleStartDeviceCode = async () => {
    if (!resolvedTenantId) {
      toast.warn('Define el Tenant ID');
      return;
    }
    try {
      const flow = await initDeviceCode({ tenantId: resolvedTenantId, scopes: DEFAULT_SCOPES });
      setDeviceFlow(flow);
      setPolling(true);
      toast.info('Código generado. Abre microsoft.com/devicelogin');
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      toast.error(`No se pudo iniciar Device Code: ${detail}`);
    }
  };

  const handleCancelDeviceCode = async () => {
    if (!deviceFlow) return;
    try {
      await cancelDeviceCode({ deviceCode: deviceFlow.device_code, tenantId: resolvedTenantId });
    } catch (error) {
      // Silencio: cancel manual
    } finally {
      setDeviceFlow(null);
      setPolling(false);
    }
  };

  const handleAnalyze = async () => {
    if (!resolvedTenantId) {
      toast.warn('Define el Tenant ID');
      return;
    }
    if (!analysisForm.scope.length) {
      toast.warn('Selecciona al menos una herramienta (Sparrow/Hawk/O365)');
      return;
    }
    
    // Limpiar consola anterior
    setExecutionLog([]);
    setAnalysisRunning(true);
    
    try {
      // Agregar log inicial
      setExecutionLog(prev => [...prev, {
        type: 'info',
        message: `Iniciando análisis forense para caso ${analysisForm.caseId}...`
      }]);

      // Preparar lista de usuarios objetivo
      const targetUsers = selectedUsers.length > 0 
        ? selectedUsers.map(u => u.userPrincipalName || u.mail)
        : (analysisForm.targetUsers
            ? analysisForm.targetUsers.split(',').map((u) => u.trim()).filter(Boolean)
            : []);

      setExecutionLog(prev => [...prev, {
        type: 'info',
        message: `Herramientas: ${analysisForm.scope.length} seleccionadas`
      }]);

      if (targetUsers.length > 0) {
        setExecutionLog(prev => [...prev, {
          type: 'info',
          message: `Usuarios objetivo: ${targetUsers.length}`
        }]);
      }

      // Mostrar opciones de extracción habilitadas
      const enabledOptions = [];
      if (extractionOptions.includeInactive) enabledOptions.push('Usuarios inactivos');
      if (extractionOptions.includeExternal) enabledOptions.push('Usuarios externos');
      if (extractionOptions.includeArchived) enabledOptions.push('Buzones archivados');
      if (extractionOptions.includeDeleted) enabledOptions.push('Objetos eliminados');
      
      if (enabledOptions.length > 0) {
        setExecutionLog(prev => [...prev, {
          type: 'info',
          message: `Opciones activas: ${enabledOptions.join(', ')}`
        }]);
      }

      const result = await startAnalysis({
        tenantId: resolvedTenantId,
        caseId: analysisForm.caseId,
        scope: analysisForm.scope,
        targetUsers,
        daysBack: analysisForm.daysBack,
        priority: analysisForm.priority
      });
      
      setExecutionLog(prev => [...prev, {
        type: 'success',
        message: `✅ Análisis iniciado - ID: ${result.task_id || result.case_id}`
      }]);
      
      toast.success(result.message || 'Análisis M365 iniciado 🚀');
      
      // Guardar análisis activo para tracking de progreso
      setActiveAnalysis({
        taskId: result.task_id || result.case_id || analysisForm.caseId,
        analysisId: result.analysis_id || `FA-${Date.now()}`,
        caseId: analysisForm.caseId,
        case_id: analysisForm.caseId, // Para compatibilidad con polling
        scope: analysisForm.scope,
        startedAt: new Date().toISOString()
      });
      setAnalysisStatus({ status: 'running', progress_percentage: 5, current_step: 'Inicializando...' });
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      setExecutionLog(prev => [...prev, {
        type: 'error',
        message: `❌ Error: ${detail}`
      }]);
      toast.error(`Error al iniciar análisis: ${detail}`);
    } finally {
      setAnalysisRunning(false);
    }
  };

  const handleDecision = (answer) => {
    if (!pendingDecision) return;
    
    setExecutionLog(prev => [...prev, {
      type: 'success',
      message: `Usuario respondió: ${answer ? '✅ SÍ' : '❌ NO'} a "${pendingDecision.question}"`
    }]);
    
    // Aquí se procesaría la decisión del usuario
    // Por ahora solo mostramos que fue capturada
    setPendingDecision(null);
  };


  const connectionBadge = tenantInfo?.connected ? (
    <span className="px-3 py-1 bg-green-900 text-green-200 rounded-full text-xs">🟢 Conectado</span>
  ) : (
    <span className="px-3 py-1 bg-yellow-900 text-yellow-200 rounded-full text-xs">🟠 Sin conexión</span>
  );

  const usersLabel = (() => {
    if (!tenantInfo?.users) return 'N/A';
    if (typeof tenantInfo.users === 'object') {
      const total = tenantInfo.users.total ?? 0;
      const enabled = tenantInfo.users.enabled ?? tenantInfo.users.active ?? 0;
      const disabled = tenantInfo.users.disabled ?? 0;
      return `${enabled}/${total} activos • ${disabled} deshabilitados`;
    }
    return tenantInfo.users;
  })();

  if (loadingTenant && !tenantInfo) {
    return <Loading message="Cargando Microsoft 365..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">☁️ Microsoft 365</h1>
          <p className="text-gray-400">Análisis forense y autenticación vía Device Code (Azure Shell / Browser)</p>
        </div>
        <div className="flex items-center gap-2">{connectionBadge}</div>
      </div>

      {!storedToken && !tenantInfo?.connected && (
        <Alert
          type="warning"
          title="Inicia sesión en Azure"
          message="Usa Device Code Flow (compatible Azure Cloud Shell y navegador) para obtener un token con los permisos Graph de la versión 1 (AuditLog.Read.All, Directory.Read.All, IdentityRiskEvent.Read.All)."
        />
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <Card
            title="Autenticación Azure (Device Code)"
            icon={LockClosedIcon}
            actions={
              <Button variant="secondary" onClick={handleSync}>
                🔄 Sync Tenant
              </Button>
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Tenant ID</label>
                <input
                  value={analysisForm.tenantId}
                  onChange={(e) => setAnalysisForm({ ...analysisForm, tenantId: e.target.value })}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="input-base w-full"
                  readOnly={tenantInfo?.connected}
                  disabled={tenantInfo?.connected}
                  title={tenantInfo?.connected ? "El Tenant ID no puede modificarse cuando está conectado" : ""}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {tenantInfo?.connected 
                    ? "🔒 Tenant conectado - ID bloqueado" 
                    : "Usa el Tenant configurado en .env o el recuperado del backend."}
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <Button variant="primary" onClick={handleStartDeviceCode} disabled={polling}>
                  <KeyIcon className="w-4 h-4" />
                  Iniciar Device Code
                </Button>
                {deviceFlow && (
                  <Button variant="secondary" onClick={handleCancelDeviceCode}>
                    Cancelar flujo
                  </Button>
                )}
              </div>
            </div>

            {deviceFlow && (
              <div className="mt-4 p-4 rounded-lg border border-blue-700 bg-blue-900/30">
                <p className="text-sm text-blue-200 mb-2">Abre <strong>https://microsoft.com/devicelogin</strong> y pega este código:</p>
                <div className="flex items-center gap-3">
                  <div className="px-4 py-2 bg-black text-white font-mono text-lg rounded">{deviceFlow.user_code}</div>
                  <Button
                    variant="secondary"
                    onClick={() => navigator.clipboard.writeText(deviceFlow.user_code)}
                  >
                    <ClipboardIcon className="w-4 h-4" />
                    Copiar código
                  </Button>
                  <Button variant="ghost" onClick={() => window.open(deviceFlow.verification_uri, '_blank')}>
                    <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                    Abrir portal
                  </Button>
                </div>
                <p className="text-xs text-blue-100 mt-2">
                  Tiempo restante: ~{Math.round((deviceFlow.expires_in || 900) / 60)} min • Intervalo de polling: {deviceFlow.interval || 5}s
                </p>
              </div>
            )}

            {storedToken && !deviceFlow && (
              <div className="mt-3 text-sm text-green-200 flex items-center gap-2">
                <ShieldCheckIcon className="w-4 h-4" />
                Token almacenado en navegador para el tenant {resolvedTenantId}.
              </div>
            )}

            <div className="mt-4 text-xs text-gray-400">
              <p className="font-semibold text-gray-300 mb-1">Permisos solicitados (solo lectura):</p>
              <ul className="list-disc list-inside grid grid-cols-1 md:grid-cols-2 gap-1">
                {DEFAULT_SCOPES.map((scope) => (
                  <li key={scope} className="text-gray-400">{scope}</li>
                ))}
              </ul>
              <p className="mt-2 text-gray-500">Requeridos para extraer señales del tenant y enviarlas a análisis en el plazo configurado.</p>
            </div>
          </Card>

          <Card title="Ejecutar Análisis Forense M365" icon={CloudIcon}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Selector de Caso con Dropdown y Buscador */}
              <div className="relative">
                <label className="block text-sm text-gray-400 mb-1">Caso</label>
                <div className="relative">
                  <input
                    value={analysisForm.caseId}
                    onChange={(e) => {
                      setAnalysisForm({ ...analysisForm, caseId: e.target.value });
                      setCaseSearchTerm(e.target.value);
                      setShowCasesDropdown(true);
                    }}
                    onFocus={() => setShowCasesDropdown(true)}
                    placeholder="Escribe o selecciona un caso..."
                    className="input-base w-full pr-10"
                  />
                  <MagnifyingGlassIcon className="w-5 h-5 text-gray-400 absolute right-3 top-3" />
                </div>
                
                {/* Dropdown de casos */}
                {showCasesDropdown && (
                  <div className="absolute z-50 w-full mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                    <div className="p-2">
                      <button
                        onClick={() => {
                          setAnalysisForm({ ...analysisForm, caseId: `IR-M365-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}` });
                          setShowCasesDropdown(false);
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-blue-900/30 rounded text-sm text-blue-300 border border-blue-700 mb-2"
                      >
                        ➕ Crear nuevo caso
                      </button>
                    </div>
                    
                    {availableCases
                      .filter(c => c.case_id && (
                        c.case_id.toLowerCase().includes(caseSearchTerm.toLowerCase()) || 
                        c.title?.toLowerCase().includes(caseSearchTerm.toLowerCase())
                      ))
                      .map(c => (
                        <button
                          key={c.case_id}
                          onClick={() => {
                            setAnalysisForm({ ...analysisForm, caseId: c.case_id });
                            setShowCasesDropdown(false);
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-gray-700 text-sm border-b border-gray-700 last:border-b-0"
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium text-white">{c.case_id}</p>
                              <p className="text-xs text-gray-400">{c.title || 'Sin título'}</p>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs ${
                              c.status === 'active' ? 'bg-green-500/20 text-green-400' :
                              c.status === 'closed' ? 'bg-gray-500/20 text-gray-400' :
                              'bg-yellow-500/20 text-yellow-400'
                            }`}>
                              {c.status || 'pending'}
                            </span>
                          </div>
                        </button>
                      ))}
                    
                    {availableCases.filter(c => 
                      c.case_id && (
                        c.case_id.toLowerCase().includes(caseSearchTerm.toLowerCase()) || 
                        c.title?.toLowerCase().includes(caseSearchTerm.toLowerCase())
                      )
                    ).length === 0 && (
                      <div className="p-4 text-center text-gray-500 text-sm">
                        No se encontraron casos
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Días de historial</label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={analysisForm.daysBack}
                  onChange={(e) => setAnalysisForm({ ...analysisForm, daysBack: Number(e.target.value) })}
                  className="input-base w-full"
                />
              </div>
              
              {/* Selector de Usuarios con Modal */}
              <div className="md:col-span-2">
                <label className="block text-sm text-gray-400 mb-1 flex items-center justify-between">
                  <span>Usuarios objetivo</span>
                  <button
                    onClick={() => setShowUsersModal(true)}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    <UserGroupIcon className="w-4 h-4" />
                    Seleccionar del directorio
                  </button>
                </label>
                <div className="relative">
                  <input
                    value={selectedUsers.map(u => u.userPrincipalName || u.mail).join(', ')}
                    readOnly
                    placeholder="Haz click arriba para seleccionar usuarios..."
                    className="input-base w-full pr-10 cursor-pointer"
                    onClick={() => setShowUsersModal(true)}
                  />
                  {selectedUsers.length > 0 && (
                    <button
                      onClick={() => setSelectedUsers([])}
                      className="absolute right-3 top-3 text-gray-400 hover:text-red-400"
                    >
                      <XMarkIcon className="w-5 h-5" />
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedUsers.length > 0 ? `${selectedUsers.length} usuario(s) seleccionado(s)` : 'Opcional - deja vacío para todos los usuarios'}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <div className="text-sm text-gray-400 mb-3 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <BoltIcon className="w-4 h-4" /> Selecciona herramientas (local + nube)
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setAnalysisForm(prev => ({ ...prev, scope: TOOL_OPTIONS.map(t => t.id) }))}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    ✓ Todas
                  </button>
                  <button
                    onClick={() => setAnalysisForm(prev => ({ ...prev, scope: [] }))}
                    className="text-xs text-gray-400 hover:text-gray-300"
                  >
                    ✗ Ninguna
                  </button>
                </div>
              </div>
              
              {/* Agrupar por categoría */}
              {['BÁSICO', 'RECONOCIMIENTO', 'AUDITORÍA', 'FORENSE'].map(category => (
                <div key={category} className="mb-4">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">{category} ({TOOL_OPTIONS.filter(t => t.category === category).length})</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {TOOL_OPTIONS.filter(t => t.category === category).map((tool) => (
                      <label
                        key={tool.id}
                        className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 hover:scale-105 ${
                          analysisForm.scope.includes(tool.id)
                            ? 'border-blue-500 bg-blue-900/20 shadow-lg shadow-blue-500/30'
                            : 'border-gray-700 hover:border-blue-500 hover:bg-gray-800'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={analysisForm.scope.includes(tool.id)}
                            onChange={(e) => {
                              const checked = e.target.checked;
                              setAnalysisForm((prev) => ({
                                ...prev,
                                scope: checked
                                  ? [...prev.scope, tool.id]
                                  : prev.scope.filter((s) => s !== tool.id)
                              }));
                            }}
                            className="w-4 h-4"
                          />
                          <span className="text-lg">{tool.icon}</span>
                          <span className="font-medium text-sm">{tool.label.split(' ')[0]}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1 ml-6">{tool.desc}</p>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 flex gap-2">
              <Button variant="primary" onClick={handleAnalyze} loading={analysisRunning}>
                <PlayIcon className="w-4 h-4" />
                Iniciar análisis
              </Button>
              <Button variant="secondary" onClick={handleSync}>
                <ArrowPathIcon className="w-4 h-4" />
                Actualizar señales
              </Button>
            </div>

            {/* Panel de Progreso del Análisis */}
            {activeAnalysis && analysisStatus && (
              <div className="mt-4 p-4 rounded-lg border border-gray-700 bg-gray-800/50">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2">
                    <ChartBarSquareIcon className="w-4 h-4 text-blue-400" />
                    Progreso del Análisis - Caso: {activeAnalysis.caseId}
                  </h4>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    analysisStatus.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    analysisStatus.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                    analysisStatus.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {analysisStatus.status === 'completed' ? '✅ Completado' :
                     analysisStatus.status === 'failed' ? '❌ Fallido' :
                     analysisStatus.status === 'running' ? '🔄 En progreso' :
                     '⏳ En cola'}
                  </span>
                </div>

                {/* Barra de progreso */}
                <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${analysisStatus.progress_percentage || 0}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-400 mb-3">
                  <span>{analysisStatus.current_step || 'Iniciando...'}</span>
                  <span>{analysisStatus.progress_percentage || 0}%</span>
                </div>

                {/* Herramientas ejecutándose */}
                <div className="flex flex-wrap gap-2 mb-3">
                  {activeAnalysis.scope?.map((tool) => (
                    <span key={tool} className={`px-2 py-1 rounded text-xs ${
                      analysisStatus.completed_tools?.includes(tool) 
                        ? 'bg-green-500/20 text-green-400' 
                        : analysisStatus.current_tool === tool
                          ? 'bg-blue-500/30 text-blue-300 animate-pulse'
                          : 'bg-gray-700 text-gray-400'
                    }`}>
                      {tool === 'sparrow' ? '🦅 Sparrow' : 
                       tool === 'hawk' ? '🦅 Hawk' : 
                       tool === 'o365extractor' ? '📧 O365' : tool}
                    </span>
                  ))}
                </div>

                {/* Resultados y acciones */}
                {analysisStatus.status === 'completed' && (
                  <div className="flex gap-2 flex-wrap">
                    <Button 
                      variant="primary" 
                      onClick={() => navigate(`/graph?case=${activeAnalysis.caseId}`)}
                    >
                      <ChartBarSquareIcon className="w-4 h-4" />
                      Ver Grafo de Ataque
                    </Button>
                    <Button 
                      variant="secondary"
                      onClick={() => navigate(`/cases/${activeAnalysis.caseId}`)}
                    >
                      📋 Ver Caso
                    </Button>
                    {analysisStatus.evidence_count > 0 && (
                      <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-xs flex items-center gap-1">
                        📁 {analysisStatus.evidence_count} archivos de evidencia
                      </span>
                    )}
                  </div>
                )}

                {analysisStatus.status === 'failed' && analysisStatus.error && (
                  <div className="p-2 bg-red-900/30 border border-red-700 rounded text-xs text-red-300">
                    Error: {analysisStatus.error}
                  </div>
                )}

                {/* Info del análisis */}
                <div className="mt-2 text-xs text-gray-500">
                  Iniciado: {new Date(activeAnalysis.startedAt).toLocaleString()}
                  {analysisStatus.estimated_completion && (
                    <span className="ml-3">• Estimado: {analysisStatus.estimated_completion}</span>
                  )}
                </div>
              </div>
            )}
          </Card>

          {/* Tarjeta de Comandos Automatizados */}
          <Card title="Comandos Automatizados" icon={CommandLineIcon}>
            <div className="space-y-3">
              {/* Consola de Ejecución */}
              <div 
                ref={consoleRef}
                className="bg-gray-950 border border-gray-700 rounded-lg p-4 font-mono text-sm max-h-96 overflow-y-auto"
              >
                <div className="space-y-2 text-gray-200">
                  {/* Línea de estado inicial */}
                  {!analysisRunning && analysisForm.scope.length === 0 && (
                    <div className="text-gray-500">
                      <span className="text-blue-400">$</span> Selecciona herramientas para iniciar análisis automatizado
                    </div>
                  )}

                  {/* Línea de espera */}
                  {analysisRunning && !executionLog && (
                    <div className="text-gray-400">
                      <span className="text-blue-400">$</span> Iniciando extracción de datos...
                      <span className="animate-pulse">▌</span>
                    </div>
                  )}

                  {/* Log de ejecución */}
                  {executionLog?.map((log, idx) => (
                    <div 
                      key={idx}
                      className={`flex items-start gap-2 ${
                        log.type === 'error' ? 'text-red-400' :
                        log.type === 'success' ? 'text-green-400' :
                        log.type === 'warning' ? 'text-yellow-400' :
                        log.type === 'prompt' ? 'text-purple-400' :
                        'text-gray-300'
                      }`}
                    >
                      <span className="text-blue-400 flex-shrink-0">$</span>
                      <span>{log.message}</span>
                    </div>
                  ))}

                  {/* Línea de cursor si está en progreso */}
                  {analysisRunning && executionLog && (
                    <div className="text-gray-400 animate-pulse">
                      <span className="text-blue-400">$</span> ▌
                    </div>
                  )}
                </div>
              </div>

              {/* Panel de Decisión Interactiva */}
              {pendingDecision && (
                <div className="bg-purple-900/20 border border-purple-700 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-purple-400">❓</span>
                    <p className="text-sm text-purple-300 font-medium">{pendingDecision.question}</p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="primary" 
                      onClick={() => handleDecision(true)}
                      className="text-xs"
                    >
                      ✅ Sí
                    </Button>
                    <Button 
                      variant="secondary" 
                      onClick={() => handleDecision(false)}
                      className="text-xs"
                    >
                      ❌ No
                    </Button>
                  </div>
                </div>
              )}

              {/* Opciones de Extracción */}
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 space-y-2">
                <p className="text-xs font-medium text-gray-300 mb-2">Opciones de extracción:</p>
                
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={extractionOptions.includeInactive} 
                    onChange={(e) => setExtractionOptions({...extractionOptions, includeInactive: e.target.checked})}
                    className="w-3 h-3"
                  />
                  <span className="text-xs text-gray-300">Incluir usuarios inactivos (&gt;90 días)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={extractionOptions.includeExternal} 
                    onChange={(e) => setExtractionOptions({...extractionOptions, includeExternal: e.target.checked})}
                    className="w-3 h-3"
                  />
                  <span className="text-xs text-gray-300">Incluir usuarios externos (B2B)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={extractionOptions.includeArchived} 
                    onChange={(e) => setExtractionOptions({...extractionOptions, includeArchived: e.target.checked})}
                    className="w-3 h-3"
                  />
                  <span className="text-xs text-gray-300">Incluir buzones archivados</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={extractionOptions.includeDeleted} 
                    onChange={(e) => setExtractionOptions({...extractionOptions, includeDeleted: e.target.checked})}
                    className="w-3 h-3"
                  />
                  <span className="text-xs text-gray-300">Incluir objetos eliminados (últimos 30 días)</span>
                </label>
              </div>

              {/* Información del Análisis */}
              {activeAnalysis && (
                <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 text-xs text-blue-300 space-y-1">
                  <div><span className="font-medium">ID Análisis:</span> {activeAnalysis.analysisId}</div>
                  <div><span className="font-medium">Herramientas:</span> {analysisForm.scope.length} seleccionadas</div>
                  <div><span className="font-medium">Caso:</span> {activeAnalysis.caseId}</div>
                  {activeAnalysis.startedAt && (
                    <div><span className="font-medium">Iniciado:</span> {new Date(activeAnalysis.startedAt).toLocaleString()}</div>
                  )}
                </div>
              )}
            </div>
          </Card>

          <Card title="Señales de Identidad y Auditoría" icon={ServerIcon}>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <SignalBlock title="Risky Sign-ins" count={riskySignins.length} items={riskySignins} type="signin" />
              <SignalBlock title="Risky Users" count={riskyUsers.length} items={riskyUsers} type="user" />
              <SignalBlock title="Audit Logs" count={auditLogs.length} items={auditLogs} type="audit" />
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card 
            title="Tenant" 
            icon={BuildingOfficeIcon}
            actions={
              tenants.length > 1 && (
                <select 
                  value={analysisForm.tenantId}
                  onChange={(e) => {
                    setAnalysisForm({ ...analysisForm, tenantId: e.target.value });
                    // Recargar info del tenant seleccionado
                    loadTenant();
                  }}
                  className="text-sm bg-gray-800 border border-gray-700 rounded px-3 py-1 text-white"
                >
                  <option value="">Seleccionar tenant...</option>
                  {tenants.map(t => (
                    <option key={t.tenant_id} value={t.tenant_id}>
                      {t.name || t.tenant_id.slice(0, 8)}...
                    </option>
                  ))}
                </select>
              )
            }
          >
            {tenantInfo?.connected ? (
              <div className="space-y-2 text-sm">
                <div><span className="text-gray-400">Tenant ID:</span> {tenantInfo.tenant_id}</div>
                <div><span className="text-gray-400">Organización:</span> {tenantInfo.organization}</div>
                <div><span className="text-gray-400">Usuarios:</span> {usersLabel}</div>
                <div className="mt-2">
                  <div className="text-gray-400 mb-1">Dominios verificados:</div>
                  <ul className="list-disc list-inside text-gray-200 text-xs">
                    {(tenantInfo.domains || []).map((d, idx) => (
                      <li key={idx}>{d.name || d}</li>
                    ))}
                  </ul>
                </div>
                
                {tenants.length > 1 && (
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <p className="text-xs text-gray-500">Tienes {tenants.length} tenants configurados</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-400 text-sm">No conectado. Configura el Tenant ID y ejecuta Device Code.</p>
            )}
          </Card>

          <Card title="Instrucciones Azure Shell" icon={ArrowTopRightOnSquareIcon}>
            <ol className="list-decimal list-inside text-sm text-gray-300 space-y-2">
              <li>Click en <strong>Iniciar Device Code</strong> para generar el código.</li>
              <li>Abre <code className="bg-gray-800 px-1">https://microsoft.com/devicelogin</code> (Azure Cloud Shell o navegador) y pega el código.</li>
              <li>Completa MFA y acepta permisos (Graph: AuditLog.Read.All, Directory.Read.All, IdentityRiskEvent.Read.All).</li>
              <li>El token se guarda localmente y se usa para Sparrow/Hawk/O365 Extractor.</li>
            </ol>
          </Card>

          <Card title="Estado de Token" icon={ShieldCheckIcon}>
            {storedToken ? (
              <div className="text-sm text-green-200">
                ✅ Token presente en navegador para {resolvedTenantId}. Exp: {formatExpiry(resolvedTenantId)}
              </div>
            ) : (
              <div className="text-sm text-gray-400">No hay token almacenado. Inicia Device Code para obtenerlo.</div>
            )}
          </Card>
        </div>
      </div>

      {/* Modal de selección de usuarios */}
      {showUsersModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <UserGroupIcon className="w-5 h-5 text-blue-400" />
                Seleccionar Usuarios de M365
              </h3>
              <button 
                onClick={() => {
                  setShowUsersModal(false);
                  setUserSearchTerm('');
                }}
                className="text-gray-400 hover:text-white"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>
            
            <div className="p-4">
              <input
                type="text"
                placeholder="🔍 Buscar usuarios..."
                value={userSearchTerm}
                className="input-base w-full mb-4"
                onChange={(e) => setUserSearchTerm(e.target.value)}
              />
              
              <div className="space-y-1 max-h-96 overflow-y-auto pr-2">
                {m365Users
                  .filter(user => {
                    // Filtrar usuarios sin datos válidos
                    if (!user.displayName && !user.userPrincipalName && !user.mail) {
                      return false;
                    }
                    
                    // Aplicar búsqueda
                    if (!userSearchTerm) return true;
                    
                    const term = userSearchTerm.toLowerCase();
                    const displayName = (user.displayName || '').toLowerCase();
                    const email = (user.userPrincipalName || user.mail || '').toLowerCase();
                    
                    return displayName.includes(term) || email.includes(term);
                  })
                  .map((user, idx) => {
                  const isSelected = selectedUsers.some(u => u.id === user.id);
                  return (
                    <label
                      key={user.id || idx}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected 
                          ? 'border-blue-500 bg-blue-900/20' 
                          : 'border-gray-700 hover:border-blue-500 hover:bg-gray-800'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedUsers([...selectedUsers, user]);
                          } else {
                            setSelectedUsers(selectedUsers.filter(u => u.id !== user.id));
                          }
                        }}
                        className="w-4 h-4"
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-white">
                          {user.displayName || user.userPrincipalName}
                        </p>
                        <p className="text-xs text-gray-400">
                          {user.userPrincipalName || user.mail}
                        </p>
                      </div>
                      {user.accountEnabled === false && (
                        <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">
                          Deshabilitado
                        </span>
                      )}
                    </label>
                  );
                })}
                
                {m365Users.filter(user => {
                  if (!user.displayName && !user.userPrincipalName && !user.mail) return false;
                  if (!userSearchTerm) return true;
                  const term = userSearchTerm.toLowerCase();
                  const displayName = (user.displayName || '').toLowerCase();
                  const email = (user.userPrincipalName || user.mail || '').toLowerCase();
                  return displayName.includes(term) || email.includes(term);
                }).length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <p className="mb-2">
                      {userSearchTerm 
                        ? 'No se encontraron usuarios con ese criterio' 
                        : 'No hay usuarios disponibles'}
                    </p>
                    {!userSearchTerm && (
                      <button
                        onClick={loadM365Users}
                        className="text-sm text-blue-400 hover:text-blue-300"
                      >
                        Recargar usuarios
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
            
            <div className="p-4 border-t border-gray-700 flex items-center justify-between">
              <p className="text-sm text-gray-400">
                {selectedUsers.length} usuario(s) seleccionado(s)
              </p>
              <div className="flex gap-2">
                <Button 
                  variant="secondary" 
                  onClick={() => setSelectedUsers([])}
                >
                  Limpiar selección
                </Button>
                <Button 
                  variant="primary" 
                  onClick={() => {
                    setAnalysisForm({
                      ...analysisForm,
                      targetUsers: selectedUsers.map(u => u.userPrincipalName || u.mail).join(',')
                    });
                    setShowUsersModal(false);
                    setUserSearchTerm('');
                  }}
                >
                  Aplicar ({selectedUsers.length})
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Consola de Ejecución Animada - Persistente con Portal */}
      {activeAnalysis && analysisStatus && analysisStatus.status === 'running' && createPortal(
        <div className="fixed bottom-4 right-4 w-96 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden z-40 animate-slide-up">
          <div className="p-3 bg-gradient-to-r from-blue-900 to-purple-900 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                <CommandLineIcon className="w-4 h-4 animate-pulse" />
                Consola de Ejecución
              </h4>
              <span className="text-xs bg-blue-500/30 px-2 py-1 rounded text-blue-300">
                {analysisStatus.progress_percentage || 0}%
              </span>
            </div>
          </div>
          
          <div className="p-4 bg-black/50 max-h-64 overflow-y-auto font-mono text-xs">
            {/* Logs simulados de ejecución */}
            <div className="space-y-1">
              <p className="text-green-400">$ Iniciando análisis forense M365...</p>
              <p className="text-gray-400">→ Caso: {activeAnalysis.caseId}</p>
              <p className="text-gray-400">→ Tenant: {analysisForm.tenantId}</p>
              <p className="text-gray-400">→ Herramientas: {activeAnalysis.scope?.join(', ')}</p>
              <br />
              
              {activeAnalysis.scope?.map((tool, idx) => {
                const isCompleted = analysisStatus.completed_tools?.includes(tool);
                const isCurrent = analysisStatus.current_tool === tool;
                
                return (
                  <div key={tool} className="mb-2">
                    {isCompleted ? (
                      <>
                        <p className="text-blue-400">
                          {tool === 'sparrow' ? '🦅 Sparrow' : 
                           tool === 'hawk' ? '🦅 Hawk' : 
                           tool === 'o365_extractor' ? '📧 O365 Extractor' : tool}
                          ... <span className="text-green-400">✓ Completado</span>
                        </p>
                        <p className="text-gray-500 ml-4">└─ Evidencia capturada</p>
                      </>
                    ) : isCurrent ? (
                      <>
                        <p className="text-yellow-400 animate-pulse">
                          {tool === 'sparrow' ? '🦅 Sparrow' : 
                           tool === 'hawk' ? '🦅 Hawk' : 
                           tool === 'o365_extractor' ? '📧 O365 Extractor' : tool}
                          ... <span className="text-yellow-300">⏳ Ejecutando</span>
                        </p>
                        <p className="text-gray-400 ml-4 animate-pulse">└─ {analysisStatus.current_step || 'Procesando...'}</p>
                      </>
                    ) : (
                      <p className="text-gray-600">
                        {tool === 'sparrow' ? '🦅 Sparrow' : 
                         tool === 'hawk' ? '🦅 Hawk' : 
                         tool === 'o365_extractor' ? '📧 O365 Extractor' : tool}
                        ... <span className="text-gray-500">⏸️ Pendiente</span>
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
          
          <div className="p-2 bg-gray-900 border-t border-gray-700">
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div 
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 rounded-full transition-all duration-500 animate-pulse"
                style={{ width: `${analysisStatus.progress_percentage || 0}%` }}
              />
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Click handler para cerrar dropdowns */}
      {(showCasesDropdown || showUsersModal) && (
        <div 
          className="fixed inset-0 z-30" 
          onClick={() => {
            setShowCasesDropdown(false);
          }}
        />
      )}
    </div>
  );
}

function SignalBlock({ title, count, items, type }) {
  const renderItem = (item, idx) => {
    if (type === 'signin') {
      return (
        <div key={idx} className="p-2 rounded bg-gray-800 border border-gray-700 text-xs space-y-1">
          <div className="flex justify-between text-gray-300">
            <span>{item.userDisplayName || item.userPrincipalName || 'Unknown'}</span>
            <span className="text-red-300">{item.riskLevel || item.riskDetail || ''}</span>
          </div>
          <p className="text-gray-400">IP: {item.ipAddress || 'N/A'}</p>
          <p className="text-gray-500">{item.createdDateTime}</p>
        </div>
      );
    }
    if (type === 'user') {
      return (
        <div key={idx} className="p-2 rounded bg-gray-800 border border-gray-700 text-xs space-y-1">
          <div className="flex justify-between text-gray-300">
            <span>{item.userPrincipalName || item.displayName || 'Unknown'}</span>
            <span className="text-red-300">{item.riskLevel || ''}</span>
          </div>
          <p className="text-gray-400">Estado: {item.riskState || 'N/A'}</p>
        </div>
      );
    }
    return (
      <div key={idx} className="p-2 rounded bg-gray-800 border border-gray-700 text-xs space-y-1">
        <p className="text-gray-300">{item.operation || item.activityDisplayName || 'Log'}</p>
        <p className="text-gray-400 truncate">{item.initiatedBy?.user?.userPrincipalName || item.userPrincipalName || 'N/A'}</p>
        <p className="text-gray-500">{item.createdDateTime || item.creationTime}</p>
      </div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-gray-400">{title}</p>
        <span className="text-xs bg-gray-800 text-gray-200 px-2 py-1 rounded">{count}</span>
      </div>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {items.length === 0 ? (
          <p className="text-gray-500 text-xs">Sin datos</p>
        ) : (
          items.map(renderItem)
        )}
      </div>
    </div>
  );
}

function formatExpiry(tenantId) {
  const exp = localStorage.getItem(`azure_token_exp_${tenantId}`);
  if (!exp) return 'desconocida';
  const date = new Date(Number(exp));
  return date.toLocaleString();
}
