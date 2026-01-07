import React from 'react';
import { GlobeAltIcon, ArrowPathIcon, CloudArrowDownIcon } from '@heroicons/react/24/outline';

/**
 * Muestra feeds de TI (ej. MISP OSINT) en formato compacto.
 */
const FeedViewer = ({ feeds = [] }) => {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-white">Feed Viewer</h2>
          <p className="text-gray-400 text-sm">Últimas ingestas normalizadas</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5">
          <ArrowPathIcon className="w-4 h-4 text-blue-400 animate-spin" />
          Refresco simulado
        </div>
      </div>

      {feeds.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 text-center text-gray-500">
          <CloudArrowDownIcon className="w-12 h-12 mb-3 text-gray-600" />
          <p>No hay feeds cargados aún.</p>
          <p className="text-xs text-gray-600 mt-1">Ejecuta ingesta o conecta MISP OSINT.</p>
        </div>
      ) : (
        <div className="space-y-3 overflow-auto">
          {feeds.map((feed, idx) => (
            <div key={`${feed.source}-${idx}`} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-gray-900 border border-gray-700">
                    <GlobeAltIcon className="w-5 h-5 text-emerald-300" />
                  </div>
                  <div>
                    <div className="text-white font-semibold">{feed.source}</div>
                    <div className="text-xs text-gray-400">Ingesta: {feed.fetchedAt}</div>
                  </div>
                </div>
                <div className="text-sm text-gray-300">
                  {feed.total} items • {feed.newItems} nuevos
                </div>
              </div>

              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-gray-300">
                <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2">
                  <span className="text-gray-500">Dominios:</span> {feed.domains}
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2">
                  <span className="text-gray-500">IPs:</span> {feed.ips}
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2">
                  <span className="text-gray-500">Hashes:</span> {feed.hashes}
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2">
                  <span className="text-gray-500">URLs:</span> {feed.urls}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FeedViewer;
