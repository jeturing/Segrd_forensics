/**
 * Global Users Management - Manage all users across tenants
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, Search, Plus, Edit, Trash2, Shield, Building2,
  Mail, Phone, Calendar, MoreVertical, Filter, Download,
  CheckCircle, XCircle, Clock, Crown, ArrowLeft
} from 'lucide-react';
import api from '../../services/api';

export default function GlobalUsersPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTenant, setFilterTenant] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [tenants, setTenants] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchUsers();
    fetchTenants();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/api/admin/global/users');
      if (response.data?.users) {
        setUsers(response.data.users);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
      // Mock data
      setUsers([
        { id: '1', username: 'admin', email: 'admin@empresa.com', full_name: 'Admin User', tenant: 'Jeturing Labs', is_active: true, is_global_admin: true, created_at: '2025-01-15', last_login: '2025-12-29' },
        { id: '2', username: 'john.doe', email: 'john@acme.com', full_name: 'John Doe', tenant: 'Acme Corp', is_active: true, is_global_admin: false, created_at: '2025-02-20', last_login: '2025-12-28' },
        { id: '3', username: 'jane.smith', email: 'jane@tech.com', full_name: 'Jane Smith', tenant: 'Tech Solutions', is_active: true, is_global_admin: false, created_at: '2025-03-10', last_login: '2025-12-27' },
        { id: '4', username: 'bob.wilson', email: 'bob@startup.com', full_name: 'Bob Wilson', tenant: 'StartupXYZ', is_active: false, is_global_admin: false, created_at: '2025-04-05', last_login: '2025-11-15' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchTenants = async () => {
    try {
      const response = await api.get('/api/admin/global/tenants');
      if (response.data?.tenants) {
        setTenants(response.data.tenants);
      }
    } catch (error) {
      setTenants([
        { id: '1', name: 'Jeturing Labs' },
        { id: '2', name: 'Acme Corp' },
        { id: '3', name: 'Tech Solutions' },
        { id: '4', name: 'StartupXYZ' }
      ]);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.full_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTenant = filterTenant === 'all' || user.tenant === filterTenant;
    const matchesStatus = filterStatus === 'all' || 
                         (filterStatus === 'active' && user.is_active) ||
                         (filterStatus === 'inactive' && !user.is_active) ||
                         (filterStatus === 'admin' && user.is_global_admin);
    return matchesSearch && matchesTenant && matchesStatus;
  });

  const toggleUserStatus = async (userId, currentStatus) => {
    try {
      await api.patch(`/api/admin/global/users/${userId}`, { is_active: !currentStatus });
      setUsers(users.map(u => u.id === userId ? { ...u, is_active: !currentStatus } : u));
    } catch (error) {
      console.error('Error updating user:', error);
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('¿Estás seguro de eliminar este usuario?')) return;
    try {
      await api.delete(`/api/admin/global/users/${userId}`);
      setUsers(users.filter(u => u.id !== userId));
    } catch (error) {
      console.error('Error deleting user:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/admin')}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Users className="w-7 h-7 text-blue-400" />
              Gestión de Usuarios
            </h1>
            <p className="text-gray-400 text-sm">Administrar usuarios de todos los tenants</p>
          </div>
        </div>
        <button 
          onClick={() => navigate('/admin/users/new')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nuevo Usuario
        </button>
      </div>

      {/* Filters */}
      <div className="bg-gray-800 rounded-xl p-4 mb-6 border border-gray-700">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por nombre, email o usuario..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <select
            value={filterTenant}
            onChange={(e) => setFilterTenant(e.target.value)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="all">Todos los Tenants</option>
            {tenants.map(t => (
              <option key={t.id} value={t.name}>{t.name}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="all">Todos los Estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
            <option value="admin">Global Admins</option>
          </select>
          <button className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300 transition-colors">
            <Download className="w-4 h-4" />
            Exportar
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700/50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Usuario</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Tenant</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Estado</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Último Login</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Creado</th>
              <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {loading ? (
              <tr>
                <td colSpan="6" className="px-6 py-12 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-12 text-center text-gray-400">
                  No se encontraron usuarios
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-gray-700/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold">
                        {user.full_name.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">{user.full_name}</span>
                          {user.is_global_admin && (
                            <Crown className="w-4 h-4 text-yellow-400" title="Global Admin" />
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                          <Mail className="w-3 h-3" />
                          {user.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-300">{user.tenant}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {user.is_active ? (
                      <span className="flex items-center gap-1 text-green-400">
                        <CheckCircle className="w-4 h-4" />
                        Activo
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-400">
                        <XCircle className="w-4 h-4" />
                        Inactivo
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm">
                    {user.last_login || 'Nunca'}
                  </td>
                  <td className="px-6 py-4 text-gray-400 text-sm">
                    {user.created_at}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button 
                        onClick={() => navigate(`/admin/users/${user.id}`)}
                        className="p-2 hover:bg-gray-600 rounded-lg transition-colors"
                        title="Editar"
                      >
                        <Edit className="w-4 h-4 text-gray-400" />
                      </button>
                      <button 
                        onClick={() => toggleUserStatus(user.id, user.is_active)}
                        className="p-2 hover:bg-gray-600 rounded-lg transition-colors"
                        title={user.is_active ? 'Desactivar' : 'Activar'}
                      >
                        {user.is_active ? (
                          <XCircle className="w-4 h-4 text-yellow-400" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        )}
                      </button>
                      <button 
                        onClick={() => deleteUser(user.id)}
                        className="p-2 hover:bg-red-600/20 rounded-lg transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
        <span>Mostrando {filteredUsers.length} de {users.length} usuarios</span>
        <div className="flex gap-2">
          <button className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700">Anterior</button>
          <button className="px-3 py-1 bg-blue-600 text-white rounded">1</button>
          <button className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700">2</button>
          <button className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700">Siguiente</button>
        </div>
      </div>
    </div>
  );
}
