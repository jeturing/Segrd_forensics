/**
 * Tenant Management - Admin panel for tenant and user management
 * Consola de administración multi-tenant con gestión de usuarios asociados
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
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  People as PeopleIcon,
  Sync as SyncIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon
} from '@mui/icons-material';
import { tenantsService } from '../services/tenants';
import { authService } from '../services/auth';

const TenantManagement = () => {
  const [tenants, setTenants] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [openTenantDialog, setOpenTenantDialog] = useState(false);
  const [openUserDialog, setOpenUserDialog] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  
  // Tenant form state
  const [tenantFormData, setTenantFormData] = useState({
    tenant_id: '',
    display_name: '',
    domain: '',
    m365_tenant_id: ''
  });

  // User form state
  const [userFormData, setUserFormData] = useState({
    email: '',
    display_name: '',
    role: 'analyst',
    tenant_id: ''
  });

  useEffect(() => {
    loadTenants();
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadTenantUsers(selectedTenant.id);
    }
  }, [selectedTenant]);

  const loadTenants = async () => {
    setLoading(true);
    try {
      const data = await tenantsService.getAll();
      setTenants(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTenantUsers = async (tenantId) => {
    setLoading(true);
    try {
      const data = await tenantsService.getTenantUsers(tenantId);
      setUsers(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTenant = async () => {
    if (!tenantFormData.tenant_id || !tenantFormData.display_name) {
      setError('ID y nombre son requeridos');
      return;
    }

    setLoading(true);
    try {
      await tenantsService.onboard(tenantFormData);
      setOpenTenantDialog(false);
      resetTenantForm();
      await loadTenants();
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTenant = async () => {
    if (!selectedTenant) return;

    setLoading(true);
    try {
      await tenantsService.update(selectedTenant.id, tenantFormData);
      setOpenTenantDialog(false);
      resetTenantForm();
      await loadTenants();
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTenant = async (tenantId) => {
    if (!confirm(`¿Eliminar tenant ${tenantId}? Esta acción marcará el tenant como inactivo.`)) {
      return;
    }

    setLoading(true);
    try {
      await tenantsService.delete(tenantId);
      await loadTenants();
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncTenant = async (tenantId) => {
    setLoading(true);
    try {
      await tenantsService.syncUsers(tenantId);
      alert('Sincronización completada');
      if (selectedTenant && selectedTenant.id === tenantId) {
        await loadTenantUsers(tenantId);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    if (!userFormData.email || !userFormData.tenant_id) {
      setError('Email y tenant son requeridos');
      return;
    }

    setLoading(true);
    try {
      await authService.createUser({
        ...userFormData,
        password: 'temp_' + Math.random().toString(36).slice(2)
      });
      setOpenUserDialog(false);
      resetUserForm();
      if (selectedTenant) {
        await loadTenantUsers(selectedTenant.id);
      }
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleActivateUser = async (userId) => {
    setLoading(true);
    try {
      await authService.activateUser(userId);
      if (selectedTenant) {
        await loadTenantUsers(selectedTenant.id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivateUser = async (userId) => {
    setLoading(true);
    try {
      await authService.deactivateUser(userId);
      if (selectedTenant) {
        await loadTenantUsers(selectedTenant.id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetTenantForm = () => {
    setTenantFormData({
      tenant_id: '',
      display_name: '',
      domain: '',
      m365_tenant_id: ''
    });
    setSelectedTenant(null);
  };

  const resetUserForm = () => {
    setUserFormData({
      email: '',
      display_name: '',
      role: 'analyst',
      tenant_id: ''
    });
  };

  const openEditTenantDialog = (tenant) => {
    setSelectedTenant(tenant);
    setTenantFormData({
      tenant_id: tenant.id,
      display_name: tenant.display_name,
      domain: tenant.domain || '',
      m365_tenant_id: tenant.m365_tenant_id || ''
    });
    setOpenTenantDialog(true);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Gestión de Tenants y Usuarios</Typography>
        <Box>
          <IconButton onClick={loadTenants} disabled={loading}>
            <RefreshIcon />
          </IconButton>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenTenantDialog(true)}
            sx={{ ml: 1 }}
          >
            Nuevo Tenant
          </Button>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="Tenants" />
          <Tab label="Usuarios" disabled={!selectedTenant} />
        </Tabs>
      </Paper>

      {/* Tenants Tab */}
      {activeTab === 0 && (
        <>
          {/* Stats */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={4}>
              <Card>
                <CardContent>
                  <Typography variant="h3">{tenants.length}</Typography>
                  <Typography color="textSecondary">Total Tenants</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={4}>
              <Card>
                <CardContent>
                  <Typography variant="h3">
                    {tenants.filter(t => t.is_active).length}
                  </Typography>
                  <Typography color="textSecondary">Activos</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={4}>
              <Card>
                <CardContent>
                  <Typography variant="h3">
                    {tenants.filter(t => t.m365_tenant_id).length}
                  </Typography>
                  <Typography color="textSecondary">Con M365</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Tenants Table */}
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Nombre</TableCell>
                  <TableCell>Dominio</TableCell>
                  <TableCell>M365 Tenant ID</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Creado</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading && tenants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <CircularProgress />
                    </TableCell>
                  </TableRow>
                ) : tenants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="textSecondary">
                        No hay tenants. Crea uno con el botón "Nuevo Tenant"
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  tenants.map((tenant) => (
                    <TableRow
                      key={tenant.id}
                      selected={selectedTenant?.id === tenant.id}
                      onClick={() => setSelectedTenant(tenant)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>{tenant.id}</TableCell>
                      <TableCell>{tenant.display_name}</TableCell>
                      <TableCell>{tenant.domain || '-'}</TableCell>
                      <TableCell>
                        {tenant.m365_tenant_id ? (
                          <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                            {tenant.m365_tenant_id.substring(0, 8)}...
                          </Typography>
                        ) : '-'}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={tenant.is_active ? 'Activo' : 'Inactivo'}
                          color={tenant.is_active ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {new Date(tenant.created_at).toLocaleDateString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Ver Usuarios">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedTenant(tenant);
                              setActiveTab(1);
                            }}
                          >
                            <PeopleIcon />
                          </IconButton>
                        </Tooltip>
                        
                        <Tooltip title="Sincronizar Usuarios">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSyncTenant(tenant.id);
                            }}
                          >
                            <SyncIcon />
                          </IconButton>
                        </Tooltip>
                        
                        <Tooltip title="Editar">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditTenantDialog(tenant);
                            }}
                          >
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                        
                        <Tooltip title="Eliminar">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteTenant(tenant.id);
                            }}
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
        </>
      )}

      {/* Users Tab */}
      {activeTab === 1 && selectedTenant && (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">
              Usuarios de {selectedTenant.display_name}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => {
                setUserFormData({ ...userFormData, tenant_id: selectedTenant.id });
                setOpenUserDialog(true);
              }}
            >
              Agregar Usuario
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Email</TableCell>
                  <TableCell>Nombre</TableCell>
                  <TableCell>Rol</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Último Acceso</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <CircularProgress />
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="textSecondary">
                        No hay usuarios. Sincroniza desde M365 o agrega uno manualmente.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.display_name || '-'}</TableCell>
                      <TableCell>
                        <Chip label={user.role} size="small" />
                      </TableCell>
                      <TableCell>
                        <Chip
                          icon={user.is_active ? <ActiveIcon /> : <InactiveIcon />}
                          label={user.is_active ? 'Activo' : 'Inactivo'}
                          color={user.is_active ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {user.last_login 
                            ? new Date(user.last_login).toLocaleString()
                            : 'Nunca'}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {user.is_active ? (
                          <Button
                            size="small"
                            onClick={() => handleDeactivateUser(user.id)}
                          >
                            Desactivar
                          </Button>
                        ) : (
                          <Button
                            size="small"
                            onClick={() => handleActivateUser(user.id)}
                          >
                            Activar
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {/* Tenant Dialog */}
      <Dialog open={openTenantDialog} onClose={() => { setOpenTenantDialog(false); resetTenantForm(); }} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedTenant ? 'Editar Tenant' : 'Nuevo Tenant'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Tenant ID"
            value={tenantFormData.tenant_id}
            onChange={(e) => setTenantFormData({ ...tenantFormData, tenant_id: e.target.value })}
            margin="normal"
            disabled={!!selectedTenant}
            helperText="Identificador único (ej: empresa-corp)"
          />
          
          <TextField
            fullWidth
            label="Nombre para Mostrar"
            value={tenantFormData.display_name}
            onChange={(e) => setTenantFormData({ ...tenantFormData, display_name: e.target.value })}
            margin="normal"
          />
          
          <TextField
            fullWidth
            label="Dominio"
            value={tenantFormData.domain}
            onChange={(e) => setTenantFormData({ ...tenantFormData, domain: e.target.value })}
            margin="normal"
            helperText="Ej: empresa.com"
          />
          
          <TextField
            fullWidth
            label="M365 Tenant ID"
            value={tenantFormData.m365_tenant_id}
            onChange={(e) => setTenantFormData({ ...tenantFormData, m365_tenant_id: e.target.value })}
            margin="normal"
            helperText="ID del tenant de Microsoft 365 (opcional)"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setOpenTenantDialog(false); resetTenantForm(); }}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={selectedTenant ? handleUpdateTenant : handleCreateTenant}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : (selectedTenant ? 'Actualizar' : 'Crear')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* User Dialog */}
      <Dialog open={openUserDialog} onClose={() => { setOpenUserDialog(false); resetUserForm(); }} maxWidth="sm" fullWidth>
        <DialogTitle>Agregar Usuario</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={userFormData.email}
            onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })}
            margin="normal"
          />
          
          <TextField
            fullWidth
            label="Nombre para Mostrar"
            value={userFormData.display_name}
            onChange={(e) => setUserFormData({ ...userFormData, display_name: e.target.value })}
            margin="normal"
          />
          
          <TextField
            fullWidth
            select
            label="Rol"
            value={userFormData.role}
            onChange={(e) => setUserFormData({ ...userFormData, role: e.target.value })}
            margin="normal"
            SelectProps={{
              native: true,
            }}
          >
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
            <option value="viewer">Viewer</option>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setOpenUserDialog(false); resetUserForm(); }}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleCreateUser}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Crear Usuario'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TenantManagement;
