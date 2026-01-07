import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { listTenants, getActiveTenant, switchTenant } from '../../services/tenants';

export default function Layout({ children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [tenants, setTenants] = useState([]);
  const [activeTenant, setActiveTenant] = useState(null);
  const [loadingTenants, setLoadingTenants] = useState(false);
  const [switchingTenant, setSwitchingTenant] = useState(false);

  const loadTenants = useCallback(async () => {
    setLoadingTenants(true);
    try {
      const data = await listTenants();
      setTenants(data?.tenants || []);
    } catch (error) {
      console.error('Error cargando tenants', error);
      toast.error('No se pudieron cargar los tenants');
    } finally {
      setLoadingTenants(false);
    }
  }, []);

  const loadActive = useCallback(async () => {
    try {
      const data = await getActiveTenant();
      setActiveTenant(data?.tenant || null);
    } catch (error) {
      console.error('Error cargando tenant activo', error);
    }
  }, []);

  useEffect(() => {
    loadTenants();
    loadActive();
  }, [loadTenants, loadActive]);

  const handleSwitchTenant = async (tenantId) => {
    if (!tenantId) return;
    setSwitchingTenant(true);
    try {
      await switchTenant(tenantId);
      toast.success('Tenant activo cambiado');
      await loadActive();
      await loadTenants();
    } catch (error) {
      console.error('Error cambiando tenant', error);
      toast.error(error.response?.data?.detail || 'No se pudo cambiar el tenant');
    } finally {
      setSwitchingTenant(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Topbar */}
      <Topbar
        onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
        tenants={tenants}
        activeTenant={activeTenant}
        onSwitchTenant={handleSwitchTenant}
        loadingTenants={loadingTenants || switchingTenant}
      />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar collapsed={sidebarCollapsed} />

        {/* Page Content */}
        <main className={`flex-1 overflow-auto transition-all duration-300 ${sidebarCollapsed ? 'ml-20' : 'ml-64'}`}>
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
