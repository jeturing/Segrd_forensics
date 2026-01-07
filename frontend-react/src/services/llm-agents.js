/**
 * LLM Agents Service - API Client for Ollama agents management
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8888';
const API_KEY = import.meta.env.VITE_API_KEY || 'mcp-forensics-dev-key';

class LLMAgentsService {
  constructor() {
    this.baseUrl = `${API_BASE_URL}/api/llm-agents`;
    this.headers = {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    };
  }

  /**
   * List all LLM agents, optionally filtered by tenant
   */
  async listAgents(tenantId = null) {
    const url = tenantId 
      ? `${this.baseUrl}?tenant_id=${tenantId}`
      : this.baseUrl;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: this.headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al listar agentes');
    }

    return response.json();
  }

  /**
   * Get specific agent details
   */
  async getAgent(agentName) {
    const response = await fetch(`${this.baseUrl}/${agentName}`, {
      method: 'GET',
      headers: this.headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al obtener agente');
    }

    return response.json();
  }

  /**
   * Create a new Ollama agent
   */
  async createAgent(agentData) {
    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(agentData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al crear agente');
    }

    return response.json();
  }

  /**
   * Update agent configuration
   */
  async updateAgent(agentName, updateData) {
    const response = await fetch(`${this.baseUrl}/${agentName}`, {
      method: 'PUT',
      headers: this.headers,
      body: JSON.stringify(updateData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al actualizar agente');
    }

    return response.json();
  }

  /**
   * Delete an agent
   */
  async deleteAgent(agentName, removeVolume = false) {
    const url = `${this.baseUrl}/${agentName}?remove_volume=${removeVolume}`;
    
    const response = await fetch(url, {
      method: 'DELETE',
      headers: this.headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al eliminar agente');
    }

    return response.json();
  }

  /**
   * Start a stopped agent
   */
  async startAgent(agentName) {
    const response = await fetch(`${this.baseUrl}/${agentName}/start`, {
      method: 'POST',
      headers: this.headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al iniciar agente');
    }

    return response.json();
  }

  /**
   * Stop a running agent
   */
  async stopAgent(agentName) {
    const response = await fetch(`${this.baseUrl}/${agentName}/stop`, {
      method: 'POST',
      headers: this.headers
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al detener agente');
    }

    return response.json();
  }

  /**
   * Pull a model in an agent
   */
  async pullModel(agentName, model = 'phi4-mini') {
    const response = await fetch(`${this.baseUrl}/${agentName}/pull-model`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ model })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al descargar modelo');
    }

    return response.json();
  }
}

export const llmAgentsService = new LLMAgentsService();
export default llmAgentsService;
