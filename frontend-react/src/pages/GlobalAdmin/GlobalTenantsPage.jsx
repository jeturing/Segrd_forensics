/**
 * Global Tenants Management - Manage all tenants/organizations
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Building2, Search, Plus, Edit, Trash2, Users, CreditCard,
  Calendar, ArrowLeft, CheckCircle, XCircle, Clock, 
  AlertTriangle, BarChart3, Settings, Eye
} from 'lucide-react';
import api from '../../services/api';

export default function GlobalTenantsPage() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPlan, setFilterPlan] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchTenants();
  }, []);

  const fetchTenants = async () => {
    try {
      const response = await api.get('/api/admin/global/tenants');
      if (response.data?.tenants) {
        setTenants(response.data.tenants);
      }
    } catch (error) {
      console.error('Error fetching tenants:', error);
      // Mock data
      setTenants([
        { 
          id: '1', tenant_id: 'jeturing', name: 'Jeturing Labs', subdomain: 'jeturing',
          plan: 'enterprise', status: 'active', users_count: 15, cases_count: 234,
          subscription_status: 'active', trial_end: null, monthly_revenue: 299,
          created_at: '2025-01-01', contact_email: 'admin@jeturing.com'
        },
        { 
          id: '2', tenant_id: 'acme_corp', name: 'Acme Corporation', subdomain: 'acme',
          plan: 'professional', status: 'active', users_count: 8, cases_count: 87,
          subscription_status: 'active', trial_end: null, monthly_revenue: 99,
          created_at: '2025-02-15', contact_email: 'security@acme.com'
        },
        { 
          id: '3', tenant_id: 'tech_solutions', name: 'Tech Solutions', subdomain: 'techsol',
          plan: 'professional', status: 'active', users_count: 5, cases_count: 45,
          subscription_status: 'active', trial_end: null, monthly_revenue: 99,
          created_at: '2025-03-20', contact_email: 'it@techsolutions.com'
        },
        { 
          id: '4', tenant_id: 'startup_xyz', name: 'StartupXYZ', subdomain: 'startupxyz',
          plan: 'free_trial', status: 'active', users_count: 2, cases_count: 12,
          subscription_status: 'trialing', trial_end: '2026-01-10', monthly_revenue: 0,
          created_at: '2025-12-26', contact_email: 'founder@startupxyz.com'
        },
        { 
          id: '5', tenant_id: 'old_company', name: 'Old Company', subdomain: 'oldco',
          plan: 'free_trial', status: 'suspended', users_count: 1, cases_count: 3,
          subscription_status: 'expired', trial_end: '2025-12-01', monthly_revenue: 0,
          created_at: '2025-11-15', contact_email: 'info@oldcompany.com'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getPlanBadge = (plan) => {
    const plans = {
      'enterprise': { label: 'Enterprise', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
      'professional': { label: 'Professional', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
      'free_trial': { label: 'Free Trial', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' }
    };
    const p = plans[plan] || plans['free_trial'];
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${p.color}`}>
        {p.label}
      </span>
    );
  };

  const getStatusBadge = (status, subStatus) => {
    if (status === 'suspended') {
      return <span className="flex items-center gap-1 text-red-400"><XCircle className="w-4 h-4" />Suspendido</span>;
    }
    if (subStatus === 'trialing') {
      return <span className="flex items-center gap-1 text-yellow-400"><Clock className="w-4 h-4" />En Trial</span>;
    }
    if (subStatus === 'expired') {
      return <span className="flex items-center gap-1 text-red-400"><AlertTriangle className="w-4 h-4" />Expirado</span>;
    }
    return <span className="flex items-center gap-1 text-green-400"><CheckCircle className="w-4 h-4" />Activo</span>;
  };

  const filteredTenants = tenants.filter(tenant => {
    const matchesSearch = tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tenant.tenant_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tenant.contact_email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPlan = filterPlan === 'all' || tenant.plan === filterPlan;
    const matchesStatus = filterStatus === 'all' || 
                         (filterStatus === 'active' && tenant.status === 'active' && tenant.subscription_status === 'active') ||
                         (filterStatus === 'trialing' && tenant.subscription_status === 'trialing') ||
                         (filterStatus === 'suspended' && (tenant.status === 'suspended' || tenant.subscription_status === 'expired'));
    return matchesSearch && matchesPlan && matchesStatus;
  });

  const totalRevenue = tenants.reduce((sum, t) => sum + (t.monthly_revenue || 0), 0);
  const activeCount = tenants.filter(t => t.subscription_status === 'active').length;
  const trialCount = tenants.filter(t => t.subscription_status === 'trialing').length;

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/admin')}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Building2 className="w-7 h-7 text-purple-400" />
              Gestión de Tenants
            </h1>
            <p className="text-gray-400 text-sm">Administrar organizaciones y cuentas</p>
          </div>
        </div>
        <button 
          onClick={() => navigate('/admin/tenants/new')}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo Tenant
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-gray-400 text-sm">Total Tenants</p>
          <p className="text-2xl font-bold text-white">{tenants.length}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-gray-400 text-sm">Activos</p>
          <p className="text-2xl font-bold text-green-400">{activeCount}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-gray-400 text-sm">En Trial</p>
          <p className="text-2xl font-bold text-yellow-400">{trialCount}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-gray-400 text-sm">Ingresos Mensuales</p>
          <p className="text-2xl font-bold text-emerald-400">${totalRevenue}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-gray-800 rounded-xl p-4 mb-6 border border-gray-700">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por nombre, ID o email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none"
              />
            </div>
          </div>
          <select
            value={filterPlan}
            onChange={(e) => setFilterPlan(e.target.value)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
          >
            <option value="all">Todos los Planes</option>
            <option value="enterprise">Enterprise</option>
            <option value="professional">Professional</option>
            <option value="free_trial">Free Trial</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
          >
            <option value="all">Todos los Estados</option>
            <option value="active">Activos</option>
            <option value="trialing">En Trial</option>
            <option value="suspended">Suspendidos/Expirados</option>
          </select>
        </div>
      </div>

      {/* Tenants Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-3 flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
          </div>
        ) : filteredTenants.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-gray-400">
            No se encontraron tenants
          </div>
        ) : (
          filteredTenants.map((tenant) => (
            <div 
              key={tenant.id} 
              className="bg-gray-800 rounded-xl p-5 border border-gray-700 hover:border-gray-600 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-white">{tenant.name}</h3>
                  <p className="text-sm text-gray-400">{tenant.tenant_id}</p>
                </div>
                {getPlanBadge(tenant.plan)}
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Estado:</span>
                  {getStatusBadge(tenant.status, tenant.subscription_status)}
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Usuarios:</span>
                  <span className="text-white flex items-center gap-1">
                    <Users className="w-4 h-4" />{tenant.users_count}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Casos:</span>
                  <span className="text-white">{tenant.cases_count}</span>
                </div>
                {tenant.trial_end && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Trial expira:</span>
                    <span className="text-yellow-400">{tenant.trial_end}</span>
                  </div>
                )}
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Ingresos:</span>
                  <span className="text-emerald-400 font-medium">${tenant.monthly_revenue}/mes</span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-4 border-t border-gray-700">
                <button 
                  onClick={() => navigate(`/admin/tenants/${tenant.id}`)}
                  className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors"
                >
                  <Eye className="w-4 h-4" />
                  Ver
                </button>
                <button 
                  onClick={() => navigate(`/admin/tenants/${tenant.id}/edit`)}
                  className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors"
                >
                  <Edit className="w-4 h-4" />
                  Editar
                </button>
                <button 
                  onClick={() => navigate(`/admin/tenants/${tenant.id}/billing`)}
                  className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors"
                >
                  <CreditCard className="w-4 h-4" />
                  Billing
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
