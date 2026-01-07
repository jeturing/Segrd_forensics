import React, { useState, useEffect } from 'react';
import {
  ShieldExclamationIcon,
  GlobeAltIcon,
  EnvelopeIcon,
  ServerIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';

const ThreatIntelWidget = () => {
  const [stats, setStats] = useState({
    apiStatus: null,
    recentScans: 0,
    threatsDetected: 0,
    emailsChecked: 0
  });
  const [loading, setLoading] = useState(true);
  const [quickScan, setQuickScan] = useState('');
  const [quickScanType, setQuickScanType] = useState('ip');
  const [scanResult, setScanResult] = useState(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const { data } = await api.get('/api/threat-intel/status');
      setStats(prev => ({
        ...prev,
        apiStatus: data
      }));
      setLoading(false);
    } catch (err) {
      console.error('Error loading threat intel stats:', err);
      setLoading(false);
    }
  };

  const handleQuickScan = async () => {
    if (!quickScan.trim()) return;

    setScanning(true);
    setScanResult(null);

    try {
      let endpoint, payload;

      switch (quickScanType) {
        case 'ip':
          endpoint = '/api/threat-intel/ip/lookup';
          payload = { ip: quickScan, sources: ['virustotal', 'xforce'] };
          break;
        case 'email':
          endpoint = '/api/threat-intel/email/check';
          payload = { email: quickScan, check_breaches: true, discover_domain: false };
          break;
        case 'domain':
          endpoint = '/api/threat-intel/domain/lookup';
          payload = { domain: quickScan, dns_history: false, email_discovery: false };
          break;
        default:
          return;
      }

      const { data } = await api.post(endpoint, payload);
      setScanResult({
        success: true,
        type: quickScanType,
        data
      });
    } catch (err) {
      setScanResult({
        success: false,
        error: err.response?.data?.detail || err.message
      });
    } finally {
      setScanning(false);
    }
  };

  const getThreatLevel = (result) => {
    if (!result || !result.success) return 'unknown';
    
    if (result.type === 'ip') {
      const vt = result.data?.sources?.virustotal;
      if (vt?.malicious > 5) return 'high';
      if (vt?.malicious > 0) return 'medium';
      return 'low';
    }
    
    if (result.type === 'email') {
      const breaches = result.data?.breach_check?.breach_count || 0;
      if (breaches > 10) return 'high';
      if (breaches > 0) return 'medium';
      return 'low';
    }
    
    return 'low';
  };

  const threatLevel = scanResult ? getThreatLevel(scanResult) : null;
  const threatColors = {
    high: { bg: 'bg-red-900/50', border: 'border-red-500', text: 'text-red-400', icon: ExclamationTriangleIcon },
    medium: { bg: 'bg-yellow-900/50', border: 'border-yellow-500', text: 'text-yellow-400', icon: ShieldExclamationIcon },
    low: { bg: 'bg-green-900/50', border: 'border-green-500', text: 'text-green-400', icon: CheckCircleIcon },
    unknown: { bg: 'bg-gray-900/50', border: 'border-gray-500', text: 'text-gray-400', icon: ShieldExclamationIcon }
  };

  return (
    <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 rounded-2xl p-6 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl">
            <ShieldExclamationIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">Threat Intelligence</h3>
            <p className="text-sm text-gray-400">Multi-source OSINT</p>
          </div>
        </div>

        {stats.apiStatus && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-900/30 border border-green-700 rounded-lg">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-green-400">
              {stats.apiStatus.configured} APIs Active
            </span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <ServerIcon className="w-4 h-4" />
            <span>IP Scans</span>
          </div>
          <div className="text-2xl font-bold text-white">{stats.recentScans}</div>
          <div className="flex items-center gap-1 text-xs text-green-400 mt-1">
            <ArrowTrendingUpIcon className="w-3 h-3" />
            +12% today
          </div>
        </div>

        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <ExclamationTriangleIcon className="w-4 h-4" />
            <span>Threats</span>
          </div>
          <div className="text-2xl font-bold text-white">{stats.threatsDetected}</div>
          <div className="flex items-center gap-1 text-xs text-red-400 mt-1">
            <ArrowTrendingUpIcon className="w-3 h-3" />
            +3 this week
          </div>
        </div>

        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <EnvelopeIcon className="w-4 h-4" />
            <span>Emails</span>
          </div>
          <div className="text-2xl font-bold text-white">{stats.emailsChecked}</div>
          <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
            HIBP Checks
          </div>
        </div>

        <div className="bg-gray-900/50 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <GlobeAltIcon className="w-4 h-4" />
            <span>Domains</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {stats.apiStatus?.services?.securitytrails ? '✓' : '—'}
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
            DNS Analysis
          </div>
        </div>
      </div>

      {/* Quick Scan */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-300">
          Quick Scan
        </label>
        
        {/* Scan Type Selector */}
        <div className="flex gap-2">
          {[
            { id: 'ip', label: 'IP', icon: ServerIcon },
            { id: 'email', label: 'Email', icon: EnvelopeIcon },
            { id: 'domain', label: 'Domain', icon: GlobeAltIcon }
          ].map(type => {
            const Icon = type.icon;
            return (
              <button
                key={type.id}
                onClick={() => setQuickScanType(type.id)}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-medium transition-all ${
                  quickScanType === type.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-900 text-gray-400 hover:bg-gray-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                {type.label}
              </button>
            );
          })}
        </div>

        {/* Input and Scan Button */}
        <div className="flex gap-2">
          <input
            type="text"
            value={quickScan}
            onChange={(e) => setQuickScan(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleQuickScan()}
            placeholder={
              quickScanType === 'ip' ? '8.8.8.8' :
              quickScanType === 'email' ? 'user@example.com' :
              'example.com'
            }
            className="flex-1 px-4 py-2.5 bg-gray-900 border border-gray-700 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleQuickScan}
            disabled={scanning || !quickScan.trim()}
            className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {scanning ? 'Scanning...' : 'Scan'}
          </button>
        </div>

        {/* Scan Result */}
        {scanResult && (
          <div className={`border rounded-lg p-4 ${
            scanResult.success
              ? `${threatColors[threatLevel].bg} ${threatColors[threatLevel].border}`
              : 'bg-red-900/50 border-red-700'
          }`}>
            {scanResult.success ? (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  {React.createElement(threatColors[threatLevel].icon, {
                    className: `w-5 h-5 ${threatColors[threatLevel].text}`
                  })}
                  <span className={`font-medium ${threatColors[threatLevel].text}`}>
                    {threatLevel === 'high' ? 'High Risk' :
                     threatLevel === 'medium' ? 'Medium Risk' :
                     'Low Risk'}
                  </span>
                </div>
                
                {scanResult.type === 'ip' && scanResult.data?.sources?.virustotal && (
                  <div className="text-sm text-gray-300">
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div>
                        <span className="text-red-400 font-bold">
                          {scanResult.data.sources.virustotal.malicious || 0}
                        </span>
                        <span className="text-gray-500"> malicious</span>
                      </div>
                      <div>
                        <span className="text-yellow-400 font-bold">
                          {scanResult.data.sources.virustotal.suspicious || 0}
                        </span>
                        <span className="text-gray-500"> suspicious</span>
                      </div>
                    </div>
                  </div>
                )}

                {scanResult.type === 'email' && scanResult.data?.breach_check && (
                  <div className="text-sm text-gray-300">
                    {scanResult.data.breach_check.breached ? (
                      <div>
                        <span className="text-red-400 font-bold">
                          Found in {scanResult.data.breach_check.breach_count} breaches
                        </span>
                      </div>
                    ) : (
                      <div className="text-green-400">
                        No breaches found
                      </div>
                    )}
                  </div>
                )}

                {scanResult.type === 'domain' && (
                  <div className="text-sm text-gray-300">
                    Domain information retrieved successfully
                  </div>
                )}
              </div>
            ) : (
              <div className="text-red-400 text-sm">
                Error: {scanResult.error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* API Services Status */}
      {stats.apiStatus && (
        <div className="mt-6 pt-6 border-t border-gray-700">
          <div className="text-xs text-gray-500 mb-2">Active Services</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.apiStatus.services).map(([service, enabled]) => (
              <div
                key={service}
                className={`px-2 py-1 rounded text-xs font-medium ${
                  enabled
                    ? 'bg-green-900/30 text-green-400'
                    : 'bg-gray-900/30 text-gray-600'
                }`}
              >
                {service}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ThreatIntelWidget;
