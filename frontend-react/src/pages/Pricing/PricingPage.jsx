/**
 * Pricing Page - Jeturing Commercial Pricing Structure v2.0
 * Aligned with the Jeturing 2025 Commercial Proposal
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import { 
  Check, 
  X, 
  Shield, 
  Zap, 
  Building2,
  ArrowRight,
  Crown,
  Users,
  Server,
  Eye,
  FileSearch,
  Lock,
  Cloud,
  Cpu,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Mail
} from 'lucide-react';

// v-CISO Plans (Leadership-as-a-Service)
const vcisoPLans = [
  {
    id: 'vciso_lite',
    name: 'v-CISO Lite',
    subtitle: 'Asesoría y Acompañamiento',
    price: 1500,
    description: 'Ideal para PYMEs que necesitan guía estratégica en seguridad sin un ejecutivo de tiempo completo.',
    features: [
      'Reuniones mensuales de asesoría (2h)',
      'Revisión de políticas y procedimientos',
      'Evaluación trimestral de riesgos',
      'Acceso a plantillas de seguridad',
      'Consulta por email (respuesta 48h)',
      'Reporte mensual de estado',
    ],
    recommended: false,
    color: 'blue'
  },
  {
    id: 'vciso_standard',
    name: 'v-CISO Estándar',
    subtitle: 'Liderazgo Activo de Seguridad',
    price: 3500,
    description: 'Para empresas que requieren un líder de seguridad activo sin el costo de un CISO interno.',
    features: [
      'Reuniones semanales de dirección (4h/mes)',
      'Gestión activa del programa de seguridad',
      'Roadmap anual de madurez',
      'Supervisión de proveedores de seguridad',
      'Representación ante auditorías',
      'Desarrollo y capacitación del equipo',
      'Línea directa de consulta (respuesta 24h)',
      'Reportes ejecutivos para C-Level',
    ],
    recommended: true,
    color: 'purple'
  }
];

// Security Bundles
const securityBundles = [
  {
    id: 'bundle_essential',
    name: 'Protección Esencial',
    bundle: 'Bundle I',
    price: 2500,
    description: 'Cobertura base para empresas que inician su programa de ciberseguridad.',
    targetCompanies: 'Hasta 100 empleados',
    includes: [
      { name: 'Evaluación Anual de Seguridad', included: true },
      { name: 'EDR (Endpoint Detection & Response)', included: true },
      { name: 'Protección DNS', included: true },
      { name: 'v-CISO Lite (2h/mes)', included: true },
      { name: 'Backup Cloud Básico (500GB)', included: true },
      { name: 'MDR 24x7', included: false },
      { name: 'SIEM Gestionado', included: false },
      { name: 'SEGRD™ Forense', included: false },
      { name: 'Protección M365', included: false },
    ],
    color: 'blue',
    recommended: false
  },
  {
    id: 'bundle_professional',
    name: 'Resiliencia Profesional',
    bundle: 'Bundle II',
    price: 4500,
    description: 'Protección robusta con monitoreo activo y capacidad de respuesta rápida.',
    targetCompanies: '100-300 empleados',
    includes: [
      { name: 'Todo de Esencial +', included: true, highlight: true },
      { name: 'MDR 24x7 (SOC gestionado)', included: true },
      { name: 'SIEM Gestionado', included: true },
      { name: 'v-CISO Activo (4h/mes)', included: true },
      { name: 'SEGRD™ Análisis Forense', included: true },
      { name: 'Protección M365 Avanzada', included: true },
      { name: 'Pruebas de Penetración (anual)', included: true },
      { name: 'Cloud Security Posture', included: true },
      { name: 'BCDR Completo', included: false },
      { name: 'v-CISO Dedicado', included: false },
    ],
    color: 'purple',
    recommended: true
  },
  {
    id: 'bundle_critical',
    name: 'Blindaje Misión Crítica',
    bundle: 'Bundle III',
    price: 6500,
    description: 'Máxima protección para operaciones críticas. Cero tolerancia al downtime.',
    targetCompanies: '300+ empleados / Infraestructura crítica',
    includes: [
      { name: 'Todo de Profesional +', included: true, highlight: true },
      { name: 'v-CISO Dedicado (8h/mes)', included: true },
      { name: 'SOC 24/7 con Analista Asignado', included: true },
      { name: 'SEGRD™ con IA Forense Avanzada', included: true },
      { name: 'BCDR Garantizado (RTO 4h)', included: true },
      { name: 'Pentesting Trimestral', included: true },
      { name: 'Threat Hunting Proactivo', included: true },
      { name: 'Cyber Insurance Assistance', included: true },
      { name: 'Simulacros de IR Semestrales', included: true },
      { name: 'Retainer de Respuesta a Incidentes', included: true },
    ],
    color: 'amber',
    recommended: false
  }
];

// Add-on Services (Escudos de Seguridad)
const addOnServices = [
  {
    name: 'Escudo DNS',
    icon: Shield,
    price: 150,
    unit: '/mes',
    description: 'Filtrado DNS avanzado contra malware, phishing y dominios maliciosos'
  },
  {
    name: 'MDR 24x7',
    icon: Eye,
    price: 500,
    unit: '/mes',
    description: 'Monitoreo, detección y respuesta gestionada por analistas SOC'
  },
  {
    name: 'SIEM Cloud',
    icon: Server,
    price: 750,
    unit: '/mes',
    description: 'Correlación de eventos y logs con retención de 12 meses'
  },
  {
    name: 'SEGRD™ Forense',
    icon: FileSearch,
    price: 1200,
    unit: '/mes',
    description: 'Plataforma forense con análisis M365, credenciales y endpoints'
  },
  {
    name: 'Protección M365',
    icon: Mail,
    price: 350,
    unit: '/mes',
    description: 'Backup, DLP y protección avanzada para Microsoft 365'
  },
  {
    name: 'BCDR Cloud',
    icon: Cloud,
    price: 800,
    unit: '/mes',
    description: 'Backup y recuperación ante desastres con RTO garantizado'
  }
];

const PricingPage = () => {
  const { t, i18n } = useTranslation(['common', 'pricing']);
  const navigate = useNavigate();
  const [billingPeriod, setBillingPeriod] = useState('monthly');
  const [showVCISO, setShowVCISO] = useState(false);
  const [showAddOns, setShowAddOns] = useState(false);

  const getPrice = (basePrice) => {
    if (billingPeriod === 'yearly') {
      return Math.round(basePrice * 12 * 0.85 / 12);
    }
    return basePrice;
  };

  const handleContactSales = (planId) => {
    navigate(`/contact?plan=${planId}&source=pricing`);
  };

  const handleStartChecklist = () => {
    navigate('/security-checklist');
  };

  return (
    <>
      <Helmet>
        <title>{t('pricing:title')} - SEGRD</title>
        <meta name="description" content={t('pricing:subtitle')} />
      </Helmet>
      
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 py-12 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Hero Section with Image */}
          <div className="mb-16 rounded-2xl overflow-hidden bg-gradient-to-r from-slate-800 to-slate-900 border border-cyan-500/20">
            <div className="grid md:grid-cols-2 gap-8 items-center p-8 md:p-12">
              <div>
                <div className="flex items-center justify-center gap-3 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
                    <Shield className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-2xl font-bold text-white">JETURING</span>
                </div>
                <h1 className="text-4xl font-bold text-white mb-4">
                  {t('pricing:title')}
                </h1>
                <p className="text-slate-300 text-lg">
                  {t('pricing:subtitle')}
                </p>
              </div>
            </div>
          </div>

          {/* CTA: Take Assessment */}
          <div className="text-center mb-12">
            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-6 max-w-2xl mx-auto">
              <h3 className="text-xl font-semibold text-white mb-2">{i18n.language === 'es' ? '¿No sabes qué plan necesitas?' : "Don't know which plan you need?"}</h3>
              <p className="text-slate-400 mb-4">
                {i18n.language === 'es' 
                  ? 'Responde nuestro checklist rápido de ciberseguridad y te recomendaremos el nivel adecuado.'
                  : 'Answer our quick security checklist and we\'ll recommend the right level for you.'
                }
              </p>
              <button
                onClick={handleStartChecklist}
                className="bg-cyan-600 hover:bg-cyan-700 text-white font-semibold py-3 px-8 rounded-lg transition flex items-center gap-2 mx-auto"
              >
                <FileSearch className="w-5 h-5" />
                {i18n.language === 'es' ? 'Hacer Evaluación Gratuita' : 'Free Assessment'}
              </button>
            </div>
          </div>

        {/* Billing Toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-slate-800 rounded-lg p-1 inline-flex">
            <button
              onClick={() => setBillingPeriod('monthly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'monthly'
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Mensual
            </button>
            <button
              onClick={() => setBillingPeriod('yearly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'yearly'
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Anual
              <span className="ml-2 text-xs text-green-400">Ahorra 15%</span>
            </button>
          </div>
        </div>

        {/* Security Bundles - Main Grid */}
        <div className="mb-16">
          <h2 className="text-2xl font-bold text-white text-center mb-8">
            🛡️ Bundles de Seguridad Integral
          </h2>
          <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {securityBundles.map((bundle) => (
              <div
                key={bundle.id}
                className={`relative rounded-2xl border-2 p-6 transition-all hover:scale-[1.02] ${
                  bundle.color === 'blue' ? 'border-blue-500/50 bg-blue-500/5 hover:border-blue-500' :
                  bundle.color === 'purple' ? 'border-purple-500/50 bg-purple-500/5 hover:border-purple-500' :
                  'border-amber-500/50 bg-amber-500/5 hover:border-amber-500'
                }`}
              >
                {/* Popular Badge */}
                {bundle.recommended && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <span className="bg-purple-500 text-white text-xs font-bold px-4 py-1 rounded-full flex items-center gap-1">
                      <Crown className="w-3 h-3" />
                      MÁS POPULAR
                    </span>
                  </div>
                )}

                {/* Bundle Header */}
                <div className="text-center mb-6">
                  <span className={`text-sm font-semibold ${
                    bundle.color === 'blue' ? 'text-blue-400' :
                    bundle.color === 'purple' ? 'text-purple-400' :
                    'text-amber-400'
                  }`}>
                    {bundle.bundle}
                  </span>
                  <h3 className="text-xl font-bold text-white mt-1">{bundle.name}</h3>
                  <p className="text-slate-400 text-sm mt-2">{bundle.description}</p>
                  <p className="text-slate-500 text-xs mt-1">{bundle.targetCompanies}</p>
                </div>

                {/* Price */}
                <div className="text-center mb-6">
                  <span className="text-4xl font-bold text-white">${getPrice(bundle.price).toLocaleString()}</span>
                  <span className="text-slate-400 ml-1">/mes</span>
                  {billingPeriod === 'yearly' && (
                    <p className="text-green-400 text-sm mt-1">
                      ${(bundle.price * 12 * 0.85).toLocaleString()}/año
                    </p>
                  )}
                </div>

                {/* Features */}
                <div className="space-y-2 mb-6">
                  {bundle.includes.map((item, idx) => (
                    <div key={idx} className={`flex items-center gap-2 text-sm ${
                      item.highlight ? 'text-white font-semibold' : 
                      item.included ? 'text-slate-300' : 'text-slate-500 line-through'
                    }`}>
                      {item.included ? (
                        <Check className={`w-4 h-4 flex-shrink-0 ${
                          bundle.color === 'blue' ? 'text-blue-400' :
                          bundle.color === 'purple' ? 'text-purple-400' :
                          'text-amber-400'
                        }`} />
                      ) : (
                        <X className="w-4 h-4 text-slate-600 flex-shrink-0" />
                      )}
                      <span>{item.name}</span>
                    </div>
                  ))}
                </div>

                {/* CTA Button */}
                <button
                  onClick={() => handleContactSales(bundle.id)}
                  className={`w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors ${
                    bundle.color === 'blue' ? 'bg-blue-600 hover:bg-blue-700 text-white' :
                    bundle.color === 'purple' ? 'bg-purple-600 hover:bg-purple-700 text-white' :
                    'bg-amber-600 hover:bg-amber-700 text-white'
                  }`}
                >
                  Solicitar Propuesta
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>



        {/* v-CISO Section (Collapsible) */}
        <div className="mb-12">
          <button
            onClick={() => setShowVCISO(!showVCISO)}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl p-6 flex items-center justify-between hover:border-cyan-500/50 transition"
          >
            <div className="flex items-center gap-4">
              <Users className="w-8 h-8 text-cyan-400" />
              <div className="text-left">
                <h3 className="text-xl font-bold text-white">v-CISO: Director Virtual de Seguridad</h3>
                <p className="text-slate-400">Liderazgo de seguridad sin el costo de un ejecutivo tiempo completo</p>
              </div>
            </div>
            {showVCISO ? (
              <ChevronUp className="w-6 h-6 text-slate-400" />
            ) : (
              <ChevronDown className="w-6 h-6 text-slate-400" />
            )}
          </button>

          {showVCISO && (
            <div className="mt-4 grid md:grid-cols-2 gap-6">
              {vcisoPLans.map((plan) => (
                <div
                  key={plan.id}
                  className={`rounded-xl border-2 p-6 ${
                    plan.color === 'blue' ? 'border-blue-500/50 bg-blue-500/5' : 
                    'border-purple-500/50 bg-purple-500/5'
                  }`}
                >
                  {plan.recommended && (
                    <span className="bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-full mb-4 inline-block">
                      RECOMENDADO
                    </span>
                  )}
                  <h4 className="text-xl font-bold text-white">{plan.name}</h4>
                  <p className="text-slate-400 text-sm mb-4">{plan.subtitle}</p>
                  <div className="mb-4">
                    <span className="text-3xl font-bold text-white">${getPrice(plan.price).toLocaleString()}</span>
                    <span className="text-slate-400">/mes</span>
                  </div>
                  <p className="text-slate-300 text-sm mb-4">{plan.description}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-slate-300 text-sm">
                        <Check className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                          plan.color === 'blue' ? 'text-blue-400' : 'text-purple-400'
                        }`} />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => handleContactSales(plan.id)}
                    className={`w-full py-2 rounded-lg font-medium ${
                      plan.color === 'blue' ? 'bg-blue-600 hover:bg-blue-700' : 
                      'bg-purple-600 hover:bg-purple-700'
                    } text-white transition`}
                  >
                    Contratar v-CISO
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add-on Services (Collapsible) */}
        <div className="mb-12">
          <button
            onClick={() => setShowAddOns(!showAddOns)}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl p-6 flex items-center justify-between hover:border-cyan-500/50 transition"
          >
            <div className="flex items-center gap-4">
              <Zap className="w-8 h-8 text-yellow-400" />
              <div className="text-left">
                <h3 className="text-xl font-bold text-white">Escudos de Seguridad (Add-ons)</h3>
                <p className="text-slate-400">Servicios individuales para complementar tu protección</p>
              </div>
            </div>
            {showAddOns ? (
              <ChevronUp className="w-6 h-6 text-slate-400" />
            ) : (
              <ChevronDown className="w-6 h-6 text-slate-400" />
            )}
          </button>

          {showAddOns && (
            <div className="mt-4 grid md:grid-cols-3 gap-4">
              {addOnServices.map((service, idx) => (
                <div
                  key={idx}
                  className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-slate-600 transition"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <service.icon className="w-6 h-6 text-cyan-400" />
                    <h4 className="font-semibold text-white">{service.name}</h4>
                  </div>
                  <p className="text-slate-400 text-sm mb-3">{service.description}</p>
                  <div className="flex items-baseline">
                    <span className="text-2xl font-bold text-white">${service.price}</span>
                    <span className="text-slate-400 text-sm ml-1">{service.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Comparison Note */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 max-w-4xl mx-auto mb-12">
          <h3 className="text-xl font-bold text-white mb-4 text-center">¿Por qué elegir Jeturing?</h3>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="w-12 h-12 bg-cyan-500/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Shield className="w-6 h-6 text-cyan-400" />
              </div>
              <h4 className="font-semibold text-white mb-1">Sin Sorpresas</h4>
              <p className="text-slate-400 text-sm">Precio fijo mensual. Sin costos ocultos ni sorpresas.</p>
            </div>
            <div>
              <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Cpu className="w-6 h-6 text-purple-400" />
              </div>
              <h4 className="font-semibold text-white mb-1">Tecnología + Humanos</h4>
              <p className="text-slate-400 text-sm">IA forense + analistas expertos 24/7.</p>
            </div>
            <div>
              <div className="w-12 h-12 bg-amber-500/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Lock className="w-6 h-6 text-amber-400" />
              </div>
              <h4 className="font-semibold text-white mb-1">Cumplimiento Incluido</h4>
              <p className="text-slate-400 text-sm">Te ayudamos con ISO 27001, PCI, HIPAA y más.</p>
            </div>
          </div>
        </div>

        {/* Contact CTA */}
        <div className="text-center">
          <p className="text-slate-400 mb-4">
            ¿Necesitas una solución personalizada o tienes preguntas?
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <a
              href="mailto:sales@jeturing.com"
              className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg transition"
            >
              <Mail className="w-5 h-5" />
              sales@jeturing.com
            </a>
            <button
              onClick={() => navigate('/contact')}
              className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-6 py-3 rounded-lg transition"
            >
              Contactar Ventas
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Login Link */}
        <div className="text-center mt-8">
          <p className="text-slate-500">
            ¿Ya tienes cuenta?{' '}
            <a href="/login" className="text-cyan-400 hover:underline">
              Iniciar sesión
            </a>
          </p>
        </div>

        {/* Footer */}
        <div className="text-center mt-12 pt-8 border-t border-slate-800">
          <p className="text-slate-500 text-sm">
            🔐 Jeturing Inc. – Innovate. Secure. Transform.
          </p>
          <p className="text-slate-600 text-xs mt-2">
            {i18n.language === 'es' 
              ? 'Todos los precios en USD. Facturación disponible en moneda local para LATAM.'
              : 'All prices in USD. Local currency billing available for LATAM.'
            }
          </p>
        </div>
      </div>
    </div>
    </>
  );
};

export default PricingPage;
