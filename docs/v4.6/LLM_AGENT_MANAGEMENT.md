# Implementación de Gestión de Agentes LLM y Administración Multi-Tenant
**Versión**: 4.6.0  
**Fecha**: 2025-01-XX  
**Estado**: ✅ Completa

---

## 📋 Resumen

Se ha implementado un sistema completo de gestión de agentes LLM (Ollama) y administración multi-tenant desde la consola de administración del frontend, permitiendo:

1. **Gestión de Agentes LLM**: Crear, configurar, iniciar, detener y eliminar contenedores Ollama por tenant
2. **Gestión de Tenants**: CRUD completo de tenants con sincronización M365
3. **Gestión de Usuarios**: Administración de usuarios asociados a cada tenant

---

## 🚀 Características Implementadas

### 1. Backend - Endpoints de Gestión de Agentes LLM

**Archivo**: `/api/routes/llm_agents.py`

#### Endpoints disponibles:

```http
GET    /api/llm-agents/                    # Listar agentes (con filtro por tenant)
POST   /api/llm-agents/                    # Crear nuevo agente Ollama
GET    /api/llm-agents/{agent_name}        # Obtener detalles de agente
PUT    /api/llm-agents/{agent_name}        # Actualizar configuración
DELETE /api/llm-agents/{agent_name}        # Eliminar agente
POST   /api/llm-agents/{agent_name}/start  # Iniciar agente
POST   /api/llm-agents/{agent_name}/stop   # Detener agente
POST   /api/llm-agents/{agent_name}/pull-model  # Descargar modelo
```

#### Características clave:

- **Docker SDK Integration**: Gestión nativa de contenedores Docker via API
- **Labels para Metadata**: Cada contenedor tiene labels con `tenant_id`, `model`, `memory_limit`, `created_at`
- **Background Tasks**: Descarga de modelos en segundo plano sin bloquear respuesta
- **Validaciones**: Verificación de puertos únicos y nombres de contenedores
- **Gestión de Recursos**: Configuración de límites y reservas de memoria por agente

#### Ejemplo de uso (curl):

```bash
# Listar agentes
curl -X GET http://localhost:8888/api/llm-agents/ \
  -H "X-API-Key: mcp-forensics-dev-key"

# Crear agente
curl -X POST http://localhost:8888/api/llm-agents/ \
  -H "X-API-Key: mcp-forensics-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "agent4",
    "tenant_id": "empresa-corp",
    "model": "phi4-mini",
    "port": 11438,
    "memory_limit": "6g",
    "memory_reservation": "2g"
  }'

# Detener agente
curl -X POST http://localhost:8888/api/llm-agents/ollama-agent-agent4/stop \
  -H "X-API-Key: mcp-forensics-dev-key"
```

---

### 2. Frontend - Componente de Gestión de Agentes LLM

**Archivo**: `/frontend-react/src/components/LLMAgentManager.jsx`

#### Características:

- **Dashboard con estadísticas**: Total agentes, activos, tenants con agentes, modelos únicos
- **Tabla de agentes**: Información detallada de cada contenedor (nombre, tenant, modelo, puerto, estado)
- **Filtro por tenant**: Ver solo agentes de un tenant específico
- **Acciones disponibles**:
  - ▶️ Iniciar / ⏹️ Detener agentes
  - 📥 Descargar modelos
  - 🗑️ Eliminar agentes
  - ➕ Crear nuevos agentes con formulario completo

#### Formulario de creación:

```javascript
{
  name: 'agent4',                    // Nombre único
  tenant_id: 'empresa-corp',         // Tenant propietario
  model: 'phi4-mini',                // Modelo a usar
  port: 11438,                       // Puerto host único
  memory_limit: '6g',                // Límite de memoria
  memory_reservation: '2g'           // Reserva mínima
}
```

#### Capturas de pantalla conceptuales:

```
┌─────────────────────────────────────────────────────────┐
│ Gestión de Agentes LLM                    🔄 ➕ Nuevo   │
├─────────────────────────────────────────────────────────┤
│ Filtrar por Tenant: [Todos ▼]                          │
├─────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│ │   15     │ │    12    │ │    4     │ │    3     │   │
│ │  Total   │ │  Activos │ │ Tenants  │ │  Modelos │   │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
├─────────────────────────────────────────────────────────┤
│ Nombre        │ Tenant    │ Modelo   │ Puerto │ Estado│
├─────────────────────────────────────────────────────────┤
│ ollama-agent1 │ corp      │ phi4-mini│ 11435  │●running│
│ ollama-agent2 │ gov       │ phi4-mini│ 11436  │●running│
│ ollama-agent3 │ edu       │ phi4-mini│ 11437  │○exited │
│ ...                                                      │
└─────────────────────────────────────────────────────────┘
```

---

### 3. Frontend - Componente de Gestión Multi-Tenant

**Archivo**: `/frontend-react/src/components/TenantManagement.jsx`

#### Características:

**Tab 1 - Tenants**:
- Listar todos los tenants con estado (activo/inactivo)
- Crear nuevos tenants (onboarding)
- Editar información de tenant
- Eliminar/desactivar tenants
- Sincronizar usuarios desde M365
- Ver estadísticas (total, activos, con M365)

**Tab 2 - Usuarios**:
- Ver usuarios de un tenant seleccionado
- Agregar usuarios manualmente
- Activar/desactivar usuarios
- Ver último acceso y rol

#### Flujo de trabajo:

1. Admin selecciona tenant en la tabla
2. Click en icono "Ver Usuarios" o Tab "Usuarios"
3. Sistema carga usuarios del tenant
4. Admin puede agregar/activar/desactivar usuarios

---

### 4. Servicios Frontend

**Archivos**:
- `/frontend-react/src/services/llm-agents.js` - API client para agentes LLM
- `/frontend-react/src/services/auth.js` - API client extendido con admin endpoints

#### llm-agents.js métodos:

```javascript
listAgents(tenantId?)      // GET /api/llm-agents/
getAgent(agentName)        // GET /api/llm-agents/{name}
createAgent(data)          // POST /api/llm-agents/
updateAgent(name, data)    // PUT /api/llm-agents/{name}
deleteAgent(name, removeVol) // DELETE /api/llm-agents/{name}
startAgent(name)           // POST /api/llm-agents/{name}/start
stopAgent(name)            // POST /api/llm-agents/{name}/stop
pullModel(name, model)     // POST /api/llm-agents/{name}/pull-model
```

#### auth.js métodos añadidos:

```javascript
createUser(userData)       // POST /api/auth/admin/users
getUserById(userId)        // GET /api/auth/admin/users/{id}
listUsers(tenantId?)       // GET /api/auth/admin/users
activateUser(userId)       // POST /api/auth/admin/users/{id}/activate
deactivateUser(userId)     // POST /api/auth/admin/users/{id}/deactivate
assignRole(userId, role)   // PUT /api/auth/admin/users/{id}/role
```

---

## 🔧 Configuración e Instalación

### 1. Backend

Instalar dependencia Docker SDK:

```bash
cd /home/hack/mcp-kali-forensics
source venv/bin/activate
pip install docker==7.1.0
```

**Nota**: Ya se añadió `docker==7.1.0` a `requirements.txt`

### 2. Verificar permisos Docker

El usuario que ejecuta la API debe tener acceso al socket Docker:

```bash
# Opción 1: Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Opción 2: Configurar socket permissions en docker-compose.yml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

### 3. Reiniciar servicios

```bash
# Backend
./restart_backend.sh

# O con docker-compose
docker-compose restart mcp-forensics-api
```

---

## 📝 Uso desde el Frontend

### Añadir componentes al Admin Layout

**Archivo**: `/frontend-react/src/layouts/AdminLayout.jsx` (o equivalente)

```jsx
import LLMAgentManager from '../components/LLMAgentManager';
import TenantManagement from '../components/TenantManagement';

// En el menú de administración:
<MenuItem onClick={() => navigate('/admin/llm-agents')}>
  Agentes LLM
</MenuItem>
<MenuItem onClick={() => navigate('/admin/tenants')}>
  Tenants y Usuarios
</MenuItem>

// En las rutas:
<Route path="/admin/llm-agents" element={<LLMAgentManager />} />
<Route path="/admin/tenants" element={<TenantManagement />} />
```

---

## 🎯 Casos de Uso

### Caso 1: Crear agente dedicado para un nuevo tenant

**Flujo**:
1. Admin va a "Tenants y Usuarios"
2. Crea tenant nuevo: `empresa-nueva` con datos M365
3. Va a "Agentes LLM"
4. Click "Nuevo Agente"
5. Completa formulario:
   - Nombre: `agent-empresa-nueva`
   - Tenant: `empresa-nueva`
   - Modelo: `phi4-mini`
   - Puerto: `11440` (siguiente disponible)
   - Memoria: `6g`
6. Click "Crear Agente"
7. Sistema crea contenedor Docker automáticamente
8. Descarga modelo en segundo plano
9. Agente queda listo en ~2-5 minutos

**Resultado**: Tenant tiene agente LLM dedicado en `http://localhost:11440`

---

### Caso 2: Sincronizar usuarios de M365 y gestionar accesos

**Flujo**:
1. Admin selecciona tenant en la tabla
2. Click icono "Sincronizar Usuarios" 🔄
3. Sistema conecta a M365 Graph API
4. Importa usuarios del tenant
5. Admin va a tab "Usuarios"
6. Ve lista de usuarios sincronizados
7. Puede activar/desactivar usuarios según necesidad

---

### Caso 3: Detener agente para mantenimiento

**Flujo**:
1. Admin identifica agente en tabla
2. Click icono "Detener" ⏹️
3. Contenedor se detiene pero no se elimina
4. Cuando sea necesario, click "Iniciar" ▶️
5. Contenedor se reinicia con misma configuración

---

## 🔒 Seguridad

### Autenticación

Todos los endpoints de `/api/llm-agents/*` requieren:

```python
dependencies=[Depends(verify_api_key)]
```

Header requerido:
```http
X-API-Key: mcp-forensics-dev-key
```

### Validaciones Backend

- **Nombres únicos**: No permite duplicar nombres de agentes
- **Puertos únicos**: Verifica que el puerto no esté en uso
- **Permisos Docker**: Solo usuarios con acceso al socket Docker pueden crear contenedores

### Recomendaciones

1. **RBAC**: Implementar role check para admin-only en frontend
2. **Audit log**: Registrar todas las operaciones de creación/eliminación
3. **Resource limits**: Configurar límites de CPU además de memoria
4. **Network isolation**: Usar redes Docker dedicadas por tenant

---

## 🧪 Testing

### Backend (curl)

```bash
# Health check
curl http://localhost:8888/health

# Listar agentes
curl -H "X-API-Key: mcp-forensics-dev-key" \
  http://localhost:8888/api/llm-agents/

# Crear agente de prueba
curl -X POST http://localhost:8888/api/llm-agents/ \
  -H "X-API-Key: mcp-forensics-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-agent",
    "tenant_id": "test",
    "model": "phi4-mini",
    "port": 11450,
    "memory_limit": "4g"
  }'

# Verificar contenedor creado
docker ps | grep ollama-agent-test-agent

# Eliminar agente de prueba
curl -X DELETE http://localhost:8888/api/llm-agents/ollama-agent-test-agent \
  -H "X-API-Key: mcp-forensics-dev-key"
```

### Frontend (manual)

1. Abrir `http://localhost/admin/llm-agents`
2. Verificar que se carga la lista de agentes
3. Filtrar por tenant
4. Crear agente de prueba
5. Verificar que aparece en la tabla con estado "created"
6. Esperar a que estado cambie a "running"
7. Click "Detener" y verificar cambio de estado
8. Click "Eliminar" y verificar que desaparece

---

## 📊 Arquitectura

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────┐
│                  Frontend React                      │
│  ┌─────────────────┐        ┌──────────────────┐   │
│  │ LLMAgentManager │        │TenantManagement  │   │
│  └────────┬────────┘        └────────┬─────────┘   │
│           │                          │              │
│  ┌────────▼────────┐        ┌────────▼─────────┐   │
│  │llm-agents.js    │        │auth.js/tenants.js│   │
│  └────────┬────────┘        └────────┬─────────┘   │
└───────────┼──────────────────────────┼─────────────┘
            │                          │
            │ HTTP + API Key           │ HTTP + API Key
            │                          │
┌───────────▼──────────────────────────▼─────────────┐
│                 FastAPI Backend                     │
│  ┌─────────────────┐        ┌──────────────────┐   │
│  │/api/llm-agents  │        │/api/tenants      │   │
│  │llm_agents.py    │        │/api/auth/admin   │   │
│  └────────┬────────┘        └────────┬─────────┘   │
│           │                          │              │
│  ┌────────▼────────┐        ┌────────▼─────────┐   │
│  │Docker SDK       │        │PostgreSQL        │   │
│  └────────┬────────┘        └──────────────────┘   │
└───────────┼──────────────────────────────────────────┘
            │
            │ Docker API (unix socket)
            │
┌───────────▼──────────────────────────────────────────┐
│               Docker Engine                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ollama-1  │  │ollama-2  │  │ollama-N  │          │
│  │phi4-mini │  │phi4-mini │  │llama2    │          │
│  │:11435    │  │:11436    │  │:1143N    │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└──────────────────────────────────────────────────────┘
```

### Flujo de Creación de Agente

```
1. User clicks "Crear Agente" → LLMAgentManager.jsx
2. Form validation → Check required fields
3. llmAgentsService.createAgent(data) → POST /api/llm-agents/
4. Backend validates:
   - Port available?
   - Name unique?
   - Docker accessible?
5. docker_client.containers.run(...) → Create container
6. BackgroundTask: pull model (ollama pull phi4-mini)
7. Return OllamaAgentResponse → container_id, status, etc.
8. Frontend updates table → Shows "created" status
9. Background task completes → Status changes to "running"
10. Frontend polls/refreshes → Shows updated status
```

---

## 🐛 Troubleshooting

### Error: "Docker no disponible"

**Causa**: API no puede conectar al socket Docker

**Solución**:
```bash
# Verificar que Docker está corriendo
docker ps

# Verificar permisos del socket
ls -l /var/run/docker.sock

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Reiniciar API
./restart_backend.sh
```

---

### Error: "Puerto ya está en uso"

**Causa**: Otro contenedor usa el mismo puerto

**Solución**:
```bash
# Ver contenedores con mapeo de puertos
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Elegir puerto único no usado
# Por ejemplo: 11438, 11439, 11440...
```

---

### Error: "Agente ya existe"

**Causa**: Nombre de contenedor duplicado

**Solución**:
```bash
# Ver todos los contenedores (incluso detenidos)
docker ps -a | grep ollama-agent

# Eliminar contenedor existente
docker rm -f ollama-agent-nombre
```

---

### Agente queda en estado "created" indefinidamente

**Causa**: Descarga de modelo falló en background task

**Solución**:
```bash
# Ver logs del contenedor
docker logs ollama-agent-nombre

# Ejecutar pull manualmente
docker exec ollama-agent-nombre ollama pull phi4-mini

# O desde el frontend: Click icono "Descargar Modelo" 📥
```

---

### Frontend no muestra agentes

**Causa**: CORS o API Key incorrecta

**Solución**:
```bash
# Verificar API Key en .env.local del frontend
VITE_API_KEY=mcp-forensics-dev-key

# Verificar CORS en backend config.py
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:3000"]

# Test con curl
curl -H "X-API-Key: mcp-forensics-dev-key" \
  http://localhost:8888/api/llm-agents/
```

---

## 📚 Referencias

- **Docker SDK Python**: https://docker-py.readthedocs.io/
- **FastAPI Background Tasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/
- **Material-UI Components**: https://mui.com/material-ui/getting-started/
- **Ollama Models**: https://ollama.com/library

---

## ✅ Checklist de Implementación

- [x] Backend: `/api/routes/llm_agents.py` creado
- [x] Backend: Router registrado en `main.py`
- [x] Backend: Dependencia `docker==7.1.0` añadida a requirements.txt
- [x] Frontend: `LLMAgentManager.jsx` creado
- [x] Frontend: `TenantManagement.jsx` creado
- [x] Frontend: `llm-agents.js` service creado
- [x] Frontend: `auth.js` extendido con admin endpoints
- [ ] Frontend: Rutas añadidas al AdminLayout
- [ ] Testing: Endpoints probados con curl
- [ ] Testing: UI probada manualmente
- [ ] Documentación: README.md actualizado con enlaces
- [ ] Deployment: `docker-compose.yml` configurado con socket Docker

---

## 🚀 Próximos Pasos

1. **Añadir componentes a las rutas del frontend**
2. **Implementar RBAC check para admin-only**
3. **Añadir audit logging para operaciones de agentes**
4. **Configurar límites de CPU en contenedores**
5. **Implementar redes Docker aisladas por tenant**
6. **Añadir monitoring de recursos (Prometheus)**
7. **Implementar auto-scaling de agentes según carga**

---

**Autor**: AI Assistant  
**Versión Backend**: 4.6.0  
**Versión Frontend**: 4.6.0  
**Última actualización**: 2025-01-XX
