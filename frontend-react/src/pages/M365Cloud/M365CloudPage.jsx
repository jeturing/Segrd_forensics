import React, { useEffect, useState } from 'react';
import { Cloud, Shield, AlertTriangle, CheckCircle, Play, RefreshCw, ExternalLink, FileText } from 'lucide-react';
import api from '../../services/api';

const M365CloudPage = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedScan, setSelectedScan] = useState(null);
  const [showNewScanModal, setShowNewScanModal] = useState(false);
  const [scanForm, setScanForm] = useState({
    scan_name: 'security_assessment',
    instance: 'Microsoft365',
    include_entra_id: true,
    export_format: 'HTML'
  });
  const [startingScan, setStartingScan] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/monkey365/status');
      setStatus(response.data);
    } catch (error) {
      console.error('Error fetching Monkey365 status:', error);
    } finally {
      setLoading(false);
    }
  };

  const startNewScan = async () => {
    try {
      setStartingScan(true);
      const response = await api.post('/api/monkey365/scan/start', scanForm);
      if (response.data.success) {
        setShowNewScanModal(false);
        fetchStatus();
        // Mostrar notificación
        alert(`Scan iniciado: ${response.data.scan_id}`);
      }
    } catch (error) {
      console.error('Error starting scan:', error);
      alert('Error al iniciar scan: ' + (error.response?.data?.detail || error.message));
    } finally {
      setStartingScan(false);
    }
  };

  const openDashboard = () => {
    window.open('/api/monkey365/dashboard', '_blank');
  };

  const viewReport = (scanName) => {
    setSelectedScan(scanName);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Cargando M365 Cloud Security...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl">
            <Cloud className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">M365 Cloud Security</h1>
            <p className="text-gray-400">Análisis de seguridad con Monkey365</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchStatus}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Actualizar
          </button>
          <button
            onClick={openDashboard}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Dashboard Completo
          </button>
          <button
            onClick={() => setShowNewScanModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all"
          >
            <Play className="w-4 h-4" />
            Nuevo Scan
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Estado</p>
              <p className={`text-xl font-bold ${status?.installed ? 'text-green-400' : 'text-red-400'}`}>
                {status?.installed ? 'Instalado' : 'No Instalado'}
              </p>
            </div>
            {status?.installed ? (
              <CheckCircle className="w-10 h-10 text-green-500" />
            ) : (
              <AlertTriangle className="w-10 h-10 text-red-500" />
            )}
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">PowerShell</p>
              <p className={`text-xl font-bold ${status?.powershell_available ? 'text-green-400' : 'text-red-400'}`}>
                {status?.powershell_available ? 'Disponible' : 'No Disponible'}
              </p>
            </div>
            <Shield className="w-10 h-10 text-blue-500" />
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Scans Previos</p>
              <p className="text-xl font-bold text-blue-400">
                {status?.previous_scans?.length || 0}
              </p>
            </div>
            <FileText className="w-10 h-10 text-purple-500" />
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Scans Activos</p>
              <p className="text-xl font-bold text-orange-400">
                {status?.active_scans?.length || 0}
              </p>
            </div>
            <RefreshCw className={`w-10 h-10 text-orange-500 ${status?.active_scans?.length > 0 ? 'animate-spin' : ''}`} />
          </div>
        </div>
      </div>

      {/* Supported Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Cloud className="w-5 h-5 text-blue-400" />
            Instancias Soportadas
          </h3>
          <div className="flex flex-wrap gap-2">
            {status?.supported_instances?.map((instance) => (
              <span key={instance} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm border border-blue-500/30">
                {instance}
              </span>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-purple-400" />
            Colectores Disponibles
          </h3>
          <div className="flex flex-wrap gap-2">
            {status?.supported_collectors?.map((collector) => (
              <span key={collector} className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg text-sm border border-purple-500/30">
                {collector}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Previous Scans Table */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold">Scans Recientes</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Fecha</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {status?.previous_scans?.length > 0 ? (
                status.previous_scans.map((scan, idx) => (
                  <tr key={idx} className="hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium">{scan.name}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {scan.has_report ? (
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs">
                          Completado
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full text-xs">
                          En Proceso
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 text-sm">
                      {new Date(scan.created).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => viewReport(scan.name)}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm transition-colors"
                      >
                        Ver Reporte
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-gray-500">
                    No hay scans previos. Inicia uno nuevo para comenzar.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Report Viewer */}
      {selectedScan && (
        <div className="mt-8 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-gray-700 flex justify-between items-center">
            <h3 className="text-lg font-semibold">Reporte: {selectedScan}</h3>
            <button
              onClick={() => setSelectedScan(null)}
              className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm"
            >
              Cerrar
            </button>
          </div>
          <iframe
            src={`/api/monkey365/scan/${selectedScan}/report`}
            className="w-full h-[600px] bg-white"
            title="Monkey365 Report"
          />
        </div>
      )}

      {/* New Scan Modal */}
      {showNewScanModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md border border-gray-700 shadow-2xl">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Shield className="w-6 h-6 text-blue-400" />
              Nuevo Scan de Seguridad
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Nombre del Scan</label>
                <input
                  type="text"
                  value={scanForm.scan_name}
                  onChange={(e) => setScanForm({ ...scanForm, scan_name: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Tipo de Análisis</label>
                <select
                  value={scanForm.instance}
                  onChange={(e) => setScanForm({ ...scanForm, instance: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:border-blue-500 focus:outline-none"
                >
                  <option value="Microsoft365">Microsoft 365</option>
                  <option value="Azure">Azure Subscription</option>
                  <option value="EntraID">Microsoft Entra ID</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="includeEntraID"
                  checked={scanForm.include_entra_id}
                  onChange={(e) => setScanForm({ ...scanForm, include_entra_id: e.target.checked })}
                  className="w-4 h-4 bg-gray-700 border-gray-600 rounded"
                />
                <label htmlFor="includeEntraID" className="text-sm text-gray-300">
                  Incluir análisis de Entra ID
                </label>
              </div>
            </div>

            <div className="flex gap-3 mt-8">
              <button
                onClick={() => setShowNewScanModal(false)}
                className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={startNewScan}
                disabled={startingScan}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg font-semibold transition-all disabled:opacity-50"
              >
                {startingScan ? 'Iniciando...' : 'Iniciar Scan'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default M365CloudPage;
