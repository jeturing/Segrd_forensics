/**
 * Modal para guardar resultados de Threat Intel en un caso
 */

import React, { useState, useEffect } from 'react';
import {
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusIcon
} from '@heroicons/react/24/outline';
import { threatIntelCaseService } from '../../services/threatIntelCaseService';
import { caseService } from '../../services/cases';

export const SaveToCaseModal = ({ 
  isOpen, 
  onClose, 
  analysisType, 
  target, 
  result,
  onSaved
}) => {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [newCaseName, setNewCaseName] = useState('');
  const [showNewCase, setShowNewCase] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingCases, setLoadingCases] = useState(true);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadCases();
      setMessage('');
      setShowNewCase(false);
      setNewCaseName('');
    }
  }, [isOpen]);

  const loadCases = async () => {
    setLoadingCases(true);
    try {
      // Obtener casos del backend
      const response = await caseService.getCases(1, 100);
      const casesData = response.items || [];
      setCases(casesData);
      if (casesData.length > 0) {
        setSelectedCase(casesData[0].id);
      }
    } catch (error) {
      console.error('Error loading cases:', error);
      // Fallback: crear caso demo
      const demoCases = [
        { id: 'IR-2024-001', name: 'Investigación Demo' }
      ];
      setCases(demoCases);
      setSelectedCase('IR-2024-001');
    } finally {
      setLoadingCases(false);
    }
  };

  const handleCreateNewCase = async () => {
    if (!newCaseName.trim()) {
      setMessage('Ingrese un nombre para el caso');
      setMessageType('error');
      return;
    }

    try {
      const newCase = await caseService.createCase({
        name: newCaseName,
        description: `Caso creado desde Threat Intel - ${target}`,
        type: 'threat_investigation'
      });
      
      setCases([...cases, newCase]);
      setSelectedCase(newCase.id);
      setShowNewCase(false);
      setNewCaseName('');
      setMessage('✅ Caso creado exitosamente');
      setMessageType('success');
    } catch (error) {
      // Crear caso local si el backend falla
      const newCaseId = `IR-${Date.now()}`;
      const localCase = { id: newCaseId, name: newCaseName };
      setCases([...cases, localCase]);
      setSelectedCase(newCaseId);
      setShowNewCase(false);
      setNewCaseName('');
    }
  };

  const handleSave = async () => {
    if (!selectedCase) {
      setMessage('Seleccione un caso');
      setMessageType('error');
      return;
    }

    setLoading(true);
    try {
      const savedData = await threatIntelCaseService.analyzeAndSaveToCase(
        selectedCase,
        analysisType,
        target
      );

      setMessage(`✅ Guardado exitosamente. Ver en Grafo de Ataque.`);
      setMessageType('success');
      
      setTimeout(() => {
        if (onSaved) onSaved(savedData);
        onClose();
      }, 1500);
    } catch (error) {
      console.error('Error saving to case:', error);
      setMessage('Error al guardar: ' + (error.response?.data?.detail || error.message));
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">💾 Guardar en Caso</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Target Info */}
          <div className="bg-gray-700/30 rounded p-3">
            <p className="text-xs text-gray-400 mb-1">Objetivo:</p>
            <p className="text-sm font-mono text-blue-400 break-all">{target}</p>
          </div>

          {/* Case Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Seleccionar Caso:
            </label>
            {loadingCases ? (
              <div className="flex items-center justify-center py-4">
                <div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                <span className="ml-2 text-gray-400">Cargando casos...</span>
              </div>
            ) : !showNewCase ? (
              <div className="space-y-2">
                {cases.length > 0 ? (
                  <select
                    value={selectedCase}
                    onChange={(e) => setSelectedCase(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white 
                               focus:outline-none focus:border-blue-500 transition-colors"
                  >
                    {cases.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.name || c.title} ({c.id})
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded text-yellow-400 text-sm">
                    No hay casos disponibles.
                  </div>
                )}
                <button
                  onClick={() => setShowNewCase(true)}
                  className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                >
                  <PlusIcon className="w-4 h-4" />
                  Crear nuevo caso
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  value={newCaseName}
                  onChange={(e) => setNewCaseName(e.target.value)}
                  placeholder="Nombre del nuevo caso..."
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white 
                             focus:outline-none focus:border-blue-500 transition-colors"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleCreateNewCase}
                    className="flex-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-sm"
                  >
                    ✅ Crear
                  </button>
                  <button
                    onClick={() => setShowNewCase(false)}
                    className="flex-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-500 text-white rounded text-sm"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Message */}
          {message && (
            <div className={`p-3 rounded text-sm ${
              messageType === 'success' 
                ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                : 'bg-red-500/10 text-red-400 border border-red-500/30'
            }`}>
              <div className="flex items-center">
                {messageType === 'success' ? (
                  <CheckCircleIcon className="w-4 h-4 flex-shrink-0 mr-2" />
                ) : (
                  <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0 mr-2" />
                )}
                {message}
              </div>
              {messageType === 'success' && selectedCase && (
                <a 
                  href={`/graph?case=${selectedCase}`}
                  className="mt-2 inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 text-xs"
                >
                  📊 Ver en Grafo de Ataque →
                </a>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-6 border-t border-gray-700">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={loading || !selectedCase}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded
                       transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Guardando...
              </>
            ) : (
              <>💾 Guardar</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
