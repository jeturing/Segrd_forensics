import React, { useEffect, useRef, useState, useMemo } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import fcose from 'cytoscape-fcose';
import { 
  Search, Filter, ZoomIn, ZoomOut, Maximize, Download, 
  Share2, Shield, AlertTriangle, Activity, Layers, 
  ChevronRight, ChevronLeft, Play, Cpu, Database, Globe,
  User, FileText, Mail, Terminal, Sparkles
} from 'lucide-react';
import { caseService } from '../../services/cases';
import { threatIntelCaseService } from '../../services/threatIntelCaseService';
import { llmService } from '../../services/llmService';

// Register layouts
cytoscape.use(cola);
cytoscape.use(fcose);

// --- CONFIGURATION ---

const NODE_STYLES = {
  // Infrastructure
  ip: { color: '#ef4444', icon: Globe, shape: 'ellipse' },
  domain: { color: '#f59e0b', icon: Globe, shape: 'diamond' },
  url: { color: '#14b8a6', icon: Globe, shape: 'round-rectangle' },
  
  // Identity
  user: { color: '#3b82f6', icon: User, shape: 'round-rectangle' },
  email: { color: '#8b5cf6', icon: Mail, shape: 'round-rectangle' },
  
  // System
  process: { color: '#ec4899', icon: Cpu, shape: 'ellipse' },
  file: { color: '#10b981', icon: FileText, shape: 'rectangle' },
  hash: { color: '#6366f1', icon: FileText, shape: 'hexagon' },
  
  // Threat Intel
  threat_ip: { color: '#dc2626', icon: AlertTriangle, shape: 'star' },
  threat_domain: { color: '#ea580c', icon: AlertTriangle, shape: 'star' },
  threat_url: { color: '#0891b2', icon: AlertTriangle, shape: 'star' },
  
  // Actions
  playbook: { color: '#7c3aed', icon: Layers, shape: 'round-octagon' },
};

const EDGE_COLORS = {
  connected_to: '#94a3b8',
  executed: '#ef4444',
  downloaded: '#f59e0b',
  sent_to: '#3b82f6',
  logged_in: '#10b981',
  communicated: '#8b5cf6',
  threat_analysis: '#fbbf24',
};

// --- COMPONENTS ---

const SidebarSection = ({ title, children, isOpen = true }) => (
  <div className="border-b border-gray-700">
    <div className="px-4 py-3 flex items-center justify-between bg-gray-800/50 cursor-pointer hover:bg-gray-800">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</span>
      <ChevronRight className="w-4 h-4 text-gray-500" />
    </div>
    {isOpen && <div className="p-4">{children}</div>}
  </div>
);

const NodeDetailPanel = ({ node, onClose }) => {
  if (!node) return (
    <div className="h-full flex flex-col items-center justify-center text-gray-500 p-8 text-center">
      <Activity className="w-12 h-12 mb-4 opacity-20" />
      <p>Selecciona un nodo para ver sus detalles y relaciones</p>
    </div>
  );

  const style = NODE_STYLES[node.type] || { color: '#9ca3af', icon: Activity };
  const Icon = style.icon;

  return (
    <div className="h-full flex flex-col bg-gray-800 border-l border-gray-700 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-800/80 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-start justify-between mb-3">
          <div className="p-2 rounded-lg bg-gray-700/50 flex-shrink-0" style={{ color: style.color }}>
            <Icon className="w-6 h-6" />
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
        <h2 className="text-lg font-bold text-white break-words line-clamp-2" title={node.label}>{node.label}</h2>
        <div className="flex items-center gap-2 mt-2">
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-700 text-gray-300 uppercase">
            {node.type?.replace('_', ' ')}
          </span>
          {node.threatLevel && (
            <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
              node.threatLevel === 'critical' ? 'bg-red-500/20 text-red-400' :
              node.threatLevel === 'high' ? 'bg-orange-500/20 text-orange-400' :
              'bg-green-500/20 text-green-400'
            }`}>
              {node.threatLevel}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Risk Score */}
        {node.riskScore !== undefined && (
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Risk Score</span>
              <span className="font-bold text-white">{node.riskScore}/100</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full transition-all duration-500"
                style={{ 
                  width: `${node.riskScore}%`,
                  backgroundColor: node.riskScore > 70 ? '#ef4444' : node.riskScore > 40 ? '#f59e0b' : '#10b981'
                }}
              />
            </div>
          </div>
        )}

        {/* Properties */}
        <div>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Propiedades</h3>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {Object.entries(node)
              .filter(([k]) => !['id', 'label', 'type', 'threatLevel', 'riskScore', 'indicators', 'recommendations', 'metadata', 'allScopes'].includes(k))
              .slice(0, 15) // Mostrar hasta 15 propiedades
              .map(([key, value]) => {
                // Formatear valores especiales
                let displayValue = value;
                let valueClass = "text-gray-200";
                
                if (value === null || value === undefined) {
                  displayValue = "—"; // Guión para null/undefined
                  valueClass = "text-gray-500 italic";
                } else if (typeof value === 'boolean') {
                  displayValue = value ? "true" : "false";
                  valueClass = value ? "text-green-400" : "text-red-400";
                } else if (typeof value === 'object') {
                  if (Array.isArray(value)) {
                    displayValue = value.length > 0 
                      ? value.slice(0, 5).join(', ') + (value.length > 5 ? ` (+${value.length - 5} más)` : '')
                      : "—";
                  } else {
                    displayValue = JSON.stringify(value, null, 1).slice(0, 200);
                  }
                } else if (typeof value === 'string') {
                  // Detectar fechas ISO
                  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) {
                    try {
                      const date = new Date(value);
                      displayValue = date.toLocaleString('es-ES', { 
                        year: 'numeric', 
                        month: 'short', 
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      });
                    } catch {
                      displayValue = value;
                    }
                  } else {
                    displayValue = String(value);
                  }
                } else {
                  displayValue = String(value);
                }
                
                return (
                  <div key={key} className="group">
                    <div className="text-xs text-gray-500 mb-0.5" title={key}>{key}</div>
                    <div 
                      className={`text-xs font-mono bg-gray-900/50 p-1.5 rounded border border-transparent group-hover:border-gray-600 break-all ${valueClass}`}
                      style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}
                      title={typeof value === 'string' ? value : undefined}
                    >
                      {displayValue}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Indicators */}
        {node.indicators && node.indicators.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Indicadores</h3>
            <div className="flex flex-wrap gap-2">
              {node.indicators.map((ind, i) => (
                <span key={i} className="px-2 py-1 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded">
                  {ind}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Actions Footer */}
      <div className="p-4 border-t border-gray-700 bg-gray-800">
        <div className="grid grid-cols-2 gap-3">
          <button className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
            <Shield className="w-4 h-4" />
            Investigar
          </button>
          <button className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
            <Share2 className="w-4 h-4" />
            Expandir
          </button>
        </div>
        <button className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-sm font-medium transition-colors">
          <Terminal className="w-4 h-4" />
          Analizar con IA
        </button>
      </div>
    </div>
  );
};

export default function AttackGraph({ caseId, data }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState(data || { nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [layout, setLayout] = useState('cola');
  const [analyzing, setAnalyzing] = useState(false);
  const [enrichmentResult, setEnrichmentResult] = useState(null);
  const [showEnrichmentPanel, setShowEnrichmentPanel] = useState(false);
  const [filters, setFilters] = useState({
    infrastructure: true,
    identity: true,
    system: true,
    threats: true
  });

  const handleAIEnrichment = async () => {
    if (!caseId) return;
    setAnalyzing(true);
    try {
      // Call new enrichment endpoint
      const result = await caseService.enrichGraphWithAI(caseId, {
        analysisType: 'full',
        graphData: graphData
      });
      
      if (result.success) {
        // Update graph with enriched data
        setGraphData(result.enriched_graph);
        setEnrichmentResult(result.enrichment);
        setShowEnrichmentPanel(true);
        console.log('🤖 Enrichment complete:', result.enrichment);
      } else {
        console.error("AI Enrichment failed:", result.error);
        // Show fallback enrichment if available
        if (result.fallback_enrichment) {
          setEnrichmentResult({
            fallback: true,
            ...result.fallback_enrichment
          });
          setShowEnrichmentPanel(true);
        }
      }
    } catch (error) {
      console.error("AI Enrichment error:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAIAnalysis = async () => {
    if (!caseId) return;
    setAnalyzing(true);
    try {
      // Trigger deep analysis with context
      await llmService.analyzeFindings({
        context: 'general',
        findings: [], // Backend will fetch findings via case_id
        case_id: caseId,
        severity_threshold: 'medium'
      });
      // Could show a notification here
    } catch (error) {
      console.error("AI Analysis failed:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  // --- DATA LOADING ---
  useEffect(() => {
    let isMounted = true;
    const fetchGraph = async () => {
      if (!caseId || data) {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      try {
        // Fetch base graph
        const response = await caseService.getCaseGraph(caseId);
        const payload = response.graph || response;
        let nodes = payload.nodes || [];
        let edges = payload.edges || [];

        // Fetch threat intel
        try {
          const threatNodes = await threatIntelCaseService.getCaseGraphNodes(caseId);
          nodes = [...nodes, ...threatNodes];
          
          // Create implicit edges
          threatNodes.forEach(tNode => {
            nodes.forEach(bNode => {
              if (tNode.label && bNode.label && 
                 (tNode.label.includes(bNode.label) || bNode.label.includes(tNode.label))) {
                edges.push({
                  source: bNode.id,
                  target: tNode.id,
                  type: 'threat_analysis'
                });
              }
            });
          });
        } catch (e) {
          console.warn('Threat intel fetch failed', e);
        }

        if (isMounted) {
          setGraphData({ nodes, edges });
        }
      } catch (err) {
        console.error('Graph load error:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchGraph();
    return () => { isMounted = false; };
  }, [caseId, data]);

  // --- CYTOSCAPE INITIALIZATION ---
  useEffect(() => {
    if (!containerRef.current || !graphData.nodes.length) return;

    // Cleanup
    if (cyRef.current) cyRef.current.destroy();

    // Filter nodes based on state
    const filteredNodes = graphData.nodes.filter(n => {
      const type = n.type || 'unknown';
      if (['ip', 'domain', 'url'].includes(type)) return filters.infrastructure;
      if (['user', 'email'].includes(type)) return filters.identity;
      if (['process', 'file', 'hash'].includes(type)) return filters.system;
      if (type.includes('threat')) return filters.threats;
      return true;
    });

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = graphData.edges.filter(e => 
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    // Initialize
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [
        ...filteredNodes.map(n => ({ data: { ...n, ...n.data } })),
        ...filteredEdges.map((e, i) => ({ data: { id: `e${i}`, ...e } }))
      ],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-size': 10,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'width': 30,
            'height': 30,
            'background-color': '#1e293b',
            'border-width': 2,
            'border-color': '#334155'
          }
        },
        // Apply custom styles
        ...Object.entries(NODE_STYLES).map(([type, style]) => ({
          selector: `node[type="${type}"]`,
          style: {
            'background-color': style.color,
            'border-color': style.color,
            'shape': style.shape || 'ellipse'
          }
        })),
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8
          }
        },
        ...Object.entries(EDGE_COLORS).map(([type, color]) => ({
          selector: `edge[type="${type}"]`,
          style: { 'line-color': color, 'target-arrow-color': color }
        })),
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#fff',
            'shadow-blur': 10,
            'shadow-color': '#fff',
            'shadow-opacity': 0.5
          }
        }
      ],
      layout: {
        name: layout,
        animate: true,
        animationDuration: 500,
        nodeDimensionsIncludeLabels: true,
        randomize: false
      }
    });

    // Events
    cyRef.current.on('tap', 'node', (evt) => setSelectedNode(evt.target.data()));
    cyRef.current.on('tap', (evt) => {
      if (evt.target === cyRef.current) setSelectedNode(null);
    });

  }, [graphData, layout, filters]);

  // --- HANDLERS ---
  const handleZoom = (dir) => {
    if (!cyRef.current) return;
    const zoom = cyRef.current.zoom();
    cyRef.current.animate({
      zoom: dir === 'in' ? zoom * 1.3 : zoom / 1.3,
      duration: 200
    });
  };

  const handleFit = () => cyRef.current?.animate({ fit: { padding: 50 } });

  const toggleFilter = (key) => setFilters(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="flex h-[calc(100vh-100px)] bg-gray-950 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
      
      {/* LEFT SIDEBAR - FILTERS */}
      <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Filter className="w-4 h-4 text-blue-400" />
            Graph Filters
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          <SidebarSection title="Node Types">
            <div className="space-y-3">
              {[
                { id: 'infrastructure', label: 'Infrastructure', color: '#ef4444' },
                { id: 'identity', label: 'Identity', color: '#3b82f6' },
                { id: 'system', label: 'System', color: '#ec4899' },
                { id: 'threats', label: 'Threat Intel', color: '#dc2626' }
              ].map(f => (
                <label key={f.id} className="flex items-center gap-3 cursor-pointer group">
                  <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                    filters[f.id] ? 'bg-blue-600 border-blue-600' : 'border-gray-600 group-hover:border-gray-500'
                  }`}>
                    {filters[f.id] && <div className="w-2 h-2 bg-white rounded-sm" />}
                  </div>
                  <input 
                    type="checkbox" 
                    className="hidden" 
                    checked={filters[f.id]} 
                    onChange={() => toggleFilter(f.id)} 
                  />
                  <span className="text-sm text-gray-300 group-hover:text-white transition-colors">{f.label}</span>
                </label>
              ))}
            </div>
          </SidebarSection>

          <SidebarSection title="Layout">
            <div className="grid grid-cols-2 gap-2">
              {['cola', 'fcose', 'grid', 'circle'].map(l => (
                <button
                  key={l}
                  onClick={() => setLayout(l)}
                  className={`px-3 py-2 text-xs rounded-lg border transition-all ${
                    layout === l 
                      ? 'bg-blue-600/20 border-blue-500 text-blue-300' 
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                  }`}
                >
                  {l.toUpperCase()}
                </button>
              ))}
            </div>
          </SidebarSection>
        </div>
      </div>

      {/* MAIN CANVAS */}
      <div className="flex-1 flex flex-col relative bg-gray-950">
        {/* Toolbar */}
        <div className="absolute top-4 left-4 right-4 z-10 flex justify-between pointer-events-none">
          <div className="flex gap-2 pointer-events-auto">
            <div className="bg-gray-800/90 backdrop-blur border border-gray-700 rounded-lg p-1 flex gap-1">
              <button onClick={() => handleZoom('in')} className="p-2 hover:bg-gray-700 rounded text-gray-300">
                <ZoomIn className="w-4 h-4" />
              </button>
              <button onClick={() => handleZoom('out')} className="p-2 hover:bg-gray-700 rounded text-gray-300">
                <ZoomOut className="w-4 h-4" />
              </button>
              <button onClick={handleFit} className="p-2 hover:bg-gray-700 rounded text-gray-300">
                <Maximize className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div className="flex gap-2 pointer-events-auto">
            <button 
              onClick={handleAIEnrichment}
              disabled={analyzing}
              className={`bg-gradient-to-r from-purple-600 to-pink-600 backdrop-blur border border-purple-500 text-white px-3 py-2 rounded-lg text-xs font-medium hover:from-purple-500 hover:to-pink-500 flex items-center gap-2 transition-all shadow-lg ${analyzing ? 'opacity-75 cursor-wait' : ''}`}
            >
              <Sparkles className={`w-3 h-3 ${analyzing ? 'animate-spin' : ''}`} />
              {analyzing ? 'Enriqueciendo...' : '🤖 IA Enriquecer'}
            </button>
            <button 
              onClick={handleAIAnalysis}
              disabled={analyzing}
              className={`bg-purple-600/90 backdrop-blur border border-purple-500 text-white px-3 py-2 rounded-lg text-xs font-medium hover:bg-purple-500 flex items-center gap-2 transition-all ${analyzing ? 'opacity-75 cursor-wait' : ''}`}
            >
              <Sparkles className={`w-3 h-3 ${analyzing ? 'animate-spin' : ''}`} />
              {analyzing ? 'Analyzing...' : 'AI Analysis'}
            </button>
            <button className="bg-gray-800/90 backdrop-blur border border-gray-700 text-gray-300 px-3 py-2 rounded-lg text-xs font-medium hover:bg-gray-700 flex items-center gap-2">
              <Download className="w-3 h-3" />
              Export
            </button>
          </div>
        </div>

        {/* Enrichment Result Panel */}
        {showEnrichmentPanel && enrichmentResult && (
          <div className="absolute top-16 right-4 w-80 bg-gray-900/95 backdrop-blur border border-purple-500/50 rounded-lg shadow-2xl z-30 max-h-96 overflow-y-auto">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between sticky top-0 bg-gray-900">
              <h3 className="font-semibold text-purple-400 flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Análisis IA
              </h3>
              <button 
                onClick={() => setShowEnrichmentPanel(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="p-4 space-y-3">
              {enrichmentResult.fallback ? (
                <div className="text-yellow-400 text-sm">
                  <p>⚠️ Análisis basado en reglas (sin IA)</p>
                  <p className="text-gray-300 mt-2">
                    Apps críticas: {enrichmentResult.critical_apps || 0}<br/>
                    Apps alto riesgo: {enrichmentResult.high_risk_apps || 0}
                  </p>
                </div>
              ) : (
                <>
                  {enrichmentResult.risk_summary?.overall_risk && (
                    <div className={`p-3 rounded-lg ${
                      enrichmentResult.risk_summary.overall_risk === 'critical' ? 'bg-red-500/20 border border-red-500' :
                      enrichmentResult.risk_summary.overall_risk === 'high' ? 'bg-orange-500/20 border border-orange-500' :
                      'bg-green-500/20 border border-green-500'
                    }`}>
                      <span className="text-xs font-bold uppercase">
                        Riesgo: {enrichmentResult.risk_summary.overall_risk}
                      </span>
                    </div>
                  )}
                  
                  {enrichmentResult.risk_summary?.executive_summary && (
                    <div className="text-sm text-gray-300">
                      {enrichmentResult.risk_summary.executive_summary}
                    </div>
                  )}
                  
                  {enrichmentResult.attack_patterns?.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-gray-400">Patrones de Ataque:</h4>
                      {enrichmentResult.attack_patterns.map((p, i) => (
                        <div key={i} className="text-xs bg-gray-800 p-2 rounded">
                          <span className="text-red-400">{p.pattern_name}</span>
                          <p className="text-gray-400 mt-1">{p.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {enrichmentResult.recommendations?.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-gray-400">Recomendaciones:</h4>
                      {enrichmentResult.recommendations.map((r, i) => (
                        <div key={i} className={`text-xs p-2 rounded ${
                          r.priority === 'CRÍTICA' ? 'bg-red-900/50 text-red-300' :
                          r.priority === 'ALTA' ? 'bg-orange-900/50 text-orange-300' :
                          'bg-gray-800 text-gray-300'
                        }`}>
                          <span className="font-bold">[{r.priority}]</span> {r.action}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="text-xs text-gray-500 pt-2 border-t border-gray-700">
                    Modelo: {enrichmentResult.model_used || 'N/A'}<br/>
                    Nodos analizados: {enrichmentResult.nodes_analyzed || 0}<br/>
                    Nuevas conexiones: {enrichmentResult.new_connections?.length || 0}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Canvas */}
        <div ref={containerRef} className="flex-1 w-full h-full cursor-grab active:cursor-grabbing" />
        
        {/* Loading Overlay */}
        {loading && (
          <div className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm flex items-center justify-center z-20">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-blue-400 font-medium">Analyzing Graph Topology...</span>
            </div>
          </div>
        )}
      </div>

      {/* RIGHT SIDEBAR - DETAILS */}
      {selectedNode && (
        <div className="w-[420px] min-w-[420px] max-w-[420px] bg-gray-900 border-l border-gray-800 flex-shrink-0 overflow-hidden">
          <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        </div>
      )}

    </div>
  );
}
