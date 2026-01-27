/**
 * Security Checklist Form - Dimensionamiento de Servicios
 * Formulario interactivo para recopilar requisitos y generar informe
 */

import React, { useState } from 'react';
import axios from 'axios';
import { AlertCircle, CheckCircle2, Loader } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '/api';

const SecurityChecklistForm = () => {
  const [formData, setFormData] = useState({
    // Sección 1: Datos básicos
    company_name: '',
    country: '',
    industry: '',
    employees: '',

    // Sección 2: Tecnología
    computers: '',
    has_servers: '',
    uses_m365: '',
    m365_users: '',
    has_vpn: '',

    // Sección 3: Seguridad actual
    has_security_officer: false,
    security_only_it: false,
    has_policies: false,

    // Sección 4: Riesgos
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
    recovery_time_target: '',

    // Sección 8: Legal
    needs_digital_evidence: false,
    concerned_internal_fraud: false,

    // Sección 9: Comentarios
    comments: ''
  });

  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
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

  const calculateRiskScore = () => {
    let score = 0;
    const weights = {
      had_incidents: 2,
      operates_24_7: 1,
      attack_could_stop_business: 2,
      clients_demand_security: 1,
      has_cyber_insurance: 0,
      needs_digital_evidence: 1,
      concerned_internal_fraud: 1,
      has_24_7_monitoring: -1,
      has_centralized_logs: -1,
      has_backups: -1,
      tested_backups: -1,
      can_reconstruct_incident: -1
    };

    Object.keys(weights).forEach(key => {
      if (formData[key] === true) {
        score += weights[key];
      }
    });

    return Math.max(1, Math.min(10, score));
  };

  const recommendedTier = () => {
    const score = calculateRiskScore();
    if (score <= 3) return 'Esencial';
    if (score <= 6) return 'Profesional';
    return 'Misión Crítica';
  };

  const validateForm = () => {
    if (!formData.company_name.trim()) return 'Nombre de empresa es requerido';
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

    try {
      const payload = {
        ...formData,
        recommended_tier: recommendedTier(),
        risk_score: calculateRiskScore(),
        submitted_at: new Date().toISOString()
      };

      const response = await axios.post(`${API_BASE_URL}/security-checklist/submit`, payload);

      if (response.data.success) {
        setSubmitted(true);
        setTimeout(() => {
          window.scrollTo(0, 0);
        }, 300);
      } else {
        setError('Error al enviar formulario. Por favor intenta nuevamente.');
      }
    } catch (err) {
      console.error('Error submitting form:', err);
      setError(err.response?.data?.detail || 'Error al enviar formulario. Contacta a sales@jeturing.com');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
        <div className="max-w-2xl mx-auto pt-20">
          <div className="bg-slate-800 border border-green-500/30 rounded-xl p-8 text-center">
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-white mb-4">¡Formulario Enviado!</h2>
            <p className="text-slate-300 text-lg mb-6">
              Gracias por completar el checklist de ciberseguridad.
            </p>
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 mb-6 text-left">
              <h3 className="text-xl font-semibold text-blue-400 mb-4">Recomendación para tu empresa:</h3>
              <p className="text-slate-300 mb-2">
                <span className="font-semibold">Nivel Recomendado:</span> <span className="text-blue-300">{recommendedTier()}</span>
              </p>
              <p className="text-slate-300">
                <span className="font-semibold">Puntuación de Riesgo:</span> <span className="text-yellow-300">{calculateRiskScore()}/10</span>
              </p>
            </div>
            <p className="text-slate-400 mb-6">
              Un especialista de Jeturing se pondrá en contacto contigo en breve en los datos proporcionados.
            </p>
            <button
              onClick={() => window.location.href = '/'}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg transition"
            >
              Volver al Inicio
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
          <h1 className="text-4xl font-bold text-white mb-4">
            🛡️ Checklist de Ciberseguridad
          </h1>
          <p className="text-slate-300 text-lg">
            Ayúdanos a dimensionar correctamente tu propuesta de seguridad
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
              <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">1</span>
              Datos básicos
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <input
                type="text"
                name="company_name"
                placeholder="Nombre de la empresa"
                value={formData.company_name}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                required
              />
              <input
                type="text"
                name="country"
                placeholder="País de operación"
                value={formData.country}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                required
              />
              <input
                type="text"
                name="industry"
                placeholder="Industria / Sector"
                value={formData.industry}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                required
              />
              <input
                type="number"
                name="employees"
                placeholder="Cantidad aproximada de empleados"
                value={formData.employees}
                onChange={handleInputChange}
                className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Sección 2: Tecnología */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">2</span>
              Tecnología e Inventario
            </h2>
            <div className="space-y-6">
              <input
                type="number"
                name="computers"
                placeholder="¿Cuántas computadoras/laptops? (aprox.)"
                value={formData.computers}
                onChange={handleInputChange}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />

              <div>
                <label className="text-white font-semibold mb-3 block">¿Tienen servidores?</label>
                <div className="flex gap-4">
                  {['No', 'Sí, locales', 'Sí, en la nube'].map(option => (
                    <label key={option} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="has_servers"
                        value={option}
                        checked={formData.has_servers === option}
                        onChange={handleInputChange}
                        className="w-4 h-4"
                      />
                      <span className="text-slate-300">{option}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-white font-semibold mb-3 block">¿Usan Microsoft 365?</label>
                <div className="flex gap-4">
                  {['Sí', 'No'].map(option => (
                    <label key={option} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="uses_m365"
                        value={option}
                        checked={formData.uses_m365 === option}
                        onChange={handleInputChange}
                        className="w-4 h-4"
                      />
                      <span className="text-slate-300">{option}</span>
                    </label>
                  ))}
                </div>
              </div>

              {formData.uses_m365 === 'Sí' && (
                <input
                  type="number"
                  name="m365_users"
                  placeholder="¿Cuántos usuarios de M365?"
                  value={formData.m365_users}
                  onChange={handleInputChange}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                />
              )}

              <div>
                <label className="text-white font-semibold mb-3 block">¿Tienen acceso remoto/VPN?</label>
                <div className="flex gap-4">
                  {['Sí', 'No'].map(option => (
                    <label key={option} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="has_vpn"
                        value={option}
                        checked={formData.has_vpn === option}
                        onChange={handleInputChange}
                        className="w-4 h-4"
                      />
                      <span className="text-slate-300">{option}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Sección 3: Seguridad actual */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">3</span>
              Seguridad Actual
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="has_security_officer"
                  checked={formData.has_security_officer}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Tienen responsable formal de ciberseguridad?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="security_only_it"
                  checked={formData.security_only_it}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Seguridad a cargo solo de IT/soporte?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
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
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-red-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">4</span>
              Riesgos e Incidentes
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="had_incidents"
                  checked={formData.had_incidents}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Han sufrido incidentes de seguridad antes?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="operates_24_7"
                  checked={formData.operates_24_7}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Operan fuera de horario o 24/7?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="attack_could_stop_business"
                  checked={formData.attack_could_stop_business}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Un ataque podría detener la operación?</span>
              </label>
            </div>
          </div>

          {/* Sección 5: Cumplimiento */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">5</span>
              Cumplimiento y Presión Externa
            </h2>
            <div className="space-y-4 mb-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="clients_demand_security"
                  checked={formData.clients_demand_security}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Clientes/bancos exigen controles de seguridad?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
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

            <label className="text-white font-semibold mb-3 block">¿Deben cumplir alguna norma?</label>
            <div className="flex flex-wrap gap-4">
              {['ISO 27001', 'PCI', 'Ley local', 'Ninguna'].map(compliance => (
                <label key={compliance} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.compliance_requirements.includes(compliance)}
                    onChange={() => handleComplianceChange(compliance)}
                    className="w-4 h-4"
                  />
                  <span className="text-slate-300">{compliance}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Sección 6: Monitoreo */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-green-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">6</span>
              Monitoreo y Respuesta
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="has_24_7_monitoring"
                  checked={formData.has_24_7_monitoring}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Alguien monitorea la seguridad 24/7?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="has_centralized_logs"
                  checked={formData.has_centralized_logs}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Tienen logs centralizados para investigar incidentes?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="can_reconstruct_incident"
                  checked={formData.can_reconstruct_incident}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Podrían reconstruir qué pasó en un incidente?</span>
              </label>
            </div>
          </div>

          {/* Sección 7: Respaldo */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">7</span>
              Respaldo y Continuidad
            </h2>
            <div className="space-y-4 mb-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="has_backups"
                  checked={formData.has_backups}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Realizan backups de la información?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="tested_backups"
                  checked={formData.tested_backups}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Han probado restaurar esos backups?</span>
              </label>
            </div>

            <input
              type="text"
              name="recovery_time_target"
              placeholder="¿En cuánto tiempo deberían recuperarse? (ej: 4 horas)"
              value={formData.recovery_time_target}
              onChange={handleInputChange}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Sección 8: Legal y Forense */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-yellow-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">8</span>
              Legal y Forense
            </h2>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="needs_digital_evidence"
                  checked={formData.needs_digital_evidence}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Necesitan evidencia digital válida para auditorías?</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="concerned_internal_fraud"
                  checked={formData.concerned_internal_fraud}
                  onChange={handleInputChange}
                  className="w-5 h-5"
                />
                <span className="text-slate-300">¿Preocupación por fraude interno o disputas?</span>
              </label>
            </div>
          </div>

          {/* Sección 9: Comentarios */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">9</span>
              Comentarios Adicionales
            </h2>
            <textarea
              name="comments"
              placeholder="¿Hay algo crítico que debamos saber de tu operación?"
              value={formData.comments}
              onChange={handleInputChange}
              rows="5"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Resumen y Submit */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
            <div className="grid grid-cols-2 gap-6 mb-8">
              <div>
                <p className="text-slate-400 mb-2">Puntuación de Riesgo</p>
                <p className="text-3xl font-bold text-yellow-400">{calculateRiskScore()}/10</p>
              </div>
              <div>
                <p className="text-slate-400 mb-2">Nivel Recomendado</p>
                <p className="text-3xl font-bold text-blue-400">{recommendedTier()}</p>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-bold py-4 px-6 rounded-lg transition flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Enviando...
                </>
              ) : (
                '📧 Enviar Formulario a sales@jeturing.com'
              )}
            </button>

            <p className="text-slate-400 text-center text-sm mt-4">
              Se generará un informe detallado y será enviado a nuestro equipo de ventas.
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SecurityChecklistForm;
