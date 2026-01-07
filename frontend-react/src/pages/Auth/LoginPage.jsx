/**
 * Login Page - BRAC Authentication
 * SEGRD Security v4.5
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Eye, EyeOff, AlertCircle, Loader2, Building2, X, Check } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { authService } from '../../services/auth';

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, error, clearError } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');
  
  // Tenant selection modal state
  const [showTenantModal, setShowTenantModal] = useState(false);
  const [availableTenants, setAvailableTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [selectingTenant, setSelectingTenant] = useState(false);

  const from = location.state?.from?.pathname || '/dashboard';

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    clearError();
    setLocalError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');

    if (!formData.username.trim()) {
      setLocalError('El nombre de usuario es requerido');
      return;
    }
    if (!formData.password) {
      setLocalError('La contraseña es requerida');
      return;
    }

    try {
      const result = await login(formData.username, formData.password, null);
      
      // Check if tenant selection is required
      if (result?.requiresTenantSelection) {
        setAvailableTenants(result.availableTenants || []);
        setShowTenantModal(true);
        return;
      }
      
      navigate(from, { replace: true });
    } catch (err) {
      setLocalError(err.message);
    }
  };

  const handleTenantSelect = async (tenant) => {
    setSelectedTenant(tenant);
    setSelectingTenant(true);
    setLocalError('');
    
    try {
      await authService.selectTenant(tenant.tenant_id);
      setShowTenantModal(false);
      navigate(from, { replace: true });
    } catch (err) {
      setLocalError(err.response?.data?.detail || err.message || 'Error al seleccionar tenant');
    } finally {
      setSelectingTenant(false);
    }
  };

  const closeTenantModal = () => {
    setShowTenantModal(false);
    setAvailableTenants([]);
    setSelectedTenant(null);
    authService.clearPendingAuth();
  };

  // Get initials for tenant logo placeholder
  const getTenantInitials = (name) => {
    if (!name) return '?';
    const words = name.split(' ');
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  // Get color based on tenant name (consistent for same name)
  const getTenantColor = (name) => {
    const colors = [
      'bg-blue-600', 'bg-purple-600', 'bg-green-600', 'bg-orange-600',
      'bg-pink-600', 'bg-indigo-600', 'bg-cyan-600', 'bg-teal-600'
    ];
    let hash = 0;
    for (let i = 0; i < (name || '').length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-xl mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">SEGRD Security</h1>
          <p className="text-gray-400 mt-1">Sistema de Análisis Forense v4.5</p>
        </div>

        {/* Login Card */}
        <div className="bg-gray-800 rounded-xl shadow-xl p-8 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-6">Iniciar Sesión</h2>

          {displayError && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{displayError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Usuario
              </label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
                placeholder="Tu nombre de usuario"
                autoComplete="username"
                autoFocus
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors pr-10"
                  placeholder="Tu contraseña"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar Sesión'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-gray-700 text-center">
            <p className="text-sm text-gray-400">
              ¿Olvidaste tu contraseña?{' '}
              <a href="/forgot-password" className="text-blue-400 hover:text-blue-300">
                Recuperar acceso
              </a>
            </p>
          </div>
        </div>

        {/* Info */}
        <p className="text-center text-xs text-gray-500 mt-6">
          BRAC Authentication System • Multi-Tenant • RBAC
        </p>
      </div>

      {/* Tenant Selection Modal */}
      {showTenantModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-600/20 rounded-lg">
                  <Building2 className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Seleccionar Organización</h3>
                  <p className="text-sm text-gray-400">Elige con cuál organización deseas trabajar</p>
                </div>
              </div>
              <button 
                onClick={closeTenantModal}
                className="text-gray-400 hover:text-white transition-colors p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 max-h-80 overflow-y-auto">
              {localError && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm">{localError}</span>
                </div>
              )}
              
              <div className="space-y-2">
                {availableTenants.map((tenant) => (
                  <button
                    key={tenant.id || tenant.tenant_id}
                    onClick={() => handleTenantSelect(tenant)}
                    disabled={selectingTenant}
                    className={`w-full flex items-center gap-4 p-4 rounded-lg border transition-all ${
                      selectedTenant?.tenant_id === tenant.tenant_id
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-gray-700 hover:border-gray-600 hover:bg-gray-700/50'
                    } ${selectingTenant ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    {/* Tenant Logo/Initial */}
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-lg ${getTenantColor(tenant.name)}`}>
                      {getTenantInitials(tenant.name)}
                    </div>
                    
                    {/* Tenant Info */}
                    <div className="flex-1 text-left">
                      <div className="text-white font-medium">{tenant.name}</div>
                      <div className="text-sm text-gray-400">{tenant.subdomain || tenant.tenant_id}</div>
                    </div>

                    {/* Selection indicator */}
                    {selectingTenant && selectedTenant?.tenant_id === tenant.tenant_id ? (
                      <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                    ) : selectedTenant?.tenant_id === tenant.tenant_id ? (
                      <Check className="w-5 h-5 text-blue-400" />
                    ) : null}
                  </button>
                ))}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-700 bg-gray-800/50">
              <p className="text-xs text-gray-500 text-center">
                Puedes cambiar de organización en cualquier momento desde el menú superior
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoginPage;
