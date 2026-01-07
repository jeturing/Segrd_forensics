/**
 * SEGRD Security - System Configuration Service
 * Obtiene configuración del sistema desde la API
 * Permite URLs dinámicas desde la base de datos
 */

// Configuración por defecto (fallback)
const DEFAULT_CONFIG = {
  api_url: 'http://localhost:9000',
  api_port: '9000',
  frontend_url: 'http://localhost:3000',
  frontend_port: '3000',
  ws_url: 'ws://localhost:9000/ws',
  cors_origins: 'http://localhost:3000'
};

// Cache de configuración
let cachedConfig = null;
let configPromise = null;

/**
 * Obtener la URL base de la API
 * Prioridad: 1) Variable de entorno VITE, 2) Config de BD, 3) Default
 */
export const getApiBaseUrl = () => {
  // Prioridad 1: Variable de entorno de Vite
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // Prioridad 2: Config cacheada
  if (cachedConfig?.api_url) {
    return cachedConfig.api_url;
  }
  
  // Prioridad 3: Default
  return DEFAULT_CONFIG.api_url;
};

/**
 * Obtener URL del WebSocket
 */
export const getWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  
  if (cachedConfig?.ws_url) {
    return cachedConfig.ws_url;
  }
  
  return DEFAULT_CONFIG.ws_url;
};

/**
 * Cargar configuración del sistema desde la API
 * Se llama una vez al inicio de la aplicación
 */
export const loadSystemConfig = async () => {
  // Si ya hay una promesa en curso, esperarla
  if (configPromise) {
    return configPromise;
  }
  
  // Si ya tenemos config cacheada, devolverla
  if (cachedConfig) {
    return cachedConfig;
  }
  
  configPromise = (async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || DEFAULT_CONFIG.api_url;
      const response = await fetch(`${baseUrl}/api/configuration/system`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.config) {
          cachedConfig = data.config;
          console.log('✅ System config loaded:', cachedConfig);
          return cachedConfig;
        }
      }
    } catch (error) {
      console.warn('⚠️ Could not load system config, using defaults:', error.message);
    }
    
    // Usar defaults si falla
    cachedConfig = DEFAULT_CONFIG;
    return cachedConfig;
  })();
  
  return configPromise;
};

/**
 * Obtener toda la configuración del sistema
 */
export const getSystemConfig = () => {
  return cachedConfig || DEFAULT_CONFIG;
};

/**
 * Forzar recarga de configuración
 */
export const reloadSystemConfig = async () => {
  cachedConfig = null;
  configPromise = null;
  return loadSystemConfig();
};

/**
 * Crear URL completa para endpoint de API
 */
export const apiUrl = (endpoint) => {
  const base = getApiBaseUrl();
  // Asegurar que no haya doble slash
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${cleanEndpoint}`;
};

export default {
  getApiBaseUrl,
  getWsUrl,
  loadSystemConfig,
  getSystemConfig,
  reloadSystemConfig,
  apiUrl,
  DEFAULT_CONFIG
};
