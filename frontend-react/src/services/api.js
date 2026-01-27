import axios from 'axios';

// Normaliza la URL base y evita duplicar el sufijo /api
const normalizeBaseUrl = (url) => {
  if (!url) return '';
  let normalized = url.trim();
  if (normalized.endsWith('/')) {
    normalized = normalized.slice(0, -1);
  }
  if (normalized.toLowerCase().endsWith('/api')) {
    normalized = normalized.slice(0, -4);
  }
  return normalized;
};

const envApiUrl = normalizeBaseUrl(import.meta.env.VITE_API_URL);
const inferredBaseUrl = typeof window !== 'undefined'
  ? normalizeBaseUrl(`${window.location.protocol}//${window.location.host}`)
  : '';
// Use relative /api path for production deployment behind proxy (nginx/Kong)
// This ensures frontend calls API at same origin as served from
const API_BASE_URL = envApiUrl || inferredBaseUrl || '/api';

console.log(`🔧 API Configured Base URL: ${API_BASE_URL}`);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000
});

// Request interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  // Usa la misma API key que el backend por defecto para evitar 401 al cargar el dashboard
  const apiKey = localStorage.getItem('apiKey') ||
    import.meta.env.VITE_API_KEY ||
    'mcp-forensics-dev-key';

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }

  console.log(`📡 API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`❌ API Error: ${error.response?.status || 'Network'} ${error.config?.url}`, error.message);
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export { API_BASE_URL };
export default api;
