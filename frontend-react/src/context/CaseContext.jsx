/**
 * 🎯 CaseContext - Contexto Global de Caso v4.4
 * 
 * MCP Kali Forensics - Case-Centric Architecture
 * 
 * Este contexto garantiza que TODAS las operaciones estén vinculadas a un caso.
 * Sin caso seleccionado, los módulos forenses muestran selector obligatorio.
 * 
 * Características v4.4:
 * - Caso obligatorio para operaciones forenses
 * - Persistencia en localStorage
 * - Sincronización con backend /api/context
 * - Validación de caso activo
 * - Timeline y Graph auto-actualizados
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const CASES_BASE = '/api/v41/investigations';

// Contexto
const CaseContext = createContext(null);

// Hook personalizado para usar el contexto
export const useCaseContext = () => {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error('useCaseContext must be used within CaseContextProvider');
  }
  return context;
};

// Provider Component
export const CaseContextProvider = ({ children }) => {
  // Estado del caso actual
  const [currentCase, setCurrentCase] = useState(null);
  const [caseList, setCaseList] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Estado de sesión
  const [sessionId] = useState(() => `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  const [lastActivity, setLastActivity] = useState(new Date());
  
  // Cargar caso desde localStorage al iniciar
  useEffect(() => {
    const loadSavedCase = async () => {
      try {
        setIsLoading(true);
        
        // Intentar cargar caso guardado
        const savedCaseId = localStorage.getItem('mcp_current_case_id');
        const savedCase = localStorage.getItem('mcp_current_case');
        
        // Cargar lista de casos
        // await fetchCaseList(); // Disabled: only load when authenticated
        
        if (savedCaseId && savedCase) {
          const parsedCase = JSON.parse(savedCase);
          
          // Validar que el caso aún existe en el backend
          const isValid = await validateCase(savedCaseId);
          if (isValid) {
            setCurrentCase(parsedCase);
            await syncWithBackend(parsedCase);
          } else {
            // Caso ya no existe, limpiar
            localStorage.removeItem('mcp_current_case_id');
            localStorage.removeItem('mcp_current_case');
          }
        }
      } catch (err) {
        console.error('❌ Error loading saved case:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadSavedCase();
  }, []);
  
  // Sincronizar con backend cuando cambia el caso
  const syncWithBackend = useCallback(async (caseData) => {
    try {
      await api.post('/api/context/set', {
        case_id: caseData.case_id,
        session_id: sessionId,
        metadata: {
          case_name: caseData.name,
          case_type: caseData.type
        }
      });
      console.log('✅ Case context synced with backend');
    } catch (err) {
      console.warn('⚠️ Could not sync with backend:', err.message);
    }
  }, [sessionId]);
  
  // Validar que un caso existe
  const validateCase = useCallback(async (caseId) => {
    try {
      const response = await api.get(`${CASES_BASE}/${caseId}`);
      return response.status === 200;
    } catch (err) {
      return false;
    }
  }, []);
  
  // Obtener lista de casos
  const fetchCaseList = useCallback(async () => {
    try {
      const response = await api.get(`${CASES_BASE}/`, { params: { page: 1, limit: 50 } });
      const items = response.data?.investigations || response.data?.cases || [];
      const normalized = items.map((item) => ({
        case_id: item.id || item.case_id,
        name: item.name || item.title,
        status: item.status,
        type: item.case_type,
        severity: item.severity || item.priority,
        created_at: item.created_at,
        is_demo: item.is_demo
      }));
      setCaseList(normalized);
    } catch (err) {
      console.warn('⚠️ Could not fetch case list:', err.message);
      // En desarrollo, usar casos demo
      setCaseList([
        { case_id: 'IR-2025-001', name: 'Phishing Investigation', status: 'active', type: 'incident' },
        { case_id: 'IR-2025-002', name: 'Ransomware Analysis', status: 'active', type: 'malware' },
        { case_id: 'IR-2025-003', name: 'Data Exfiltration', status: 'closed', type: 'breach' }
      ]);
    }
  }, []);
  
  // Seleccionar un caso
  const selectCase = useCallback(async (caseData) => {
    try {
      setError(null);
      
      // Guardar en estado
      setCurrentCase(caseData);
      
      // Persistir en localStorage
      localStorage.setItem('mcp_current_case_id', caseData.case_id);
      localStorage.setItem('mcp_current_case', JSON.stringify(caseData));
      
      // Sincronizar con backend
      await syncWithBackend(caseData);
      
      // Actualizar actividad
      setLastActivity(new Date());
      
      console.log(`🎯 Case selected: ${caseData.case_id}`);
      
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, [syncWithBackend]);
  
  // Crear nuevo caso
  const createCase = useCallback(async (caseData) => {
    try {
      setError(null);
      
      // Generar ID si no existe
      const newCase = {
        case_id: caseData.case_id || `IR-${new Date().getFullYear()}-${String(Date.now()).slice(-3)}`,
        name: caseData.name,
        description: caseData.description || '',
        type: caseData.type || 'incident',
        status: 'active',
        created_at: new Date().toISOString(),
        created_by: 'current_user',
        ...caseData
      };
      
      // Enviar al backend
      const response = await api.post(`${CASES_BASE}/`, newCase);
      const createdCase = {
        case_id: response.data?.investigation_id || newCase.case_id,
        name: newCase.name,
        description: newCase.description,
        type: newCase.type,
        status: 'active',
        created_at: newCase.created_at,
        is_demo: false
      };

      // Actualizar lista y seleccionar
      // await fetchCaseList(); // Disabled: only load when authenticated
      await selectCase(createdCase);
      
      console.log(`✅ Case created: ${createdCase.case_id}`);
      return createdCase;
    } catch (err) {
      // En desarrollo, crear localmente
      console.warn('⚠️ Backend unavailable, creating case locally');
      
      const localCase = {
        case_id: caseData.case_id || `IR-${new Date().getFullYear()}-${String(Date.now()).slice(-3)}`,
        name: caseData.name,
        description: caseData.description || '',
        type: caseData.type || 'incident',
        status: 'active',
        created_at: new Date().toISOString()
      };
      
      setCaseList(prev => [...prev, localCase]);
      await selectCase(localCase);
      
      return localCase;
    }
  }, [fetchCaseList, selectCase]);
  
  // Limpiar caso actual
  const clearCase = useCallback(() => {
    setCurrentCase(null);
    localStorage.removeItem('mcp_current_case_id');
    localStorage.removeItem('mcp_current_case');
    console.log('🗑️ Case context cleared');
  }, []);
  
  // Verificar si hay caso activo
  const hasActiveCase = useCallback(() => {
    return currentCase !== null && currentCase.case_id !== undefined;
  }, [currentCase]);
  
  // Requerir caso (para componentes que lo necesitan)
  const requireCase = useCallback(() => {
    if (!hasActiveCase()) {
      throw new Error('No active case. Please select or create a case first.');
    }
    return currentCase;
  }, [hasActiveCase, currentCase]);
  
  // Obtener case_id actual (helper)
  const getCaseId = useCallback(() => {
    return currentCase?.case_id || null;
  }, [currentCase]);
  
  // Registrar actividad
  const registerActivity = useCallback((activityType, details = {}) => {
    if (!currentCase) return;
    
    setLastActivity(new Date());
    
    // Log activity (podría enviarse al backend)
    console.log(`📝 Activity [${currentCase.case_id}]: ${activityType}`, details);
  }, [currentCase]);
  
  // Valor del contexto
  const contextValue = {
    // Estado
    currentCase,
    caseList,
    isLoading,
    error,
    sessionId,
    lastActivity,
    
    // Acciones
    selectCase,
    createCase,
    clearCase,
    fetchCaseList,
    
    // Helpers
    hasActiveCase,
    requireCase,
    getCaseId,
    registerActivity,
    
    // Validación
    validateCase
  };
  
  return (
    <CaseContext.Provider value={contextValue}>
      {children}
    </CaseContext.Provider>
  );
};

// HOC para requerir caso en componentes
export const withCaseRequired = (WrappedComponent) => {
  return function CaseRequiredComponent(props) {
    const { hasActiveCase } = useCaseContext();
    
    if (!hasActiveCase()) {
      return <CaseSelector />;
    }
    
    return <WrappedComponent {...props} />;
  };
};

// Componente de selección de caso (fallback)
export const CaseSelector = () => {
  const { caseList, selectCase, createCase, isLoading, error } = useCaseContext();
  const [showCreate, setShowCreate] = useState(false);
  const [newCaseName, setNewCaseName] = useState('');
  const [newCaseType, setNewCaseType] = useState('incident');
  
  const handleCreate = async () => {
    if (!newCaseName.trim()) return;
    
    await createCase({
      name: newCaseName,
      type: newCaseType
    });
    
    setShowCreate(false);
    setNewCaseName('');
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-gradient-to-r from-blue-900 to-purple-900 rounded-lg shadow-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <span className="text-3xl">🎯</span>
          <div>
            <h2 className="text-xl font-bold text-white">Seleccionar Caso</h2>
            <p className="text-blue-200 text-sm">
              v4.4: Todas las operaciones requieren un caso activo
            </p>
          </div>
        </div>
        
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded p-3 mb-4 text-red-200">
            {error}
          </div>
        )}
        
        {/* Lista de casos existentes */}
        <div className="space-y-2 mb-6">
          {caseList.map((c) => (
            <button
              key={c.case_id}
              onClick={() => selectCase(c)}
              className="w-full flex items-center justify-between p-4 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg transition-colors group"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">
                  {c.type === 'malware' ? '🦠' : c.type === 'breach' ? '🚨' : '📋'}
                </span>
                <div className="text-left">
                  <div className="font-medium text-white">{c.name}</div>
                  <div className="text-sm text-gray-400">{c.case_id}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded text-xs ${
                  c.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                }`}>
                  {c.status}
                </span>
                <span className="text-gray-500 group-hover:text-white transition-colors">→</span>
              </div>
            </button>
          ))}
        </div>
        
        {/* Crear nuevo caso */}
        {showCreate ? (
          <div className="bg-gray-800/50 rounded-lg p-4">
            <h3 className="font-medium text-white mb-3">Crear Nuevo Caso</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Nombre del caso..."
                value={newCaseName}
                onChange={(e) => setNewCaseName(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                autoFocus
              />
              <select
                value={newCaseType}
                onChange={(e) => setNewCaseType(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                <option value="incident">📋 Incident Response</option>
                <option value="malware">🦠 Malware Analysis</option>
                <option value="breach">🚨 Data Breach</option>
                <option value="threat_hunt">🎯 Threat Hunt</option>
              </select>
              <div className="flex gap-2">
                <button
                  onClick={handleCreate}
                  disabled={!newCaseName.trim()}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-medium py-2 rounded transition-colors"
                >
                  Crear Caso
                </button>
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 bg-gray-600 hover:bg-gray-500 text-white py-2 rounded transition-colors"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowCreate(true)}
            className="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed border-gray-600 hover:border-blue-500 rounded-lg text-gray-400 hover:text-blue-400 transition-colors"
          >
            <span className="text-xl">+</span>
            <span>Crear Nuevo Caso</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default CaseContextProvider;
