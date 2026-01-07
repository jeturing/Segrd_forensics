/**
 * EJEMPLO: Integración de componentes de administración en el router principal
 * 
 * Este archivo muestra cómo integrar LLMAgentManager y TenantManagement
 * en tu configuración de rutas existente.
 * 
 * INSTRUCCIONES:
 * 1. Importa los componentes
 * 2. Añade las rutas al AdminLayout o similar
 * 3. Añade items al menú de administración
 */

// ============================================================================
// PASO 1: Importar componentes
// ============================================================================

import LLMAgentManager from '../components/LLMAgentManager';
import TenantManagement from '../components/TenantManagement';

// ============================================================================
// PASO 2: Añadir rutas (en tu archivo de rutas principal)
// ============================================================================

// Ejemplo con React Router v6:
const adminRoutes = [
  {
    path: '/admin',
    element: <AdminLayout />,
    children: [
      {
        path: 'llm-agents',
        element: <LLMAgentManager />,
        meta: {
          title: 'Gestión de Agentes LLM',
          requiresAdmin: true
        }
      },
      {
        path: 'tenants',
        element: <TenantManagement />,
        meta: {
          title: 'Tenants y Usuarios',
          requiresAdmin: true
        }
      }
    ]
  }
];

// ============================================================================
// PASO 3: Añadir items al menú de administración
// ============================================================================

// Ejemplo con Material-UI Menu:
const AdminMenu = () => {
  const navigate = useNavigate();

  return (
    <List>
      {/* Otros items del menú */}
      
      <ListItem button onClick={() => navigate('/admin/llm-agents')}>
        <ListItemIcon>
          <ComputerIcon />
        </ListItemIcon>
        <ListItemText primary="Agentes LLM" />
      </ListItem>

      <ListItem button onClick={() => navigate('/admin/tenants')}>
        <ListItemIcon>
          <PeopleIcon />
        </ListItemIcon>
        <ListItemText primary="Tenants y Usuarios" />
      </ListItem>
    </List>
  );
};

// ============================================================================
// PASO 4: Proteger rutas (opcional - RBAC)
// ============================================================================

import { authService } from '../services/auth';

const ProtectedAdminRoute = ({ children }) => {
  const user = authService.getCurrentUser();
  
  if (!user || !user.is_global_admin) {
    return <Navigate to="/login" />;
  }

  return children;
};

// Uso:
<Route
  path="/admin/llm-agents"
  element={
    <ProtectedAdminRoute>
      <LLMAgentManager />
    </ProtectedAdminRoute>
  }
/>

// ============================================================================
// EJEMPLO COMPLETO: App.jsx o Routes.jsx
// ============================================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LLMAgentManager from './components/LLMAgentManager';
import TenantManagement from './components/TenantManagement';
import AdminLayout from './layouts/AdminLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Rutas públicas */}
        <Route path="/login" element={<Login />} />
        
        {/* Rutas de administración */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          
          {/* NUEVAS RUTAS */}
          <Route path="llm-agents" element={<LLMAgentManager />} />
          <Route path="tenants" element={<TenantManagement />} />
          
          {/* Otras rutas admin existentes */}
          <Route path="users" element={<UserManagement />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Redirect */}
        <Route path="*" element={<Navigate to="/admin" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

// ============================================================================
// VERIFICACIÓN
// ============================================================================

/**
 * Para verificar que todo funciona:
 * 
 * 1. Iniciar backend:
 *    cd /home/hack/mcp-kali-forensics
 *    ./restart_backend.sh
 * 
 * 2. Iniciar frontend:
 *    cd frontend-react
 *    npm run dev
 * 
 * 3. Navegar a:
 *    http://localhost:3000/admin/llm-agents
 *    http://localhost:3000/admin/tenants
 * 
 * 4. Verificar que se cargan los datos desde la API
 * 
 * 5. Probar crear un agente de prueba:
 *    - Nombre: test-agent
 *    - Tenant: cualquier tenant existente
 *    - Puerto: 11450
 *    - Click "Crear Agente"
 *    - Verificar con: docker ps | grep test-agent
 */
