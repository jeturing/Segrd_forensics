/**
 * SEGRD Security - API Configuration Panel
 * Panel de configuración de APIs en Mantenimiento
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  KeyIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  EyeIcon,
  EyeSlashIcon,
  CloudArrowUpIcon,
  CloudArrowDownIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ShieldCheckIcon,
  GlobeAltIcon,
  ServerStackIcon,
  FingerPrintIcon,
  BugAntIcon,
  BellIcon,
  CubeIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  ClipboardDocumentIcon,
  TrashIcon,
  PlusIcon,
  LinkIcon
} from '@heroicons/react/24/outline';
import api, { API_BASE_URL } from '../../services/api';

// Iconos por categoría
const categoryIcons = {
  threat_intel: ShieldCheckIcon,
  network: GlobeAltIcon,
  identity: FingerPrintIcon,
  malware: BugAntIcon,
  credentials: KeyIcon,
  cloud: ServerStackIcon,
  notification: BellIcon,
  integration: CubeIcon,
  general: Cog6ToothIcon
};

// Colores por categoría
const categoryColors = {
  threat_intel: 'violet',
  network: 'blue',
  identity: 'indigo',
  malware: 'red',
  credentials: 'amber',
  cloud: 'cyan',
  notification: 'green',
  integration: 'purple',
  general: 'gray'
};

const ConfigurationPanel = () => {
  const [configurations, setConfigurations] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState({});
  const [validating, setValidating] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showSecrets, setShowSecrets] = useState({});
  const [editValues, setEditValues] = useState({});
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Cargar configuraciones
  const loadConfigurations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Primero inicializar si es necesario
      await api.post('/api/configuration/initialize');

      // Cargar configuraciones
      const [configRes, summaryRes] = await Promise.all([
        api.get('/api/configuration/'),
        api.get('/api/configuration/summary')
      ]);

      if (configRes.data) {
        setConfigurations(configRes.data.configurations || []);
        
        // Inicializar valores de edición
        const values = {};
        configRes.data.configurations?.forEach(c => {
          values[c.key] = c.has_value ? '' : '';
        });
        setEditValues(values);
      }

      if (summaryRes.data) {
        setSummary(summaryRes.data);
      }

    } catch (err) {
      console.error('Error loading configurations:', err);
      setError('Error cargando configuraciones');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigurations();
  }, [loadConfigurations]);

  // Guardar configuración
  const saveConfiguration = async (key, value) => {
    if (!value?.trim()) return;

    try {
      setSaving(prev => ({ ...prev, [key]: true }));
      setError(null);

      const response = await api.put(`/api/configuration/${key}`, { value: value.trim() });

      if (response.data) {
        setSuccess(`Configuración ${key} guardada`);
        await loadConfigurations();
        setEditValues(prev => ({ ...prev, [key]: '' }));
        setTimeout(() => setSuccess(null), 3000);
      }

    } catch (err) {
      setError(`Error guardando ${key}: ${err.message}`);
    } finally {
      setSaving(prev => ({ ...prev, [key]: false }));
    }
  };

  // Validar configuración
  const validateConfiguration = async (key) => {
    try {
      setValidating(prev => ({ ...prev, [key]: true }));
      setError(null);

      const response = await api.post(`/api/configuration/${key}/validate`);

      const data = response.data;

      if (data.valid) {
        setSuccess(`${key}: ${data.message}`);
      } else {
        setError(`${key}: ${data.message}`);
      }

      await loadConfigurations();
      setTimeout(() => { setSuccess(null); setError(null); }, 5000);

    } catch (err) {
      setError(`Error validando ${key}: ${err.message}`);
    } finally {
      setValidating(prev => ({ ...prev, [key]: false }));
    }
  };

  // Eliminar valor
  const deleteConfiguration = async (key) => {
    if (!confirm(`¿Eliminar valor de ${key}?`)) return;

    try {
      setError(null);
      await api.delete(`/api/configuration/${key}`);

      setSuccess(`Valor de ${key} eliminado`);
      await loadConfigurations();
      setTimeout(() => setSuccess(null), 3000);

    } catch (err) {
      setError(`Error eliminando ${key}: ${err.message}`);
    }
  };

  // Filtrar configuraciones
  const filteredConfigs = configurations.filter(config => {
    const matchesSearch = 
      config.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      config.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      config.service_name?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = 
      selectedCategory === 'all' || config.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  // Agrupar por servicio
  const groupedByService = filteredConfigs.reduce((acc, config) => {
    const service = config.service_name || 'Other';
    if (!acc[service]) {
      acc[service] = [];
    }
    acc[service].push(config);
    return acc;
  }, {});

  // Obtener categorías únicas
  const categories = [...new Set(configurations.map(c => c.category))].filter(Boolean);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <ArrowPathIcon className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="ml-3 text-gray-400">Cargando configuraciones...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header con resumen */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <KeyIcon className="w-8 h-8 text-amber-500" />
            <div>
              <h2 className="text-xl font-bold text-white">Configuración de APIs</h2>
              <p className="text-sm text-gray-400">
                Gestiona las API keys y credenciales de servicios externos
              </p>
            </div>
          </div>
          <button
            onClick={loadConfigurations}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
          >
            <ArrowPathIcon className="w-4 h-4" />
            Recargar
          </button>
        </div>

        {/* Stats */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="bg-gray-900 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-white">{summary.total}</div>
              <div className="text-xs text-gray-400">Total APIs</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{summary.configured}</div>
              <div className="text-xs text-gray-400">Configuradas</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-amber-400">
                {summary.total - summary.configured}
              </div>
              <div className="text-xs text-gray-400">Pendientes</div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">{summary.enabled}</div>
              <div className="text-xs text-gray-400">Habilitadas</div>
            </div>
          </div>
        )}
      </div>

      {/* Mensajes */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 flex items-center gap-3">
          <XCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span className="text-red-300">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
            ✕
          </button>
        </div>
      )}

      {success && (
        <div className="bg-green-900/50 border border-green-700 rounded-lg p-4 flex items-center gap-3">
          <CheckCircleIcon className="w-5 h-5 text-green-400 flex-shrink-0" />
          <span className="text-green-300">{success}</span>
          <button onClick={() => setSuccess(null)} className="ml-auto text-green-400 hover:text-green-300">
            ✕
          </button>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
        <div className="flex flex-wrap gap-4">
          {/* Búsqueda */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar API, servicio..."
                className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Filtro por categoría */}
          <div className="flex items-center gap-2">
            <FunnelIcon className="w-5 h-5 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todas las categorías</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {cat.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Pills de categorías */}
        <div className="flex flex-wrap gap-2 mt-4">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              selectedCategory === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Todas ({configurations.length})
          </button>
          {categories.map(cat => {
            const Icon = categoryIcons[cat] || Cog6ToothIcon;
            const count = configurations.filter(c => c.category === cat).length;
            const color = categoryColors[cat] || 'gray';
            
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors flex items-center gap-1 ${
                  selectedCategory === cat
                    ? `bg-${color}-600 text-white`
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                <Icon className="w-4 h-4" />
                {cat.replace('_', ' ')}
                <span className="text-xs opacity-75">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Lista de configuraciones por servicio */}
      <div className="space-y-6">
        {Object.entries(groupedByService).map(([service, configs]) => (
          <div key={service} className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            {/* Header del servicio */}
            <div className="bg-gray-900 px-6 py-4 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ServerStackIcon className="w-6 h-6 text-blue-400" />
                  <h3 className="text-lg font-semibold text-white">{service}</h3>
                  <span className="text-xs px-2 py-1 bg-gray-700 rounded-full text-gray-300">
                    {configs.length} key{configs.length !== 1 ? 's' : ''}
                  </span>
                </div>
                {configs[0]?.service_url && (
                  <a
                    href={configs[0].service_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-sm"
                  >
                    <LinkIcon className="w-4 h-4" />
                    Docs
                  </a>
                )}
              </div>
            </div>

            {/* Configuraciones del servicio */}
            <div className="divide-y divide-gray-700">
              {configs.map(config => {
                const CategoryIcon = categoryIcons[config.category] || Cog6ToothIcon;
                const isEditing = editValues[config.key] !== undefined && editValues[config.key] !== '';
                
                return (
                  <div key={config.key} className="p-4 hover:bg-gray-750">
                    <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <CategoryIcon className={`w-4 h-4 text-${categoryColors[config.category] || 'gray'}-400`} />
                          <span className="font-mono text-sm text-gray-300">{config.key}</span>
                          {config.is_configured && (
                            <CheckCircleIcon className="w-4 h-4 text-green-400" />
                          )}
                          {config.validation_status === 'valid' && (
                            <ShieldCheckIcon className="w-4 h-4 text-blue-400" title="Validated" />
                          )}
                          {config.validation_status === 'invalid' && (
                            <ExclamationTriangleIcon className="w-4 h-4 text-red-400" title="Invalid" />
                          )}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {config.description}
                        </div>
                        {config.has_value && config.is_secret && (
                          <div className="text-xs text-gray-600 mt-1 font-mono flex items-center gap-1">
                            {showSecrets[config.key] ? config.value : '••••••••••••••••••••••••'}
                            <button
                              onClick={() => setShowSecrets(prev => ({ 
                                ...prev, 
                                [config.key]: !prev[config.key] 
                              }))}
                              className="text-gray-500 hover:text-gray-400"
                            >
                              {showSecrets[config.key] ? (
                                <EyeSlashIcon className="w-4 h-4" />
                              ) : (
                                <EyeIcon className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Input y acciones */}
                      <div className="flex items-center gap-2">
                        <input
                          type={config.is_secret ? 'password' : 'text'}
                          value={editValues[config.key] || ''}
                          onChange={(e) => setEditValues(prev => ({
                            ...prev,
                            [config.key]: e.target.value
                          }))}
                          placeholder={config.has_value ? 'Actualizar valor...' : 'Ingresar valor...'}
                          className="w-48 lg:w-64 px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-blue-500"
                        />

                        {/* Guardar */}
                        <button
                          onClick={() => saveConfiguration(config.key, editValues[config.key])}
                          disabled={saving[config.key] || !editValues[config.key]?.trim()}
                          className="p-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                          title="Guardar"
                        >
                          {saving[config.key] ? (
                            <ArrowPathIcon className="w-4 h-4 animate-spin" />
                          ) : (
                            <CloudArrowUpIcon className="w-4 h-4" />
                          )}
                        </button>

                        {/* Validar */}
                        {config.is_configured && (
                          <button
                            onClick={() => validateConfiguration(config.key)}
                            disabled={validating[config.key]}
                            className="p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded-lg transition-colors"
                            title="Validar API Key"
                          >
                            {validating[config.key] ? (
                              <ArrowPathIcon className="w-4 h-4 animate-spin" />
                            ) : (
                              <ShieldCheckIcon className="w-4 h-4" />
                            )}
                          </button>
                        )}

                        {/* Eliminar */}
                        {config.is_configured && (
                          <button
                            onClick={() => deleteConfiguration(config.key)}
                            className="p-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                            title="Eliminar valor"
                          >
                            <TrashIcon className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Si no hay resultados */}
      {filteredConfigs.length === 0 && (
        <div className="text-center py-12">
          <MagnifyingGlassIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No se encontraron configuraciones</p>
          <button
            onClick={() => { setSearchTerm(''); setSelectedCategory('all'); }}
            className="mt-4 text-blue-400 hover:text-blue-300"
          >
            Limpiar filtros
          </button>
        </div>
      )}

      {/* Footer con acciones globales */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
        <div className="flex flex-wrap gap-4 justify-between items-center">
          <div className="text-sm text-gray-400">
            Mostrando {filteredConfigs.length} de {configurations.length} configuraciones
          </div>
          <div className="flex gap-2">
            <button
              onClick={async () => {
                try {
                  const res = await api.get('/api/configuration/export/env');
                  navigator.clipboard.writeText(res.data.content);
                  setSuccess('Exportado al portapapeles');
                  setTimeout(() => setSuccess(null), 3000);
                } catch (err) {
                  setError('Error exportando');
                }
              }}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
            >
              <ClipboardDocumentIcon className="w-4 h-4" />
              Exportar .env
            </button>
            <button
              onClick={async () => {
                try {
                  setLoading(true);
                  await api.post('/api/configuration/validate-all');
                  await loadConfigurations();
                  setSuccess('Validación completada');
                } catch (err) {
                  setError('Error validando');
                } finally {
                  setLoading(false);
                }
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
            >
              <ShieldCheckIcon className="w-4 h-4" />
              Validar Todas
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfigurationPanel;
