import React, { useState, useEffect } from 'react';
import { Card, Button, Alert, Loading } from '../Common';

const AGENT_TYPES = {
  intune: {
    name: 'Microsoft Intune',
    icon: '☁️',
    description: 'Full endpoint forensics (Windows/Mac)',
    platforms: ['Windows', 'macOS', 'iOS', 'Android'],
    color: 'blue',
    features: ['Process list', 'Registry', 'Event logs', 'Network', 'Remote PowerShell']
  },
  osquery: {
    name: 'OSQuery',
    icon: '🔍',
    description: 'Lightweight SQL-like queries',
    platforms: ['Windows', 'macOS', 'Linux'],
    color: 'purple',
    features: ['Process queries', 'Network sockets', 'File analysis', 'System info']
  },
  velociraptor: {
    name: 'Velociraptor',
    icon: '🦖',
    description: 'Enterprise EDR - Advanced artifacts',
    platforms: ['Windows', 'macOS', 'Linux'],
    color: 'red',
    features: ['YARA scanning', 'Memory capture', 'Registry collection', 'Event logs', 'Network capture']
  }
};

export default function MobileAgents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('agents');
  const [deployModal, setDeployModal] = useState({ show: false, agentType: null });

  useEffect(() => {
    // Simular carga de agentes
    setTimeout(() => {
      setAgents([
        {
          id: 'agent-001',
          name: 'WORKSTATION-01',
          type: 'intune',
          status: 'online',
          lastSeen: '2 minutes ago',
          osVersion: 'Windows 11 Pro Build 23435',
          ipAddress: '192.168.1.100',
          cases: 3
        },
        {
          id: 'agent-002',
          name: 'LAPTOP-MAC-01',
          type: 'osquery',
          status: 'online',
          lastSeen: '5 minutes ago',
          osVersion: 'macOS 14.2.1',
          ipAddress: '192.168.1.105',
          cases: 1
        },
        {
          id: 'agent-003',
          name: 'SERVER-PROD-01',
          type: 'velociraptor',
          status: 'offline',
          lastSeen: '2 hours ago',
          osVersion: 'Ubuntu 22.04 LTS',
          ipAddress: '10.0.1.50',
          cases: 5
        }
      ]);
    }, 800);
  }, []);

  const getStatusBadge = (status) => {
    return status === 'online' 
      ? '🟢 Online' 
      : '🔴 Offline';
  };

  const getTypeColor = (type) => {
    const colors = { intune: 'blue', osquery: 'purple', velociraptor: 'red' };
    return colors[type] || 'gray';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">🔌 Agentes Remotos</h1>
        <p className="text-gray-400 mt-1">Deploy y gestión de agentes forenses en endpoints</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('agents')}
          className={`px-6 py-2 rounded-lg font-medium transition ${
            activeTab === 'agents'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          📱 Agentes Activos
        </button>
        <button
          onClick={() => setActiveTab('deploy')}
          className={`px-6 py-2 rounded-lg font-medium transition ${
            activeTab === 'deploy'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          ➕ Desplegar Nuevo
        </button>
        <button
          onClick={() => setActiveTab('commands')}
          className={`px-6 py-2 rounded-lg font-medium transition ${
            activeTab === 'commands'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          ⌨️ Ejecutar Comando
        </button>
      </div>

      {/* Agents List */}
      {activeTab === 'agents' && (
        <div>
          <Card title="📱 Dispositivos Conectados">
            {loading ? (
              <Loading message="Cargando agentes..." />
            ) : agents.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400">Sin agentes conectados</p>
              </div>
            ) : (
              <div className="space-y-4">
                {agents.map((agent) => (
                  <div key={agent.id} className="bg-gray-700/30 rounded-lg p-4 hover:bg-gray-700/50 transition">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-2xl">{AGENT_TYPES[agent.type]?.icon}</span>
                          <div>
                            <h3 className="font-semibold text-lg">{agent.name}</h3>
                            <p className="text-sm text-gray-400">{AGENT_TYPES[agent.type]?.name}</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-sm">
                          <div>
                            <p className="text-gray-500">Estado</p>
                            <p className="font-medium">{getStatusBadge(agent.status)}</p>
                          </div>
                          <div>
                            <p className="text-gray-500">Última actividad</p>
                            <p className="font-medium">{agent.lastSeen}</p>
                          </div>
                          <div>
                            <p className="text-gray-500">IP Address</p>
                            <p className="font-medium text-blue-400">{agent.ipAddress}</p>
                          </div>
                          <div>
                            <p className="text-gray-500">SO</p>
                            <p className="font-medium text-xs">{agent.osVersion}</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col gap-2 ml-4">
                        <Button variant="primary" size="sm">
                          ▶️ Ejecutar
                        </Button>
                        <Button variant="secondary" size="sm">
                          📊 Reporte
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Deploy Tab */}
      {activeTab === 'deploy' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {Object.entries(AGENT_TYPES).map(([key, agent]) => (
            <Card key={key} title={agent.name} icon={agent.icon}>
              <div className="space-y-4">
                <p className="text-gray-400 text-sm">{agent.description}</p>
                
                <div>
                  <p className="text-xs text-gray-500 mb-2">Plataformas soportadas:</p>
                  <div className="flex flex-wrap gap-2">
                    {agent.platforms.map((platform) => (
                      <span key={platform} className="badge badge-info text-xs">
                        {platform}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-2">Características:</p>
                  <ul className="text-sm space-y-1">
                    {agent.features.map((feature) => (
                      <li key={feature} className="text-gray-300">
                        ✓ {feature}
                      </li>
                    ))}
                  </ul>
                </div>

                <Button
                  variant="primary"
                  onClick={() => setDeployModal({ show: true, agentType: key })}
                  className="w-full"
                >
                  ➕ Desplegar {agent.name}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Commands Tab */}
      {activeTab === 'commands' && (
        <Card title="⌨️ Ejecutar Comando Remoto">
          <CommandExecutorPanel agents={agents} />
        </Card>
      )}

      {/* Deploy Modal */}
      {deployModal.show && (
        <DeployModal
          agentType={AGENT_TYPES[deployModal.agentType]}
          onClose={() => setDeployModal({ show: false, agentType: null })}
        />
      )}
    </div>
  );
}

function CommandExecutorPanel({ agents }) {
  const [selectedAgent, setSelectedAgent] = useState(agents[0]?.id || '');
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  const [executing, setExecuting] = useState(false);

  const handleExecute = async () => {
    setExecuting(true);
    // Simular ejecución
    setTimeout(() => {
      setOutput(`$ ${command}\n\nOutput...\n[Comando ejecutado en ${agents.find(a => a.id === selectedAgent)?.name}]\n`);
      setExecuting(false);
    }, 1000);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Seleccionar dispositivo</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="input-base w-full"
          >
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} ({agent.type})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Comando</label>
        <textarea
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="Ej: tasklist /v"
          rows={4}
          className="input-base w-full font-mono text-sm"
        />
      </div>

      <div className="flex gap-2">
        <Button
          onClick={handleExecute}
          variant="primary"
          loading={executing}
        >
          ▶️ Ejecutar
        </Button>
        <Button
          onClick={() => setCommand('')}
          variant="secondary"
        >
          🗑️ Limpiar
        </Button>
      </div>

      {output && (
        <div>
          <p className="text-sm font-medium mb-2">Resultado:</p>
          <pre className="bg-gray-900 p-4 rounded-lg text-sm text-gray-200 overflow-x-auto max-h-60 overflow-y-auto">
            {output}
          </pre>
        </div>
      )}
    </div>
  );
}

function DeployModal({ agentType, onClose }) {
  const [deployCode, setDeployCode] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Generar código de deploy basado en el tipo
    const codes = {
      intune: `# PowerShell - Intune Deploy
$IntuneUrl = "https://your-intune-instance/api"
$AgentId = "kali-forensics-agent-001"
$Token = "your-bearer-token"

# Descargar agente
Invoke-WebRequest -Uri "$IntuneUrl/agents/download" \\
  -Headers @{ Authorization = "Bearer $Token" } \\
  -OutFile "C:\\Windows\\Temp\\agent.exe"

# Ejecutar
& "C:\\Windows\\Temp\\agent.exe" --register --case-id IR-2025-001`,
      osquery: `#!/bin/bash
# OSQuery Deploy Script

AGENT_URL="https://your-server/agents/osquery"
INSTALL_DIR="/opt/forensics-agent"

# Descargar
wget $AGENT_URL -O agent.tar.gz

# Instalar
sudo mkdir -p $INSTALL_DIR
sudo tar -xzf agent.tar.gz -C $INSTALL_DIR
sudo $INSTALL_DIR/install.sh

# Ejecutar
sudo $INSTALL_DIR/osqueryd --config_path=/etc/osquery/osquery.conf`,
      velociraptor: `#!/bin/bash
# Velociraptor Deploy

DOWNLOAD_URL="https://your-server/agents/velociraptor"
wget $DOWNLOAD_URL -O velociraptor.exe

# En Windows PowerShell:
.\\velociraptor.exe --config client.config.yaml client

# En Linux/Mac:
chmod +x velociraptor
./velociraptor --config client.config.yaml client`
    };
    setDeployCode(codes[agentType?.name?.toLowerCase()] || codes.intune);
  }, [agentType]);

  const handleCopy = () => {
    navigator.clipboard.writeText(deployCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-semibold">🚀 Desplegar {agentType?.name}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-4">
          <Alert type="info" message="Copia el código y ejecuta en el endpoint destino" />

          <div>
            <p className="text-sm font-medium mb-2">Código de Deploy:</p>
            <pre className="bg-gray-900 p-4 rounded-lg text-xs text-gray-200 overflow-x-auto">
              {deployCode}
            </pre>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleCopy}
              variant="primary"
              className="flex-1"
            >
              {copied ? '✅ Copiado' : '📋 Copiar Código'}
            </Button>
            <Button
              onClick={onClose}
              variant="secondary"
              className="flex-1"
            >
              Cerrar
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
