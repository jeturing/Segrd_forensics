import React from 'react';
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

const severityColors = {
  critical: 'bg-red-500/20 text-red-200 border border-red-500/40',
  high: 'bg-orange-500/20 text-orange-200 border border-orange-500/40',
  medium: 'bg-amber-500/20 text-amber-200 border border-amber-500/40',
  low: 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/40'
};

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center py-10 text-center">
    <InformationCircleIcon className="w-10 h-10 text-gray-500 mb-3" />
    <p className="text-gray-400">Aún no hay IOCs cargados en esta vista.</p>
    <p className="text-gray-500 text-sm">Ejecuta una búsqueda o ingesta para poblar la lista.</p>
  </div>
);

/**
 * Tabla simple para explorar IOCs normalizados.
 */
const IOCExplorer = ({ iocs = [] }) => {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-white">IOC Explorer</h2>
          <p className="text-gray-400 text-sm">Vista filtrable de IOCs normalizados</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5">
          <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
          Muestra de UI
        </div>
      </div>

      {iocs.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="overflow-auto -mx-4 px-4">
          <table className="min-w-full text-sm text-left text-gray-300">
            <thead className="text-xs uppercase bg-gray-800 text-gray-400">
              <tr>
                <th className="px-3 py-2 font-medium">IOC</th>
                <th className="px-3 py-2 font-medium">Tipo</th>
                <th className="px-3 py-2 font-medium">Severidad</th>
                <th className="px-3 py-2 font-medium">Fuente</th>
                <th className="px-3 py-2 font-medium">Primera vez</th>
                <th className="px-3 py-2 font-medium">Última vez</th>
                <th className="px-3 py-2 font-medium">Tags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {iocs.map((ioc, idx) => (
                <tr key={`${ioc.value}-${idx}`} className="hover:bg-gray-800/60">
                  <td className="px-3 py-3 font-mono text-xs text-white break-all">{ioc.value}</td>
                  <td className="px-3 py-3 text-gray-200">{ioc.type}</td>
                  <td className="px-3 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${severityColors[ioc.severity] || severityColors.low}`}>
                      {ioc.severity}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-gray-200">{ioc.source}</td>
                  <td className="px-3 py-3 text-gray-400">{ioc.firstSeen}</td>
                  <td className="px-3 py-3 text-gray-400">{ioc.lastSeen}</td>
                  <td className="px-3 py-3 text-gray-300">
                    <div className="flex flex-wrap gap-1">
                      {(ioc.tags || []).map((tag) => (
                        <span key={tag} className="px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-xs">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default IOCExplorer;
