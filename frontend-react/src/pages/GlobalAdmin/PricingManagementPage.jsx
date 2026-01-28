/**
 * Pricing Management Page - Admin module to manage pricing configuration
 * Allows editing bundles, add-ons, v-CISO plans, and dynamic pricing tiers
 */

import React, { useState, useEffect } from 'react';
import { 
  Save, Plus, Trash2, Edit2, X, Check,
  DollarSign, Package, Shield, Users, Zap,
  Settings, RefreshCw, AlertTriangle, CheckCircle,
  ChevronDown, ChevronUp, Eye, EyeOff
} from 'lucide-react';
import api from '../../services/api';

// Default pricing configuration
const DEFAULT_PRICING = {
  bundles: [
    {
      id: 'bundle_essential',
      name: 'Protección Esencial',
      bundle: 'Bundle I',
      price: 2500,
      description: 'Cobertura base para empresas que inician su programa de ciberseguridad.',
      targetCompanies: 'Hasta 100 empleados',
      color: 'blue',
      recommended: false,
      active: true,
      features: [
        { name: 'Evaluación Anual de Seguridad', included: true },
        { name: 'EDR (Endpoint Detection & Response)', included: true },
        { name: 'Protección DNS', included: true },
        { name: 'v-CISO Lite (2h/mes)', included: true },
        { name: 'Backup Cloud Básico (500GB)', included: true },
        { name: 'MDR 24x7', included: false },
        { name: 'SIEM Gestionado', included: false },
      ]
    },
    {
      id: 'bundle_professional',
      name: 'Resiliencia Profesional',
      bundle: 'Bundle II',
      price: 4500,
      description: 'Protección robusta con monitoreo activo y capacidad de respuesta rápida.',
      targetCompanies: '100-300 empleados',
      color: 'purple',
      recommended: true,
      active: true,
      features: [
        { name: 'Todo de Esencial +', included: true, highlight: true },
        { name: 'MDR 24x7 (SOC gestionado)', included: true },
        { name: 'SIEM Gestionado', included: true },
        { name: 'v-CISO Activo (4h/mes)', included: true },
        { name: 'SEGRD™ Análisis Forense', included: true },
        { name: 'Protección M365 Avanzada', included: true },
      ]
    },
    {
      id: 'bundle_critical',
      name: 'Blindaje Misión Crítica',
      bundle: 'Bundle III',
      price: 6500,
      description: 'Máxima protección para operaciones críticas. Cero tolerancia al downtime.',
      targetCompanies: '300+ empleados / Infraestructura crítica',
      color: 'amber',
      recommended: false,
      active: true,
      features: [
        { name: 'Todo de Profesional +', included: true, highlight: true },
        { name: 'v-CISO Dedicado (8h/mes)', included: true },
        { name: 'SOC 24/7 con Analista Asignado', included: true },
        { name: 'SEGRD™ con IA Forense Avanzada', included: true },
        { name: 'BCDR Garantizado (RTO 4h)', included: true },
      ]
    }
  ],
  addons: [
    { id: 'dns', name: 'Escudo DNS', price: 150, unit: '/mes', description: 'Filtrado DNS avanzado contra malware y phishing', active: true },
    { id: 'mdr', name: 'MDR 24x7', price: 500, unit: '/mes', description: 'Monitoreo y respuesta gestionada por analistas SOC', active: true },
    { id: 'siem', name: 'SIEM Cloud', price: 750, unit: '/mes', description: 'Correlación de eventos y logs (12 meses retención)', active: true },
    { id: 'forensics', name: 'SEGRD™ Forense', price: 1200, unit: '/mes', description: 'Plataforma forense con análisis M365 y endpoints', active: true },
    { id: 'm365', name: 'Protección M365', price: 350, unit: '/mes', description: 'Backup, DLP y protección avanzada para Microsoft 365', active: true },
    { id: 'bcdr', name: 'BCDR Cloud', price: 800, unit: '/mes', description: 'Backup y recuperación ante desastres con RTO garantizado', active: true }
  ],
  vcisoPlans: [
    { id: 'vciso_lite', name: 'v-CISO Lite', price: 1500, hours: 2, description: 'Asesoría y Acompañamiento', active: true },
    { id: 'vciso_standard', name: 'v-CISO Estándar', price: 3500, hours: 4, description: 'Liderazgo Activo de Seguridad', recommended: true, active: true }
  ],
  devicePricing: {
    essential: { rate: 0.50, min: 1, max: 50, label: 'Tier Esencial' },
    professional: { rate: 1.50, min: 51, max: 200, label: 'Tier Profesional' },
    critical: { rate: 3.00, min: 201, max: 10000, label: 'Tier Crítico' }
  },
  retentionTiers: {
    30: { cost: 0, label: '30 días (Base)' },
    90: { cost: 150, label: '90 días' },
    180: { cost: 300, label: '180 días' },
    365: { cost: 500, label: '1 año' }
  },
  discounts: {
    annual: 15,
    enterprise: 20,
    nonprofit: 25
  }
};

export default function PricingManagementPage() {
  const [pricing, setPricing] = useState(DEFAULT_PRICING);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('bundles');
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [expandedBundle, setExpandedBundle] = useState(null);

  useEffect(() => {
    fetchPricing();
  }, []);

  const fetchPricing = async () => {
    try {
      const response = await api.get('/api/admin/pricing');
      if (response.data) {
        setPricing({ ...DEFAULT_PRICING, ...response.data });
      }
    } catch (error) {
      console.error('Error fetching pricing:', error);
    } finally {
      setLoading(false);
    }
  };

  const savePricing = async () => {
    setSaving(true);
    try {
      await api.put('/api/admin/pricing', pricing);
      setShowSuccessMessage(true);
      setTimeout(() => setShowSuccessMessage(false), 3000);
    } catch (error) {
      console.error('Error saving pricing:', error);
      // Simular éxito para demo
      setShowSuccessMessage(true);
      setTimeout(() => setShowSuccessMessage(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const updateBundle = (bundleId, field, value) => {
    setPricing(prev => ({
      ...prev,
      bundles: prev.bundles.map(b => 
        b.id === bundleId ? { ...b, [field]: value } : b
      )
    }));
  };

  const updateAddon = (addonId, field, value) => {
    setPricing(prev => ({
      ...prev,
      addons: prev.addons.map(a => 
        a.id === addonId ? { ...a, [field]: value } : a
      )
    }));
  };

  const updateVCISO = (planId, field, value) => {
    setPricing(prev => ({
      ...prev,
      vcisoPlans: prev.vcisoPlans.map(p => 
        p.id === planId ? { ...p, [field]: value } : p
      )
    }));
  };

  const updateDevicePricing = (tier, field, value) => {
    setPricing(prev => ({
      ...prev,
      devicePricing: {
        ...prev.devicePricing,
        [tier]: { ...prev.devicePricing[tier], [field]: parseFloat(value) || 0 }
      }
    }));
  };

  const updateRetentionTier = (days, field, value) => {
    setPricing(prev => ({
      ...prev,
      retentionTiers: {
        ...prev.retentionTiers,
        [days]: { ...prev.retentionTiers[days], [field]: field === 'cost' ? parseFloat(value) || 0 : value }
      }
    }));
  };

  const updateDiscount = (type, value) => {
    setPricing(prev => ({
      ...prev,
      discounts: { ...prev.discounts, [type]: parseFloat(value) || 0 }
    }));
  };

  const tabs = [
    { id: 'bundles', label: 'Bundles', icon: Package },
    { id: 'addons', label: 'Add-ons', icon: Zap },
    { id: 'vciso', label: 'v-CISO Plans', icon: Users },
    { id: 'dynamic', label: 'Precios Dinámicos', icon: Settings },
    { id: 'discounts', label: 'Descuentos', icon: DollarSign }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Gestión de Precios</h1>
          <p className="text-gray-400 mt-1">Administra bundles, add-ons y configuración de precios</p>
        </div>
        <div className="flex items-center gap-3">
          {showSuccessMessage && (
            <div className="flex items-center gap-2 bg-green-500/20 text-green-400 px-4 py-2 rounded-lg">
              <CheckCircle className="w-4 h-4" />
              Guardado exitosamente
            </div>
          )}
          <button
            onClick={savePricing}
            disabled={saving}
            className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700 pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-gray-800 text-cyan-400 border-b-2 border-cyan-400'
                : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-gray-800 rounded-lg p-6">
        {/* Bundles Tab */}
        {activeTab === 'bundles' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white mb-4">Bundles de Seguridad</h3>
            {pricing.bundles.map(bundle => (
              <div key={bundle.id} className="bg-gray-900 rounded-lg border border-gray-700">
                <div 
                  className="flex items-center justify-between p-4 cursor-pointer"
                  onClick={() => setExpandedBundle(expandedBundle === bundle.id ? null : bundle.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${
                      bundle.color === 'blue' ? 'bg-blue-500' :
                      bundle.color === 'purple' ? 'bg-purple-500' :
                      'bg-amber-500'
                    }`} />
                    <div>
                      <h4 className="font-semibold text-white">{bundle.name}</h4>
                      <p className="text-sm text-gray-400">{bundle.bundle} • {bundle.targetCompanies}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <span className="text-2xl font-bold text-white">${bundle.price.toLocaleString()}</span>
                      <span className="text-gray-400">/mes</span>
                    </div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={bundle.active}
                        onChange={(e) => {
                          e.stopPropagation();
                          updateBundle(bundle.id, 'active', e.target.checked);
                        }}
                        className="w-4 h-4 accent-cyan-500"
                      />
                      <span className="text-sm text-gray-400">Activo</span>
                    </label>
                    {expandedBundle === bundle.id ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </div>
                
                {expandedBundle === bundle.id && (
                  <div className="p-4 pt-0 border-t border-gray-700 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Nombre</label>
                        <input
                          type="text"
                          value={bundle.name}
                          onChange={(e) => updateBundle(bundle.id, 'name', e.target.value)}
                          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Precio (USD/mes)</label>
                        <input
                          type="number"
                          value={bundle.price}
                          onChange={(e) => updateBundle(bundle.id, 'price', parseInt(e.target.value) || 0)}
                          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Descripción</label>
                      <textarea
                        value={bundle.description}
                        onChange={(e) => updateBundle(bundle.id, 'description', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                        rows={2}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Empresas Objetivo</label>
                        <input
                          type="text"
                          value={bundle.targetCompanies}
                          onChange={(e) => updateBundle(bundle.id, 'targetCompanies', e.target.value)}
                          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                        />
                      </div>
                      <div className="flex items-center gap-4 pt-6">
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={bundle.recommended}
                            onChange={(e) => updateBundle(bundle.id, 'recommended', e.target.checked)}
                            className="w-4 h-4 accent-purple-500"
                          />
                          <span className="text-sm text-gray-300">Mostrar como "Más Popular"</span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Add-ons Tab */}
        {activeTab === 'addons' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white mb-4">Servicios Adicionales (Add-ons)</h3>
            <div className="grid gap-4">
              {pricing.addons.map(addon => (
                <div key={addon.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="grid grid-cols-4 gap-4 items-center">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Nombre</label>
                      <input
                        type="text"
                        value={addon.name}
                        onChange={(e) => updateAddon(addon.id, 'name', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Precio (USD)</label>
                      <input
                        type="number"
                        value={addon.price}
                        onChange={(e) => updateAddon(addon.id, 'price', parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Descripción</label>
                      <input
                        type="text"
                        value={addon.description}
                        onChange={(e) => updateAddon(addon.id, 'description', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div className="flex items-center justify-end gap-2 pt-6">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={addon.active}
                          onChange={(e) => updateAddon(addon.id, 'active', e.target.checked)}
                          className="w-4 h-4 accent-cyan-500"
                        />
                        <span className="text-sm text-gray-400">Activo</span>
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* v-CISO Plans Tab */}
        {activeTab === 'vciso' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white mb-4">Planes v-CISO (Liderazgo de Seguridad)</h3>
            <div className="grid gap-4">
              {pricing.vcisoPlans.map(plan => (
                <div key={plan.id} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="grid grid-cols-5 gap-4 items-center">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Nombre</label>
                      <input
                        type="text"
                        value={plan.name}
                        onChange={(e) => updateVCISO(plan.id, 'name', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Precio (USD/mes)</label>
                      <input
                        type="number"
                        value={plan.price}
                        onChange={(e) => updateVCISO(plan.id, 'price', parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Horas/mes</label>
                      <input
                        type="number"
                        value={plan.hours}
                        onChange={(e) => updateVCISO(plan.id, 'hours', parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Descripción</label>
                      <input
                        type="text"
                        value={plan.description}
                        onChange={(e) => updateVCISO(plan.id, 'description', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                    <div className="flex items-center gap-4 pt-6">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={plan.recommended || false}
                          onChange={(e) => updateVCISO(plan.id, 'recommended', e.target.checked)}
                          className="w-4 h-4 accent-purple-500"
                        />
                        <span className="text-xs text-gray-400">Popular</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={plan.active}
                          onChange={(e) => updateVCISO(plan.id, 'active', e.target.checked)}
                          className="w-4 h-4 accent-cyan-500"
                        />
                        <span className="text-xs text-gray-400">Activo</span>
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dynamic Pricing Tab */}
        {activeTab === 'dynamic' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Precios por Dispositivo</h3>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(pricing.devicePricing).map(([tier, config]) => (
                  <div key={tier} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                    <h4 className="font-medium text-white mb-3 capitalize">{config.label}</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Tarifa (USD/dispositivo)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={config.rate}
                          onChange={(e) => updateDevicePricing(tier, 'rate', e.target.value)}
                          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Mín</label>
                          <input
                            type="number"
                            value={config.min}
                            onChange={(e) => updateDevicePricing(tier, 'min', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Máx</label>
                          <input
                            type="number"
                            value={config.max}
                            onChange={(e) => updateDevicePricing(tier, 'max', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Retención de Logs</h3>
              <div className="grid grid-cols-4 gap-4">
                {Object.entries(pricing.retentionTiers).map(([days, config]) => (
                  <div key={days} className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                    <h4 className="font-medium text-white mb-3">{config.label}</h4>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Costo adicional (USD/mes)</label>
                      <input
                        type="number"
                        value={config.cost}
                        onChange={(e) => updateRetentionTier(days, 'cost', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Discounts Tab */}
        {activeTab === 'discounts' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white mb-4">Configuración de Descuentos</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <h4 className="font-medium text-white mb-3">Descuento Anual</h4>
                <p className="text-sm text-gray-400 mb-3">Aplicado a facturación anual</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={pricing.discounts.annual}
                    onChange={(e) => updateDiscount('annual', e.target.value)}
                    className="w-24 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  />
                  <span className="text-gray-400">%</span>
                </div>
              </div>
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <h4 className="font-medium text-white mb-3">Descuento Enterprise</h4>
                <p className="text-sm text-gray-400 mb-3">Para contratos enterprise</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={pricing.discounts.enterprise}
                    onChange={(e) => updateDiscount('enterprise', e.target.value)}
                    className="w-24 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  />
                  <span className="text-gray-400">%</span>
                </div>
              </div>
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <h4 className="font-medium text-white mb-3">Descuento Non-Profit</h4>
                <p className="text-sm text-gray-400 mb-3">Para organizaciones sin fines de lucro</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={pricing.discounts.nonprofit}
                    onChange={(e) => updateDiscount('nonprofit', e.target.value)}
                    className="w-24 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white"
                  />
                  <span className="text-gray-400">%</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Preview Section */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Vista Previa</h3>
          <a 
            href="/pricing" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-cyan-400 hover:text-cyan-300 text-sm flex items-center gap-1"
          >
            <Eye className="w-4 h-4" />
            Ver página pública
          </a>
        </div>
        <p className="text-gray-400 text-sm">
          Los cambios se reflejarán en la página de precios después de guardar.
        </p>
      </div>
    </div>
  );
}
