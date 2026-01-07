/**
 * 🔗 Servicio de integración Threat Intelligence con Casos
 * Almacena resultados de threat intel en el caso y los vincula al grafo de ataque
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:9000';
const API_KEY = localStorage.getItem('apiKey') || import.meta.env.VITE_API_KEY || 'mcp-forensics-dev-key';

// Axios instance con headers comunes
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  }
});

export const threatIntelCaseService = {
  /**
   * Ejecuta un análisis de Threat Intelligence y lo guarda en el caso
   */
  async analyzeAndSaveToCase(
    caseId,
    analysisType, // 'ip' | 'email' | 'domain' | 'url'
    target,
    sources = null
  ) {
    try {
      // 1. Ejecutar análisis en threat intel API
      const analysisResult = await this.runThreatIntelAnalysis(
        analysisType,
        target,
        sources
      );

      // 2. Guardar en el backend del caso
      const savedResult = await api.post(
        `/forensics/case/${caseId}/threat-intel`,
        {
          analysis_type: analysisType,
          target: target,
          result: analysisResult,
          threat_level: this.calculateThreatLevel(analysisType, analysisResult),
          indicators: this.extractIndicators(analysisType, analysisResult),
          metadata: {
            sources: sources || [],
            analyzed_at: new Date().toISOString()
          }
        }
      );

      return {
        success: true,
        analysis: analysisResult,
        saved: savedResult.data
      };
    } catch (error) {
      console.error('Error analyzing and saving to case:', error);
      throw error;
    }
  },

  /**
   * Calcula el nivel de amenaza basado en el resultado
   */
  calculateThreatLevel(analysisType, result) {
    if (analysisType === 'ip') {
      const riskScore = result.risk_score || 0;
      if (riskScore >= 80) return 'critical';
      if (riskScore >= 60) return 'high';
      if (riskScore >= 40) return 'medium';
      return 'low';
    }
    if (analysisType === 'email') {
      const breachCount = result.breaches_found || 0;
      if (breachCount >= 5) return 'critical';
      if (breachCount >= 3) return 'high';
      if (breachCount >= 1) return 'medium';
      return 'low';
    }
    if (analysisType === 'url') {
      const detections = result.malicious_detections || 0;
      if (detections >= 30) return 'critical';
      if (detections >= 10) return 'high';
      if (detections >= 1) return 'medium';
      return 'low';
    }
    return 'medium';
  },

  /**
   * Extrae indicadores del resultado
   */
  extractIndicators(analysisType, result) {
    const indicators = [];
    
    if (analysisType === 'ip') {
      if (result.ports?.length) indicators.push(`${result.ports.length} puertos abiertos`);
      if (result.vulns?.length) indicators.push(`${result.vulns.length} vulnerabilidades`);
      if (result.malicious) indicators.push('Detectado como malicioso');
    }
    if (analysisType === 'email') {
      if (result.breaches_found) indicators.push(`${result.breaches_found} brechas encontradas`);
      if (result.exposed_data?.length) indicators.push(`Datos expuestos: ${result.exposed_data.join(', ')}`);
    }
    if (analysisType === 'url') {
      if (result.malicious_detections) indicators.push(`${result.malicious_detections} detecciones maliciosas`);
      if (result.phishing) indicators.push('Phishing detectado');
    }
    
    return indicators;
  },

  /**
   * Ejecuta análisis en Threat Intel API
   */
  async runThreatIntelAnalysis(analysisType, target, sources) {
    const endpoints = {
      ip: '/api/threat-intel/ip/lookup',
      email: '/api/threat-intel/email/check',
      domain: '/api/threat-intel/domain/lookup',
      url: '/api/threat-intel/url/scan'
    };

    const endpoint = endpoints[analysisType];
    if (!endpoint) {
      throw new Error(`Unknown analysis type: ${analysisType}`);
    }

    const payload = {
      [analysisType === 'ip' ? 'ip' : 
       analysisType === 'email' ? 'email' :
       analysisType === 'domain' ? 'domain' : 'url']: target
    };

    if (sources && analysisType === 'ip') {
      payload.sources = sources;
    }

    const response = await api.post(endpoint, payload);
    return response.data;
  },

  /**
   * Ejecuta un playbook SOAR y lo guarda en el caso
   */
  async executePlaybookAndSaveToCase(caseId, playbookName, target, investigationId) {
    try {
      // 1. Ejecutar playbook
      const playbookResult = await this.executePlaybook(
        playbookName,
        target,
        investigationId
      );

      // 2. Crear nodos para cada paso del playbook
      const nodes = this.createPlaybookNodes(playbookName, target, playbookResult);

      // 3. Guardar en caso
      const savedPlaybook = await this.savePlaybookToCase(
        caseId,
        playbookName,
        target,
        playbookResult,
        nodes
      );

      return {
        success: true,
        playbook: playbookResult,
        nodes: nodes,
        saved: savedPlaybook
      };
    } catch (error) {
      console.error('Error executing playbook:', error);
      throw error;
    }
  },

  /**
   * Ejecuta playbook SOAR
   */
  async executePlaybook(playbookName, target, investigationId) {
    const response = await api.post(
      `/api/threat-intel/playbooks/execute`,
      {
        playbook_name: playbookName,
        target: target,
        investigation_id: investigationId || `INV-${Date.now()}`
      }
    );
    return response.data;
  },

  /**
   * Crea nodo de Threat Intel para el grafo
   */
  createThreatIntelNode(analysisType, target, result) {
    const typeMap = {
      ip: 'threat_ip',
      email: 'threat_email',
      domain: 'threat_domain',
      url: 'threat_url'
    };

    // Extraer información relevante del resultado
    let threatLevel = 'low';
    let indicators = [];
    let metadata = {};

    if (analysisType === 'ip') {
      const riskScore = result.success ? (result.risk_score || 0) : 0;
      threatLevel = riskScore >= 60 ? 'critical' : riskScore >= 40 ? 'high' : 'medium';
      indicators = result.indicators || [];
      metadata = {
        organization: result.organization,
        country: result.country,
        ports: result.ports,
        services: result.services
      };
    } else if (analysisType === 'email') {
      const breachCount = result.breaches_found || 0;
      threatLevel = breachCount >= 5 ? 'critical' : breachCount >= 3 ? 'high' : 'medium';
      indicators = result.breaches?.map(b => b.name) || [];
      metadata = {
        breaches_found: breachCount,
        exposed_data: result.exposed_data
      };
    } else if (analysisType === 'domain') {
      threatLevel = 'medium';
      indicators = result.dns_records?.length ? ['DNS records found'] : [];
      metadata = {
        dns_records: result.dns_records,
        emails_found: result.emails_found
      };
    } else if (analysisType === 'url') {
      const detections = result.malicious_detections || 0;
      threatLevel = detections >= 30 ? 'critical' : detections >= 10 ? 'high' : 'medium';
      indicators = ['Malware detected', 'Phishing indicators'].filter(() => detections > 0);
      metadata = {
        detections: detections,
        threat_type: result.threat_type
      };
    }

    return {
      id: `threat_${analysisType}_${target.replace(/[^a-zA-Z0-9]/g, '_')}`,
      label: target,
      type: typeMap[analysisType],
      threatLevel,
      indicators,
      metadata,
      timestamp: new Date().toISOString(),
      analysisType
    };
  },

  /**
   * Crea nodos de playbook SOAR para el grafo
   */
  createPlaybookNodes(playbookName, target, result) {
    const nodes = [];

    // Nodo principal del playbook
    const mainNodeId = `playbook_${playbookName}_${Date.now()}`;
    nodes.push({
      id: mainNodeId,
      label: `${playbookName.replace(/_/g, ' ')} - ${target}`,
      type: 'playbook',
      riskScore: result.risk_score || result.exposure_level,
      recommendations: result.recommendations,
      timestamp: result.timestamp || new Date().toISOString()
    });

    // Nodos para cada paso del playbook
    if (result.steps && Array.isArray(result.steps)) {
      result.steps.forEach((step, idx) => {
        nodes.push({
          id: `step_${mainNodeId}_${idx}`,
          label: `Step ${step.step}: ${step.name}`,
          type: 'playbook_step',
          status: step.status,
          parentId: mainNodeId,
          data: step.data
        });
      });
    }

    return nodes;
  },

  /**
   * Guarda análisis en la base de datos del caso (localStorage temporalmente)
   */
  async saveToCaseDatabase(caseId, analysisType, target, result, node) {
    try {
      // Guardar en localStorage para demo
      // En producción: POST a /api/cases/{caseId}/threat-intel
      const caseKey = `case_${caseId}_threat_intel`;
      const existingData = JSON.parse(localStorage.getItem(caseKey) || '[]');

      const analysis = {
        id: node.id,
        type: analysisType,
        target,
        result,
        node,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };

      existingData.push(analysis);
      localStorage.setItem(caseKey, JSON.stringify(existingData));

      return {
        caseId,
        analysisId: node.id,
        saved: true
      };
    } catch (error) {
      console.error('Error saving to case database:', error);
      throw error;
    }
  },

  /**
   * Guarda playbook en la base de datos del caso
   */
  async savePlaybookToCase(caseId, playbookName, target, result, nodes) {
    try {
      const caseKey = `case_${caseId}_playbooks`;
      const existingData = JSON.parse(localStorage.getItem(caseKey) || '[]');

      const playbook = {
        id: `playbook_${Date.now()}`,
        name: playbookName,
        target,
        result,
        nodes,
        createdAt: new Date().toISOString()
      };

      existingData.push(playbook);
      localStorage.setItem(caseKey, JSON.stringify(existingData));

      return {
        caseId,
        playbookId: playbook.id,
        saved: true
      };
    } catch (error) {
      console.error('Error saving playbook to case:', error);
      throw error;
    }
  },

  /**
   * Obtiene todos los análisis de Threat Intel guardados en un caso
   */
  async getCaseThreatIntelAnalyses(caseId) {
    try {
      const response = await api.get(`/forensics/case/${caseId}/threat-intel`);
      return response.data.analyses || [];
    } catch (error) {
      console.error('Error fetching threat intel analyses:', error);
      // Fallback a localStorage
      const caseKey = `case_${caseId}_threat_intel`;
      return JSON.parse(localStorage.getItem(caseKey) || '[]');
    }
  },

  /**
   * Obtiene todos los playbooks guardados en un caso
   */
  async getCasePlaybooks(caseId) {
    const caseKey = `case_${caseId}_playbooks`;
    const data = JSON.parse(localStorage.getItem(caseKey) || '[]');
    return data;
  },

  /**
   * Obtiene el grafo completo del caso desde el backend
   */
  async getCaseGraph(caseId) {
    try {
      const response = await api.get(`/forensics/case/${caseId}/graph`);
      return response.data;
    } catch (error) {
      console.error('Error fetching case graph:', error);
      return { nodes: [], edges: [] };
    }
  },

  /**
   * Obtiene nodos del grafo basados en análisis de threat intel
   */
  async getCaseGraphNodes(caseId) {
    try {
      const graphData = await this.getCaseGraph(caseId);
      return graphData.nodes || [];
    } catch (error) {
      // Fallback a localStorage
      const analyses = await this.getCaseThreatIntelAnalyses(caseId);
      const playbooks = await this.getCasePlaybooks(caseId);

      const nodes = [
        ...analyses.map(a => a.node || a.graph_node),
        ...playbooks.flatMap(p => p.nodes)
      ].filter(Boolean);

      return nodes;
    }
  },

  /**
   * Vincula resultado de threat intel con nodo existente en el grafo
   */
  createConnectionEdges(threatNode, existingNodes) {
    const edges = [];

    existingNodes.forEach(node => {
      // Lógica para determinar si hay relación
      if (node.type === 'ip' && threatNode.type === 'threat_ip') {
        edges.push({
          source: node.id,
          target: threatNode.id,
          type: 'threat_analysis',
          label: 'Threat Intel Analysis'
        });
      } else if (node.type === 'email' && threatNode.type === 'threat_email') {
        edges.push({
          source: node.id,
          target: threatNode.id,
          type: 'breach_check',
          label: 'Breach Analysis'
        });
      } else if (node.type === 'domain' && threatNode.type === 'threat_domain') {
        edges.push({
          source: node.id,
          target: threatNode.id,
          type: 'domain_analysis',
          label: 'Domain Intelligence'
        });
      }
    });

    return edges;
  }
};
