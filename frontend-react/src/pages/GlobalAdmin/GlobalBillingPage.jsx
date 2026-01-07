/**
 * Global Billing Management - Manage subscriptions, invoices, and payments
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CreditCard, Search, ArrowLeft, DollarSign, TrendingUp,
  Calendar, CheckCircle, XCircle, Clock, AlertTriangle,
  Download, Filter, RefreshCw, Building2, FileText, Eye
} from 'lucide-react';
import api from '../../services/api';

export default function GlobalBillingPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('subscriptions');
  const [subscriptions, setSubscriptions] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({
    totalMRR: 0,
    activeSubscriptions: 0,
    trialSubscriptions: 0,
    pendingInvoices: 0,
    overdueAmount: 0
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [subRes, invRes, statsRes] = await Promise.all([
        api.get('/api/admin/global/subscriptions'),
        api.get('/api/admin/global/invoices'),
        api.get('/api/admin/global/billing-stats')
      ]);
      
      if (subRes.data?.subscriptions) setSubscriptions(subRes.data.subscriptions);
      if (invRes.data?.invoices) setInvoices(invRes.data.invoices);
      if (statsRes.data) setStats(statsRes.data);
    } catch (error) {
      console.error('Error fetching billing data:', error);
      // Mock data
      setSubscriptions([
        { id: '1', tenant: 'Jeturing Labs', plan: 'Enterprise', status: 'active', amount: 299, billing_period: 'monthly', next_billing: '2026-01-29', stripe_id: 'sub_xxx1' },
        { id: '2', tenant: 'Acme Corporation', plan: 'Professional', status: 'active', amount: 99, billing_period: 'monthly', next_billing: '2026-01-15', stripe_id: 'sub_xxx2' },
        { id: '3', tenant: 'Tech Solutions', plan: 'Professional', status: 'active', amount: 99, billing_period: 'monthly', next_billing: '2026-01-20', stripe_id: 'sub_xxx3' },
        { id: '4', tenant: 'StartupXYZ', plan: 'Free Trial', status: 'trialing', amount: 0, billing_period: 'trial', next_billing: null, trial_end: '2026-01-10', stripe_id: null },
        { id: '5', tenant: 'Old Company', plan: 'Free Trial', status: 'expired', amount: 0, billing_period: 'trial', next_billing: null, trial_end: '2025-12-01', stripe_id: null }
      ]);
      setInvoices([
        { id: 'INV-001', tenant: 'Jeturing Labs', amount: 299, status: 'paid', date: '2025-12-01', due_date: '2025-12-01', paid_date: '2025-12-01' },
        { id: 'INV-002', tenant: 'Acme Corporation', amount: 99, status: 'paid', date: '2025-12-15', due_date: '2025-12-15', paid_date: '2025-12-15' },
        { id: 'INV-003', tenant: 'Tech Solutions', amount: 99, status: 'pending', date: '2025-12-20', due_date: '2025-12-27', paid_date: null },
        { id: 'INV-004', tenant: 'Another Corp', amount: 99, status: 'overdue', date: '2025-12-01', due_date: '2025-12-08', paid_date: null }
      ]);
      setStats({
        totalMRR: 596,
        activeSubscriptions: 3,
        trialSubscriptions: 1,
        pendingInvoices: 1,
        overdueAmount: 99
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      active: 'bg-green-500/20 text-green-400 border-green-500/30',
      trialing: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      expired: 'bg-red-500/20 text-red-400 border-red-500/30',
      canceled: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
      paid: 'bg-green-500/20 text-green-400 border-green-500/30',
      pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      overdue: 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

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
              <CreditCard className="w-7 h-7 text-green-400" />
              Gestión de Billing
            </h1>
            <p className="text-gray-400 text-sm">Suscripciones, facturas y pagos</p>
          </div>
        </div>
        <button 
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Sincronizar Stripe
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-5 h-5 text-emerald-400" />
            <span className="text-gray-400 text-sm">MRR</span>
          </div>
          <p className="text-2xl font-bold text-emerald-400">${stats.totalMRR}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-gray-400 text-sm">Activas</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.activeSubscriptions}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-yellow-400" />
            <span className="text-gray-400 text-sm">En Trial</span>
          </div>
          <p className="text-2xl font-bold text-yellow-400">{stats.trialSubscriptions}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <span className="text-gray-400 text-sm">Pendientes</span>
          </div>
          <p className="text-2xl font-bold text-blue-400">{stats.pendingInvoices}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span className="text-gray-400 text-sm">Vencido</span>
          </div>
          <p className="text-2xl font-bold text-red-400">${stats.overdueAmount}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('subscriptions')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'subscriptions' 
              ? 'bg-green-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Suscripciones
        </button>
        <button
          onClick={() => setActiveTab('invoices')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'invoices' 
              ? 'bg-green-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Facturas
        </button>
        <button
          onClick={() => setActiveTab('plans')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'plans' 
              ? 'bg-green-600 text-white' 
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Planes
        </button>
      </div>

      {/* Content */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        {activeTab === 'subscriptions' && (
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Tenant</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Plan</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Estado</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Monto</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Próximo Cobro</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {subscriptions.map((sub) => (
                <tr key={sub.id} className="hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-gray-400" />
                      <span className="text-white font-medium">{sub.tenant}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-300">{sub.plan}</td>
                  <td className="px-6 py-4">{getStatusBadge(sub.status)}</td>
                  <td className="px-6 py-4 text-emerald-400 font-medium">
                    ${sub.amount}/{sub.billing_period === 'trial' ? 'trial' : 'mes'}
                  </td>
                  <td className="px-6 py-4 text-gray-400">
                    {sub.next_billing || sub.trial_end || '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-2 hover:bg-gray-600 rounded-lg">
                      <Eye className="w-4 h-4 text-gray-400" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'invoices' && (
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Factura</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Tenant</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Monto</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Estado</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Fecha</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase">Vencimiento</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-700/50">
                  <td className="px-6 py-4 text-white font-mono">{inv.id}</td>
                  <td className="px-6 py-4 text-gray-300">{inv.tenant}</td>
                  <td className="px-6 py-4 text-emerald-400 font-medium">${inv.amount}</td>
                  <td className="px-6 py-4">{getStatusBadge(inv.status)}</td>
                  <td className="px-6 py-4 text-gray-400">{inv.date}</td>
                  <td className="px-6 py-4 text-gray-400">{inv.due_date}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-2 hover:bg-gray-600 rounded-lg">
                      <Download className="w-4 h-4 text-gray-400" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'plans' && (
          <div className="p-6">
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-gray-700/50 rounded-xl p-6 border border-gray-600">
                <h3 className="text-xl font-bold text-white mb-2">Free Trial</h3>
                <p className="text-3xl font-bold text-emerald-400 mb-4">$0<span className="text-sm text-gray-400">/15 días</span></p>
                <ul className="space-y-2 text-sm text-gray-300">
                  <li>• 2 usuarios</li>
                  <li>• 10 casos</li>
                  <li>• 5 GB storage</li>
                  <li>• Soporte email</li>
                </ul>
              </div>
              <div className="bg-blue-900/30 rounded-xl p-6 border border-blue-500/50">
                <h3 className="text-xl font-bold text-white mb-2">Professional</h3>
                <p className="text-3xl font-bold text-blue-400 mb-4">$99<span className="text-sm text-gray-400">/mes</span></p>
                <ul className="space-y-2 text-sm text-gray-300">
                  <li>• 5 usuarios</li>
                  <li>• 100 casos</li>
                  <li>• 50 GB storage</li>
                  <li>• Soporte prioritario</li>
                  <li>• API access</li>
                </ul>
              </div>
              <div className="bg-purple-900/30 rounded-xl p-6 border border-purple-500/50">
                <h3 className="text-xl font-bold text-white mb-2">Enterprise</h3>
                <p className="text-3xl font-bold text-purple-400 mb-4">$299<span className="text-sm text-gray-400">/mes</span></p>
                <ul className="space-y-2 text-sm text-gray-300">
                  <li>• 25 usuarios</li>
                  <li>• Casos ilimitados</li>
                  <li>• 500 GB storage</li>
                  <li>• Soporte dedicado</li>
                  <li>• SSO/SAML</li>
                  <li>• SLA garantizado</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
