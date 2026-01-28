/**
 * Dynamic Pricing Calculator Component
 * Calcula precios basado en:
 * - Cantidad de dispositivos
 * - Período de retención de logs
 * - Nivel de servicio (v-CISO)
 * - Add-ons adicionales
 */

import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Zap, 
  Download, 
  Mail, 
  ChevronDown, 
  ChevronUp,
  Check,
  TrendingUp
} from 'lucide-react';

// Pricing Model Configuration
const PRICING_MODEL = {
  // Per-device pricing tiers (monthly)
  devicePricing: {
    essential: {
      rate: 0.50,
      min: 1,
      max: 50
    },
    professional: {
      rate: 1.50,
      min: 51,
      max: 200
    },
    critical: {
      rate: 3.00,
      min: 201,
      max: Infinity
    }
  },
  
  // Log retention cost (monthly add-on)
  retentionTiers: {
    30: { cost: 0, label: '30 días' },
    90: { cost: 150, label: '90 días' },
    180: { cost: 300, label: '180 días' },
    365: { cost: 500, label: '1 año' }
  },
  
  // v-CISO Leadership plans
  vcisoPlans: {
    none: { cost: 0, label: 'Sin v-CISO', hours: 0 },
    lite: { cost: 1500, label: 'v-CISO Lite', hours: 2 },
    standard: { cost: 3500, label: 'v-CISO Estándar', hours: 4 }
  },
  
  // Add-ons (optional)
  addons: {
    dns: { cost: 150, label: 'Escudo DNS', unit: '/mes' },
    mdr: { cost: 500, label: 'MDR 24x7', unit: '/mes' },
    siem: { cost: 750, label: 'SIEM Cloud', unit: '/mes' },
    forensics: { cost: 1200, label: 'SEGRD™ Forense', unit: '/mes' },
    m365: { cost: 350, label: 'Protección M365', unit: '/mes' },
    bcdr: { cost: 800, label: 'BCDR Cloud', unit: '/mes' }
  }
};

const PricingCalculator = () => {
  const { t, i18n } = useTranslation(['common', 'pricing']);
  const [devices, setDevices] = useState(50);
  const [retention, setRetention] = useState(90);
  const [vciso, setVciso] = useState('none');
  const [selectedAddons, setSelectedAddons] = useState({});
  const [expandedSection, setExpandedSection] = useState('devices');

  // Calculate device tier cost
  const getDeviceTierCost = (deviceCount) => {
    if (deviceCount <= 50) return deviceCount * PRICING_MODEL.devicePricing.essential.rate;
    if (deviceCount <= 200) return deviceCount * PRICING_MODEL.devicePricing.professional.rate;
    return deviceCount * PRICING_MODEL.devicePricing.critical.rate;
  };

  // Calculate total price
  const calculations = useMemo(() => {
    const deviceCost = getDeviceTierCost(devices);
    const retentionCost = PRICING_MODEL.retentionTiers[retention].cost;
    const vcisosCost = PRICING_MODEL.vcisoPlans[vciso].cost;
    
    const addonsCost = Object.entries(selectedAddons).reduce((sum, [key, selected]) => {
      return selected ? sum + PRICING_MODEL.addons[key].cost : sum;
    }, 0);

    const subtotal = deviceCost + retentionCost + vcisosCost + addonsCost;
    const monthlyTotal = subtotal;
    const annualTotal = subtotal * 12;
    const annualSavings = (subtotal * 0.15) * 12; // 15% discount annually

    return {
      deviceCost: Math.round(deviceCost * 100) / 100,
      retentionCost,
      vcisosCost,
      addonsCost,
      subtotal: Math.round(subtotal * 100) / 100,
      monthlyTotal: Math.round(monthlyTotal * 100) / 100,
      annualTotal: Math.round(annualTotal * 100) / 100,
      annualSavings: Math.round(annualSavings * 100) / 100,
      monthlyAnnual: Math.round((annualTotal - annualSavings) / 12 * 100) / 100
    };
  }, [devices, retention, vciso, selectedAddons]);

  const toggleAddon = (addonKey) => {
    setSelectedAddons(prev => ({
      ...prev,
      [addonKey]: !prev[addonKey]
    }));
  };

  const handleExportEstimate = () => {
    const summary = generateSummary();
    // Could implement PDF generation or email sending
    console.log('Export estimate:', summary);
  };

  const generateSummary = () => ({
    devices,
    retention,
    vciso,
    selectedAddons,
    calculations,
    timestamp: new Date().toISOString()
  });

  return (
    <div className="w-full bg-gradient-to-br from-gray-900 via-gray-800 to-black rounded-lg p-8 text-white">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Estimador de Precios Dinámico</h2>
        <p className="text-gray-400">Calcula tu plan personalizado según dispositivos y retención de logs</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: Calculator Controls */}
        <div className="space-y-6">
          {/* Devices Slider */}
          <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
            <div 
              className="flex justify-between items-center cursor-pointer mb-4"
              onClick={() => setExpandedSection(expandedSection === 'devices' ? null : 'devices')}
            >
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Zap className="w-5 h-5 text-blue-400" />
                Dispositivos a Proteger
              </h3>
              {expandedSection === 'devices' ? 
                <ChevronUp className="w-5 h-5" /> : 
                <ChevronDown className="w-5 h-5" />
              }
            </div>
            
            {expandedSection === 'devices' && (
              <div className="space-y-4">
                <div className="flex items-end justify-between">
                  <span className="text-2xl font-bold text-blue-400">{devices}</span>
                  <span className="text-sm text-gray-400">dispositivos</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="500"
                  value={devices}
                  onChange={(e) => setDevices(Number(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1</span>
                  <span>500+</span>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3 text-sm">
                  <p className="text-blue-200">
                    Tier: <strong>{
                      devices <= 50 ? 'Esencial ($0.50/dispositivo)' :
                      devices <= 200 ? 'Profesional ($1.50/dispositivo)' :
                      'Crítico ($3.00/dispositivo)'
                    }</strong>
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Retention Period */}
          <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
            <div 
              className="flex justify-between items-center cursor-pointer mb-4"
              onClick={() => setExpandedSection(expandedSection === 'retention' ? null : 'retention')}
            >
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-amber-400" />
                Retención de Logs
              </h3>
              {expandedSection === 'retention' ? 
                <ChevronUp className="w-5 h-5" /> : 
                <ChevronDown className="w-5 h-5" />
              }
            </div>
            
            {expandedSection === 'retention' && (
              <div className="space-y-3">
                {Object.entries(PRICING_MODEL.retentionTiers).map(([days, { cost, label }]) => (
                  <label key={days} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      type="radio"
                      name="retention"
                      value={days}
                      checked={retention === Number(days)}
                      onChange={(e) => setRetention(Number(e.target.value))}
                      className="w-4 h-4 accent-amber-500"
                    />
                    <span className="flex-1 group-hover:text-amber-200">{label}</span>
                    <span className="text-amber-400 font-semibold">
                      {cost > 0 ? `+$${cost}/mes` : 'Base'}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* v-CISO Selection */}
          <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
            <div 
              className="flex justify-between items-center cursor-pointer mb-4"
              onClick={() => setExpandedSection(expandedSection === 'vciso' ? null : 'vciso')}
            >
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Check className="w-5 h-5 text-purple-400" />
                Liderazgo de Seguridad (v-CISO)
              </h3>
              {expandedSection === 'vciso' ? 
                <ChevronUp className="w-5 h-5" /> : 
                <ChevronDown className="w-5 h-5" />
              }
            </div>
            
            {expandedSection === 'vciso' && (
              <div className="space-y-3">
                {Object.entries(PRICING_MODEL.vcisoPlans).map(([key, { cost, label, hours }]) => (
                  <label key={key} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      type="radio"
                      name="vciso"
                      value={key}
                      checked={vciso === key}
                      onChange={(e) => setVciso(e.target.value)}
                      className="w-4 h-4 accent-purple-500"
                    />
                    <span className="flex-1 group-hover:text-purple-200">
                      {label} {hours > 0 && <span className="text-sm text-gray-500">({hours}h/mes)</span>}
                    </span>
                    <span className="text-purple-400 font-semibold">
                      {cost > 0 ? `$${cost.toLocaleString()}/mes` : 'Gratis'}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Add-ons */}
          <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
            <div 
              className="flex justify-between items-center cursor-pointer mb-4"
              onClick={() => setExpandedSection(expandedSection === 'addons' ? null : 'addons')}
            >
              <h3 className="text-lg font-semibold">Servicios Adicionales</h3>
              {expandedSection === 'addons' ? 
                <ChevronUp className="w-5 h-5" /> : 
                <ChevronDown className="w-5 h-5" />
              }
            </div>
            
            {expandedSection === 'addons' && (
              <div className="space-y-3">
                {Object.entries(PRICING_MODEL.addons).map(([key, { cost, label }]) => (
                  <label key={key} className="flex items-center gap-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={selectedAddons[key] || false}
                      onChange={() => toggleAddon(key)}
                      className="w-4 h-4 accent-green-500 rounded"
                    />
                    <span className="flex-1 group-hover:text-green-200">{label}</span>
                    <span className="text-green-400 font-semibold">+$${cost}/mes</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Summary & Total */}
        <div className="space-y-6">
          {/* Summary Card */}
          <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-lg p-8 border border-blue-500/30 sticky top-8">
            <h3 className="text-xl font-bold mb-6">Resumen de tu Estimación</h3>
            
            <div className="space-y-4 mb-6 pb-6 border-b border-gray-700">
              {/* Device Cost */}
              <div className="flex justify-between items-center">
                <span className="text-gray-300">Costo por Dispositivos</span>
                <span className="text-lg font-semibold text-blue-400">
                  ${calculations.deviceCost.toLocaleString()}
                </span>
              </div>

              {/* Retention Cost */}
              {calculations.retentionCost > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Retención Extendida</span>
                  <span className="text-lg font-semibold text-amber-400">
                    +${calculations.retentionCost.toLocaleString()}
                  </span>
                </div>
              )}

              {/* v-CISO Cost */}
              {calculations.vcisosCost > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">v-CISO Leadership</span>
                  <span className="text-lg font-semibold text-purple-400">
                    +${calculations.vcisosCost.toLocaleString()}
                  </span>
                </div>
              )}

              {/* Add-ons Cost */}
              {calculations.addonsCost > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Add-ons Seleccionados</span>
                  <span className="text-lg font-semibold text-green-400">
                    +${calculations.addonsCost.toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {/* Monthly Total */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg p-6 mb-4">
              <div className="text-sm text-blue-100 mb-2">Precio Mensual</div>
              <div className="text-4xl font-bold text-white mb-2">
                ${calculations.monthlyTotal.toLocaleString()}
                <span className="text-lg text-blue-100">/mes</span>
              </div>
              <div className="text-sm text-blue-100">
                = ${(calculations.monthlyTotal * 12).toLocaleString()} anual
              </div>
            </div>

            {/* Annual Option */}
            <div className="bg-gray-800 border border-green-500/30 rounded-lg p-4 mb-4">
              <div className="text-sm text-gray-300 mb-2">Opción Anual (15% Descuento)</div>
              <div className="text-2xl font-bold text-green-400 mb-2">
                ${calculations.monthlyAnnual.toLocaleString()}
                <span className="text-sm text-green-300">/mes</span>
              </div>
              <div className="text-xs text-gray-400">
                Total anual: ${calculations.annualTotal.toLocaleString()} (Ahorra ${calculations.annualSavings.toLocaleString()})
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              <button 
                onClick={handleExportEstimate}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
              >
                <Download className="w-5 h-5" />
                Descargar Estimación
              </button>
              <button 
                className="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
              >
                <Mail className="w-5 h-5" />
                Enviar por Email
              </button>
            </div>

            {/* Disclaimer */}
            <p className="text-xs text-gray-500 mt-4 text-center">
              Esta es una estimación. Los precios finales pueden variar según auditoría de dispositivos reales.
            </p>
          </div>

          {/* Info Box */}
          <div className="bg-amber-900/20 border border-amber-600/30 rounded-lg p-4">
            <h4 className="text-amber-300 font-semibold mb-2">💡 Tip: Cómo Ahorrar</h4>
            <ul className="text-sm text-amber-100/80 space-y-1">
              <li>• Combina retención de 30 días con rotación de logs externos</li>
              <li>• Agrupa dispositivos por función para optimizar costos</li>
              <li>• Negocia descuentos especiales para compromisos anuales</li>
              <li>• Consulta nuestro equipo de ventas para casos corporativos</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingCalculator;
