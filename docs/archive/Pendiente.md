# 📋 TAREAS PENDIENTES - MCP Kali Forensics

**Última actualización**: 2025-12-05  
**Estado del proyecto**: 🟡 En desarrollo activo

---

## 📊 RESUMEN DE PROGRESO

| Módulo | Estado | Progreso | Prioridad |
|--------|--------|----------|-----------|
| React Frontend Base | ✅ Completado | 100% | P0 |
| Mobile Agents UI | 🟡 Parcial | 70% | P0 |
| Investigaciones UI | 🟡 Parcial | 60% | P0 |
| Active Investigation UI | 🟡 Parcial | 65% | P0 |
| Backend API Endpoints | 🔴 Pendiente | 30% | P0 |
| WebSocket Real-time | 🔴 Pendiente | 10% | P1 |
| Grafo de Ataque | 🔴 Pendiente | 20% | P1 |

---

## 🔌 MOBILE AGENTS

### ✅ Completado
- [x] Componente `MobileAgents.jsx` creado (421 líneas)
- [x] UI de listado de agentes con estado online/offline
- [x] Soporte visual para 3 tipos de agentes (Intune, OSQuery, Velociraptor)
- [x] Tabs para navegación (Agentes / Deploy / Colecciones)
- [x] Modal de deploy de agentes
- [x] Plantillas de comandos predefinidas

### 🔴 Pendiente

#### Backend API
- [ ] `POST /api/agents/deploy` - Deploy de agente a endpoint
  ```python
  # Requiere implementar en api/routes/agents.py
  @router.post("/deploy")
  async def deploy_agent(request: DeployAgentRequest):
      # Generar link de instalación según tipo (Intune/OSQuery/Velociraptor)
      # Retornar: download_url, install_script, instructions
  ```

- [ ] `GET /api/agents/` - Listar agentes conectados
  ```python
  @router.get("/")
  async def list_agents():
      # Obtener lista de agentes desde DB/cache
      # Incluir: id, name, type, status, lastSeen, osVersion, ipAddress
  ```

- [ ] `POST /api/agents/{id}/execute` - Ejecutar comando remoto
  ```python
  @router.post("/{agent_id}/execute")
  async def execute_command(agent_id: str, command: CommandRequest):
      # Enviar comando al agente via Intune API / OSQuery / Velociraptor
      # Retornar: stdout, stderr, exit_code
  ```

- [ ] `GET /api/agents/{id}/status` - Estado de agente
- [ ] `DELETE /api/agents/{id}` - Desregistrar agente
- [ ] `POST /api/agents/{id}/collect` - Iniciar recolección forense

#### Integraciones Externas
- [ ] **Microsoft Intune Integration**
  - [ ] Autenticación con Graph API para Intune
  - [ ] Script de ejecución remota via Intune PowerShell
  - [ ] Recolección de dispositivos registrados
  - [ ] Wrapper para `Invoke-IntuneManagedDeviceAction`

- [ ] **OSQuery Integration**
  - [ ] Fleet manager o TLS server para agentes
  - [ ] Generador de instaladores con config preconfigurada
  - [ ] Ejecución de queries SQL remotas
  - [ ] Esquema de tablas disponibles por OS

- [ ] **Velociraptor Integration**
  - [ ] Conexión a servidor Velociraptor existente
  - [ ] Generador de clientes con certificados
  - [ ] Ejecución de artifacts VQL
  - [ ] Descarga de colecciones completadas

#### UI/UX Pendiente
- [ ] Página de detalle de agente individual
- [ ] Historial de comandos ejecutados por agente
- [ ] Gráficos de actividad del agente
- [ ] Notificaciones push cuando agente conecta/desconecta
- [ ] Filtros avanzados (por tipo, estado, OS)

---

## 🔍 INVESTIGACIONES

### ✅ Completado
- [x] Componente `Investigations.jsx` creado (320 líneas)
- [x] Listado de casos con filtros y búsqueda
- [x] Tabs por estado (Todos, Abiertos, En Progreso, Resueltos, Cerrados)
- [x] Badges de severidad y estado
- [x] Integración con Redux store
- [x] Mock data para desarrollo

### 🔴 Pendiente

#### Backend API
- [ ] `GET /api/cases/` - Ya existe, verificar paginación
- [ ] `GET /api/cases/{id}` - Detalle completo del caso
  ```python
  # Debe incluir:
  # - Información básica del caso
  # - Lista de IOCs asociados
  # - Timeline de eventos
  # - Evidencia recolectada
  # - Notas y comentarios
  # - Historial de cambios
  ```

- [ ] `POST /api/cases/` - Crear caso con validación completa
- [ ] `PUT /api/cases/{id}` - Actualizar caso
- [ ] `DELETE /api/cases/{id}` - Eliminar caso (soft delete)
- [ ] `POST /api/cases/{id}/iocs` - Agregar IOCs al caso
- [ ] `POST /api/cases/{id}/evidence` - Subir evidencia
- [ ] `GET /api/cases/{id}/timeline` - Timeline de eventos

#### UI/UX Pendiente
- [ ] **Página de detalle de caso**
  - [ ] Vista completa con tabs (Resumen, IOCs, Evidencia, Timeline, Notas)
  - [ ] Editor de descripción/notas con markdown
  - [ ] Upload de archivos de evidencia
  - [ ] Asignación de usuarios

- [ ] **Formulario de nuevo caso**
  - [ ] Wizard multi-paso
  - [ ] Selección de tenant M365
  - [ ] Campos: nombre, descripción, severidad, asignado
  - [ ] Validación en tiempo real

- [ ] **Grafo de ataque integrado**
  - [ ] Visualización Cytoscape.js del caso
  - [ ] Nodos: IPs, Usuarios, Archivos, Procesos
  - [ ] Edges: Relaciones y timeline
  - [ ] Export a imagen/PDF

- [ ] **Timeline visual**
  - [ ] Línea de tiempo interactiva
  - [ ] Filtros por tipo de evento
  - [ ] Zoom in/out temporal
  - [ ] Marcadores de eventos críticos

---

## ⚡ ACTIVE INVESTIGATION

### ✅ Completado
- [x] Componente `ActiveInvestigation.jsx` creado (328 líneas)
- [x] Selector de dispositivo con estado online/offline
- [x] Selector de sistema operativo (Windows/Mac/Linux)
- [x] Editor de comandos con textarea
- [x] Plantillas de comandos organizadas por categoría
- [x] Área de output con copy to clipboard
- [x] Historial de comandos ejecutados
- [x] Panel lateral con plantillas predefinidas

### 🔴 Pendiente

#### Backend API
- [ ] `POST /api/active-investigation/execute` - Ejecutar comando
  ```python
  @router.post("/execute")
  async def execute_active_command(request: ExecuteCommandRequest):
      # Validar dispositivo está online
      # Ejecutar comando via agente (Intune/OSQuery/Velociraptor)
      # Retornar streaming output via WebSocket
      # Guardar en historial de auditoría
  ```

- [ ] `GET /api/active-investigation/history` - Historial de comandos
- [ ] `POST /api/active-investigation/capture/network` - Iniciar captura de red
- [ ] `POST /api/active-investigation/capture/memory` - Dump de memoria
- [ ] `POST /api/active-investigation/yara-scan` - Escaneo YARA en vivo

#### WebSocket Real-time
- [ ] **Implementar WebSocket endpoint**
  ```python
  # api/routes/websocket.py
  @router.websocket("/ws/active")
  async def active_investigation_ws(websocket: WebSocket):
      await websocket.accept()
      # Streaming de output de comandos
      # Notificaciones de estado de agentes
      # Updates en tiempo real
  ```

- [ ] Cliente WebSocket en React
  ```javascript
  // src/hooks/useWebSocket.js
  const { status, messages, send } = useWebSocket('/ws/active');
  ```

#### Network Capture
- [ ] Componente `NetworkCapture.jsx`
  - [ ] Iniciar/detener captura
  - [ ] Filtros BPF (host, port, protocol)
  - [ ] Visualización de paquetes en tiempo real
  - [ ] Exportar a PCAP
  - [ ] Estadísticas de tráfico

#### Memory Analysis
- [ ] Componente `MemoryCapture.jsx`
  - [ ] Trigger de dump de memoria
  - [ ] Progreso de transferencia
  - [ ] Análisis con Volatility 3
  - [ ] Listado de procesos/conexiones extraídas

#### YARA Scanning
- [ ] Componente `YARAScanner.jsx`
  - [ ] Selección de reglas YARA
  - [ ] Escaneo de paths remotos
  - [ ] Resultados con matches
  - [ ] Quarantine de archivos detectados

---

## 📊 GRAFO DE ATAQUE

### ✅ Completado
- [x] Cytoscape.js incluido en dependencias
- [x] Ruta `/graph` definida en router
- [x] Placeholder de página creado

### 🔴 Pendiente

#### Componentes UI
- [ ] `AttackGraph.jsx` - Visualización principal
  ```jsx
  // Nodos: IP, Usuario, Archivo, Proceso, Dominio, Hash
  // Edges: connected_to, executed, downloaded, communicated
  // Layouts: fcose, dagre, cose
  ```

- [ ] `GraphControls.jsx` - Controles de zoom/layout
- [ ] `NodeDetails.jsx` - Panel de detalles de nodo seleccionado
- [ ] `GraphFilters.jsx` - Filtros por tipo de nodo/edge
- [ ] `GraphExport.jsx` - Export a PNG/SVG/JSON

#### Backend API
- [ ] `GET /api/graph/{case_id}` - Obtener grafo del caso
  ```python
  @router.get("/{case_id}")
  async def get_case_graph(case_id: str):
      # Retornar nodos y edges del caso
      # Formato: { nodes: [...], edges: [...] }
  ```

- [ ] `POST /api/graph/{case_id}/nodes` - Agregar nodo manual
- [ ] `POST /api/graph/{case_id}/edges` - Agregar relación
- [ ] `DELETE /api/graph/{case_id}/nodes/{node_id}` - Eliminar nodo
- [ ] `POST /api/graph/{case_id}/auto-generate` - Generar grafo automáticamente desde IOCs

#### Integración con Evidence
- [ ] Extracción automática de nodos desde archivos de evidencia M365
- [ ] Parser de logs de Sparrow/Hawk para generar grafo
- [ ] Correlación automática de IOCs

---

## 🔧 BACKEND GENERAL

### Nuevos Routers Pendientes
- [ ] `api/routes/agents.py` - Gestión de agentes remotos
- [ ] `api/routes/active_investigation.py` - Investigación activa
- [ ] `api/routes/websocket.py` - WebSocket endpoints

### Servicios Pendientes
- [ ] `api/services/intune.py` - Integración Microsoft Intune
- [ ] `api/services/osquery.py` - Integración OSQuery
- [ ] `api/services/velociraptor.py` - Integración Velociraptor
- [ ] `api/services/network_capture.py` - Captura de red
- [ ] `api/services/memory_analysis.py` - Análisis de memoria

### Base de Datos
- [ ] Tabla `agents` - Registro de agentes conectados
- [ ] Tabla `command_history` - Historial de comandos ejecutados
- [ ] Tabla `network_captures` - Capturas de red
- [ ] Tabla `memory_dumps` - Dumps de memoria
- [ ] Migración Alembic para nuevas tablas

---

## 📱 MEJORAS DE UX

### Responsive Design
- [ ] Hamburger menu para mobile
- [ ] Sidebar colapsable en tablet
- [ ] Touch-friendly buttons

### Accesibilidad
- [ ] Keyboard navigation
- [ ] ARIA labels
- [ ] Color contrast improvements
- [ ] Screen reader support

### Performance
- [ ] Lazy loading de componentes
- [ ] Virtualización de listas largas
- [ ] Caché de queries con React Query

### Notificaciones
- [ ] Toast notifications funcionales
- [ ] Push notifications del browser
- [ ] Sonidos para alertas críticas

---

## 🧪 TESTING

### Frontend
- [ ] Tests unitarios de componentes con Vitest
- [ ] Tests de integración con React Testing Library
- [ ] E2E tests con Playwright/Cypress

### Backend
- [ ] Tests de endpoints con pytest
- [ ] Mocks de servicios externos (Intune, OSQuery)
- [ ] Tests de WebSocket

---

## 📚 DOCUMENTACIÓN

### Pendiente
- [ ] API Reference (Swagger/OpenAPI actualizado)
- [ ] Guía de deployment a producción
- [ ] Manual de usuario
- [ ] Arquitectura técnica actualizada
- [ ] Changelog automatizado

---

## 🎯 PRIORIDADES RECOMENDADAS

### 🔴 Crítico (Esta semana)
1. Implementar `api/routes/agents.py` con endpoints básicos
2. Conectar UI de MobileAgents con API real
3. Implementar detalle de caso en Investigaciones
4. WebSocket básico para output de comandos

### 🟠 Alto (Próximas 2 semanas)
1. Integración completa con Microsoft Intune
2. Grafo de ataque funcional con Cytoscape
3. Network capture básico
4. Formulario de nuevo caso

### 🟡 Medio (Próximo mes)
1. Integración OSQuery
2. Integración Velociraptor
3. Memory analysis con Volatility
4. Timeline visual interactivo

### 🟢 Bajo (Backlog)
1. Tests completos
2. Documentación detallada
3. Mejoras de accesibilidad
4. Optimizaciones de performance

---

## 📅 ESTIMACIÓN DE TIEMPO

| Tarea | Horas Estimadas |
|-------|-----------------|
| Backend API Agents | 16h |
| Backend API Active Investigation | 12h |
| WebSocket Implementation | 8h |
| Intune Integration | 20h |
| OSQuery Integration | 12h |
| Velociraptor Integration | 16h |
| Grafo de Ataque | 24h |
| Detalle de Caso UI | 12h |
| Network Capture | 16h |
| Memory Analysis | 20h |
| Testing | 24h |
| **TOTAL** | **~180 horas** |

Con 1 desarrollador tiempo completo: **~5-6 semanas**  
Con 2 desarrolladores: **~3 semanas**

---

## 📞 NOTAS

- Los componentes React están creados con datos mock para desarrollo
- El backend FastAPI está funcional pero necesita nuevos endpoints
- La integración M365 ya está configurada (tenant SINERLEX)
- Las herramientas forenses están instaladas en `/opt/forensics-tools/`

---

*Documento generado: 2025-12-05*  
*Mantener actualizado con cada sprint*
