/**
 * Auth Context - React context for authentication state
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authService from '../services/auth';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check initial auth state
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (authService.isAuthenticated()) {
          const storedUser = authService.getCurrentUser();
          if (storedUser) {
            setUser(storedUser);
          } else {
            // Fetch fresh user data
            const profile = await authService.getProfile();
            setUser(profile);
          }
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        authService.logout();
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
  }, []);

  const login = useCallback(async (username, password, tenantId = null) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.login(username, password, tenantId);
      
      // Only set user if not requiring tenant selection
      if (!result.requiresTenantSelection) {
        setUser(result.user);
      }
      
      return result;
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Login failed';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await authService.logout();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const profile = await authService.getProfile();
      setUser(profile);
      return profile;
    } catch (err) {
      console.error('Profile refresh failed:', err);
      throw err;
    }
  }, []);

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    isAdmin: user?.is_global_admin || false,
    login,
    logout,
    refreshProfile,
    hasPermission: authService.hasPermission,
    hasRole: authService.hasRole,
    clearError: () => setError(null)
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
