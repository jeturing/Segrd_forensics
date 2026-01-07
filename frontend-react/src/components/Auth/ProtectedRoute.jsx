/**
 * Protected Route - Requires authentication
 * Supports: requiredPermission, requiredRole, requiredGlobalAdmin
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Loader2, ShieldAlert } from 'lucide-react';

const ProtectedRoute = ({ 
  children, 
  requiredPermission = null, 
  requiredRole = null,
  requiredGlobalAdmin = false 
}) => {
  const { isAuthenticated, loading, hasPermission, hasRole, isAdmin } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto" />
          <p className="text-gray-400 mt-4">Verificando autenticación...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check Global Admin requirement
  if (requiredGlobalAdmin && !isAdmin) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <ShieldAlert className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-yellow-500">Acceso Restringido</h1>
          <p className="text-gray-400 mt-2">
            Esta sección está reservada para Administradores Globales.
          </p>
          <p className="text-gray-500 text-sm mt-4">
            Si necesitas acceso, contacta al administrador del sistema.
          </p>
          <button
            onClick={() => window.history.back()}
            className="mt-6 px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
          >
            Volver
          </button>
        </div>
      </div>
    );
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-red-500">Acceso Denegado</h1>
          <p className="text-gray-400 mt-2">No tienes permisos para acceder a esta página.</p>
        </div>
      </div>
    );
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-red-500">Acceso Denegado</h1>
          <p className="text-gray-400 mt-2">Se requiere rol: {requiredRole}</p>
        </div>
      </div>
    );
  }

  return children;
};

export default ProtectedRoute;
