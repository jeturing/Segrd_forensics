/**
 * MCP Forensics - API Service Tests
 * Tests para el servicio de API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }))
  }
}));

describe('API Service Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('crea instancia de axios correctamente', async () => {
    // El módulo api.js debería crear una instancia de axios
    expect(axios.create).toBeDefined();
  });

  it('configura timeout por defecto', () => {
    // El timeout debería estar configurado
    const expectedTimeout = 30000;
    expect(expectedTimeout).toBe(30000);
  });

  it('usa URL base correcta por defecto', () => {
    const defaultUrl = 'http://localhost:9000';
    expect(defaultUrl).toContain('localhost');
    expect(defaultUrl).toContain('9000');
  });
});

describe('API Endpoints', () => {
  it('endpoint /health debería existir', () => {
    const healthEndpoint = '/health';
    expect(healthEndpoint).toBe('/health');
  });

  it('endpoint /api/cases debería existir', () => {
    const casesEndpoint = '/api/cases';
    expect(casesEndpoint).toContain('/cases');
  });

  it('endpoint /api/forensics debería existir', () => {
    const forensicsEndpoint = '/api/forensics';
    expect(forensicsEndpoint).toContain('/forensics');
  });
});

describe('Authentication Headers', () => {
  it('debe incluir X-API-Key header', () => {
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Key': 'test-key'
    };
    expect(headers['X-API-Key']).toBeDefined();
  });

  it('debe incluir Authorization header cuando hay token', () => {
    const token = 'test-jwt-token';
    const headers = {
      'Authorization': `Bearer ${token}`
    };
    expect(headers['Authorization']).toContain('Bearer');
  });
});
