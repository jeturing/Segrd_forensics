/**
 * 🎯 CaseHeader - Header con Selector de Caso v4.4
 * 
 * Componente de header que muestra el caso activo y permite cambiar.
 * Se integra en todas las páginas forenses.
 */

import React, { useState } from 'react';
import { useCaseContext } from '../context/CaseContext';

const CaseHeader = ({ title, subtitle, icon = '🔍', showCaseSelector = true }) => {
  const { 
    currentCase, 
    caseList, 
    selectCase, 
    clearCase,
    hasActiveCase,
    lastActivity 
  } = useCaseContext();
  
  const [showDropdown, setShowDropdown] = useState(false);
  
  const formatTime = (date) => {
    return new Intl.DateTimeFormat('es', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(date));
  };
  
  return (
    <div className="bg-gradient-to-r from-gray-900 to-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Título de la página */}
        <div className="flex items-center gap-4">
          <span className="text-3xl">{icon}</span>
          <div>
            <h1 className="text-2xl font-bold text-white">{title}</h1>
            {subtitle && <p className="text-gray-400 text-sm">{subtitle}</p>}
          </div>
        </div>
        
        {/* Selector de caso */}
        {showCaseSelector && (
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg border transition-colors ${
                hasActiveCase()
                  ? 'bg-green-900/30 border-green-600 hover:bg-green-900/50'
                  : 'bg-yellow-900/30 border-yellow-600 hover:bg-yellow-900/50'
              }`}
            >
              <span className="text-xl">
                {hasActiveCase() ? '🎯' : '⚠️'}
              </span>
              <div className="text-left">
                {hasActiveCase() ? (
                  <>
                    <div className="font-medium text-white text-sm">{currentCase.name}</div>
                    <div className="text-xs text-gray-400">{currentCase.case_id}</div>
                  </>
                ) : (
                  <div className="text-yellow-400 text-sm font-medium">Sin caso seleccionado</div>
                )}
              </div>
              <svg className={`w-4 h-4 text-gray-400 transition-transform ${showDropdown ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Dropdown */}
            {showDropdown && (
              <div className="absolute right-0 mt-2 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
                <div className="p-3 border-b border-gray-700">
                  <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Caso Actual</div>
                  {hasActiveCase() ? (
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-white">{currentCase.name}</div>
                        <div className="text-xs text-gray-400">
                          Última actividad: {formatTime(lastActivity)}
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          clearCase();
                          setShowDropdown(false);
                        }}
                        className="text-red-400 hover:text-red-300 text-xs"
                      >
                        Cerrar
                      </button>
                    </div>
                  ) : (
                    <div className="text-yellow-400 text-sm">Selecciona un caso para continuar</div>
                  )}
                </div>
                
                <div className="p-2 max-h-64 overflow-y-auto">
                  <div className="text-xs text-gray-500 uppercase tracking-wider px-2 mb-2">Cambiar Caso</div>
                  {caseList.map((c) => (
                    <button
                      key={c.case_id}
                      onClick={() => {
                        selectCase(c);
                        setShowDropdown(false);
                      }}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded transition-colors ${
                        currentCase?.case_id === c.case_id
                          ? 'bg-blue-600/30 text-blue-300'
                          : 'hover:bg-gray-700 text-gray-300'
                      }`}
                    >
                      <span className="text-lg">
                        {c.type === 'malware' ? '🦠' : c.type === 'breach' ? '🚨' : '📋'}
                      </span>
                      <div className="text-left flex-1">
                        <div className="text-sm">{c.name}</div>
                        <div className="text-xs text-gray-500">{c.case_id}</div>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${
                        c.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-500'
                      }`}>
                        {c.status === 'active' ? '●' : '○'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Banner de advertencia si no hay caso */}
      {!hasActiveCase() && (
        <div className="mt-4 bg-yellow-900/30 border border-yellow-600 rounded-lg p-3 flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div className="flex-1">
            <div className="font-medium text-yellow-300">Caso Requerido</div>
            <div className="text-sm text-yellow-400/80">
              v4.4: Todas las operaciones forenses deben estar vinculadas a un caso. 
              Selecciona o crea un caso para continuar.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CaseHeader;
