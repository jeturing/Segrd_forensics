/**
 * Global Admin Settings - System-wide configuration
 * Conectado al backend real con CRUD funcional
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Settings, ArrowLeft, Save, RefreshCw, Database, Server,
  Shield, Mail, CreditCard, Bell, Globe, Key, Lock, CheckCircle,
  AlertCircle, Loader2
} from 'lucide-react';
import api from '../../services/api';

export default function GlobalSettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('general');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  
  const [settings, setSettings] = useState({
    // General
    siteName: 'JETURING Forensics',
    siteUrl: 'https://forensics.jeturing.com',
    supportEmail: 'support@jeturing.com',
    
    // Registration
    allowPublicRegistration: true,
    requireEmailVerification: true,
    defaultTrialDays: 15,
    
    // Stripe
    stripeEnabled: true,
    stripeMode: 'test',
    stripePublicKey: 'pk_test_...',
    
    // Email
    smtpHost: 'smtp.sendgrid.net',
    smtpPort: 587,
    smtpUser: 'apikey',
    fromEmail: 'noreply@jeturing.com',
    
    // Security
    sessionTimeout: 3600,
    maxLoginAttempts: 5,
    lockoutDuration: 900,
    requireMFA: false,
    
    // System
    maintenanceMode: false,
    debugMode: false,
    logLevel: 'INFO'
  });

  // Cargar settings desde el backend
  useEffect(() => {
    loadSettings();
    loadSystemStatus();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/global-admin/settings');
      if (response.data?.settings) {
        setSettings(prev => ({
          ...prev,
          ...response.data.settings
        }));
      }
    } catch (err) {
      console.error('Error loading settings:', err);
      setError('Error al cargar configuración. Usando valores por defecto.');
    } finally {
      setLoading(false);
    }
  };

  const loadSystemStatus = async () => {
    try {
      const response = await api.get('/api/global-admin/stats');
      setSystemStatus(response.data);
    } catch (err) {
      console.error('Error loading system status:', err);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Globe },
    { id: 'registration', label: 'Registro', icon: Shield },
    { id: 'billing', label: 'Billing/Stripe', icon: CreditCard },
    { id: 'email', label: 'Email', icon: Mail },
    { id: 'security', label: 'Seguridad', icon: Lock },
    { id: 'system', label: 'Sistema', icon: Server }
  ];

  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setSuccess(null); // Clear success message on change
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await api.put('/api/global-admin/settings/bulk', settings);
      if (response.data?.success) {
        setSuccess(`${response.data.updated_count || 'Todas las'} configuraciones guardadas exitosamente`);
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setError(error.response?.data?.detail || 'Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };

  const InputField = ({ label, name, type = 'text', value, onChange, placeholder, help }) => (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-300 mb-2">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(name, type === 'number' ? parseInt(e.target.value) || 0 : e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none"
      />
      {help && <p className="text-xs text-gray-500 mt-1">{help}</p>}
    </div>
  );

  const ToggleField = ({ label, name, value, onChange, help }) => (
    <div className="flex items-center justify-between py-3">
      <div>
        <p className="text-sm font-medium text-gray-300">{label}</p>
        {help && <p className="text-xs text-gray-500">{help}</p>}
      </div>
      <button
        onClick={() => onChange(name, !value)}
        className={`relative w-12 h-6 rounded-full transition-colors ${value ? 'bg-blue-600' : 'bg-gray-600'}`}
      >
        <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${value ? 'left-7' : 'left-1'}`} />
      </button>
    </div>
  );

  const SelectField = ({ label, name, value, options, onChange, help }) => (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-300 mb-2">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {help && <p className="text-xs text-gray-500 mt-1">{help}</p>}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Cargando configuración...</p>
        </div>
      </div>
    );
  }

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
              <Settings className="w-7 h-7 text-orange-400" />
              Configuración del Sistema
            </h1>
            <p className="text-gray-400 text-sm">Ajustes globales de la plataforma</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={loadSettings}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Recargar
          </button>
          <button 
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Guardar Cambios
          </button>
        </div>
      </div>

      {/* Mensajes de estado */}
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">×</button>
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-4 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-green-400">{success}</p>
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-400 hover:text-green-300">×</button>
        </div>
      )}

      <div className="flex gap-6">
        {/* Sidebar Tabs */}
        <div className="w-64 bg-gray-800 rounded-xl p-4 border border-gray-700 h-fit">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                activeTab === tab.id 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 bg-gray-800 rounded-xl p-6 border border-gray-700">
          {activeTab === 'general' && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Configuración General</h2>
              <InputField 
                label="Nombre del Sitio" 
                name="siteName" 
                value={settings.siteName} 
                onChange={handleChange}
              />
              <InputField 
                label="URL del Sitio" 
                name="siteUrl" 
                value={settings.siteUrl} 
                onChange={handleChange}
              />
              <InputField 
                label="Email de Soporte" 
                name="supportEmail" 
                type="email"
                value={settings.supportEmail} 
                onChange={handleChange}
              />
            </div>
          )}

          {activeTab === 'registration' && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Configuración de Registro</h2>
              <div className="space-y-4 mb-6">
                <ToggleField 
                  label="Permitir Registro Público" 
                  name="allowPublicRegistration" 
                  value={settings.allowPublicRegistration} 
                  onChange={handleChange}
                  help="Permite que nuevos usuarios se registren sin invitación"
                />
                <ToggleField 
                  label="Requerir Verificación de Email" 
                  name="requireEmailVerification" 
                  value={settings.requireEmailVerification} 
                  onChange={handleChange}
                  help="Los usuarios deben verificar su email antes de acceder"
                />
              </div>
              <InputField 
                label="Días de Trial Gratuito" 
                name="defaultTrialDays" 
                type="number"
                value={settings.defaultTrialDays} 
                onChange={handleChange}
                help="Número de días del período de prueba gratuito"
              />
            </div>
          )}

          {activeTab === 'billing' && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Configuración de Stripe</h2>
              <ToggleField 
                label="Habilitar Stripe" 
                name="stripeEnabled" 
                value={settings.stripeEnabled} 
                onChange={handleChange}
              />
              <SelectField 
                label="Modo de Stripe" 
                name="stripeMode"
                value={settings.stripeMode}
                options={[
                  { value: 'test', label: 'Test (Sandbox)' },
                  { value: 'live', label: 'Live (Producción)' }
                ]}
                onChange={handleChange}
                help="Usa Test para pruebas, Live para pagos reales"
              />
              <InputField 
                label="Stripe Public Key" 
                name="stripePublicKey" 
                value={settings.stripePublicKey} 
                onChange={handleChange}
                help="Clave pública de Stripe (pk_test_... o pk_live_...)"
              />
              <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <p className="text-yellow-400 text-sm">
                  ⚠️ La Secret Key se configura en las variables de entorno del servidor (STRIPE_SECRET_KEY)
                </p>
              </div>
            </div>
          )}

          {activeTab === 'email' && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Configuración de Email</h2>
              <InputField 
                label="SMTP Host" 
                name="smtpHost" 
                value={settings.smtpHost} 
                onChange={handleChange}
              />
              <InputField 
                label="SMTP Port" 
                name="smtpPort" 
                type="number"
                value={settings.smtpPort} 
                onChange={handleChange}
              />
              <InputField 
                label="SMTP Usuario" 
                name="smtpUser" 
                value={settings.smtpUser} 
                onChange={handleChange}
              />
              <InputField 
                label="Email de Origen" 
                name="fromEmail" 
                type="email"
                value={settings.fromEmail} 
                onChange={handleChange}
              />
            </div>
          )}

          {activeTab === 'security' && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Configuración de Seguridad</h2>
              <InputField 
                label="Timeout de Sesión (segundos)" 
                name="sessionTimeout" 
                type="number"
                value={settings.sessionTimeout} 
                onChange={handleChange}
                help="Tiempo de inactividad antes de cerrar sesión"
              />
              <InputField 
                label="Máximo Intentos de Login" 
                name="maxLoginAttempts" 
                type="number"
                value={settings.maxLoginAttempts} 
                onChange={handleChange}
              />
              <InputField 
                label="Duración del Bloqueo (segundos)" 
                name="lockoutDuration" 
                type="number"
                value={settings.lockoutDuration} 
                onChange={handleChange}
              />
              <ToggleField 
                label="Requerir MFA" 
                name="requireMFA" 
                value={settings.requireMFA} 
                onChange={handleChange}
                help="Forzar autenticación de dos factores para todos los usuarios"
              />
            </div>
          )}

          {activeTab === 'system' && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">Configuración del Sistema</h2>
              <ToggleField 
                label="Modo Mantenimiento" 
                name="maintenanceMode" 
                value={settings.maintenanceMode} 
                onChange={handleChange}
                help="Bloquea el acceso a usuarios no admin"
              />
              <ToggleField 
                label="Modo Debug" 
                name="debugMode" 
                value={settings.debugMode} 
                onChange={handleChange}
                help="Muestra información detallada de errores"
              />
              <SelectField 
                label="Nivel de Log" 
                name="logLevel"
                value={settings.logLevel}
                options={[
                  { value: 'DEBUG', label: 'DEBUG' },
                  { value: 'INFO', label: 'INFO' },
                  { value: 'WARNING', label: 'WARNING' },
                  { value: 'ERROR', label: 'ERROR' }
                ]}
                onChange={handleChange}
              />
              
              <div className="mt-6 p-4 bg-gray-700/50 rounded-lg">
                <h3 className="text-lg font-medium text-white mb-4">Estado del Sistema</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Base de Datos:</span>
                    <span className="text-green-400 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" />Conectada
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Tenants Activos:</span>
                    <span className="text-white">
                      {systemStatus?.active_tenants || 0} / {systemStatus?.total_tenants || 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Usuarios Totales:</span>
                    <span className="text-white">{systemStatus?.total_users || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Casos Totales:</span>
                    <span className="text-white">{systemStatus?.total_cases || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Análisis Totales:</span>
                    <span className="text-white">{systemStatus?.total_analyses || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Stripe:</span>
                    <span className={settings.stripeMode === 'live' ? 'text-green-400' : 'text-yellow-400'}>
                      {settings.stripeMode === 'live' ? 'Live Mode' : 'Test Mode'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Versión:</span>
                    <span className="text-white">v4.6.0</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
