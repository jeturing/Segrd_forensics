/**
 * Authentication Service - BRAC Login
 * Handles user authentication and token management
 */

import api from './api';

const TOKEN_KEY = 'auth_token';
const REFRESH_KEY = 'refresh_token';
const USER_KEY = 'auth_user';
const PENDING_AUTH_KEY = 'pending_auth';

export const authService = {
  /**
   * Login with username and password
   * Returns either full auth or tenant selection required
   */
  login: async (username, password, tenantId = null) => {
    const response = await api.post('/api/auth/login', {
      username,
      password,
      tenant_id: tenantId
    });
    
    const data = response.data;
    
    // Check if tenant selection is required
    if (data.requires_tenant_selection) {
      // Store pending auth for tenant selection
      localStorage.setItem(PENDING_AUTH_KEY, JSON.stringify({
        username,
        user: data.user,
        available_tenants: data.available_tenants
      }));
      
      return {
        requiresTenantSelection: true,
        user: data.user,
        availableTenants: data.available_tenants
      };
    }
    
    // Full auth successful
    const { access_token, refresh_token, user } = data;
    
    // Store tokens
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.removeItem(PENDING_AUTH_KEY);
    
    return { 
      requiresTenantSelection: false,
      user, 
      accessToken: access_token 
    };
  },

  /**
   * Complete login by selecting a tenant
   */
  selectTenant: async (tenantId) => {
    const pendingAuth = authService.getPendingAuth();
    if (!pendingAuth) {
      throw new Error('No pending authentication');
    }

    const response = await api.post('/api/auth/select-tenant', {
      username: pendingAuth.username,
      session_token: '', // Not used in current implementation
      tenant_id: tenantId
    });
    
    const { access_token, refresh_token, user } = response.data;
    
    // Store tokens
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.removeItem(PENDING_AUTH_KEY);
    
    return { user, accessToken: access_token };
  },

  /**
   * Get pending auth data (for tenant selection)
   */
  getPendingAuth: () => {
    const data = localStorage.getItem(PENDING_AUTH_KEY);
    if (!data) return null;
    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  },

  /**
   * Clear pending auth
   */
  clearPendingAuth: () => {
    localStorage.removeItem(PENDING_AUTH_KEY);
  },

  /**
   * Logout and clear tokens
   */
  logout: async () => {
    try {
      await api.post('/api/auth/logout');
    } catch (e) {
      // Ignore logout errors
    }
    
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(PENDING_AUTH_KEY);
  },

  /**
   * Refresh access token
   */
  refresh: async () => {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) {
      throw new Error('No refresh token');
    }

    const response = await api.post('/api/auth/refresh', {
      refresh_token: refreshToken
    });
    
    const { access_token, refresh_token: newRefresh } = response.data;
    
    localStorage.setItem(TOKEN_KEY, access_token);
    if (newRefresh) {
      localStorage.setItem(REFRESH_KEY, newRefresh);
    }
    
    return access_token;
  },

  /**
   * Get current user from storage
   */
  getCurrentUser: () => {
    const userStr = localStorage.getItem(USER_KEY);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  },

  /**
   * Get current access token
   */
  getToken: () => {
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return false;
    
    // Check if token is expired (basic check)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  },

  /**
   * Get user profile from API
   */
  getProfile: async () => {
    const response = await api.get('/api/auth/me');
    const user = response.data;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  },

  /**
   * Update user profile
   */
  updateProfile: async (data) => {
    const response = await api.put('/api/auth/me', data);
    const user = response.data;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  },

  /**
   * Change password
   */
  changePassword: async (currentPassword, newPassword) => {
    await api.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    });
  },

  /**
   * Check if user has permission
   */
  hasPermission: (permission) => {
    const user = authService.getCurrentUser();
    if (!user) return false;
    if (user.is_global_admin) return true;
    
    // Check roles permissions (simplified)
    const permissions = user.roles?.flatMap(r => r.permissions || []) || [];
    return permissions.includes(permission);
  },

  /**
   * Check if user has role
   * Global admins have access to all roles
   */
  hasRole: (roleName) => {
    const user = authService.getCurrentUser();
    if (!user) return false;
    
    // Global admins have all roles
    if (user.is_global_admin) return true;
    
    return user.roles?.some(r => r.name === roleName || r === roleName) || false;
  },

  // ============================================================================
  // ADMIN USER MANAGEMENT
  // ============================================================================

  /**
   * Create a new user (admin only)
   */
  createUser: async (userData) => {
    const response = await api.post('/api/auth/admin/users', userData);
    return response.data;
  },

  /**
   * Get user by ID (admin only)
   */
  getUserById: async (userId) => {
    const response = await api.get(`/api/auth/admin/users/${userId}`);
    return response.data;
  },

  /**
   * List all users (admin only)
   */
  listUsers: async (tenantId = null) => {
    const url = tenantId 
      ? `/api/auth/admin/users?tenant_id=${tenantId}`
      : '/api/auth/admin/users';
    const response = await api.get(url);
    return response.data;
  },

  /**
   * Activate a user (admin only)
   */
  activateUser: async (userId) => {
    const response = await api.post(`/api/auth/admin/users/${userId}/activate`);
    return response.data;
  },

  /**
   * Deactivate a user (admin only)
   */
  deactivateUser: async (userId) => {
    const response = await api.post(`/api/auth/admin/users/${userId}/deactivate`);
    return response.data;
  },

  /**
   * Assign role to user (admin only)
   */
  assignRole: async (userId, role) => {
    const response = await api.put(`/api/auth/admin/users/${userId}/role`, { role });
    return response.data;
  }
};

export default authService;
