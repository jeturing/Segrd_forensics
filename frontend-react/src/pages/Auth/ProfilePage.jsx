/**
 * Profile Page - User Profile Management
 * SEGRD Security v4.5
 */

import React, { useState, useEffect } from 'react';
import { 
  User, Mail, Phone, Building, Shield, Key, Clock, 
  Save, AlertCircle, CheckCircle, Loader2, LogOut
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import authService from '../../services/auth';
import { toast } from 'react-toastify';

const ProfilePage = () => {
  const { user, logout, refreshProfile } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [profileData, setProfileData] = useState({
    full_name: '',
    phone: '',
    department: '',
    title: ''
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name || '',
        phone: user.phone || '',
        department: user.department || '',
        title: user.title || ''
      });
    }
  }, [user]);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authService.updateProfile(profileData);
      await refreshProfile();
      toast.success('Perfil actualizado correctamente');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error actualizando perfil');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    
    if (passwordData.new_password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    setLoading(true);
    try {
      await authService.changePassword(
        passwordData.current_password,
        passwordData.new_password
      );
      toast.success('Contraseña cambiada correctamente');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error cambiando contraseña');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <User className="w-8 h-8" />
            Mi Perfil
          </h1>
          <p className="text-gray-400 mt-1">Gestiona tu información y seguridad</p>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Cerrar Sesión
        </button>
      </div>

      {/* User Info Card */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 bg-blue-600 rounded-full flex items-center justify-center text-3xl font-bold text-white">
            {user.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">{user.full_name || user.username}</h2>
            <p className="text-gray-400">{user.email}</p>
            <div className="flex items-center gap-4 mt-2">
              {user.is_global_admin && (
                <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  Admin Global
                </span>
              )}
              {user.roles?.map(role => (
                <span key={role.id} className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                  {role.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('profile')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'profile'
                ? 'text-blue-400 border-blue-400'
                : 'text-gray-400 border-transparent hover:text-gray-300'
            }`}
          >
            <User className="w-4 h-4 inline mr-2" />
            Información
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'security'
                ? 'text-blue-400 border-blue-400'
                : 'text-gray-400 border-transparent hover:text-gray-300'
            }`}
          >
            <Key className="w-4 h-4 inline mr-2" />
            Seguridad
          </button>
          <button
            onClick={() => setActiveTab('sessions')}
            className={`px-4 py-3 font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'sessions'
                ? 'text-blue-400 border-blue-400'
                : 'text-gray-400 border-transparent hover:text-gray-300'
            }`}
          >
            <Clock className="w-4 h-4 inline mr-2" />
            Sesiones
          </button>
        </nav>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Información Personal</h3>
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Nombre Completo
                </label>
                <input
                  type="text"
                  name="full_name"
                  value={profileData.full_name}
                  onChange={handleProfileChange}
                  className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Teléfono
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={profileData.phone}
                  onChange={handleProfileChange}
                  className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Departamento
                </label>
                <input
                  type="text"
                  name="department"
                  value={profileData.department}
                  onChange={handleProfileChange}
                  className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Cargo
                </label>
                <input
                  type="text"
                  name="title"
                  value={profileData.title}
                  onChange={handleProfileChange}
                  className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end pt-4">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white rounded-lg flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Guardar Cambios
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Cambiar Contraseña</h3>
          <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-md">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Contraseña Actual
              </label>
              <input
                type="password"
                name="current_password"
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Nueva Contraseña
              </label>
              <input
                type="password"
                name="new_password"
                value={passwordData.new_password}
                onChange={handlePasswordChange}
                className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Confirmar Contraseña
              </label>
              <input
                type="password"
                name="confirm_password"
                value={passwordData.confirm_password}
                onChange={handlePasswordChange}
                className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex justify-end pt-4">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white rounded-lg flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
                Cambiar Contraseña
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Sessions Tab */}
      {activeTab === 'sessions' && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Sesiones Activas</h3>
          <div className="space-y-3">
            <div className="p-4 bg-gray-700/50 rounded-lg border border-gray-600">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white font-medium">Sesión Actual</p>
                  <p className="text-sm text-gray-400">
                    Último acceso: {user.last_login ? new Date(user.last_login).toLocaleString('es-ES') : 'N/A'}
                  </p>
                </div>
                <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  Activa
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
