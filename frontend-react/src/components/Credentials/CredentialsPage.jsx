import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import api from '../../services/api';
import { 
  MagnifyingGlassIcon, 
  ShieldExclamationIcon, 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
  ArrowPathIcon,
  GlobeAltIcon,
  KeyIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';

const Badge = ({ color = 'gray', children }) => {
  const colors = {
    green: 'bg-green-500/15 text-green-300 border-green-500/40',
    blue: 'bg-blue-500/15 text-blue-300 border-blue-500/40',
    yellow: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
    red: 'bg-red-500/15 text-red-300 border-red-500/40',
    purple: 'bg-purple-500/15 text-purple-300 border-purple-500/40',
    orange: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
    gray: 'bg-gray-500/15 text-gray-300 border-gray-500/40'
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${colors[color] || colors.gray}`}>
      {children}
    </span>
  );
};

const RiskBadge = ({ level }) => {
  const config = {
    critical: { color: 'red', label: '🔴 CRÍTICO' },
    high: { color: 'orange', label: '🟠 ALTO' },
    medium: { color: 'yellow', label: '🟡 MEDIO' },
    low: { color: 'blue', label: '🔵 BAJO' },
    none: { color: 'green', label: '🟢 SEGURO' }
  };
  const { color, label } = config[level] || config.none;
  return <Badge color={color}>{label}</Badge>;
};

const Stat = ({ label, value, color = 'blue', icon: Icon }) => (
  <div className={`p-4 bg-slate-800/60 border border-slate-700 rounded-xl`}>
    <div className="flex items-center justify-between">
      <div>
        <div className="text-sm text-slate-400">{label}</div>
        <div className={`text-2xl font-bold text-${color}-400`}>{value}</div>
      </div>
      {Icon && <Icon className={`w-8 h-8 text-${color}-400 opacity-60`} />}
    </div>
  </div>
);

export default function CredentialsPage() {
  const [searchType, setSearchType] = useState('email'); // email, domain, username
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [history, setHistory] = useState([]);
  const [apiStatus, setApiStatus] = useState({});
  const [showPasswords, setShowPasswords] = useState(false);

  // Cargar estado de APIs
  const loadApiStatus = useCallback(async () => {
    try {
      const { data } = await api.get('/credentials/api-status');
      setApiStatus(data);
    } catch (err) {
      console.error('Error loading API status:', err);
    }
  }, []);

  // Cargar historial
  const loadHistory = useCallback(async () => {
    try {
      const { data } = await api.get('/credentials/history');
      setHistory(data.searches || []);
    } catch (err) {
      console.error('Error loading history:', err);
    }
  }, []);

  useEffect(() => {
    loadApiStatus();
    loadHistory();
  }, [loadApiStatus, loadHistory]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Ingresa un término de búsqueda');
      return;
    }

    setSearching(true);
    setResults(null);

    try {
      const { data } = await api.post('/credentials/search', {
        query: searchQuery.trim(),
        type: searchType,
        sources: ['hibp', 'dehashed', 'intelx', 'leakcheck', 'local']
      });
      
      setResults(data);
      loadHistory();
      
      if (data.total_breaches > 0) {
        toast.warning(`⚠️ Encontradas ${data.total_breaches} exposiciones`);
      } else {
        toast.success('✅ No se encontraron exposiciones');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error en la búsqueda');
    } finally {
      setSearching(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado al portapapeles');
  };

  const SourceBadge = ({ source }) => {
    const sources = {
      hibp: { color: 'blue', label: 'HIBP' },
      dehashed: { color: 'purple', label: 'Dehashed' },
      intelx: { color: 'orange', label: 'IntelX' },
      leakcheck: { color: 'red', label: 'LeakCheck' },
      local: { color: 'gray', label: 'Local Dumps' },
      stealer: { color: 'red', label: 'Stealer Logs' }
    };
    const config = sources[source] || { color: 'gray', label: source };
    return <Badge color={config.color}>{config.label}</Badge>;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <KeyIcon className="w-7 h-7 text-purple-400" />
            Búsqueda de Credenciales Filtradas
          </h1>
          <p className="text-slate-400 text-sm">
            Busca en HIBP, Dehashed, Intelligence X, LeakCheck y dumps locales
          </p>
        </div>
        <button
          onClick={loadApiStatus}
          className="p-2 text-slate-400 hover:text-white transition-colors"
          title="Actualizar estado de APIs"
        >
          <ArrowPathIcon className="w-5 h-5" />
        </button>
      </div>

      {/* API Status */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(apiStatus).map(([key, status]) => (
          <div 
            key={key}
            className={`p-3 rounded-lg border ${
              status.enabled 
                ? 'bg-emerald-500/10 border-emerald-500/30' 
                : 'bg-slate-800/50 border-slate-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${status.enabled ? 'bg-emerald-500' : 'bg-slate-500'}`} />
              <span className="text-sm font-medium text-white">{status.name}</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {status.enabled ? 'Configurado' : 'No configurado'}
            </div>
          </div>
        ))}
      </div>

      {/* Search Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm text-slate-400 mb-2">Tipo de búsqueda</label>
            <div className="flex gap-2">
              {[
                { id: 'email', label: 'Email', icon: '📧' },
                { id: 'domain', label: 'Dominio', icon: '🌐' },
                { id: 'username', label: 'Usuario', icon: '👤' },
                { id: 'phone', label: 'Teléfono', icon: '📱' },
                { id: 'ip', label: 'IP', icon: '🔗' }
              ].map(type => (
                <button
                  key={type.id}
                  onClick={() => setSearchType(type.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    searchType === type.id 
                      ? 'bg-purple-600 text-white' 
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {type.icon} {type.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm text-slate-400 mb-2">
              {searchType === 'email' && 'Email a buscar'}
              {searchType === 'domain' && 'Dominio a buscar'}
              {searchType === 'username' && 'Nombre de usuario'}
              {searchType === 'phone' && 'Número de teléfono'}
              {searchType === 'ip' && 'Dirección IP'}
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={
                searchType === 'email' ? 'usuario@empresa.com' :
                searchType === 'domain' ? 'empresa.com' :
                searchType === 'username' ? 'johndoe' :
                searchType === 'phone' ? '+1234567890' :
                '192.168.1.1'
              }
              className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={searching}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
            >
              {searching ? (
                <>
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  Buscando...
                </>
              ) : (
                <>
                  <MagnifyingGlassIcon className="w-5 h-5" />
                  Buscar en Dark Web
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat 
              label="Total Exposiciones" 
              value={results.total_breaches} 
              color={results.total_breaches > 0 ? 'red' : 'green'}
              icon={ShieldExclamationIcon}
            />
            <Stat 
              label="Fuentes Consultadas" 
              value={results.sources_checked} 
              color="blue"
              icon={GlobeAltIcon}
            />
            <Stat 
              label="Nivel de Riesgo" 
              value={results.risk_level?.toUpperCase() || 'N/A'} 
              color={results.risk_level === 'critical' ? 'red' : results.risk_level === 'high' ? 'orange' : 'green'}
              icon={ExclamationTriangleIcon}
            />
            <Stat 
              label="Credenciales Expuestas" 
              value={results.credentials_found || 0} 
              color={results.credentials_found > 0 ? 'red' : 'green'}
              icon={KeyIcon}
            />
          </div>

          {/* Risk Level Alert */}
          {results.risk_level && results.risk_level !== 'none' && (
            <div className={`p-4 rounded-xl border ${
              results.risk_level === 'critical' ? 'bg-red-500/10 border-red-500/40' :
              results.risk_level === 'high' ? 'bg-orange-500/10 border-orange-500/40' :
              'bg-yellow-500/10 border-yellow-500/40'
            }`}>
              <div className="flex items-center gap-3">
                <ExclamationTriangleIcon className={`w-6 h-6 ${
                  results.risk_level === 'critical' ? 'text-red-400' :
                  results.risk_level === 'high' ? 'text-orange-400' :
                  'text-yellow-400'
                }`} />
                <div>
                  <div className="font-semibold text-white">
                    {results.risk_level === 'critical' && '🚨 RIESGO CRÍTICO - Acción inmediata requerida'}
                    {results.risk_level === 'high' && '⚠️ RIESGO ALTO - Revisar urgentemente'}
                    {results.risk_level === 'medium' && '⚡ RIESGO MEDIO - Monitorear'}
                  </div>
                  <div className="text-sm text-slate-300 mt-1">
                    {results.recommendations?.[0] || 'Se recomienda cambiar contraseñas y habilitar MFA'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Breaches List */}
          {results.breaches && results.breaches.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white">Exposiciones Encontradas</h3>
                <button
                  onClick={() => setShowPasswords(!showPasswords)}
                  className="text-sm text-slate-400 hover:text-white flex items-center gap-1"
                >
                  {showPasswords ? <EyeSlashIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
                  {showPasswords ? 'Ocultar' : 'Mostrar'} detalles
                </button>
              </div>
              <div className="divide-y divide-slate-800">
                {results.breaches.map((breach, idx) => (
                  <div key={idx} className="p-4 hover:bg-slate-800/50">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center gap-3">
                          <span className="text-lg font-semibold text-white">{breach.name || breach.source}</span>
                          <SourceBadge source={breach.source} />
                          <RiskBadge level={breach.risk_level || 'medium'} />
                        </div>
                        {breach.breach_date && (
                          <div className="text-sm text-slate-400">
                            Fecha de brecha: {new Date(breach.breach_date).toLocaleDateString()}
                          </div>
                        )}
                        {breach.data_classes && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {breach.data_classes.map((dc, i) => (
                              <span key={i} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">
                                {dc}
                              </span>
                            ))}
                          </div>
                        )}
                        {showPasswords && breach.credentials && (
                          <div className="mt-3 p-3 bg-slate-800 rounded-lg">
                            <div className="text-sm text-slate-400 mb-2">Credenciales expuestas:</div>
                            {breach.credentials.map((cred, i) => (
                              <div key={i} className="flex items-center gap-4 text-sm">
                                <span className="text-slate-300">{cred.username || cred.email}</span>
                                <span className="text-red-400 font-mono">{cred.password || '[REDACTED]'}</span>
                                <button
                                  onClick={() => copyToClipboard(cred.password || '')}
                                  className="text-slate-400 hover:text-white"
                                >
                                  <ClipboardDocumentIcon className="w-4 h-4" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="text-right text-sm text-slate-400">
                        {breach.pwn_count && (
                          <div>{breach.pwn_count.toLocaleString()} afectados</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {results.recommendations && results.recommendations.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-lg font-semibold text-white mb-3">📋 Recomendaciones</h3>
              <ul className="space-y-2">
                {results.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-slate-300">
                    <CheckCircleIcon className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* No results */}
          {results.total_breaches === 0 && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-8 text-center">
              <CheckCircleIcon className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">¡Sin exposiciones encontradas!</h3>
              <p className="text-slate-300">
                No se encontraron credenciales filtradas en las fuentes consultadas.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Search History */}
      {history.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <h3 className="text-lg font-semibold text-white mb-3">🕐 Historial de búsquedas</h3>
          <div className="divide-y divide-slate-800">
            {history.slice(0, 10).map((item, idx) => (
              <div 
                key={idx} 
                className="py-2 flex items-center justify-between cursor-pointer hover:bg-slate-800/50 px-2 rounded"
                onClick={() => {
                  setSearchQuery(item.query);
                  setSearchType(item.type);
                }}
              >
                <div className="flex items-center gap-3">
                  <span className="text-slate-300">{item.query}</span>
                  <Badge color="gray">{item.type}</Badge>
                </div>
                <div className="flex items-center gap-3">
                  <RiskBadge level={item.risk_level || 'none'} />
                  <span className="text-xs text-slate-500">{new Date(item.timestamp).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
