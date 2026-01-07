import React from 'react';
import { FireIcon } from '@heroicons/react/24/outline';

/**
 * Heatmap simple para visualizar actividad reciente de IOCs.
 * Usa datos sintéticos hasta conectar con backend.
 */
const ThreatHeatmap = ({ data = [] }) => {
  const days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  const hours = ['00-04', '04-08', '08-12', '12-16', '16-20', '20-24'];

  const intensity = (value) => {
    if (value >= 14) return 'bg-red-500/80';
    if (value >= 10) return 'bg-orange-500/80';
    if (value >= 6) return 'bg-amber-400/80';
    if (value >= 3) return 'bg-lime-400/70';
    if (value > 0) return 'bg-emerald-400/60';
    return 'bg-gray-800';
  };

  const lookup = (dayIdx, hourIdx) => data.find((d) => d.day === dayIdx && d.slot === hourIdx)?.count || 0;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FireIcon className="w-5 h-5 text-amber-400" />
          <h2 className="text-xl font-bold text-white">Heatmap de Actividad</h2>
        </div>
        <p className="text-xs text-gray-500">Conteos sintéticos por día/franja</p>
      </div>

      <div className="overflow-auto">
        <table className="text-xs text-gray-300">
          <thead>
            <tr>
              <th className="px-2 py-1 text-left text-gray-500">Día</th>
              {hours.map((h) => (
                <th key={h} className="px-2 py-1 text-center text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {days.map((day, dIdx) => (
              <tr key={day}>
                <td className="px-2 py-1 text-gray-400">{day}</td>
                {hours.map((_, hIdx) => {
                  const val = lookup(dIdx, hIdx);
                  return (
                    <td key={`${day}-${hIdx}`} className="px-1 py-1">
                      <div className={`h-6 w-10 rounded ${intensity(val)} border border-gray-800 text-center text-[10px] text-black/70`}>
                        {val || ''}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ThreatHeatmap;
