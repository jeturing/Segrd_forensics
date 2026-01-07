import React, { useState, useEffect } from 'react';
import {
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  GlobeAltIcon,
  EnvelopeIcon,
  LockClosedIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  DocumentMagnifyingGlassIcon,
  ChartBarIcon,
  ArrowUpTrayIcon,
  CircleStackIcon,
  UserIcon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import { SaveToCaseModal } from './SaveToCaseModal';
import ThreatIntelDashboard from './ThreatIntelDashboard';
import IOCExplorer from './IOCExplorer';
import FeedViewer from './FeedViewer';
import ThreatHeatmap from './ThreatHeatmap';
import MISPExplorer from './MISPExplorer';
import { useCaseContext } from '../../context/CaseContext';

const ThreatIntel = () => {
  // Obtener caso activo del contexto
  const { currentCase, getCaseId } = useCaseContext();
  const caseId = getCaseId ? getCaseId() : currentCase?.id || 'default';
  
  const [activeTab, setActiveTab] = useState('ip');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [apiStatus, setApiStatus] = useState(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);

  // Form states
  const [ipAddress, setIpAddress] = useState('');
  const [ipSources, setIpSources] = useState(['shodan', 'virustotal', 'xforce']);
  const [email, setEmail] = useState('');
  const [checkBreaches, setCheckBreaches] = useState(true);
  const [discoverEmails, setDiscoverEmails] = useState(false);
  const [domain, setDomain] = useState('');
  const [dnsHistory, setDnsHistory] = useState(false);
  const [emailDiscovery, setEmailDiscovery] = useState(true);
  const [shodanQuery, setShodanQuery] = useState('');
  const [urlToScan, setUrlToScan] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  
  // FullContact states
  const [fcEmail, setFcEmail] = useState('');
  const [fcDomain, setFcDomain] = useState('');
  const [fcEnrichType, setFcEnrichType] = useState('person');  // 'person' or 'company'
  const [fcStatus, setFcStatus] = useState(null);
  const sampleIocs = [
    { value: '45.77.12.34', type: 'ip', severity: 'critical', source: 'MISP OSINT', firstSeen: '2025-12-02', lastSeen: '2025-12-08', tags: ['c2', 'bruteforce'] },
    { value: 'login.example.com', type: 'domain', severity: 'high', source: 'Shodan', firstSeen: '2025-12-03', lastSeen: '2025-12-08', tags: ['exposed-panel'] },
    { value: '7c4a8d09ca3762af61e59520943dc26494f8941b', type: 'sha1', severity: 'medium', source: 'VT', firstSeen: '2025-12-05', lastSeen: '2025-12-08', tags: ['malware'] },
    { value: 'user@example.com', type: 'email', severity: 'low', source: 'HIBP', firstSeen: '2025-11-30', lastSeen: '2025-12-08', tags: ['breach'] }
  ];
  const sampleFeeds = [
    { source: 'MISP OSINT', fetchedAt: '2025-12-08 08:30 UTC', total: 420, newItems: 58, domains: 120, ips: 95, hashes: 160, urls: 45 },
    { source: 'Abuse.ch', fetchedAt: '2025-12-08 07:50 UTC', total: 210, newItems: 24, domains: 40, ips: 70, hashes: 60, urls: 40 }
  ];
  const sampleHeatmap = [
    { day: 0, slot: 0, count: 2 }, { day: 0, slot: 3, count: 8 },
    { day: 1, slot: 1, count: 6 }, { day: 1, slot: 4, count: 12 },
    { day: 2, slot: 2, count: 14 }, { day: 2, slot: 5, count: 9 },
    { day: 3, slot: 0, count: 1 }, { day: 3, slot: 3, count: 7 },
    { day: 4, slot: 2, count: 10 }, { day: 4, slot: 4, count: 5 },
    { day: 5, slot: 1, count: 3 }, { day: 5, slot: 5, count: 6 },
    { day: 6, slot: 0, count: 4 }, { day: 6, slot: 3, count: 11 }
  ];

  useEffect(() => {
    loadApiStatus();
  }, []);

  const loadApiStatus = async () => {
    try {
      const { data } = await api.get('/api/threat-intel/status');
      setApiStatus(data);
    } catch (err) {
      console.error('Error loading API status:', err);
    }
  };

  const handleIPLookup = async () => {
    if (!ipAddress.trim()) {
      setError('Ingrese una dirección IP');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const { data } = await api.post('/api/threat-intel/ip/lookup', {
        ip: ipAddress,
        sources: ipSources
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailCheck = async () => {
    if (!email.trim()) {
      setError('Ingrese un email');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const { data } = await api.post('/api/threat-intel/email/check', {
        email,
        check_breaches: checkBreaches,
        discover_domain: discoverEmails
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDomainLookup = async () => {
    if (!domain.trim()) {
      setError('Ingrese un dominio');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const { data } = await api.post('/api/threat-intel/domain/lookup', {
        domain,
        dns_history: dnsHistory,
        email_discovery: emailDiscovery
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleShodanSearch = async () => {
    if (!shodanQuery.trim()) {
      setError('Ingrese una query de búsqueda');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const { data } = await api.post('/api/threat-intel/shodan/search', {
        query: shodanQuery,
        limit: 100
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleURLScan = async () => {
    if (!urlToScan.trim()) {
      setError('Ingrese una URL');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const { data } = await api.post('/api/threat-intel/url/scan', {
        url: urlToScan,
        vendor: 'virustotal'
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIntelXSearch = async () => {
    if (!searchTerm.trim()) {
      setError('Ingrese un término de búsqueda');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const { data } = await api.post('/api/threat-intel/intelx/search', {
        term: searchTerm,
        maxresults: 100
      });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  // FullContact Handlers
  const handleFullContactEnrich = async () => {
    const value = fcEnrichType === 'person' ? fcEmail : fcDomain;
    
    if (!value.trim()) {
      setError(`Ingrese ${fcEnrichType === 'person' ? 'un email' : 'un dominio'}`);
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const endpoint = fcEnrichType === 'person' 
        ? '/api/threat-intel/fullcontact/person'
        : '/api/threat-intel/fullcontact/company';
      
      const payload = fcEnrichType === 'person' 
        ? { email: fcEmail }
        : { domain: fcDomain };
      
      const { data } = await api.post(endpoint, payload);
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadFullContactStatus = async () => {
    try {
      const { data } = await api.get('/api/threat-intel/fullcontact/status');
      setFcStatus(data);
    } catch (err) {
      console.error('Error loading FullContact status:', err);
      setFcStatus({ configured: false, status: 'error' });
    }
  };

  useEffect(() => {
    if (activeTab === 'fullcontact' && !fcStatus) {
      loadFullContactStatus();
    }
  }, [activeTab]);

  const tabs = [
    { id: 'ip', name: 'IP Lookup', icon: ServerIcon, color: 'blue' },
    { id: 'email', name: 'Email Check', icon: EnvelopeIcon, color: 'green' },
    { id: 'domain', name: 'Domain Info', icon: GlobeAltIcon, color: 'purple' },
    { id: 'fullcontact', name: 'FullContact', icon: UserIcon, color: 'cyan' },
    { id: 'misp', name: 'MISP', icon: CircleStackIcon, color: 'violet' },
    { id: 'shodan', name: 'Shodan Search', icon: MagnifyingGlassIcon, color: 'red' },
    { id: 'url', name: 'URL Scan', icon: ShieldCheckIcon, color: 'orange' },
    { id: 'darkweb', name: 'Dark Web', icon: DocumentMagnifyingGlassIcon, color: 'gray' }
  ];

  const availableSources = [
    { id: 'shodan', name: 'Shodan', enabled: apiStatus?.services?.shodan },
    { id: 'censys', name: 'Censys', enabled: apiStatus?.services?.censys },
    { id: 'virustotal', name: 'VirusTotal', enabled: apiStatus?.services?.virustotal },
    { id: 'xforce', name: 'X-Force', enabled: apiStatus?.services?.xforce }
  ];
  const severityTotals = sampleIocs.reduce((acc, curr) => {
    acc[curr.severity] = (acc[curr.severity] || 0) + 1;
    return acc;
  }, {});
  const serviceStatus = {
    configured: apiStatus?.configured || Object.values(apiStatus?.services || {}).filter(Boolean).length || 0,
    available: Object.keys(apiStatus?.services || {}).length || 4
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">
              🔍 Threat Intelligence
            </h1>
            <p className="text-gray-400">
              Consulta APIs de inteligencia de amenazas en tiempo real
            </p>
          </div>
          
          {/* API Status Badge */}
          {apiStatus && (
            <div className="bg-gray-800 border border-gray-700 rounded-xl px-6 py-3">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  {apiStatus.percentage === 100 ? (
                    <CheckCircleIcon className="w-6 h-6 text-green-400" />
                  ) : (
                    <ExclamationTriangleIcon className="w-6 h-6 text-yellow-400" />
                  )}
                  <div>
                    <div className="text-sm text-gray-400">APIs Configured</div>
                    <div className="text-xl font-bold text-white">
                      {apiStatus.configured}
                    </div>
                  </div>
                </div>
                <div className="h-12 w-px bg-gray-700" />
                <div className="text-3xl font-bold text-green-400">
                  {apiStatus.percentage}%
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Dashboard Snapshot */}
      <div className="mb-6">
        <ThreatIntelDashboard
          stats={{
            totalIocs: sampleIocs.length,
            critical: severityTotals.critical || 0,
            high: severityTotals.high || 0,
            medium: severityTotals.medium || 0,
            feeds: sampleFeeds.length,
            lastIngest: sampleFeeds[0]?.fetchedAt || 'N/A'
          }}
          services={serviceStatus}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setResults(null);
                setError(null);
              }}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all whitespace-nowrap ${
                isActive
                  ? `bg-${tab.color}-600 text-white shadow-lg shadow-${tab.color}-500/50`
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <Icon className="w-5 h-5" />
              {tab.name}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Input Form */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <ChartBarIcon className="w-6 h-6 text-blue-400" />
              Input Parameters
            </h2>

            {/* IP Lookup Form */}
            {activeTab === 'ip' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    IP Address
                  </label>
                  <input
                    type="text"
                    value={ipAddress}
                    onChange={(e) => setIpAddress(e.target.value)}
                    placeholder="8.8.8.8"
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Sources to Query
                  </label>
                  <div className="space-y-2">
                    {availableSources.map((source) => (
                      <label key={source.id} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={ipSources.includes(source.id)}
                          disabled={!source.enabled}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setIpSources([...ipSources, source.id]);
                            } else {
                              setIpSources(ipSources.filter(s => s !== source.id));
                            }
                          }}
                          className="w-4 h-4 rounded"
                        />
                        <span className={source.enabled ? 'text-white' : 'text-gray-600'}>
                          {source.name}
                          {!source.enabled && ' (Not configured)'}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <button
                  onClick={handleIPLookup}
                  disabled={loading || ipSources.length === 0}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <MagnifyingGlassIcon className="w-5 h-5" />
                      Lookup IP
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Email Check Form */}
            {activeTab === 'email' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-green-500"
                  />
                </div>

                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={checkBreaches}
                      onChange={(e) => setCheckBreaches(e.target.checked)}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-white">Check HaveIBeenPwned</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={discoverEmails}
                      onChange={(e) => setDiscoverEmails(e.target.checked)}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-white">Discover Domain Emails</span>
                  </label>
                </div>

                <button
                  onClick={handleEmailCheck}
                  disabled={loading}
                  className="w-full px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Checking...
                    </>
                  ) : (
                    <>
                      <EnvelopeIcon className="w-5 h-5" />
                      Check Email
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Domain Lookup Form */}
            {activeTab === 'domain' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Domain Name
                  </label>
                  <input
                    type="text"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="example.com"
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={dnsHistory}
                      onChange={(e) => setDnsHistory(e.target.checked)}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-white">Include DNS History</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={emailDiscovery}
                      onChange={(e) => setEmailDiscovery(e.target.checked)}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-white">Discover Emails</span>
                  </label>
                </div>

                <button
                  onClick={handleDomainLookup}
                  disabled={loading}
                  className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <GlobeAltIcon className="w-5 h-5" />
                      Lookup Domain
                    </>
                  )}
                </button>
              </div>
            )}

            {/* FullContact Enrichment Form */}
            {activeTab === 'fullcontact' && (
              <div className="space-y-4">
                {/* API Status */}
                {fcStatus && (
                  <div className={`p-3 rounded-lg ${fcStatus.configured ? 'bg-cyan-900/30 border border-cyan-700' : 'bg-red-900/30 border border-red-700'}`}>
                    <div className="flex items-center gap-2">
                      {fcStatus.configured ? (
                        <CheckCircleIcon className="w-5 h-5 text-cyan-400" />
                      ) : (
                        <XCircleIcon className="w-5 h-5 text-red-400" />
                      )}
                      <span className={fcStatus.configured ? 'text-cyan-300' : 'text-red-300'}>
                        {fcStatus.message || (fcStatus.configured ? 'API configurada' : 'API no configurada')}
                      </span>
                    </div>
                  </div>
                )}

                {/* Enrich Type Selector */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Tipo de Enriquecimiento
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setFcEnrichType('person')}
                      className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
                        fcEnrichType === 'person'
                          ? 'bg-cyan-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      <UserIcon className="w-5 h-5" />
                      Persona
                    </button>
                    <button
                      onClick={() => setFcEnrichType('company')}
                      className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
                        fcEnrichType === 'company'
                          ? 'bg-cyan-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      <BuildingOfficeIcon className="w-5 h-5" />
                      Empresa
                    </button>
                  </div>
                </div>

                {/* Person Enrichment */}
                {fcEnrichType === 'person' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={fcEmail}
                      onChange={(e) => setFcEmail(e.target.value)}
                      placeholder="john.doe@company.com"
                      className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500"
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Obtiene: nombre, cargo, empresa, redes sociales, ubicación
                    </p>
                  </div>
                )}

                {/* Company Enrichment */}
                {fcEnrichType === 'company' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Company Domain
                    </label>
                    <input
                      type="text"
                      value={fcDomain}
                      onChange={(e) => setFcDomain(e.target.value)}
                      placeholder="company.com"
                      className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500"
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Obtiene: empresa, empleados, industria, redes sociales, logo
                    </p>
                  </div>
                )}

                <button
                  onClick={handleFullContactEnrich}
                  disabled={loading || !fcStatus?.configured}
                  className="w-full px-6 py-3 bg-cyan-600 text-white rounded-lg font-medium hover:bg-cyan-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Enriching...
                    </>
                  ) : (
                    <>
                      <UserIcon className="w-5 h-5" />
                      Enrich {fcEnrichType === 'person' ? 'Person' : 'Company'}
                    </>
                  )}
                </button>

                <div className="pt-4 border-t border-gray-700">
                  <p className="text-xs text-gray-500">
                    🔒 FullContact enriquece datos de identidad para investigaciones forenses.
                    Útil para identificar actores de amenazas o verificar identidades.
                  </p>
                </div>
              </div>
            )}

            {/* MISP Panel - Full Width */}
            {activeTab === 'misp' && (
              <div className="space-y-4">
                <p className="text-sm text-gray-400 mb-4">
                  Integración con MISP para compartir y consultar IOCs
                </p>
                <div className="text-center py-4">
                  <CircleStackIcon className="w-12 h-12 text-violet-400 mx-auto mb-3" />
                  <p className="text-gray-300">Panel MISP cargado en vista expandida →</p>
                </div>
              </div>
            )}

            {/* Shodan Search Form */}
            {activeTab === 'shodan' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Search Query
                  </label>
                  <input
                    type="text"
                    value={shodanQuery}
                    onChange={(e) => setShodanQuery(e.target.value)}
                    placeholder="apache country:ES"
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-red-500"
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Examples: "apache", "port:3306", "vuln:CVE-2021-44228"
                  </p>
                </div>

                <button
                  onClick={handleShodanSearch}
                  disabled={loading || !apiStatus?.services?.shodan}
                  className="w-full px-6 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <MagnifyingGlassIcon className="w-5 h-5" />
                      Search Shodan
                    </>
                  )}
                </button>
              </div>
            )}

            {/* URL Scan Form */}
            {activeTab === 'url' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    URL to Scan
                  </label>
                  <input
                    type="url"
                    value={urlToScan}
                    onChange={(e) => setUrlToScan(e.target.value)}
                    placeholder="https://suspicious-site.com"
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-orange-500"
                  />
                </div>

                <button
                  onClick={handleURLScan}
                  disabled={loading || !apiStatus?.services?.virustotal}
                  className="w-full px-6 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Scanning...
                    </>
                  ) : (
                    <>
                      <ShieldCheckIcon className="w-5 h-5" />
                      Scan URL
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Dark Web Search Form */}
            {activeTab === 'darkweb' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Search Term
                  </label>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="email, company, credential"
                    className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gray-500"
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Search in dark web forums, pastes, and data breaches
                  </p>
                </div>

                <button
                  onClick={handleIntelXSearch}
                  disabled={loading || !apiStatus?.services?.intelx}
                  className="w-full px-6 py-3 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <ArrowPathIcon className="w-5 h-5 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <DocumentMagnifyingGlassIcon className="w-5 h-5" />
                      Search Dark Web
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Results */}
        <div className="lg:col-span-2">
          {/* MISP Explorer - Full Panel */}
          {activeTab === 'misp' ? (
            <MISPExplorer caseId={caseId} />
          ) : (
          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-6 min-h-[600px]">
            {error && (
              <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 text-red-400">
                  <XCircleIcon className="w-5 h-5" />
                  <span className="font-medium">Error</span>
                </div>
                <p className="text-red-300 mt-1">{error}</p>
              </div>
            )}

            {loading && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <ArrowPathIcon className="w-16 h-16 text-blue-500 animate-spin mx-auto mb-4" />
                  <p className="text-gray-400">Analyzing threat intelligence...</p>
                </div>
              </div>
            )}

            {!loading && !error && !results && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <MagnifyingGlassIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-400">Enter parameters and click search</p>
                </div>
              </div>
            )}

            {results && (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-white">Results</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        const target = activeTab === 'ip' ? ipAddress :
                                       activeTab === 'email' ? email :
                                       activeTab === 'domain' ? domain :
                                       activeTab === 'url' ? urlToScan : searchTerm;
                        setCurrentAnalysis({ type: activeTab, target, results });
                        setShowSaveModal(true);
                      }}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2 transition-colors"
                    >
                      <ArrowUpTrayIcon className="w-4 h-4" />
                      Guardar en Caso
                    </button>
                    <button
                      onClick={() => window.open(`/graph?case=demo`, '_blank')}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center gap-2 transition-colors"
                    >
                      <ChartBarIcon className="w-4 h-4" />
                      Ver en Grafo
                    </button>
                  </div>
                </div>
                <pre className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-sm text-gray-300 overflow-auto max-h-[500px]">
                  {JSON.stringify(results, null, 2)}
                </pre>
              </div>
            )}
          </div>
          )}
        </div>
      </div>

      {/* Save to Case Modal */}
      <SaveToCaseModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        analysisType={currentAnalysis?.type}
        target={currentAnalysis?.target}
        result={currentAnalysis?.results}
        onSaved={(data) => {
          console.log('Saved to case:', data);
          setShowSaveModal(false);
        }}
      />

      {/* Secondary views: heatmap, explorer, feeds */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-8">
        <ThreatHeatmap data={sampleHeatmap} />
        <IOCExplorer iocs={sampleIocs} />
        <FeedViewer feeds={sampleFeeds} />
      </div>
    </div>
  );
};

export default ThreatIntel;
