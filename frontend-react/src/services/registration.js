/**
 * Registration Service - Handles self-service registration flow
 */

import api from './api';

const REGISTRATION_SESSION_KEY = 'registration_session';

export const registrationService = {
  /**
   * Get available subscription plans
   */
  getPlans: async () => {
    const response = await api.get('/api/register/plans');
    return response.data.plans;
  },

  /**
   * Start registration process
   */
  startRegistration: async (data) => {
    const response = await api.post('/api/register/start', {
      email: data.email,
      full_name: data.fullName,
      company_name: data.companyName,
      phone: data.phone,
      referral_source: data.referralSource,
    });
    
    if (response.data.success) {
      // Store session token
      localStorage.setItem(REGISTRATION_SESSION_KEY, response.data.session_token);
    }
    
    return response.data;
  },

  /**
   * Select a plan
   */
  selectPlan: async (planId, billingPeriod = 'monthly') => {
    const sessionToken = localStorage.getItem(REGISTRATION_SESSION_KEY);
    if (!sessionToken) {
      throw new Error('No registration session found');
    }

    const response = await api.post('/api/register/select-plan', {
      session_token: sessionToken,
      plan_id: planId,
      billing_period: billingPeriod,
    });
    
    return response.data;
  },

  /**
   * Create account (final step)
   */
  createAccount: async (username, password) => {
    const sessionToken = localStorage.getItem(REGISTRATION_SESSION_KEY);
    if (!sessionToken) {
      throw new Error('No registration session found');
    }

    const response = await api.post('/api/register/create-account', {
      session_token: sessionToken,
      username,
      password,
    });
    
    if (response.data.success) {
      // Clear registration session
      localStorage.removeItem(REGISTRATION_SESSION_KEY);
    }
    
    return response.data;
  },

  /**
   * Create Stripe checkout session for paid plans
   */
  createCheckoutSession: async () => {
    const sessionToken = localStorage.getItem(REGISTRATION_SESSION_KEY);
    if (!sessionToken) {
      throw new Error('No registration session found');
    }

    const response = await api.post('/api/register/create-checkout-session', {
      session_token: sessionToken,
    });
    
    return response.data;
  },

  /**
   * Get current registration session status
   */
  getSessionStatus: async () => {
    const sessionToken = localStorage.getItem(REGISTRATION_SESSION_KEY);
    if (!sessionToken) {
      return null;
    }

    try {
      const response = await api.get(`/api/register/session/${sessionToken}`);
      return response.data;
    } catch (error) {
      // Session expired or not found
      localStorage.removeItem(REGISTRATION_SESSION_KEY);
      return null;
    }
  },

  /**
   * Clear registration session
   */
  clearSession: () => {
    localStorage.removeItem(REGISTRATION_SESSION_KEY);
  },

  /**
   * Check if there's an active registration session
   */
  hasActiveSession: () => {
    return !!localStorage.getItem(REGISTRATION_SESSION_KEY);
  },
};

export default registrationService;
