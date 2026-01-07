import React, { useEffect, useState, useCallback, useRef } from 'react';
import { toast } from 'react-toastify';
import { listTenants, getActiveTenant, switchTenant, syncTenant, initDeviceAuth, pollDeviceToken, onboardTenantWithDeviceCode } from '../../services/tenants';
import { ClipboardDocumentIcon, XMarkIcon, PlusIcon } from '@heroicons/react/24/outline';

const Badge = ({ color = 'gray', children }) => {
  const colors = {
    green: 'bg-green-500/15 text-green-300 border-green-500/40',
    blue: 'bg-blue-500/15 text-blue-300 border-blue-500/40',
    yellow: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
    red: 'bg-red-500/15 text-red-300 border-red-500/40',
    gray: 'bg-gray-500/15 text-gray-300 border-gray-500/40'
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${colors[color] || colors.gray}`}>
      {children}
    </span>
  );
};

const Stat = ({ label, value }) => (
  <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-xl">
    <div className="text-sm text-slate-400">{label}</div>
    <div className="text-xl font-bold text-white">{value}</div>
  </div>
);

export default function TenantsPage() {
  const [tenants, setTenants] = useState([]);
  const [activeTenant, setActiveTenant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  
  // Device Code State
  const [deviceModalOpen, setDeviceModalOpen] = useState(false);
  const [deviceCodeData, setDeviceCodeData] = useState(null);
  const [deviceModalMode, setDeviceModalMode] = useState('sync'); // 'sync' or 'onboard'
  const pollInterval = useRef(null);
  
  // Add Tenant Modal State
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newTenantId, setNewTenantId] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [all, active] = await Promise.all([listTenants(), getActiveTenant()]);
      setTenants(all?.tenants || []);
      setActiveTenant(active?.tenant || null);
    } catch (err) {
      toast.error('No se pudieron cargar los tenants');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [loadData]);

  const handleActivate = async (tenantId) => {
    try {
      await switchTenant(tenantId);
      toast.success('Tenant activado');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error activando tenant');
    }
  };

  const handleSync = async (tenantId) => {
    setSyncing(true);
    try {
      await syncTenant(tenantId);
      toast.success('Sincronización iniciada');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al sincronizar');
    } finally {
      setSyncing(false);
    }
  };

  const handleDeviceSync = async (tenantId) => {
    try {
      const data = await initDeviceAuth(tenantId);
      setDeviceCodeData({ ...data, tenantId });
      setDeviceModalMode('sync');
      setDeviceModalOpen(true);
      
      // Start polling
      if (pollInterval.current) clearInterval(pollInterval.current);
      
      pollInterval.current = setInterval(async () => {
        try {
          const result = await pollDeviceToken(tenantId, data.device_code);
          if (result.access_token) {
            clearInterval(pollInterval.current);
            setDeviceModalOpen(false);
            toast.success('Autenticación exitosa! Iniciando sincronización...');
            
            // Trigger sync with token
            try {
                await syncTenant(tenantId, result.access_token);
                toast.success('Sincronización completada');
                loadData();
            } catch (syncErr) {
                toast.error('Error al sincronizar con el token obtenido');
            }
          } else if (result.error && result.error !== 'authorization_pending') {
             clearInterval(pollInterval.current);
             toast.error(`Error: ${result.error_description || result.error}`);
          }
        } catch (err) {
          // Ignore polling errors
        }
      }, 5000);
      
    } catch (err) {
      toast.error('Error iniciando autenticación por dispositivo');
    }
  };

  const handleAddTenantStart = () => {
    setAddModalOpen(true);
    setNewTenantId('');
  };

  const handleAddTenantDeviceCode = async () => {
    if (!newTenantId.trim()) {
      toast.error('Ingresa el Tenant ID');
      return;
    }
    
    setAddModalOpen(false);
    
    try {
      const data = await initDeviceAuth(newTenantId.trim());
      setDeviceCodeData({ ...data, tenantId: newTenantId.trim() });
      setDeviceModalMode('onboard');
      setDeviceModalOpen(true);
      
      // Start polling
      if (pollInterval.current) clearInterval(pollInterval.current);
      
      pollInterval.current = setInterval(async () => {
        try {
          const result = await pollDeviceToken(newTenantId.trim(), data.device_code);
          if (result.access_token) {
            clearInterval(pollInterval.current);
            setDeviceModalOpen(false);
            toast.success('Autenticación exitosa! Registrando tenant...');
            
            // Onboard tenant with token
            try {
                await onboardTenantWithDeviceCode(newTenantId.trim(), result.access_token);
                toast.success('Tenant registrado correctamente');
                loadData();
            } catch (onboardErr) {
                toast.error('Error al registrar el tenant');
            }
          } else if (result.error && result.error !== 'authorization_pending') {
             clearInterval(pollInterval.current);
             toast.error(`Error: ${result.error_description || result.error}`);
             setDeviceModalOpen(false);
          }
        } catch (err) {
          // Ignore polling errors
        }
      }, 5000);
      
    } catch (err) {
      toast.error('Error iniciando autenticación. Verifica el Tenant ID.');
    }
  };

  const closeDeviceModal = () => {
    if (pollInterval.current) clearInterval(pollInterval.current);
    setDeviceModalOpen(false);
    setDeviceCodeData(null);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado al portapapeles');
  };

  const TenantCard = ({ tenant }) => (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold text-white">{tenant.name || tenant.tenant_name}</div>
          <div className="text-sm text-slate-400">{tenant.tenant_id}</div>
        </div>
        <div className="flex items-center gap-2">
          <Badge color={tenant.is_active ? 'green' : 'gray'}>{tenant.is_active ? 'Activo' : tenant.status || 'Inactivo'}</Badge>
          <Badge color="blue">{tenant.users_count || 0} users</Badge>
          <Badge color="yellow">{tenant.cases_count || 0} casos</Badge>
        </div>
      </div>
      <div className="text-xs text-slate-400">
        Dominio: {tenant.primary_domain || 'N/A'} • Última sync: {tenant.last_sync || 'N/A'}
      </div>
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => handleActivate(tenant.tenant_id)}
          className="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm"
        >
          Activar
        </button>
        <button
          onClick={() => handleSync(tenant.tenant_id)}
          className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm disabled:opacity-60"
          disabled={syncing}
        >
          {syncing ? 'Sincronizando...' : 'Sincronizar'}
        </button>
        <button
          onClick={() => handleDeviceSync(tenant.tenant_id)}
          className="px-3 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm flex items-center gap-1"
        >
          <span>Sync (Device)</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Gestión de Tenants</h1>
          <p className="text-slate-400 text-sm">Multi-tenant M365: activa, sincroniza y revisa métricas rápidas.</p>
        </div>
        <button
          onClick={handleAddTenantStart}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Agregar Tenant (Azure Shell)
        </button>
      </div>

      {activeTenant && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="Tenant activo" value={activeTenant.name || activeTenant.tenant_name} />
          <Stat label="Usuarios" value={activeTenant.users_count || 0} />
          <Stat label="Casos" value={activeTenant.cases_count || 0} />
          <Stat label="Última sync" value={activeTenant.last_sync || 'N/A'} />
        </div>
      )}

      {loading ? (
        <div className="text-slate-400">Cargando tenants...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tenants.map((t) => (
            <TenantCard key={t.tenant_id} tenant={t} />
          ))}
          {tenants.length === 0 && (
            <div className="col-span-2 text-center py-12 text-slate-400">
              <p className="text-lg">No hay tenants registrados</p>
              <p className="text-sm mt-2">Usa el botón "Agregar Tenant" para conectar tu primer tenant M365</p>
            </div>
          )}
        </div>
      )}

      {/* Add Tenant Modal */}
      {addModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-md w-full shadow-2xl relative">
            <button onClick={() => setAddModalOpen(false)} className="absolute top-4 right-4 text-slate-400 hover:text-white">
              <XMarkIcon className="w-6 h-6" />
            </button>
            
            <h3 className="text-xl font-bold text-white mb-4">Agregar Nuevo Tenant</h3>
            
            <div className="space-y-4">
              <p className="text-slate-300 text-sm">
                Ingresa el Tenant ID de Azure AD. Lo puedes encontrar en Azure Portal &gt; Azure Active Directory &gt; Overview.
              </p>
              
              <div>
                <label className="block text-sm text-slate-400 mb-2">Tenant ID (GUID)</label>
                <input
                  type="text"
                  value={newTenantId}
                  onChange={(e) => setNewTenantId(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>
              
              <button
                onClick={handleAddTenantDeviceCode}
                className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
              >
                Continuar con Azure Shell (Device Code)
              </button>
              
              <p className="text-xs text-slate-500 text-center">
                Se abrirá una ventana para autenticarte con tu cuenta de Microsoft
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Device Code Modal */}
      {deviceModalOpen && deviceCodeData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-md w-full shadow-2xl relative">
            <button onClick={closeDeviceModal} className="absolute top-4 right-4 text-slate-400 hover:text-white">
              <XMarkIcon className="w-6 h-6" />
            </button>
            
            <h3 className="text-xl font-bold text-white mb-4">
              {deviceModalMode === 'onboard' ? 'Registrar Tenant' : 'Autenticación Device Code'}
            </h3>
            
            <div className="space-y-4">
              <p className="text-slate-300 text-sm">
                {deviceModalMode === 'onboard' 
                  ? 'Autentícate con una cuenta del tenant para registrarlo.'
                  : 'Para sincronizar este tenant, necesitas autenticarte en Microsoft.'
                }
              </p>
              
              <div className="bg-slate-800 p-4 rounded-lg space-y-2">
                <div className="text-xs text-slate-400 uppercase">1. Copia este código</div>
                <div className="flex items-center justify-between bg-slate-950 p-3 rounded border border-slate-700">
                  <code className="text-xl font-mono text-emerald-400 font-bold">{deviceCodeData.user_code}</code>
                  <button onClick={() => copyToClipboard(deviceCodeData.user_code)} className="text-slate-400 hover:text-white">
                    <ClipboardDocumentIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
              
              <div className="bg-slate-800 p-4 rounded-lg space-y-2">
                <div className="text-xs text-slate-400 uppercase">2. Abre este enlace e ingresa el código</div>
                <a 
                  href={deviceCodeData.verification_uri} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="block w-full text-center py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors"
                >
                  Abrir {deviceCodeData.verification_uri}
                </a>
              </div>
              
              <div className="flex items-center justify-center gap-2 text-slate-400 text-sm animate-pulse">
                <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                Esperando autenticación...
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
