/**
 * LLM Agent Manager - Gestión de agentes Ollama por tenant
 * Panel de administración para crear, configurar y asignar agentes LLM
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  CloudDownload as PullIcon
} from '@mui/icons-material';
import { llmAgentsService } from '../services/llm-agents';
import { tenantsService } from '../services/tenants';

const LLMAgentManager = () => {
  const [agents, setAgents] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState('');
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    tenant_id: '',
    model: 'phi4-mini',
    port: 11438,
    memory_limit: '6g',
    memory_reservation: '2g'
  });

  useEffect(() => {
    loadAgents();
    loadTenants();
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const data = await llmAgentsService.listAgents(selectedTenant);
      setAgents(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTenants = async () => {
    try {
      const data = await tenantsService.getAll();
      setTenants(data);
    } catch (err) {
      console.error('Error loading tenants:', err);
    }
  };

  const handleCreateAgent = async () => {
    if (!formData.name || !formData.tenant_id || !formData.port) {
      setError('Todos los campos son requeridos');
      return;
    }

    setLoading(true);
    try {
      await llmAgentsService.createAgent(formData);
      setOpenDialog(false);
      resetForm();
      await loadAgents();
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAgent = async (agentName) => {
    if (!confirm(`¿Eliminar agente ${agentName}? Esta acción no se puede deshacer.`)) {
      return;
    }

    setLoading(true);
    try {
      await llmAgentsService.deleteAgent(agentName, false);
      await loadAgents();
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartAgent = async (agentName) => {
    setLoading(true);
    try {
      await llmAgentsService.startAgent(agentName);
      await loadAgents();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStopAgent = async (agentName) => {
    setLoading(true);
    try {
      await llmAgentsService.stopAgent(agentName);
      await loadAgents();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePullModel = async (agentName, model) => {
    setLoading(true);
    try {
      await llmAgentsService.pullModel(agentName, model);
      alert(`Modelo ${model} descargado exitosamente`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      tenant_id: '',
      model: 'phi4-mini',
      port: 11438,
      memory_limit: '6g',
      memory_reservation: '2g'
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'created':
        return 'info';
      case 'exited':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Gestión de Agentes LLM</Typography>
        <Box>
          <FormControl sx={{ mr: 2, minWidth: 200 }}>
            <InputLabel>Filtrar por Tenant</InputLabel>
            <Select
              value={selectedTenant}
              onChange={(e) => {
                setSelectedTenant(e.target.value);
                loadAgents();
              }}
              label="Filtrar por Tenant"
            >
              <MenuItem value="">Todos</MenuItem>
              {tenants.map(t => (
                <MenuItem key={t.id} value={t.id}>{t.display_name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <IconButton onClick={loadAgents} disabled={loading}>
            <RefreshIcon />
          </IconButton>
          
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
            sx={{ ml: 1 }}
          >
            Nuevo Agente
          </Button>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant="h3">{agents.length}</Typography>
              <Typography color="textSecondary">Total Agentes</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant="h3">
                {agents.filter(a => a.status === 'running').length}
              </Typography>
              <Typography color="textSecondary">Activos</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant="h3">
                {new Set(agents.map(a => a.tenant_id)).size}
              </Typography>
              <Typography color="textSecondary">Tenants con Agentes</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant="h3">
                {new Set(agents.map(a => a.model)).size}
              </Typography>
              <Typography color="textSecondary">Modelos Diferentes</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Agents Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Nombre</TableCell>
              <TableCell>Tenant</TableCell>
              <TableCell>Modelo</TableCell>
              <TableCell>Puerto</TableCell>
              <TableCell>Memoria</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Creado</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && agents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : agents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="textSecondary">
                    No hay agentes. Crea uno con el botón "Nuevo Agente"
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              agents.map((agent) => (
                <TableRow key={agent.container_id}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {agent.name}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {agent.container_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {tenants.find(t => t.id === agent.tenant_id)?.display_name || agent.tenant_id}
                  </TableCell>
                  <TableCell>{agent.model}</TableCell>
                  <TableCell>
                    <Chip label={agent.port} size="small" color="primary" />
                  </TableCell>
                  <TableCell>{agent.memory_limit}</TableCell>
                  <TableCell>
                    <Chip
                      label={agent.status}
                      size="small"
                      color={getStatusColor(agent.status)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {new Date(agent.created_at).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {agent.status === 'running' ? (
                      <Tooltip title="Detener">
                        <IconButton
                          size="small"
                          onClick={() => handleStopAgent(agent.name)}
                        >
                          <StopIcon />
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Tooltip title="Iniciar">
                        <IconButton
                          size="small"
                          onClick={() => handleStartAgent(agent.name)}
                        >
                          <StartIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    
                    <Tooltip title="Descargar Modelo">
                      <IconButton
                        size="small"
                        onClick={() => handlePullModel(agent.name, 'phi4-mini')}
                      >
                        <PullIcon />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Eliminar">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteAgent(agent.name)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create Agent Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Crear Nuevo Agente LLM</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Nombre del Agente"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            helperText="Ej: agent4, agent-analytics, etc."
          />
          
          <FormControl fullWidth margin="normal">
            <InputLabel>Tenant</InputLabel>
            <Select
              value={formData.tenant_id}
              onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value })}
              label="Tenant"
            >
              {tenants.map(t => (
                <MenuItem key={t.id} value={t.id}>
                  {t.display_name} ({t.id})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl fullWidth margin="normal">
            <InputLabel>Modelo</InputLabel>
            <Select
              value={formData.model}
              onChange={(e) => setFormData({ ...formData, model: e.target.value })}
              label="Modelo"
            >
              <MenuItem value="phi4-mini">phi4-mini (2.5GB)</MenuItem>
              <MenuItem value="phi4-mini-reasoning">phi4-mini-reasoning (3.2GB)</MenuItem>
              <MenuItem value="llama2">llama2 (3.8GB)</MenuItem>
              <MenuItem value="mistral">mistral (4.1GB)</MenuItem>
            </Select>
          </FormControl>
          
          <TextField
            fullWidth
            type="number"
            label="Puerto"
            value={formData.port}
            onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
            margin="normal"
            helperText="Puerto único en el host (ej: 11438, 11439)"
          />
          
          <TextField
            fullWidth
            label="Límite de Memoria"
            value={formData.memory_limit}
            onChange={(e) => setFormData({ ...formData, memory_limit: e.target.value })}
            margin="normal"
            helperText="Ej: 6g, 8g, 4g"
          />
          
          <TextField
            fullWidth
            label="Reserva de Memoria"
            value={formData.memory_reservation}
            onChange={(e) => setFormData({ ...formData, memory_reservation: e.target.value })}
            margin="normal"
            helperText="Memoria mínima garantizada"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setOpenDialog(false); resetForm(); }}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleCreateAgent}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Crear Agente'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LLMAgentManager;
