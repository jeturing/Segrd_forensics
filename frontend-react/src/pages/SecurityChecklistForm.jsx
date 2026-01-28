/**
 * Security Checklist Form - Dimensionamiento de Servicios v2.0
 * Formulario interactivo completo con sistema de valoración y recomendaciones
 * Basado en el Checklist Rápido de Ciberseguridad de Jeturing/SEGRD
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import axios from 'axios';
import { AlertCircle, CheckCircle2, Loader, Shield, ArrowRight, Mail } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '/api';

// Sistema de puntuación para calcular nivel de riesgo y recomendaciones
const SCORING_WEIGHTS = {
  // Factores que aumentan riesgo (positivos)
  had_incidents: 3,
  operates_24_7: 2,
  attack_could_stop_business: 3,
  clients_demand_security: 2,
  needs_digital_evidence: 2,
  concerned_internal_fraud: 2,
  security_only_it: 1,
  uses_m365: 1,
  has_vpn: 1,
  
  // Factores que reducen riesgo (negativos - empresa ya tiene controles)
  has_security_officer: -2,
  has_policies: -1,
  has_24_7_monitoring: -3,
  has_centralized_logs: -2,
  has_backups: -1,
  tested_backups: -2,
  can_reconstruct_incident: -2,
  has_cyber_insurance: -1,
};

// Umbrales de empleados para escalar recomendaciones
const EMPLOYEE_THRESHOLDS = {
  small: 50,    // < 50 empleados
  medium: 200,  // 50-200 empleados
  large: 500    // > 200 empleados
};

// Precios de referencia (USD/mes)
const PRICING = {
  vciso_lite: 1500,
  vciso_standard: 3500,
  bundle_essential: 2500,
  bundle_professional: 4500,
  bundle_critical: 6500,
};

const SecurityChecklistForm = () => {
  const { t, i18n } = useTranslation(['common', 'checklist']);
  const [formData, setFormData] = useState({
    // Sección 1: Datos básicos
    company_name: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    country: '',
    industry: '',
    employees: '',

    // Sección 2: Tecnología
    computers: '',
    has_servers: '',
    uses_m365: false,
    m365_users: '',
    has_vpn: false,

    // Sección 3: Seguridad actual
    has_security_officer: false,
    security_only_it: false,
    has_policies: false,

    // Sección 4: Riesgos e Incidentes
    had_incidents: false,
    operates_24_7: false,
    attack_could_stop_business: false,

    // Sección 5: Cumplimiento
    clients_demand_security: false,
    has_cyber_insurance: false,
    compliance_requirements: [],

    // Sección 6: Monitoreo
    has_24_7_monitoring: false,
    has_centralized_logs: false,
    can_reconstruct_incident: false,

    // Sección 7: Respaldo
    has_backups: false,
    tested_backups: false,
    knows_recovery_time: false,

    // Sección 8: Legal y Forense
    needs_digital_evidence: false,
    concerned_internal_fraud: false,

    // Sección 9: Comentarios
    comments: ''
  });

  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState(null);
  const [sendEmail, setSendEmail] = useState(true);
  const [downloadPdf, setDownloadPdf] = useState(true);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleRadioChange = (name, value) => {
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleComplianceChange = (compliance) => {
    setFormData(prev => ({
      ...prev,
      compliance_requirements: prev.compliance_requirements.includes(compliance)
        ? prev.compliance_requirements.filter(c => c !== compliance)
        : [...prev.compliance_requirements, compliance]
    }));
  };

  // Calcular puntuación de riesgo basada en respuestas
  const calculateRiskScore = () => {
    let score = 5; // Base score
    
    Object.keys(SCORING_WEIGHTS).forEach(key => {
      if (formData[key] === true || formData[key] === 'Sí') {
        score += SCORING_WEIGHTS[key];
      }
    });

    // Ajustar por tamaño de empresa
    const employees = parseInt(formData.employees) || 0;
    if (employees > EMPLOYEE_THRESHOLDS.large) score += 2;
    else if (employees > EMPLOYEE_THRESHOLDS.medium) score += 1;

    // Ajustar por compliance
    if (formData.compliance_requirements.length > 0 && !formData.compliance_requirements.includes('Ninguna')) {
      score += formData.compliance_requirements.length;
    }

    return Math.max(1, Math.min(10, score));
  };

  // Determinar nivel recomendado
  const getRecommendedTier = () => {
    const score = calculateRiskScore();
    if (score <= 4) return 'esencial';
    if (score <= 7) return 'profesional';
    return 'critico';
  };

  // Generar recomendaciones detalladas
  const generateRecommendations = () => {
    const tier = getRecommendedTier();
    const score = calculateRiskScore();
    const employees = parseInt(formData.employees) || 0;
    
    const recs = {
      tier,
      score,
      tierName: tier === 'esencial' ? 'Protección Esencial' : 
                tier === 'profesional' ? 'Resiliencia Profesional' : 
                'Blindaje Misión Crítica',
      pricing: tier === 'esencial' ? PRICING.bundle_essential : 
               tier === 'profesional' ? PRICING.bundle_professional : 
               PRICING.bundle_critical,
      vciso: employees > EMPLOYEE_THRESHOLDS.medium ? 'standard' : 'lite',
      vcisoPricing: employees > EMPLOYEE_THRESHOLDS.medium ? PRICING.vciso_standard : PRICING.vciso_lite,
      services: [],
      gaps: [],
      urgentActions: []
    };

    // Identificar brechas y servicios necesarios
    if (!formData.has_security_officer && formData.security_only_it) {
      recs.gaps.push('Sin liderazgo formal de seguridad');
      recs.services.push('v-CISO (Director Virtual de Seguridad)');
    }

    if (!formData.has_policies) {
      recs.gaps.push('Políticas de seguridad no documentadas');
      recs.services.push('Desarrollo de políticas y procedimientos');
    }

    if (!formData.has_24_7_monitoring) {
      recs.gaps.push('Sin monitoreo continuo de seguridad');
      recs.services.push('MDR 24x7 (SOC gestionado)');
    }

    if (!formData.has_centralized_logs) {
      recs.gaps.push('Logs no centralizados para investigación');
      recs.services.push('SIEM (Gestión de eventos de seguridad)');
    }

    if (!formData.has_backups || !formData.tested_backups) {
      recs.gaps.push('Respaldos no probados o inexistentes');
      recs.services.push('BCDR (Respaldo y recuperación ante desastres)');
    }

    if (formData.uses_m365) {
      recs.services.push('Protección M365 (correo y colaboración)');
    }

    if (formData.has_vpn) {
      recs.services.push('Protección DNS y Zero Trust');
    }

    if (formData.needs_digital_evidence || formData.concerned_internal_fraud) {
      recs.services.push('SEGRD™ Análisis Forense Digital');
    }

    // Acciones urgentes
    if (formData.had_incidents) {
      recs.urgentActions.push('Evaluación post-incidente y remediación');
    }

    if (formData.attack_could_stop_business && !formData.has_24_7_monitoring) {
      recs.urgentActions.push('Implementar monitoreo 24/7 inmediatamente');
    }

    if (formData.clients_demand_security && !formData.has_policies) {
      recs.urgentActions.push('Documentar políticas para cumplir requisitos de clientes');
    }

    if (formData.compliance_requirements.includes('ISO 27001') || 
        formData.compliance_requirements.includes('PCI-DSS')) {
      recs.urgentActions.push('Auditoría de cumplimiento y gap analysis');
    }

    return recs;
  };

  const validateForm = () => {
    if (!formData.company_name.trim()) return 'Nombre de empresa es requerido';
    if (!formData.contact_email.trim()) return 'Email de contacto es requerido';
    if (!formData.country.trim()) return 'País es requerido';
    if (!formData.industry.trim()) return 'Industria es requerida';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    const recs = generateRecommendations();
    setRecommendations(recs);

    try {
      const payload = {
        ...formData,
        recommended_tier: recs.tierName,
        risk_score: recs.score,
        recommendations: recs,
        submitted_at: new Date().toISOString(),
        send_email: sendEmail,
        return_pdf: downloadPdf
      };

      const response = await axios.post(`${API_BASE_URL}/security-checklist/submit`, payload);

      if (response.data?.success) {
        // Descargar PDF si viene en la respuesta
        if (downloadPdf && response.data.pdf_base64) {
          const binary = atob(response.data.pdf_base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'application/pdf' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'propuesta-checklist.pdf';
          a.click();
          URL.revokeObjectURL(url);
        }

        setSubmitted(true);
        setTimeout(() => window.scrollTo(0, 0), 300);
      } else {
        setSubmitted(false);
        setError('No se pudo enviar el formulario. Por favor intenta nuevamente.');
      }
    } catch (err) {
      console.error('Error submitting form:', err);
      setSubmitted(false);
      setError('No se pudo enviar el formulario. Revisa tu conexión e intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  if (submitted && recommendations) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
        <div className="max-w-4xl mx-auto pt-12">
          {/* Header con Logo */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-white">JETURING</span>
            </div>
            <p className="text-cyan-400 font-medium">Innovate. Secure. Transform.</p>
          </div>

          {/* Resultado Principal */}
          <div className="bg-slate-800 border border-green-500/30 rounded-xl p-8 mb-8">
            <div className="flex items-center gap-4 mb-6">
              <CheckCircle2 className="w-12 h-12 text-green-500" />
              <div>
                <h2 className="text-2xl font-bold text-white">¡Análisis Completado!</h2>
                <p className="text-slate-400">Gracias, {formData.company_name}</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 mb-4">
              <button
                onClick={() => window.print()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700 text-white hover:bg-slate-600 transition"
              >
                🖨️ Imprimir / Guardar PDF
              </button>
              <button
                onClick={() => {
                  const mailtoLink = `mailto:sales@jeturing.com?subject=Resultados%20de%20Evaluación%20de%20Seguridad%20-%20${encodeURIComponent(formData.company_name)}&body=He%20completado%20la%20evaluación%20de%20seguridad.%20Mi%20puntuación%20de%20riesgo%20es%20${recommendations.score}/10%20y%20se%20recomienda%20el%20plan%20${encodeURIComponent(recommendations.tierName)}.%0A%0AContacto:%20${encodeURIComponent(formData.contact_name)}%20${encodeURIComponent(formData.contact_email)}`;
                  window.location.href = mailtoLink;
                }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-700 transition"
              >
                ✉️ Enviar por Email
              </button>
              <span className="text-slate-400 text-sm">
                *Precios tentativos, sujetos a validación comercial.*
              </span>
            </div>

            {/* Recomendación Principal */}
            <div className={`rounded-xl p-6 mb-6 ${
              recommendations.tier === 'esencial' ? 'bg-blue-500/10 border border-blue-500/30' :
              recommendations.tier === 'profesional' ? 'bg-purple-500/10 border border-purple-500/30' :
              'bg-amber-500/10 border border-amber-500/30'
            }`}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-slate-400 text-sm mb-1">Nivel Recomendado</p>
                  <h3 className={`text-2xl font-bold ${
                    recommendations.tier === 'esencial' ? 'text-blue-400' :
                    recommendations.tier === 'profesional' ? 'text-purple-400' :
                    'text-amber-400'
                  }`}>
                    {recommendations.tierName}
                  </h3>
                </div>
                <div className="text-right">
                  <p className="text-slate-400 text-sm mb-1">Inversión Mensual</p>
                  <p className="text-3xl font-bold text-white">${recommendations.pricing.toLocaleString()}</p>
                  <p className="text-slate-500 text-sm">USD/mes</p>
                </div>
              </div>
              <div className="flex items-center gap-4 flex-wrap">
                <div className="bg-slate-900/50 rounded-lg px-4 py-2">
                  <span className="text-slate-400 text-sm">Puntuación de Riesgo:</span>
                  <span className={`ml-2 font-bold ${
                    recommendations.score <= 4 ? 'text-green-400' :
                    recommendations.score <= 7 ? 'text-yellow-400' :
                    'text-red-400'
                  }`}>{recommendations.score}/10</span>
                </div>
                <div className="bg-slate-900/50 rounded-lg px-4 py-2">
                  <span className="text-slate-400 text-sm">v-CISO:</span>
                  <span className="ml-2 font-bold text-cyan-400">
                    {recommendations.vciso === 'standard' ? 'Estándar' : 'Lite'} (${recommendations.vcisoPricing.toLocaleString()}/mes)
                  </span>
                </div>
              </div>
            </div>

            {/* Brechas Identificadas */}
            {recommendations.gaps.length > 0 && (
              <div className="mb-6">
                <h4 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-yellow-500" />
                  Brechas Identificadas
                </h4>
                <ul className="space-y-2">
                  {recommendations.gaps.map((gap, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-slate-300">
                      <span className="text-yellow-500 mt-1">•</span>
                      {gap}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Servicios Recomendados */}
            {recommendations.services.length > 0 && (
              <div className="mb-6">
                <h4 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-cyan-500" />
                  Servicios Recomendados
                </h4>
                <div className="grid md:grid-cols-2 gap-2">
                  {recommendations.services.map((service, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-slate-900/50 rounded-lg px-4 py-2">
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                      <span className="text-slate-300 text-sm">{service}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Acciones Urgentes */}
            {recommendations.urgentActions.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6">
                <h4 className="text-lg font-semibold text-red-400 mb-3">🚨 Acciones Urgentes</h4>
                <ul className="space-y-2">
                  {recommendations.urgentActions.map((action, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-slate-300">
                      <ArrowRight className="w-4 h-4 text-red-500 mt-1 flex-shrink-0" />
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Próximos Pasos */}
            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-white mb-4">📋 Próximos Pasos</h4>
              <ol className="space-y-3 text-slate-300">
                <li className="flex items-start gap-3">
                  <span className="bg-cyan-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm flex-shrink-0">1</span>
                  Un especialista de Jeturing revisará este análisis
                </li>
                <li className="flex items-start gap-3">
                  <span className="bg-cyan-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm flex-shrink-0">2</span>
                  Te contactaremos para agendar una demo personalizada
                </li>
                <li className="flex items-start gap-3">
                  <span className="bg-cyan-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm flex-shrink-0">3</span>
                  Recibirás una propuesta formal con el SOW detallado
                </li>
              </ol>
            </div>
          </div>

          {/* Tabla de Niveles */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 mb-8">
            <h3 className="text-xl font-bold text-white mb-6">Comparativa de Niveles de Protección</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-slate-400">Nivel</th>
                    <th className="text-center py-3 px-4 text-slate-400">Precio/mes</th>
                    <th className="text-left py-3 px-4 text-slate-400">Incluye</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className={`border-b border-slate-700/50 ${recommendations.tier === 'esencial' ? 'bg-blue-500/10' : ''}`}>
                    <td className="py-4 px-4">
                      <span className="text-blue-400 font-semibold">Esencial</span>
                      {recommendations.tier === 'esencial' && <span className="ml-2 text-xs bg-blue-500 text-white px-2 py-0.5 rounded">Recomendado</span>}
                    </td>
                    <td className="py-4 px-4 text-center text-white font-semibold">$2,500</td>
                    <td className="py-4 px-4 text-slate-300 text-sm">Evaluación anual, EDR, v-CISO Lite, Backup básico</td>
                  </tr>
                  <tr className={`border-b border-slate-700/50 ${recommendations.tier === 'profesional' ? 'bg-purple-500/10' : ''}`}>
                    <td className="py-4 px-4">
                      <span className="text-purple-400 font-semibold">Profesional</span>
                      {recommendations.tier === 'profesional' && <span className="ml-2 text-xs bg-purple-500 text-white px-2 py-0.5 rounded">Recomendado</span>}
                    </td>
                    <td className="py-4 px-4 text-center text-white font-semibold">$4,500</td>
                    <td className="py-4 px-4 text-slate-300 text-sm">Todo Esencial + v-CISO Activo, Protección identidad, SEGRD™, Cloud Security</td>
                  </tr>
                  <tr className={recommendations.tier === 'critico' ? 'bg-amber-500/10' : ''}>
                    <td className="py-4 px-4">
                      <span className="text-amber-400 font-semibold">Misión Crítica</span>
                      {recommendations.tier === 'critico' && <span className="ml-2 text-xs bg-amber-500 text-white px-2 py-0.5 rounded">Recomendado</span>}
                    </td>
                    <td className="py-4 px-4 text-center text-white font-semibold">$6,500</td>
                    <td className="py-4 px-4 text-slate-300 text-sm">Todo Profesional + IA Forense, v-CISO Dedicado, SOC 24/7, BCDR garantizado</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Contacto */}
          <div className="text-center mb-8">
            <p className="text-slate-400 mb-4">¿Preguntas? Contáctanos directamente:</p>
            <div className="flex flex-wrap justify-center gap-4">
              <a
                href="mailto:sales@jeturing.com"
                className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-6 py-3 text-white hover:border-cyan-500 transition"
              >
                <Mail className="w-5 h-5 text-cyan-400" />
                sales@jeturing.com
              </a>
              <a
                href="/pricing"
                className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg px-6 py-3 text-white transition"
              >
                Ver todos los planes
                <ArrowRight className="w-5 h-5" />
              </a>
            </div>
          </div>

          <div className="text-center">
            <button
              onClick={() => window.location.href = '/'}
              className="text-slate-400 hover:text-white transition"
            >
              ← Volver al Inicio
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 pt-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">JETURING / SEGRD</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">
            🛡️ Checklist Rápido de Ciberseguridad
          </h1>
          <p className="text-slate-300 text-lg max-w-2xl mx-auto">
            Responde estas preguntas para que podamos dimensionar correctamente tu propuesta de seguridad. 
            Sin sobredimensionar ni vender de más.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-8 bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-red-200">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Sección 1: Datos básicos */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-cyan-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">1</span>
              Datos Básicos
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <input
                type="text"
                name="company_name"
                placeholder="Nombre de la empresa *"
                value={formData.company_name}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                required
              />
              <input
                type="text"
                name="contact_name"
                placeholder="Nombre del contacto"
                value={formData.contact_name}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />
              <input
                type="email"
                name="contact_email"
                placeholder="Email de contacto *"
                value={formData.contact_email}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                required
              />
              <input
                type="tel"
                name="contact_phone"
                placeholder="Teléfono de contacto"
                value={formData.contact_phone}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />
              <input
                type="text"
                name="country"
                placeholder="País de operación *"
                value={formData.country}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                required
              />
              <input
                type="text"
                name="industry"
                placeholder="Industria / Sector *"
                value={formData.industry}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                required
              />
              <input
                type="number"
                name="employees"
                placeholder="Cantidad aproximada de empleados"
                value={formData.employees}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 md:col-span-2"
              />
            </div>
          </div>

          {/* Sección 2: Tecnología e Inventario */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-cyan-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">2</span>
              Tecnología e Inventario
            </h2>
            <div className="space-y-6">
              <input
                type="number"
                name="computers"
                placeholder="¿Cuántas computadoras/laptops usan? (aprox.)"
                value={formData.computers}
                onChange={handleInputChange}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />

              <div>
                <label className="text-white font-semibold mb-3 block">¿Tienen servidores?</label>
                <div className="flex flex-wrap gap-4">
                  {['No', 'Sí, locales', 'Sí, en la nube', 'Ambos'].map(option => (
                    <label key={option} className="flex items-center gap-2 cursor-pointer bg-slate-700 rounded-lg px-4 py-2 hover:bg-slate-600 transition">
                      <input
                        type="radio"
                        name="has_servers"
                        checked={formData.has_servers === option}
                        onChange={() => handleRadioChange('has_servers', option)}
                        className="w-4 h-4 text-cyan-500"
                      />
                      <span className="text-slate-300">{option}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="text-white font-semibold mb-3 block">¿Usan Microsoft 365 (correo corporativo)?</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer bg-slate-700 rounded-lg px-4 py-2 hover:bg-slate-600 transition">
                      <input
                        type="checkbox"
                        name="uses_m365"
                        checked={formData.uses_m365}
                        onChange={handleInputChange}
                        className="w-4 h-4"
                      />
                      <span className="text-slate-300">Sí, usamos M365</span>
                    </label>
                  </div>
                  {formData.uses_m365 && (
                    <input
                      type="number"
                      name="m365_users"
                      placeholder="¿Cuántos usuarios M365?"
                      value={formData.m365_users}
                      onChange={handleInputChange}
                      className="mt-3 w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                    />
                  )}
                </div>

                <div>
                  <label className="text-white font-semibold mb-3 block">¿Tienen acceso remoto/VPN?</label>
                  <label className="flex items-center gap-2 cursor-pointer bg-slate-700 rounded-lg px-4 py-2 hover:bg-slate-600 transition">
                    <input
                      type="checkbox"
                      name="has_vpn"
                      checked={formData.has_vpn}
                      onChange={handleInputChange}
                      className="w-4 h-4"
                    />
                    <span className="text-slate-300">Sí, tenemos VPN/acceso remoto</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Sección 3: Seguridad Actual */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-cyan-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">3</span>
              Seguridad Actual
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="has_security_officer"
                  checked={formData.has_security_officer}
                  onChange={handleInputChange}
                  className="w-5 h-5 text-cyan-500"
                />
                <span className="text-slate-300">¿Tienen un responsable formal de ciberseguridad?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="security_only_it"
                  checked={formData.security_only_it}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿La seguridad está a cargo solo de IT/soporte?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="has_policies"
                  checked={formData.has_policies}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Cuentan con políticas de seguridad documentadas?</span>
              </label>
            </div>
          </div>

          {/* Sección 4: Riesgos e Incidentes */}
          <div className="bg-slate-800 border border-red-500/30 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-red-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">4</span>
              Riesgos e Incidentes
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-red-500/10 rounded-lg hover:bg-red-500/20 transition">
                <input
                  type="checkbox"
                  name="had_incidents"
                  checked={formData.had_incidents}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Han sufrido incidentes de seguridad antes?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-red-500/10 rounded-lg hover:bg-red-500/20 transition">
                <input
                  type="checkbox"
                  name="operates_24_7"
                  checked={formData.operates_24_7}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿La empresa opera fuera de horario laboral o 24/7?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-red-500/10 rounded-lg hover:bg-red-500/20 transition">
                <input
                  type="checkbox"
                  name="attack_could_stop_business"
                  checked={formData.attack_could_stop_business}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Un ataque podría detener la operación del negocio?</span>
              </label>
            </div>
          </div>

          {/* Sección 5: Cumplimiento y Presión Externa */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-cyan-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">5</span>
              Cumplimiento y Presión Externa
            </h2>
            <div className="space-y-4 mb-6">
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="clients_demand_security"
                  checked={formData.clients_demand_security}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Algún cliente, banco o proveedor les exige controles de seguridad?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="has_cyber_insurance"
                  checked={formData.has_cyber_insurance}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Tienen o planean tener seguro cibernético?</span>
              </label>
            </div>

            <label className="text-white font-semibold mb-3 block">¿Deben cumplir alguna norma o regulación?</label>
            <div className="flex flex-wrap gap-3">
              {['ISO 27001', 'PCI-DSS', 'HIPAA', 'SOC 2', 'Ley local', 'Ninguna'].map(compliance => (
                <label key={compliance} className={`flex items-center gap-2 cursor-pointer rounded-lg px-4 py-2 transition ${
                  formData.compliance_requirements.includes(compliance) 
                    ? 'bg-cyan-600 text-white' 
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}>
                  <input
                    type="checkbox"
                    checked={formData.compliance_requirements.includes(compliance)}
                    onChange={() => handleComplianceChange(compliance)}
                    className="w-4 h-4 hidden"
                  />
                  <span>{compliance}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Sección 6: Monitoreo y Respuesta */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-green-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">6</span>
              Monitoreo y Respuesta
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="has_24_7_monitoring"
                  checked={formData.has_24_7_monitoring}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Alguien monitorea la seguridad 24/7?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="has_centralized_logs"
                  checked={formData.has_centralized_logs}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Tienen logs/registros centralizados para investigar incidentes?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="can_reconstruct_incident"
                  checked={formData.can_reconstruct_incident}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">Si ocurre un incidente hoy, ¿podrían reconstruir qué pasó?</span>
              </label>
            </div>
          </div>

          {/* Sección 7: Respaldo y Continuidad */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">7</span>
              Respaldo y Continuidad
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="has_backups"
                  checked={formData.has_backups}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Realizan backups de la información?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="tested_backups"
                  checked={formData.tested_backups}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Han probado restaurar esos backups?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition">
                <input
                  type="checkbox"
                  name="knows_recovery_time"
                  checked={formData.knows_recovery_time}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Saben en cuánto tiempo deberían recuperar la operación?</span>
              </label>
            </div>
          </div>

          {/* Sección 8: Legal y Forense */}
          <div className="bg-slate-800 border border-amber-500/30 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-amber-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">8</span>
              Legal y Forense
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-amber-500/10 rounded-lg hover:bg-amber-500/20 transition">
                <input
                  type="checkbox"
                  name="needs_digital_evidence"
                  checked={formData.needs_digital_evidence}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Necesitan evidencia digital válida ante auditorías o procesos legales?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-amber-500/10 rounded-lg hover:bg-amber-500/20 transition">
                <input
                  type="checkbox"
                  name="concerned_internal_fraud"
                  checked={formData.concerned_internal_fraud}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Les preocupa el fraude interno o disputas tecnológicas?</span>
              </label>
            </div>
          </div>

          {/* Sección 9: Comentarios */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-cyan-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">9</span>
              Comentarios Adicionales
            </h2>
            <textarea
              name="comments"
              placeholder="¿Hay algo crítico que debamos saber de su operación?"
              value={formData.comments}
              onChange={handleInputChange}
              rows="4"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 resize-none"
            />
          </div>

          {/* Preview de Recomendación y Submit */}
          <div className="bg-slate-800 border border-cyan-500/30 rounded-xl p-8">
            <h3 className="text-xl font-bold text-white mb-6">📊 Vista Previa de Tu Evaluación</h3>
            
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="bg-slate-900/50 rounded-lg p-4">
                <p className="text-slate-400 text-sm mb-1">Puntuación de Riesgo</p>
                <p className={`text-4xl font-bold ${
                  calculateRiskScore() <= 4 ? 'text-green-400' :
                  calculateRiskScore() <= 7 ? 'text-yellow-400' :
                  'text-red-400'
                }`}>{calculateRiskScore()}/10</p>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4">
                <p className="text-slate-400 text-sm mb-1">Nivel Recomendado</p>
                <p className={`text-2xl font-bold ${
                  getRecommendedTier() === 'esencial' ? 'text-blue-400' :
                  getRecommendedTier() === 'profesional' ? 'text-purple-400' :
                  'text-amber-400'
                }`}>
                  {getRecommendedTier() === 'esencial' ? 'Protección Esencial' :
                   getRecommendedTier() === 'profesional' ? 'Resiliencia Profesional' :
                   'Blindaje Misión Crítica'}
                </p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 disabled:from-slate-600 disabled:to-slate-600 text-white font-bold py-4 px-6 rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/25"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Analizando...
                </>
              ) : (
                <>
                  <Mail className="w-5 h-5" />
                  Enviar y Ver Recomendaciones
                </>
              )}
            </button>

            <p className="text-slate-500 text-center text-sm mt-4">
              Se generará un análisis completo y un especialista te contactará con una propuesta personalizada.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-4 text-sm text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sendEmail}
                  onChange={() => setSendEmail(v => !v)}
                />
                Enviar por correo a ventas (sales@jeturing.com)
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={downloadPdf}
                  onChange={() => setDownloadPdf(v => !v)}
                />
                Descargar PDF con la propuesta
              </label>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="text-center mt-8 pb-8">
          <p className="text-slate-500 text-sm">
            🔐 Jeturing Inc. – Innovate. Secure. Transform.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SecurityChecklistForm;
