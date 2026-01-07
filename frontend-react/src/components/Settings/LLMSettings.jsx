import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import api from '../../services/api';
import { Card, Loading, Alert, Button } from '../Common';

export default function LLMSettings() {
  const [status, setStatus] = useState(null);
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [testPrompt, setTestPrompt] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 30000); // Refresh cada 30s
    return () => clearInterval(interval);
  }, []);

  async function loadAllData() {
    try {
      const [statusRes, healthRes, statsRes] = await Promise.all([
        api.get('/api/v41/llm/status'),
        api.get('/api/v41/llm/health'),
        api.get('/api/v41/llm/statistics')
      ]);

      setStatus(statusRes.data.data);
      setHealth(healthRes.data.health);
      setStats(statsRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error loading LLM data:', error);
      toast.error('Error cargando configuración LLM');
      setLoading(false);
    }
  }

  async function setProvider(provider) {
    try {
      await api.post('/api/v41/llm/provider', {
        provider,
        reason: `Cambio manual desde panel de configuración`
      });
      
      toast.success(`Proveedor cambiado a ${provider}`);
      await loadAllData();
    } catch (error) {
      console.error('Error changing provider:', error);
      toast.error('Error cambiando proveedor');
    }
  }

  async function testLLM() {
    if (!testPrompt.trim()) {
      toast.warning('Ingresa un prompt de prueba');
      return;
    }

    setTesting(true);
    try {
      const res = await api.post('/api/v41/llm/test', {
        prompt: testPrompt,
        context: { source: 'settings_panel' }
      });

      setTestResult(res.data.response);
      toast.success('Test completado exitosamente');
    } catch (error) {
      console.error('Error testing LLM:', error);
      toast.error('Error ejecutando test');
    } finally {
      setTesting(false);
    }
  }

  async function resetStats() {
    if (!window.confirm('¿Reiniciar todas las estadísticas?')) return;

    try {
      await api.post('/api/v41/llm/reset-stats');
      toast.success('Estadísticas reiniciadas');
      await loadAllData();
    } catch (error) {
      console.error('Error resetting stats:', error);
      toast.error('Error reiniciando estadísticas');
    }
  }

  if (loading) {
    return <Loading message="Cargando configuración LLM..." />;
  }

  const activeProvider = status?.active_provider;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">🧠 Configuración de IA (LLM)</h1>
          <p className="text-sm text-gray-400 mt-1">
            Gestión de modelos, proveedores y configuración del sistema LLM v4.5
          </p>
        </div>
        <button
          onClick={loadAllData}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition"
        >
          🔄 Actualizar
        </button>
      </div>

      {/* Estado General */}
      <Card title="📊 Estado del Sistema">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Proveedor Activo</div>
            <div className="text-xl font-bold text-blue-400">
              {activeProvider === 'llm_studio' && '☁️ LLM Studio'}
              {activeProvider === 'phi4_local' && '💻 Phi-4 Local'}
              {activeProvider === 'offline' && '📋 Offline'}
            </div>
          </div>

          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Estado Global</div>
            <div className={`text-xl font-bold ${
              health?.overall === 'healthy' ? 'text-green-400' : 'text-yellow-400'
            }`}>
              {health?.overall === 'healthy' ? '🟢 Saludable' : '🟡 Degradado'}
            </div>
          </div>

          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Total Requests</div>
            <div className="text-xl font-bold text-purple-400">
              {Object.values(stats?.llm_statistics || {}).reduce((sum, stat) => sum + stat.requests, 0)}
            </div>
          </div>
        </div>
      </Card>

      {/* Proveedores Disponibles */}
      <Card title="🔄 Proveedores LLM">
        <div className="space-y-3">
          {status?.available_providers?.map((provider) => (
            <div
              key={provider.name}
              className={`p-4 rounded-lg border-2 transition cursor-pointer ${
                activeProvider === provider.name
                  ? 'border-blue-500 bg-blue-900/20'
                  : 'border-gray-700 bg-gray-800 hover:border-gray-600'
              }`}
              onClick={() => setProvider(provider.name)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-100">
                      {provider.name === 'llm_studio' && '☁️ LLM Studio'}
                      {provider.name === 'phi4_local' && '💻 Phi-4 Local'}
                      {provider.name === 'offline' && '📋 Offline Engine'}
                    </h3>
                    {activeProvider === provider.name && (
                      <span className="px-2 py-1 bg-blue-600 text-xs rounded">ACTIVO</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{provider.description}</p>
                  {provider.url && (
                    <p className="text-xs text-gray-500 mt-1">URL: {provider.url}</p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded text-sm ${
                    provider.status === 'available' || provider.status === 'healthy'
                      ? 'bg-green-900/30 text-green-400'
                      : 'bg-yellow-900/30 text-yellow-400'
                  }`}>
                    {provider.status === 'available' || provider.status === 'healthy' ? '✓ Disponible' : '⚠ No configurado'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-blue-900/20 border border-blue-800 rounded-lg">
          <p className="text-sm text-blue-300">
            💡 <strong>Fallback automático:</strong> Si LLM Studio no responde, el sistema cambiará automáticamente a Phi-4 Local
          </p>
        </div>
      </Card>

      {/* Estadísticas de Uso */}
      <Card title="📈 Estadísticas de Uso">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {Object.entries(stats?.llm_statistics || {}).map(([provider, providerStats]) => (
            <div key={provider} className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400 mb-2">
                {provider === 'llm_studio' && '☁️ LLM Studio'}
                {provider === 'phi4_local' && '💻 Phi-4 Local'}
                {provider === 'offline' && '📋 Offline'}
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Requests:</span>
                  <span className="text-gray-200">{providerStats.requests}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Errores:</span>
                  <span className={providerStats.errors > 0 ? 'text-red-400' : 'text-green-400'}>
                    {providerStats.errors}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Latencia:</span>
                  <span className="text-gray-200">{providerStats.avg_latency.toFixed(2)}s</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={resetStats}
          className="px-4 py-2 bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded-lg text-sm transition"
        >
          🗑️ Reiniciar Estadísticas
        </button>
      </Card>

      {/* Test LLM */}
      <Card title="🧪 Test de Modelo LLM">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Prompt de Prueba:</label>
            <textarea
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              placeholder="Ej: Analiza estos hallazgos forenses y clasifica la severidad..."
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-blue-500"
              rows={4}
            />
          </div>

          <button
            onClick={testLLM}
            disabled={testing}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 rounded-lg font-medium transition"
          >
            {testing ? '⏳ Ejecutando...' : '🚀 Ejecutar Test'}
          </button>

          {testResult && (
            <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
              <div className="text-sm text-gray-400 mb-2">
                Proveedor: <span className="text-blue-400 font-medium">{testResult.provider}</span>
              </div>
              <div className="text-sm text-gray-400 mb-2">
                Latencia: <span className="text-purple-400 font-medium">{testResult.latency?.toFixed(2)}s</span>
              </div>
              <div className="text-sm text-gray-400 mb-2">Respuesta:</div>
              <pre className="text-sm text-gray-200 bg-gray-900 p-3 rounded overflow-auto max-h-64">
                {testResult.output}
              </pre>
            </div>
          )}
        </div>
      </Card>

      {/* Configuración de Modelos */}
      <Card title="⚙️ Configuración de Modelos">
        <div className="space-y-3">
          {Object.entries(status?.configuration || {}).map(([providerName, config]) => (
            <div key={providerName} className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm font-semibold text-gray-200 mb-2">
                {providerName.toUpperCase()}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {Object.entries(config).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-gray-400 text-xs">{key}:</div>
                    <div className="text-gray-200">{typeof value === 'object' ? JSON.stringify(value) : value}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Health Check */}
      <Card title="🏥 Health Check">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(health?.providers || {}).map(([provider, healthStatus]) => (
            <div key={provider} className="bg-gray-800 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">
                  {provider === 'llm_studio' && '☁️ LLM Studio'}
                  {provider === 'phi4_local' && '💻 Phi-4 Local'}
                  {provider === 'offline' && '📋 Offline'}
                </span>
                <span className={`px-2 py-1 rounded text-xs ${
                  healthStatus.status === 'healthy'
                    ? 'bg-green-900/30 text-green-400'
                    : healthStatus.status === 'unavailable'
                    ? 'bg-red-900/30 text-red-400'
                    : 'bg-yellow-900/30 text-yellow-400'
                }`}>
                  {healthStatus.status}
                </span>
              </div>
              {healthStatus.response_time && (
                <div className="text-xs text-gray-500">
                  Response: {healthStatus.response_time.toFixed(2)}s
                </div>
              )}
              {healthStatus.error && (
                <div className="text-xs text-red-400 mt-1">
                  {healthStatus.error}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
