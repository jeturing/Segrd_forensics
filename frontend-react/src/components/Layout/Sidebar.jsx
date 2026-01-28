import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import classNames from 'classnames';
import { useAuth } from '../../context/AuthContext';

const menuItems = [
  {
    category: 'Principal',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: '🏠', path: '/dashboard' },
      { id: 'cases', label: 'Investigaciones', icon: '🔍', path: '/investigations' },
      { id: 'graph', label: 'Grafo de Ataque', icon: '📊', path: '/graph' }
    ]
  },
  {
    category: 'Herramientas',
    items: [
      { id: 'security-tools', label: 'Security Tools', icon: '🐉', path: '/security-tools' },
      { id: 'agents', label: 'Agentes Móviles', icon: '📱', path: '/agents' },
      { id: 'active', label: 'Investigación Activa', icon: '⚡', path: '/active-investigation' }
    ]
  },
  {
    category: 'v4.1 - SOAR & Agents',
    items: [
      { id: 'playbooks', label: 'SOAR Playbooks', icon: '🎭', path: '/playbooks' },
      { id: 'correlation', label: 'Correlación', icon: '🔔', path: '/correlation' },
      { id: 'agents-v41', label: 'Agentes Red/Blue', icon: '🛡️', path: '/agents-v41' }
    ]
  },
  {
    category: 'Análisis',
    items: [
      { id: 'm365', label: 'Microsoft 365', icon: '☁️', path: '/m365' },
      { id: 'm365-cloud', label: 'M365 Cloud Security', icon: '🔒☁️', path: '/m365-cloud' },
      { id: 'credentials', label: 'Credenciales', icon: '🔑', path: '/credentials' },
      { id: 'iocs', label: 'IOC Store', icon: '🎯', path: '/iocs' }
    ]
  },
  {
    category: 'Inteligencia',
    items: [
      { id: 'threat-intel', label: 'Threat Intel', icon: '🔍🌐', path: '/threat-intel' },
      { id: 'threat-hunting', label: 'Threat Hunting', icon: '🕵️', path: '/threat-hunting' },
      { id: 'timeline', label: 'Timeline Forense', icon: '⏱️', path: '/timeline' }
    ]
  },
  {
    category: 'Reportes',
    items: [
      { id: 'reports', label: 'Reportes', icon: '📋', path: '/reports' },
      { id: 'tenants', label: 'Gestión Tenants', icon: '🏢', path: '/tenants' }
    ]
  },
  {
    category: 'Administración',
    items: [
      { id: 'maintenance', label: 'Mantenimiento', icon: '🛠️', path: '/maintenance' },
      { id: 'llm-settings', label: 'LLM / IA', icon: '🧠', path: '/settings/llm' }
    ]
  }
];

// Menu items for Global Admin only
const globalAdminMenuItems = [
  {
    category: 'Administración Global',
    requiresGlobalAdmin: true,
    items: [
      { id: 'admin-dashboard', label: 'Panel Admin', icon: '👑', path: '/admin' },
      { id: 'admin-users', label: 'Usuarios Global', icon: '👥', path: '/admin/users' },
      { id: 'admin-tenants', label: 'Tenants Global', icon: '🏛️', path: '/admin/tenants' },
      { id: 'admin-billing', label: 'Billing & Stripe', icon: '💳', path: '/admin/billing' },
      { id: 'admin-settings', label: 'Config Legado', icon: '⚙️', path: '/admin/settings' },
      { id: 'admin-system', label: 'Sistema & LLM', icon: '🤖', path: '/admin/system-config' }
    ]
  }
];

export default function Sidebar({ collapsed = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin } = useAuth();

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  // Combine regular menu with global admin menu if user is global admin
  const allMenuItems = isAdmin 
    ? [...globalAdminMenuItems, ...menuItems]
    : menuItems;

  return (
    <aside className={classNames(
      'fixed inset-y-0 left-0 bg-gray-800 border-r border-gray-700 shadow-lg z-50',
      'flex flex-col transition-all duration-300',
      collapsed ? 'w-20' : 'w-64'
    )}>
      {/* Logo */}
      <div className="flex items-center justify-center h-20 border-b border-gray-700 px-4 bg-gradient-to-r from-gray-800 to-gray-900">
        <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent transition-all duration-300 hover:scale-110">
          {collapsed ? '🛡️' : 'JETURING Forensics'}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-3">
        {allMenuItems.map((category) => (
          <div key={category.category} className={classNames(
            "mb-6",
            category.requiresGlobalAdmin && "border-b border-yellow-500/30 pb-4 mb-4"
          )}>
            {!collapsed && (
              <h3 className={classNames(
                "px-4 mb-3 text-xs font-semibold uppercase tracking-wider",
                category.requiresGlobalAdmin 
                  ? "text-yellow-400" 
                  : "text-gray-500"
              )}>
                {category.category}
                {category.requiresGlobalAdmin && !collapsed && (
                  <span className="ml-2 text-[10px] bg-yellow-500/20 px-1.5 py-0.5 rounded">ADMIN</span>
                )}
              </h3>
            )}
            
            <div className="space-y-1">
              {category.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate(item.path)}
                  className={classNames(
                    'w-full flex items-center gap-3 px-4 py-2.5 rounded-lg',
                    'transition-all duration-300 text-sm font-medium group relative',
                    'hover:scale-105 hover:shadow-lg',
                    isActive(item.path)
                      ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/50'
                      : 'text-gray-300 hover:bg-gradient-to-r hover:from-gray-700 hover:to-gray-700/50 hover:text-white'
                  )}
                  title={collapsed ? item.label : ''}
                >
                  <span className={classNames(
                    "text-lg flex-shrink-0 transition-transform duration-300",
                    isActive(item.path) ? "scale-110" : "group-hover:scale-110"
                  )}>
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <span className="transition-all duration-300 group-hover:translate-x-1">
                      {item.label}
                    </span>
                  )}
                  {isActive(item.path) && !collapsed && (
                    <span className="ml-auto">
                      <span className="w-2 h-2 bg-white rounded-full inline-block animate-pulse" />
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-700 p-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
            👤
          </div>
          {!collapsed && (
            <div className="text-sm">
              <p className="font-medium">Usuario</p>
              <p className="text-xs text-gray-400">admin@empresa.com</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
