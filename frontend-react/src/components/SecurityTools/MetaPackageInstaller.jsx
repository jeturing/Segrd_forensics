import React, { useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import api from '../../services/api';

const METAPACKAGES = {
  blue: ['kali-linux-default', 'kali-linux-top10', 'security-tools-forensics', 'security-tools-passwords'],
  red: ['kali-linux-default', 'kali-linux-top10', 'security-tools-exploitation', 'security-tools-web'],
  purple: ['kali-linux-default', 'kali-linux-top10', 'security-tools-forensics', 'security-tools-exploitation'],
  wireless: ['kali-linux-wireless', 'security-tools-wireless', 'security-tools-sniffing-spoofing'],
  custom: []
};

const ROLE_DESCRIPTIONS = {
  blue: 'Defensa/DFIR. Incluye forensics y passwords.',
  red: 'Ofensivo. Incluye exploitation y web.',
  purple: 'Mixto ofensivo-defensivo.',
  wireless: 'Análisis inalámbrico y sniffing.',
  custom: 'Selecciona manualmente'
};

const MetaPackageInstaller = () => {
  const [step, setStep] = useState(1);
  const [role, setRole] = useState('blue');
  const [customPkgs, setCustomPkgs] = useState('kali-linux-default');
  const [installing, setInstalling] = useState(false);

  const selectedPackages = useMemo(() => {
    if (role !== 'custom') return METAPACKAGES[role];
    return customPkgs
      .split(/\s+/)
      .map((p) => p.trim())
      .filter(Boolean);
  }, [role, customPkgs]);

  const installCommand = `sudo apt-get update && sudo apt-get install -y ${selectedPackages.join(' ')}`;

  const handleInstall = async () => {
    if (!selectedPackages.length) {
      toast.error('Selecciona al menos un metapaquete');
      return;
    }
    setInstalling(true);
    try {
      await api.post('/api/security-tools/install', {
        role,
        packages: selectedPackages
      });
      toast.success('Instalación lanzada (ver consola/backend)');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error instalando metapaquetes');
    } finally {
      setInstalling(false);
    }
  };

  const steps = ['Rol', 'Preferencias', 'Metapaquetes', 'Instalar'];

  return (
    <div className="bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 text-white rounded-2xl border border-slate-800 shadow-2xl p-6">
      <div className="text-sm text-blue-300 mb-2">Instalación guiada de Kali (metapaquetes oficiales)</div>
      <h2 className="text-2xl font-bold mb-4">Configura tu rol y despliega las herramientas</h2>
      <p className="text-slate-300 mb-6">Elegimos los metapaquetes adecuados según el tipo de equipo y preferencias.</p>

      <div className="flex gap-2 mb-6">
        {steps.map((label, idx) => {
          const active = step >= idx + 1;
          return (
            <div
              key={label}
              className={`px-3 py-1.5 rounded-full text-sm font-semibold ${
                active ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'
              }`}
            >
              {label}
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <div className="text-sm text-slate-300 mb-2">Rol</div>
            <div className="grid grid-cols-2 gap-2">
              {Object.keys(METAPACKAGES).map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    setRole(r);
                    setStep(2);
                  }}
                  className={`p-3 rounded-xl border transition ${
                    role === r ? 'border-blue-500 bg-blue-600/20' : 'border-slate-700 bg-slate-800 hover:border-blue-500/50'
                  }`}
                >
                  <div className="font-semibold capitalize">{r}</div>
                  <div className="text-xs text-slate-400">{ROLE_DESCRIPTIONS[r]}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="text-sm text-slate-300 mb-2">Preferencias / Metapaquetes</div>
            {role === 'custom' ? (
              <textarea
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm"
                rows={3}
                placeholder="Ej: kali-linux-default security-tools-forensics"
                value={customPkgs}
                onChange={(e) => setCustomPkgs(e.target.value)}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {selectedPackages.map((pkg) => (
                  <span key={pkg} className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-sm">
                    {pkg}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-sm text-slate-300 mb-2">Comando a ejecutar</div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-sm text-slate-200 flex items-center justify-between">
              <span className="truncate">{installCommand}</span>
              <button
                onClick={() => navigator.clipboard.writeText(installCommand)}
                className="ml-3 px-3 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm"
              >
                Copiar
              </button>
            </div>
            <div className="flex items-center text-amber-300 text-sm mt-3 gap-2">
              ⚠️ Requiere permisos root. Solo se permiten metapaquetes oficiales.
            </div>
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={() => setStep(Math.max(1, step - 1))}
              className="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700"
            >
              Atrás
            </button>
            <div className="flex gap-3">
              <button
                onClick={handleInstall}
                disabled={installing}
                className="px-5 py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold disabled:opacity-60"
              >
                {installing ? 'Instalando...' : 'Instalar metapaquetes'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetaPackageInstaller;
