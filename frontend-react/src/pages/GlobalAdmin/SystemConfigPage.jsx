/**
 * System Configuration Page v4.7
 * =============================
 * Panel de administración para configuración dinámica desde BD.
 * Carga categorías y settings dinámicamente desde /api/admin/settings/
 * 
 * Características:
 * - Tabs dinámicos por categoría (llm, email, database, security, storage)
 * - Soporte para editar valores con tipos (string, int, bool, json)
 * - Gestión de modelos LLM
 * - Encriptación automática de secrets (no se muestran valores reales)
 * - Prioridad: BD > ENV > defaults
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Settings, ArrowLeft, Save, RefreshCw, Database, Server, Bot,
  Shield, Mail, HardDrive, Key, Lock, CheckCircle, Eye, EyeOff,
  AlertCircle, Loader2, Plus, Trash2, Edit2, X, Cpu, Cloud
} from 'lucide-react';
import api from '../../services/api';

// Iconos por categoría
const CATEGORY_ICONS = {
  llm: Bot,
  email: Mail,
  database: Database,
  security: Shield,
  storage: HardDrive,
  general: Settings,
  system: Server
};

// Labels amigables por categoría
const CATEGORY_LABELS = {
  llm: 'LLM / IA',
  email: 'Email (SMTP)',
  database: 'Base de Datos',
  security: 'Seguridad',
  storage: 'Almacenamiento',
  general: 'General',
  system: 'Sistema'
};

export default function SystemConfigPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('llm');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Datos dinámicos
  const [categories, setCategories] = useState([]);
  const [settings, setSettings] = useState({});
  const [modifiedSettings, setModifiedSettings] = useState({});
  const [llmModels, setLlmModels] = useState([]);
  const [showSecrets, setShowSecrets] = useState({});
  
  // Modal para editar/agregar modelo LLM
  const [modelModal, setModelModal] = useState({ open: false, model: null });

  // Cargar datos iniciales
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        loadCategories(),
        loadLlmModels()
      ]);
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Error al cargar configuración');
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await api.get('/api/admin/settings/categories');
      if (response.data?.categories) {
        setCategories(response.data.categories);
        
        // Cargar settings de cada categoría
        const allSettings = {};
        for (const cat of response.data.categories) {
          const catResponse = await api.get(`/api/admin/settings/?category=${cat.category}`);
          if (catResponse.data?.settings) {
            allSettings[cat.category] = catResponse.data.settings;
          }
        }
        setSettings(allSettings);
      }
    } catch (err) {
      console.error('Error loading categories:', err);
      throw err;
    }
  };

  const loadLlmModels = async () => {
    try {
      const response = await api.get('/api/admin/settings/llm/models');
      if (response.data?.models) {
        setLlmModels(response.data.models);
      }
    } catch (err) {
      console.error('Error loading LLM models:', err);
    }
  };

  const handleSettingChange = (category, key, value) => {
    setModifiedSettings(prev => ({
      ...prev,
      [`${category}.${key}`]: { category, key, value }
    }));
    setSuccess(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    
    try {
      const updates = Object.values(modifiedSettings).map(s => ({
        key: s.key,
        value: String(s.value)
      }));
      
      if (updates.length === 0) {
        setSuccess('No hay cambios pendientes');
        setSaving(false);
        return;
      }
      
      const response = await api.put('/api/admin/settings/bulk', { settings: updates });
      
      if (response.data?.success) {
        setSuccess(`${response.data.updated} configuraciones guardadas`);
        setModifiedSettings({});
        await loadCategories(); // Recargar
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      setError(err.response?.data?.detail || 'Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };

  const toggleSecret = (key) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const getCurrentValue = (category, setting) => {
    const modKey = `${category}.${setting.key}`;
    if (modifiedSettings[modKey]) {
      return modifiedSettings[modKey].value;
    }
    return setting.value || '';
  };

  // ========== LLM Model Management ==========
  const handleModelToggle = async (modelId, isActive) => {
    try {
      await api.put(`/api/admin/settings/llm/models/${modelId}`, { is_active: !isActive });
      await loadLlmModels();
      setSuccess(`Modelo ${isActive ? 'desactivado' : 'activado'}`);
    } catch (err) {
      setError('Error al actualizar modelo');
    }
  };

  const handleSetDefaultModel = async (modelId) => {
    try {
      await api.post(`/api/admin/settings/llm/models/${modelId}/set-default`);
      await loadLlmModels();
      setSuccess('Modelo por defecto actualizado');
    } catch (err) {
      setError('Error al establecer modelo por defecto');
    }
  };

  const handleDeleteModel = async (modelId) => {
    if (!confirm('¿Eliminar este modelo?')) return;
    try {
      await api.delete(`/api/admin/settings/llm/models/${modelId}`);
      await loadLlmModels();
      setSuccess('Modelo eliminado');
    } catch (err) {
      setError('Error al eliminar modelo');
    }
  };

  const handleSaveModel = async (modelData) => {
    try {
      if (modelData.id) {
        await api.put(`/api/admin/settings/llm/models/${modelData.id}`, modelData);
      } else {
        await api.post('/api/admin/settings/llm/models', modelData);
      }
      await loadLlmModels();
      setModelModal({ open: false, model: null });
      setSuccess(modelData.id ? 'Modelo actualizado' : 'Modelo creado');
    } catch (err) {
      setError('Error al guardar modelo');
    }
  };

  // ========== Render Helpers ==========
  const renderSettingField = (category, setting) => {
    const value = getCurrentValue(category, setting);
    const isModified = !!modifiedSettings[`${category}.${setting.key}`];
    
    // Para secrets
    if (setting.is_secret) {
      return (
        <div key={setting.key} className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {setting.display_name}
            <span className="ml-2 text-xs text-yellow-500">🔒 Secreto</span>
            {isModified && <span className="ml-2 text-xs text-blue-400">● Modificado</span>}
          </label>
          <div className="relative">
            <input
              type={showSecrets[setting.key] ? 'text' : 'password'}
              value={value}
              onChange={(e) => handleSettingChange(category, setting.key, e.target.value)}
              placeholder={setting.display_value || '••••••••'}
              className="w-full px-4 py-2 pr-10 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => toggleSecret(setting.key)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
            >
              {showSecrets[setting.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {setting.description && <p className="text-xs text-gray-500 mt-1">{setting.description}</p>}
        </div>
      );
    }
    
    // Para booleanos
    if (setting.value_type === 'boolean') {
      const boolValue = value === 'true' || value === true;
      return (
        <div key={setting.key} className="flex items-center justify-between py-3">
          <div>
            <p className="text-sm font-medium text-gray-300">
              {setting.display_name}
              {isModified && <span className="ml-2 text-xs text-blue-400">● Modificado</span>}
            </p>
            {setting.description && <p className="text-xs text-gray-500">{setting.description}</p>}
          </div>
          <button
            onClick={() => handleSettingChange(category, setting.key, !boolValue)}
            className={`relative w-12 h-6 rounded-full transition-colors ${boolValue ? 'bg-blue-600' : 'bg-gray-600'}`}
          >
            <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${boolValue ? 'left-7' : 'left-1'}`} />
          </button>
        </div>
      );
    }
    
    // Para números
    if (setting.value_type === 'integer') {
      return (
        <div key={setting.key} className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {setting.display_name}
            {isModified && <span className="ml-2 text-xs text-blue-400">● Modificado</span>}
          </label>
          <input
            type="number"
            value={value}
            onChange={(e) => handleSettingChange(category, setting.key, parseInt(e.target.value) || 0)}
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          />
          {setting.description && <p className="text-xs text-gray-500 mt-1">{setting.description}</p>}
        </div>
      );
    }
    
    // Default: string
    return (
      <div key={setting.key} className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {setting.display_name}
          {isModified && <span className="ml-2 text-xs text-blue-400">● Modificado</span>}
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => handleSettingChange(category, setting.key, e.target.value)}
          className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
        />
        {setting.description && <p className="text-xs text-gray-500 mt-1">{setting.description}</p>}
      </div>
    );
  };

  const renderLlmModelsTab = () => (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-white">Modelos LLM Configurados</h2>
        <button
          onClick={() => setModelModal({ open: true, model: null })}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" /> Agregar Modelo
        </button>
      </div>
      
      <div className="space-y-4">
        {llmModels.map(model => (
          <div 
            key={model.id} 
            className={`p-4 rounded-lg border ${
              model.is_default 
                ? 'bg-blue-900/30 border-blue-500/50' 
                : model.is_active 
                  ? 'bg-gray-700/50 border-gray-600' 
                  : 'bg-gray-800/30 border-gray-700 opacity-60'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  model.provider === 'ollama' ? 'bg-purple-500/20' :
                  model.provider === 'lmstudio' ? 'bg-blue-500/20' :
                  model.provider === 'openai' ? 'bg-green-500/20' : 'bg-gray-500/20'
                }`}>
                  {model.provider === 'ollama' ? <Cpu className="w-5 h-5 text-purple-400" /> :
                   model.provider === 'openai' ? <Cloud className="w-5 h-5 text-green-400" /> :
                   <Bot className="w-5 h-5 text-blue-400" />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{model.display_name}</span>
                    {model.is_default && (
                      <span className="text-xs bg-blue-600 px-2 py-0.5 rounded">Por Defecto</span>
                    )}
                    {!model.is_active && (
                      <span className="text-xs bg-gray-600 px-2 py-0.5 rounded">Inactivo</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400">
                    {model.provider} • {model.model_name}
                  </p>
                  {model.description && (
                    <p className="text-xs text-gray-500 mt-1">{model.description}</p>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {!model.is_default && model.is_active && (
                  <button
                    onClick={() => handleSetDefaultModel(model.id)}
                    className="px-3 py-1 text-sm bg-blue-600/20 text-blue-400 hover:bg-blue-600/40 rounded transition-colors"
                  >
                    Usar por Defecto
                  </button>
                )}
                <button
                  onClick={() => handleModelToggle(model.id, model.is_active)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    model.is_active 
                      ? 'bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/40'
                      : 'bg-green-600/20 text-green-400 hover:bg-green-600/40'
                  }`}
                >
                  {model.is_active ? 'Desactivar' : 'Activar'}
                </button>
                <button
                  onClick={() => setModelModal({ open: true, model })}
                  className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                {!model.is_default && (
                  <button
                    onClick={() => handleDeleteModel(model.id)}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-600/20 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {llmModels.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No hay modelos LLM configurados
          </div>
        )}
      </div>
      
      {/* Settings de LLM */}
      {settings.llm && settings.llm.length > 0 && (
        <div className="mt-8 pt-6 border-t border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Configuración LLM General</h3>
          {settings.llm.map(s => renderSettingField('llm', s))}
        </div>
      )}
    </div>
  );

  // ========== Modal Component ==========
  const LlmModelModal = () => {
    const [formData, setFormData] = useState(
      modelModal.model || {
        model_name: '',
        display_name: '',
        provider: 'ollama',
        base_url: 'http://ollama:11434',
        api_key: '',
        description: '',
        is_active: true,
        is_default: false
      }
    );
    
    if (!modelModal.open) return null;
    
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg border border-gray-700">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold text-white">
              {modelModal.model ? 'Editar Modelo' : 'Agregar Modelo LLM'}
            </h3>
            <button
              onClick={() => setModelModal({ open: false, model: null })}
              className="text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-300 mb-1">Proveedor</label>
              <select
                value={formData.provider}
                onChange={(e) => setFormData(prev => ({ ...prev, provider: e.target.value }))}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              >
                <option value="ollama">Ollama (Local)</option>
                <option value="lmstudio">LM Studio</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm text-gray-300 mb-1">Nombre del Modelo</label>
              <input
                type="text"
                value={formData.model_name}
                onChange={(e) => setFormData(prev => ({ ...prev, model_name: e.target.value }))}
                placeholder="llama3.2:3b, gpt-4, etc."
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              />
            </div>
            
            <div>
              <label className="block text-sm text-gray-300 mb-1">Nombre para Mostrar</label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
                placeholder="Llama 3.2 3B"
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              />
            </div>
            
            <div>
              <label className="block text-sm text-gray-300 mb-1">Base URL</label>
              <input
                type="text"
                value={formData.base_url}
                onChange={(e) => setFormData(prev => ({ ...prev, base_url: e.target.value }))}
                placeholder="http://ollama:11434"
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              />
            </div>
            
            {(formData.provider === 'openai' || formData.provider === 'anthropic') && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">API Key</label>
                <input
                  type="password"
                  value={formData.api_key || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                  placeholder="sk-..."
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm text-gray-300 mb-1">Descripción</label>
              <textarea
                value={formData.description || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Descripción opcional..."
                rows={2}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white resize-none"
              />
            </div>
          </div>
          
          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={() => setModelModal({ open: false, model: null })}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
            >
              Cancelar
            </button>
            <button
              onClick={() => handleSaveModel(formData)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              {modelModal.model ? 'Guardar Cambios' : 'Crear Modelo'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ========== Main Render ==========
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Cargando configuración del sistema...</p>
        </div>
      </div>
    );
  }

  const hasChanges = Object.keys(modifiedSettings).length > 0;

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <LlmModelModal />
      
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
            <p className="text-gray-400 text-sm">
              Ajustes almacenados en base de datos • Prioridad: BD {`>`} ENV {`>`} defaults
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={loadAllData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Recargar
          </button>
          <button 
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={`flex items-center gap-2 px-4 py-2 text-white rounded-lg transition-colors ${
              hasChanges 
                ? 'bg-blue-600 hover:bg-blue-700' 
                : 'bg-gray-600 cursor-not-allowed'
            }`}
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Guardar Cambios
            {hasChanges && <span className="ml-1 text-xs bg-blue-500 px-1.5 rounded">{Object.keys(modifiedSettings).length}</span>}
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
        {/* Sidebar Tabs - Dinámico */}
        <div className="w-64 bg-gray-800 rounded-xl p-4 border border-gray-700 h-fit">
          {/* Tab especial para LLM Models */}
          <button
            onClick={() => setActiveTab('llm-models')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
              activeTab === 'llm-models'
                ? 'bg-purple-600 text-white' 
                : 'text-gray-400 hover:bg-gray-700 hover:text-white'
            }`}
          >
            <Bot className="w-5 h-5" />
            LLM Models
            <span className="ml-auto text-xs bg-gray-600 px-1.5 rounded">{llmModels.length}</span>
          </button>
          
          <div className="border-t border-gray-700 my-3" />
          
          {/* Tabs dinámicos por categoría */}
          {categories.map((cat) => {
            const Icon = CATEGORY_ICONS[cat.category] || Settings;
            return (
              <button
                key={cat.category}
                onClick={() => setActiveTab(cat.category)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                  activeTab === cat.category
                    ? 'bg-blue-600 text-white' 
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <Icon className="w-5 h-5" />
                {CATEGORY_LABELS[cat.category] || cat.category}
                <span className="ml-auto text-xs bg-gray-600 px-1.5 rounded">{cat.count}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 bg-gray-800 rounded-xl p-6 border border-gray-700">
          {activeTab === 'llm-models' ? (
            renderLlmModelsTab()
          ) : (
            <div>
              <h2 className="text-xl font-semibold text-white mb-6">
                {CATEGORY_LABELS[activeTab] || activeTab}
              </h2>
              
              {settings[activeTab] && settings[activeTab].length > 0 ? (
                settings[activeTab].map(s => renderSettingField(activeTab, s))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No hay configuraciones en esta categoría
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
