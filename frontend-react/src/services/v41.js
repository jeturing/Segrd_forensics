/**
 * Services v4.1 - Real Data Endpoints
 * Exporta todos los servicios que usan datos reales (sin mocks)
 */

export { agentServiceV41 } from './agentsV41';
export { investigationServiceV41 } from './investigationsV41';

// Re-export para uso simplificado
export { default as AgentsV41 } from './agentsV41';
export { default as InvestigationsV41 } from './investigationsV41';
