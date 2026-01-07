import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Card, Button, Alert, Loading } from '../Common';
import { agentService } from '../../services/agents';
import {
  executeCommand as executeActiveCommand,
  getCommandHistory,
  getCommandTemplates,
  startCapture,
  stopCapture,
  getCapturePackets
} from '../../services/activeInvestigation';
import remoteAgentsService from '../../services/remoteAgents';

const FALLBACK_AGENTS = [
  { id: 'demo-agent-blue-001', name: 'Demo Blue Agent (Workstation)', osType: 'windows', status: 'online' },
  { id: 'demo-agent-red-001', name: 'Demo Red Agent (Kali)', osType: 'linux', status: 'online' },
  { id: 'demo-agent-purple-001', name: 'Demo Purple Agent (Coordinator)', osType: 'linux', status: 'online' }
];

const CATEGORY_LABELS = {
  Processes: 'Procesos',
  Network: 'Red',
  System: 'Sistema',
  Memory: 'Memoria'
};

const CATEGORY_ICONS = {
  Processes: '📋',
  Network: '🌐',
  System: '🖥️',
  Memory: '💾'
};

const normalizeOsType = (platform = '') => {
  const value = platform.toLowerCase();
  if (value.includes('win')) return 'windows';
  if (value.includes('mac')) return 'mac';
  return 'linux';
};

export default function ActiveInvestigation() {
  const location = useLocation();
  
  // Obtener caseId desde query params (?case=IR-2025-001) o desde location.state
  const searchParams = new URLSearchParams(location.search);
  const caseId = searchParams.get('case') || location.state?.caseId || '';

  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [osType, setOsType] = useState('windows');
  const [dataSource, setDataSource] = useState('loading');

  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  const [executing, setExecuting] = useState(false);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(true);

  // v4.5 - Remote Agent Script Generation
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentOS, setNewAgentOS] = useState('windows');
  const [generatingScript, setGeneratingScript] = useState(false);
  const [generatedAgentInfo, setGeneratedAgentInfo] = useState(null);
  const [remoteTokens, setRemoteTokens] = useState([]);
  const [loadingTokens, setLoadingTokens] = useState(false);

  const loadAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const response = await agentService.getAgents();
      const normalized = (response.agents || []).map((agent) => ({
        id: agent.id,
        name: agent.name || agent.hostname || agent.id,
        status: agent.status || 'unknown',
        osType: normalizeOsType(agent.platform || agent.agent_type || agent.os_version || '')
      }));

      const list = normalized.length ? normalized : FALLBACK_AGENTS;
      setAgents(list);
      setDataSource(response.dataSource || (normalized.length ? 'real' : 'demo'));

      const first = list[0];
      setSelectedAgent((prev) => prev || first.id);
      setOsType((prev) => prev || first.osType);

      if (response.dataSource === 'real') {
        toast.success(`Agentes cargados (${list.length})`);
      } else if (!normalized.length) {
        toast.warn('Agentes reales no disponibles, usando demo');
      } else {
        toast.info('Agentes demo cargados');
      }
    } catch (error) {
      console.error('Error loading agents for Active Investigation:', error);
      setAgents(FALLBACK_AGENTS);
      setDataSource('demo');
      setSelectedAgent((prev) => prev || FALLBACK_AGENTS[0].id);
      setOsType((prev) => prev || FALLBACK_AGENTS[0].osType);
      toast.warn('No se pudieron cargar agentes reales; usando demo');
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  const loadTemplates = useCallback(async () => {
    if (!osType) return;
    setLoadingTemplates(true);
    try {
      const data = await getCommandTemplates(osType);
      const categories = Object.entries(data.templates || {}).map(([category, cmds]) => ({
        category,
        commands: (cmds || []).map((cmd) => ({ label: cmd, cmd }))
      }));
      setTemplates(categories);
    } catch (error) {
      console.error('Error loading command templates:', error);
      setTemplates([]);
      toast.error('No se pudieron cargar las plantillas de comando');
    } finally {
      setLoadingTemplates(false);
    }
  }, [osType]);

  const loadHistory = useCallback(
    async (agentId) => {
      if (!agentId) return;
      setLoadingHistory(true);
      try {
        const data = await getCommandHistory(agentId, { limit: 25, caseId: caseId || null });
        setHistory(data.history || []);
      } catch (error) {
        console.error('Error loading command history:', error);
        setHistory([]);
      } finally {
        setLoadingHistory(false);
      }
    },
    [caseId]
  );

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    if (selectedAgent) {
      loadHistory(selectedAgent);
    }
  }, [selectedAgent, loadHistory]);

  const handleExecute = async () => {
    if (!command.trim()) return;
    if (!selectedAgent) {
      toast.warn('Selecciona un agente');
      return;
    }

    setExecuting(true);
    setOutput(`⏳ Ejecutando comando en ${selectedAgent}...`);

    try {
      const response = await executeActiveCommand({
        agentId: selectedAgent,
        command,
        osType,
        caseId: caseId || null
      });

      setOutput(response.output || '✅ Comando ejecutado');
      const preview = (response.output || '').split('\n').slice(0, 3).join(' ');
      const historyEntry = {
        command: response.command || command,
        executed_at: response.timestamp || new Date().toISOString(),
        execution_time: response.execution_time,
        return_code: response.return_code,
        output_preview: preview,
        agent_id: selectedAgent
      };
      setHistory((prev) => [historyEntry, ...prev].slice(0, 25));
      toast.success('Comando ejecutado');
    } catch (error) {
      const detail = error.response?.data?.detail || error.message;
      setOutput(`❌ Error: ${detail}`);
      toast.error('Error ejecutando el comando');
    } finally {
      setExecuting(false);
    }
  };

  const handleTemplateSelect = (templateCmd) => {
    setCommand(templateCmd);
    setSelectedTemplate(templateCmd);
  };

  const handleAgentChange = (agentId) => {
    const agent = agents.find((a) => a.id === agentId);
    setSelectedAgent(agentId);
    if (agent?.osType) {
      setOsType(agent.osType);
    }
  };

  const renderTimestamp = (ts) => {
    if (!ts) return '---';
    const parsed = new Date(ts);
    return Number.isNaN(parsed.getTime()) ? ts : parsed.toLocaleTimeString();
  };

  // v4.5 - Remote Agent Functions
  const loadRemoteTokens = useCallback(async () => {
    if (!caseId) return;
    setLoadingTokens(true);
    try {
      const data = await remoteAgentsService.listAgentTokens({ case_id: caseId });
      setRemoteTokens(data.tokens || []);
    } catch (error) {
      console.error('Error loading remote tokens:', error);
    } finally {
      setLoadingTokens(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) {
      loadRemoteTokens();
    }
  }, [caseId, loadRemoteTokens]);

  const handleGenerateScript = async () => {
    if (!newAgentName.trim()) {
      toast.warn('Ingresa un nombre para el agente');
      return;
    }
    if (!caseId) {
      toast.error('Se requiere un ID de caso para generar el agente');
      return;
    }

    setGeneratingScript(true);
    try {
      const result = await remoteAgentsService.generateAgentScript({
        agent_name: newAgentName.trim(),
        os_type: newAgentOS,
        case_id: caseId,
        expires_hours: 24
      });
      
      setGeneratedAgentInfo(result);
      toast.success('🔗 Script de agente generado');
      loadRemoteTokens();
    } catch (error) {
      console.error('Error generating agent script:', error);
      toast.error('Error generando script de agente');
    } finally {
      setGeneratingScript(false);
    }
  };

  const handleDownloadScript = async () => {
    if (!generatedAgentInfo) return;
    try {
      await remoteAgentsService.downloadAgentScript(
        generatedAgentInfo.token,
        generatedAgentInfo.agent_name,
        generatedAgentInfo.os_type
      );
      toast.success('📥 Script descargado');
    } catch (error) {
      console.error('Error downloading script:', error);
      toast.error('Error descargando script');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.info('📋 Copiado al portapapeles');
  };

  if (loadingAgents && agents.length === 0) {
    return <Loading message="Cargando agentes..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold">⚡ Investigación Activa</h1>
          <p className="text-gray-400 mt-1">Ejecución de comandos en tiempo real y captura de red</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              dataSource === 'real'
                ? 'bg-green-900 text-green-200'
                : dataSource === 'demo'
                  ? 'bg-yellow-900 text-yellow-200'
                  : 'bg-gray-700 text-gray-200'
            }`}
          >
            {dataSource === 'real' ? '🟢 Datos reales' : dataSource === 'demo' ? '🟡 Demo' : '⏳ Cargando'}
          </span>
          {caseId && (
            <span className="px-3 py-1 rounded-full text-xs bg-blue-900 text-blue-100">
              Caso: {caseId}
            </span>
          )}
        </div>
      </div>

      <Alert
        type="warning"
        title="⚠️ Modo Activo Habilitado"
        message="Tienes permisos para ejecutar comandos en endpoints remotos. Todos los comandos se registran en la auditoría."
      />

      {/* v4.5 - Remote Agent Script Generator */}
      <Card title="🔗 Agentes Remotos" icon="🌐">
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex-1">
              <p className="text-sm text-gray-400 mb-2">
                Genera un script de agente para ejecutar comandos en equipos remotos en tiempo real.
                El agente se conectará vía WebSocket para recibir y ejecutar comandos.
              </p>
            </div>
            <Button
              onClick={() => setShowAgentModal(true)}
              variant="primary"
              disabled={!caseId}
              className="whitespace-nowrap"
            >
              ➕ Generar Agente
            </Button>
          </div>

          {/* Lista de tokens activos */}
          {loadingTokens ? (
            <p className="text-gray-400 text-sm">Cargando agentes remotos...</p>
          ) : remoteTokens.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase">Agentes Activos ({remoteTokens.length})</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {remoteTokens.map((token, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border ${
                      token.connected
                        ? 'border-green-600 bg-green-900/20'
                        : 'border-gray-700 bg-gray-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={token.connected ? 'text-green-400' : 'text-gray-500'}>
                          {token.connected ? '🟢' : '🔴'}
                        </span>
                        <span className="font-medium text-sm">{token.agent_name}</span>
                        <span className="text-xs text-gray-500">({token.os_type})</span>
                      </div>
                      <span className="text-xs text-gray-400">{token.token}</span>
                    </div>
                    {token.hostname && (
                      <p className="text-xs text-gray-400 mt-1">Host: {token.hostname}</p>
                    )}
                    {token.last_heartbeat && (
                      <p className="text-xs text-gray-500">Último ping: {new Date(token.last_heartbeat).toLocaleTimeString()}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : caseId ? (
            <p className="text-gray-500 text-sm">No hay agentes remotos activos para este caso.</p>
          ) : (
            <p className="text-amber-500 text-sm">⚠️ Selecciona un caso para gestionar agentes remotos.</p>
          )}
        </div>
      </Card>

      {/* Modal de generación de agente */}
      {showAgentModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl max-w-lg w-full p-6 space-y-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                🔗 Generar Agente Remoto
              </h2>
              <button
                onClick={() => {
                  setShowAgentModal(false);
                  setGeneratedAgentInfo(null);
                  setNewAgentName('');
                }}
                className="text-gray-400 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>

            {!generatedAgentInfo ? (
              <>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Nombre del Agente</label>
                    <input
                      type="text"
                      value={newAgentName}
                      onChange={(e) => setNewAgentName(e.target.value)}
                      placeholder="Ej: PC-VICTIMA-01"
                      className="input-base w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Sistema Operativo</label>
                    <select
                      value={newAgentOS}
                      onChange={(e) => setNewAgentOS(e.target.value)}
                      className="input-base w-full"
                    >
                      <option value="windows">🪟 Windows (PowerShell)</option>
                      <option value="linux">🐧 Linux (Bash)</option>
                      <option value="mac">🍎 macOS (Bash)</option>
                    </select>
                  </div>

                  <div className="bg-gray-900/50 p-3 rounded-lg">
                    <p className="text-sm text-gray-400">
                      <strong>Caso:</strong> {caseId}<br />
                      <strong>Validez:</strong> 24 horas
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    onClick={handleGenerateScript}
                    variant="primary"
                    loading={generatingScript}
                    disabled={!newAgentName.trim()}
                    className="flex-1"
                  >
                    🔗 Generar Script
                  </Button>
                  <Button
                    onClick={() => setShowAgentModal(false)}
                    variant="secondary"
                  >
                    Cancelar
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="bg-green-900/30 border border-green-700 p-4 rounded-lg space-y-3">
                  <div className="flex items-center gap-2 text-green-400">
                    <span className="text-2xl">✅</span>
                    <span className="font-medium">Script Generado Exitosamente</span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-gray-400">Agente:</span>{' '}
                      <span className="font-mono">{generatedAgentInfo.agent_name}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">OS:</span>{' '}
                      <span>{generatedAgentInfo.os_type}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Expira:</span>{' '}
                      <span>{new Date(generatedAgentInfo.expires_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Download URL */}
                <div className="bg-gray-900 p-3 rounded-lg space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase">📥 Link de Descarga</p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={generatedAgentInfo.download_url}
                      readOnly
                      className="input-base flex-1 text-sm font-mono"
                    />
                    <Button
                      onClick={() => copyToClipboard(generatedAgentInfo.download_url)}
                      variant="secondary"
                      className="px-3"
                    >
                      📋
                    </Button>
                  </div>
                </div>

                {/* WebSocket URL */}
                <div className="bg-gray-900 p-3 rounded-lg space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase">🔌 WebSocket URL</p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={generatedAgentInfo.websocket_url}
                      readOnly
                      className="input-base flex-1 text-sm font-mono text-gray-400"
                    />
                    <Button
                      onClick={() => copyToClipboard(generatedAgentInfo.websocket_url)}
                      variant="secondary"
                      className="px-3"
                    >
                      📋
                    </Button>
                  </div>
                </div>

                {/* Instructions */}
                <div className="bg-blue-900/20 border border-blue-800 p-3 rounded-lg">
                  <p className="text-xs font-semibold text-blue-400 uppercase mb-2">📋 Instrucciones</p>
                  <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">
{generatedAgentInfo.os_type === 'windows' 
  ? `# En el equipo remoto (PowerShell Admin):\nSet-ExecutionPolicy Bypass -Scope Process -Force\n.\\mcp_agent_${generatedAgentInfo.agent_name}.ps1`
  : `# En el equipo remoto:\nchmod +x mcp_agent_${generatedAgentInfo.agent_name}.sh\n./mcp_agent_${generatedAgentInfo.agent_name}.sh`}
                  </pre>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    onClick={handleDownloadScript}
                    variant="primary"
                    className="flex-1"
                  >
                    📥 Descargar Script
                  </Button>
                  <Button
                    onClick={() => {
                      setShowAgentModal(false);
                      setGeneratedAgentInfo(null);
                      setNewAgentName('');
                    }}
                    variant="secondary"
                  >
                    Cerrar
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card title="⌨️ Ejecutor de Comandos" icon="🖥️">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">🖥️ Dispositivo</label>
                  <select
                    value={selectedAgent}
                    onChange={(e) => handleAgentChange(e.target.value)}
                    className="input-base w-full"
                  >
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.status === 'online' ? '🟢' : '🔴'} {agent.name} ({agent.osType})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">🖨️ Sistema Operativo</label>
                  <select
                    value={osType}
                    onChange={(e) => setOsType(e.target.value)}
                    className="input-base w-full"
                  >
                    <option value="windows">Windows</option>
                    <option value="mac">macOS</option>
                    <option value="linux">Linux</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">⌨️ Comando</label>
                <textarea
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="Ej: tasklist /v"
                  rows={5}
                  className="input-base w-full font-mono text-sm"
                />
              </div>

              <div className="flex gap-2 flex-wrap">
                <Button onClick={handleExecute} variant="primary" loading={executing} disabled={!command.trim()}>
                  ▶️ Ejecutar
                </Button>
                <Button onClick={() => setCommand('')} variant="secondary">
                  🗑️ Limpiar
                </Button>
                <Button onClick={() => setOutput('')} variant="secondary">
                  📤 Borrar Resultado
                </Button>
                <Button onClick={() => loadHistory(selectedAgent)} variant="secondary" loading={loadingHistory}>
                  🔄 Refrescar Historial
                </Button>
              </div>

              {output && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium">📤 Resultado</label>
                    <button
                      onClick={() => navigator.clipboard.writeText(output)}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      📋 Copiar
                    </button>
                  </div>
                  <pre className="bg-gray-900 p-4 rounded-lg text-sm text-gray-200 overflow-x-auto max-h-96 overflow-y-auto border border-gray-700">
                    {output}
                  </pre>
                </div>
              )}
            </div>
          </Card>

          <Card title="📡 Captura de Tráfico de Red" icon="🌐">
            <NetworkCapture agentId={selectedAgent} caseId={caseId} />
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="📋 Plantillas" icon="⚡">
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {loadingTemplates ? (
                <p className="text-gray-400 text-sm">Cargando plantillas...</p>
              ) : templates.length === 0 ? (
                <p className="text-gray-500 text-sm">Sin plantillas para {osType}</p>
              ) : (
                templates.map((category) => (
                  <div key={category.category}>
                    <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                      {CATEGORY_ICONS[category.category] || '🗂️'}{' '}
                      {CATEGORY_LABELS[category.category] || category.category}
                    </p>
                    <div className="space-y-2">
                      {category.commands.map((tmpl, idx) => (
                        <button
                          key={`${category.category}-${idx}`}
                          onClick={() => handleTemplateSelect(tmpl.cmd)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                            selectedTemplate === tmpl.cmd
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-700/30 text-gray-300 hover:bg-gray-700/60'
                          }`}
                        >
                          <span className="mr-2">{tmpl.icon || CATEGORY_ICONS[category.category] || '⚙️'}</span>
                          {tmpl.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card title="📜 Historial" icon="⏱️">
            <div className="space-y-2 max-h-48 overflow-y-auto text-sm">
              {loadingHistory ? (
                <p className="text-gray-400">Cargando historial...</p>
              ) : history.length === 0 ? (
                <p className="text-gray-500">Sin historial</p>
              ) : (
                history.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => setCommand(item.command)}
                    className="p-2 bg-gray-700/30 rounded hover:bg-gray-700/60 cursor-pointer transition"
                  >
                    <p className="text-gray-400 text-xs flex items-center gap-2">
                      {renderTimestamp(item.executed_at || item.timestamp)}
                      {typeof item.return_code === 'number' && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-200 border border-gray-700">
                          rc: {item.return_code}
                        </span>
                      )}
                    </p>
                    <p className="text-gray-200 truncate font-mono text-xs">{item.command}</p>
                    {item.output_preview && (
                      <p className="text-gray-400 text-xs truncate">{item.output_preview}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function NetworkCapture({ agentId, caseId }) {
  const [capturing, setCapturing] = useState(false);
  const [captureId, setCaptureId] = useState(null);
  const [packets, setPackets] = useState([]);
  const [loadingPackets, setLoadingPackets] = useState(false);

  useEffect(() => {
    setCaptureId(null);
    setPackets([]);
    setCapturing(false);
  }, [agentId]);

  const fetchPackets = useCallback(async (id) => {
    if (!id) return;
    setLoadingPackets(true);
    try {
      const resp = await getCapturePackets(id, { limit: 25 });
      setPackets(resp.packets || []);
    } catch (error) {
      console.error('Error obteniendo paquetes:', error);
      toast.error('No se pudo obtener la captura');
      setPackets([]);
    } finally {
      setLoadingPackets(false);
    }
  }, []);

  const handleStartCapture = async () => {
    if (!agentId) {
      toast.warn('Selecciona un agente para capturar tráfico');
      return;
    }

    setCapturing(true);
    setPackets([]);
    try {
      const session = await startCapture({ agentId, caseId: caseId || null });
      setCaptureId(session.capture_id);
      toast.success('Captura iniciada');
      await fetchPackets(session.capture_id);
    } catch (error) {
      console.error('Error iniciando captura:', error);
      toast.error('Error iniciando captura de red');
      setCapturing(false);
    }
  };

  const handleStopCapture = async () => {
    if (!captureId) return;
    setCapturing(true);
    try {
      await stopCapture(captureId);
      toast.info('Captura detenida');
    } catch (error) {
      console.error('Error deteniendo captura:', error);
      toast.warn('No se pudo detener la captura');
    } finally {
      setCapturing(false);
    }
  };

  const handleRefresh = async () => {
    await fetchPackets(captureId);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap items-center">
        <Button onClick={handleStartCapture} variant="primary" loading={capturing}>
          {capturing ? '⏳ Iniciando...' : '▶️ Iniciar Captura'}
        </Button>
        <Button onClick={handleStopCapture} variant="danger" disabled={!captureId || capturing} loading={capturing}>
          ⏹️ Detener
        </Button>
        <Button onClick={handleRefresh} variant="secondary" disabled={!captureId} loading={loadingPackets}>
          🔄 Actualizar
        </Button>
        {captureId && (
          <span className="text-xs text-gray-400 truncate">
            ID: {captureId}
          </span>
        )}
      </div>

      {loadingPackets && <p className="text-gray-400 text-sm">Cargando paquetes...</p>}

      {packets.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-3 py-2 text-left">Hora</th>
                <th className="px-3 py-2 text-left">Origen</th>
                <th className="px-3 py-2 text-left">Destino</th>
                <th className="px-3 py-2 text-left">Protocolo</th>
                <th className="px-3 py-2 text-right">Tamaño</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {packets.map((packet, idx) => (
                <tr key={idx} className="hover:bg-gray-700/20">
                  <td className="px-3 py-2">{packet.timestamp || packet.time}</td>
                  <td className="px-3 py-2 font-mono text-xs">{packet.src}</td>
                  <td className="px-3 py-2 font-mono text-xs">{packet.dst}</td>
                  <td className="px-3 py-2">{packet.protocol}</td>
                  <td className="px-3 py-2 text-right">{packet.size}B</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loadingPackets && packets.length === 0 && captureId && (
        <p className="text-gray-500 text-sm">Captura iniciada, sin paquetes disponibles aún.</p>
      )}
    </div>
  );
}
