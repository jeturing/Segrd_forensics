/**
 * Global Admin Dashboard - Overview of system-wide administration
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, Building2, CreditCard, Settings, Activity,
  TrendingUp, AlertTriangle, CheckCircle, Clock,
  Database, Server, Shield, BarChart3
} from 'lucide-react';
import api from '../../services/api';

export default function GlobalAdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    totalTenants: 0,
    activeTenants: 0,
    totalUsers: 0,
    activeSubscriptions: 0,
    trialSubscriptions: 0,
    expiredSubscriptions: 0,
    monthlyRevenue: 0,
    pendingPayments: 0
  });
  const [loading, setLoading] = useState(true);
  const [recentActivity, setRecentActivity] = useState([]);

  useEffect(() => {
    fetchStats();
    fetchRecentActivity();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/admin/global/stats');
      if (response.data) {
        setStats(response.data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
      // Use mock data if API not available
      setStats({
        totalTenants: 12,
        activeTenants: 10,
        totalUsers: 45,
        activeSubscriptions: 8,
        trialSubscriptions: 3,
        expiredSubscriptions: 1,
        monthlyRevenue: 2450,
        pendingPayments: 2
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentActivity = async () => {
    try {
      const response = await api.get('/api/admin/global/activity');
      if (response.data?.activities) {
        setRecentActivity(response.data.activities);
      }
    } catch (error) {
      // Mock data
      setRecentActivity([
        { id: 1, type: 'user_created', message: 'Nuevo usuario registrado: john@acme.com', time: '5 min ago', tenant: 'Acme Corp' },
        { id: 2, type: 'subscription_activated', message: 'Suscripción Professional activada', time: '1 hour ago', tenant: 'Tech Solutions' },
        { id: 3, type: 'trial_expiring', message: 'Trial expira en 3 días', time: '2 hours ago', tenant: 'StartupXYZ' },
        { id: 4, type: 'payment_received', message: 'Pago recibido: $99.00', time: '1 day ago', tenant: 'Global Inc' }
      ]);
    }
  };

  const adminModules = [
    {
      title: 'Gestión de Usuarios',
      description: 'Administrar todos los usuarios del sistema',
      icon: Users,
      path: '/admin/users',
      color: 'from-blue-500 to-blue-600',
      stats: `${stats.totalUsers} usuarios`
    },
    {
      title: 'Gestión de Tenants',
      description: 'Administrar organizaciones y cuentas',
      icon: Building2,
      path: '/admin/tenants',
      color: 'from-purple-500 to-purple-600',
      stats: `${stats.totalTenants} tenants`
    },
    {
      title: 'Suscripciones & Billing',
      description: 'Gestionar planes, pagos y facturación',
      icon: CreditCard,
      path: '/admin/billing',
      color: 'from-green-500 to-green-600',
      stats: `${stats.activeSubscriptions} activas`
    },
    {
      title: 'Configuración Sistema',
      description: 'Ajustes globales y configuración',
      icon: Settings,
      path: '/admin/settings',
      color: 'from-orange-500 to-orange-600',
      stats: 'Sistema'
    }
  ];

  const statCards = [
    { label: 'Tenants Activos', value: stats.activeTenants, total: stats.totalTenants, icon: Building2, color: 'text-blue-400' },
    { label: 'Usuarios Totales', value: stats.totalUsers, icon: Users, color: 'text-purple-400' },
    { label: 'Suscripciones Activas', value: stats.activeSubscriptions, icon: CheckCircle, color: 'text-green-400' },
    { label: 'En Trial', value: stats.trialSubscriptions, icon: Clock, color: 'text-yellow-400' },
    { label: 'Ingresos Mensuales', value: `$${stats.monthlyRevenue}`, icon: TrendingUp, color: 'text-emerald-400' },
    { label: 'Pagos Pendientes', value: stats.pendingPayments, icon: AlertTriangle, color: 'text-red-400' }
  ];

  const getActivityIcon = (type) => {
    switch (type) {
      case 'user_created': return <Users className="w-4 h-4 text-blue-400" />;
      case 'subscription_activated': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'trial_expiring': return <Clock className="w-4 h-4 text-yellow-400" />;
      case 'payment_received': return <CreditCard className="w-4 h-4 text-emerald-400" />;
      default: return <Activity className="w-4 h-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="w-8 h-8 text-red-500" />
          <h1 className="text-3xl font-bold text-white">Panel de Administración Global</h1>
        </div>
        <p className="text-gray-400">Gestión centralizada de tenants, usuarios y suscripciones</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon className={`w-5 h-5 ${stat.color}`} />
              <span className="text-xs text-gray-400">{stat.label}</span>
            </div>
            <p className="text-2xl font-bold text-white">
              {stat.value}
              {stat.total && <span className="text-sm text-gray-500">/{stat.total}</span>}
            </p>
          </div>
        ))}
      </div>

      {/* Admin Modules */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {adminModules.map((module, index) => (
          <button
            key={index}
            onClick={() => navigate(module.path)}
            className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-gray-600 
                       transition-all duration-300 hover:scale-105 hover:shadow-xl text-left group"
          >
            <div className={`w-12 h-12 rounded-lg bg-gradient-to-r ${module.color} 
                            flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
              <module.icon className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">{module.title}</h3>
            <p className="text-sm text-gray-400 mb-3">{module.description}</p>
            <span className="text-xs text-blue-400 font-medium">{module.stats}</span>
          </button>
        ))}
      </div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            Actividad Reciente
          </h3>
          <div className="space-y-3">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="flex items-start gap-3 p-3 bg-gray-700/50 rounded-lg">
                {getActivityIcon(activity.type)}
                <div className="flex-1">
                  <p className="text-sm text-white">{activity.message}</p>
                  <p className="text-xs text-gray-400">{activity.tenant} • {activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            Acciones Rápidas
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <button 
              onClick={() => navigate('/admin/users/new')}
              className="p-4 bg-blue-600/20 border border-blue-500/30 rounded-lg hover:bg-blue-600/30 transition-colors"
            >
              <Users className="w-6 h-6 text-blue-400 mx-auto mb-2" />
              <span className="text-sm text-white">Crear Usuario</span>
            </button>
            <button 
              onClick={() => navigate('/admin/tenants/new')}
              className="p-4 bg-purple-600/20 border border-purple-500/30 rounded-lg hover:bg-purple-600/30 transition-colors"
            >
              <Building2 className="w-6 h-6 text-purple-400 mx-auto mb-2" />
              <span className="text-sm text-white">Crear Tenant</span>
            </button>
            <button 
              onClick={() => navigate('/admin/billing/invoices')}
              className="p-4 bg-green-600/20 border border-green-500/30 rounded-lg hover:bg-green-600/30 transition-colors"
            >
              <CreditCard className="w-6 h-6 text-green-400 mx-auto mb-2" />
              <span className="text-sm text-white">Ver Facturas</span>
            </button>
            <button 
              onClick={() => navigate('/admin/settings/system')}
              className="p-4 bg-orange-600/20 border border-orange-500/30 rounded-lg hover:bg-orange-600/30 transition-colors"
            >
              <Server className="w-6 h-6 text-orange-400 mx-auto mb-2" />
              <span className="text-sm text-white">Estado Sistema</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
