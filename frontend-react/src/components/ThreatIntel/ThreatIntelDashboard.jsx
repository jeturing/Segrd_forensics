import React from 'react';
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  GlobeAltIcon,
  ClockIcon,
  DocumentMagnifyingGlassIcon
} from '@heroicons/react/24/outline';

/**
 * Resumen visual de salud TI: conteos de IOCs, severidades y feeds activos.
 */
const ThreatIntelDashboard = ({
  stats = {
    totalIocs: 0,
    critical: 0,
    high: 0,
    medium: 0,
    feeds: 0,
    lastIngest: 'N/A'
  },
  services = {}
}) => {
  const health = Math.min(100, Math.round(((services.configured || 0) / Math.max(1, services.available || 1)) * 100));

  const cards = [
    {
      title: 'IOCs Totales',
      value: stats.totalIocs,
      icon: ShieldCheckIcon,
      color: 'from-blue-500 to-cyan-500'
    },
    {
      title: 'Críticos',
      value: stats.critical,
      icon: ExclamationTriangleIcon,
      color: 'from-red-500 to-orange-500'
    },
    {
      title: 'Altos',
      value: stats.high,
      icon: ExclamationTriangleIcon,
      color: 'from-amber-500 to-yellow-500'
    },
    {
      title: 'Feeds Activos',
      value: stats.feeds,
      icon: GlobeAltIcon,
      color: 'from-emerald-500 to-teal-500'
    }
  ];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Threat Intel Dashboard</h2>
          <p className="text-gray-400 text-sm">Visión rápida de salud, ingestión y severidad</p>
        </div>
        <div className="flex items-center gap-3 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2">
          <DocumentMagnifyingGlassIcon className="w-5 h-5 text-blue-300" />
          <div>
            <div className="text-xs text-gray-400">Última ingesta</div>
            <div className="text-sm text-white font-medium">{stats.lastIngest}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              className="bg-gray-800 border border-gray-700 rounded-xl p-4 relative overflow-hidden"
            >
              <div className={`absolute inset-0 opacity-20 bg-gradient-to-br ${card.color}`} />
              <div className="relative flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">{card.title}</p>
                  <div className="text-2xl font-bold text-white">{card.value}</div>
                </div>
                <div className="p-2 rounded-lg bg-black/30 border border-gray-700">
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Salud de Integraciones</p>
              <div className="text-2xl font-bold text-white">{health}%</div>
            </div>
            <ShieldCheckIcon className="w-6 h-6 text-emerald-400" />
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2 mt-3">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400"
              style={{ width: `${health}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {services.configured || 0} configurados / {services.available || services.configured || 0} totales
          </p>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center justify-between mb-1">
            <div>
              <p className="text-gray-400 text-sm">Tendencia Ingesta</p>
              <div className="text-sm text-white font-medium">Últimas 24h</div>
            </div>
            <ClockIcon className="w-5 h-5 text-blue-400" />
          </div>
          <div className="flex items-end gap-2 h-16">
            {[6, 8, 12, 7, 10, 14, 9].map((v, idx) => (
              <div key={idx} className="flex-1">
                <div
                  className="w-full rounded-t-md bg-gradient-to-t from-blue-500 to-cyan-400"
                  style={{ height: `${Math.max(8, v)}px` }}
                />
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">Muestras sintéticas para prototipo UI</p>
        </div>
      </div>
    </div>
  );
};

export default ThreatIntelDashboard;
