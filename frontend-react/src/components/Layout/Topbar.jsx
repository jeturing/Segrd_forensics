import React, { useState } from 'react';

export default function Topbar({
  onToggleSidebar,
  tenants = [],
  activeTenant = null,
  onSwitchTenant = () => {},
  loadingTenants = false
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <header className="sticky top-0 z-40 h-20 bg-gray-800 border-b border-gray-700 shadow-lg">
      <div className="h-full px-6 flex items-center justify-between">
        {/* Left: Toggle Sidebar */}
        <button
          onClick={onToggleSidebar}
          className="p-2 hover:bg-gray-700 rounded-lg transition text-gray-300 hover:text-white"
          title="Toggle Sidebar"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Center: Title */}
        <div className="flex-1 ml-6 flex flex-col gap-1">
          <h1 className="text-xl font-semibold text-gray-100">
            SEGRD Security & IR
          </h1>
          <div className="text-xs text-gray-400">
            Plataforma DFIR • Multi-tenant M365
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-4">
          {/* Tenant Switcher */}
          <div className="relative">
            <label className="text-xs text-gray-400 block mb-1">Tenant activo</label>
            <div className="flex items-center gap-2">
              <select
                disabled={loadingTenants || tenants.length === 0}
                value={activeTenant?.tenant_id || ''}
                onChange={(e) => onSwitchTenant(e.target.value)}
                className="bg-gray-900 border border-gray-700 text-gray-100 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {tenants.length === 0 && <option>No hay tenants</option>}
                {tenants.map((tenant) => (
                  <option key={tenant.tenant_id} value={tenant.tenant_id}>
                    {tenant.name || tenant.tenant_name || tenant.tenant_id}
                    {tenant.is_active ? ' (activo)' : ''}
                  </option>
                ))}
              </select>
              {loadingTenants && (
                <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              )}
            </div>
            {activeTenant?.primary_domain && (
              <div className="text-xs text-gray-500 mt-1">
                {activeTenant.primary_domain} • {activeTenant.tenant_id}
              </div>
            )}
          </div>

          {/* Notifications */}
          <button className="relative p-2 hover:bg-gray-700 rounded-lg transition text-gray-300 hover:text-white">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="flex items-center gap-2 p-2 hover:bg-gray-700 rounded-lg transition text-gray-300 hover:text-white"
            >
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
                👤
              </div>
              <span className="text-sm">Admin</span>
            </button>

            {/* Dropdown Menu */}
            {showMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-gray-700 rounded-lg shadow-xl border border-gray-600 overflow-hidden">
                <button className="w-full text-left px-4 py-2 hover:bg-gray-600 transition text-gray-200">
                  👤 Perfil
                </button>
                <button className="w-full text-left px-4 py-2 hover:bg-gray-600 transition text-gray-200">
                  ⚙️ Configuración
                </button>
                <hr className="border-gray-600" />
                <button className="w-full text-left px-4 py-2 hover:bg-gray-600 transition text-red-400">
                  🚪 Cerrar Sesión
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
