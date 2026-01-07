# 🔴 PLAN DE ELIMINACIÓN DE DATOS MOCK - MCP v4.1

## Análisis Realizado: 2025-12-05

---

## 📊 RESUMEN EJECUTIVO

Se identificaron **4 archivos JSON mock** y **múltiples variables SIMULATED_*** en rutas que deben ser reemplazados por datos reales de la base de datos SQLite y servicios en vivo.

### Archivos Mock a Eliminar

| Archivo | Líneas | Contenido | Acción |
|---------|--------|-----------|--------|
| `api/mock/agents.json` | 106 | Agentes simulados | Migrar a tabla `agents` |
| `api/mock/capture.json` | 117 | Capturas de red | Migrar a tabla `tool_executions` |
| `api/mock/commands.json` | 146 | Plantillas de comandos | Mantener como config (no mock) |
| `api/mock/investigations.json` | 195 | Casos simulados | Migrar a tabla `cases` |

### Variables Simuladas en Código

| Archivo | Variable | Líneas | Acción |
|---------|----------|--------|--------|
| `api/routes/agents.py` | `SIMULATED_AGENTS` | 68-106 | Reemplazar por `AgentManager.list_agents()` |
| `api/routes/agents.py` | `AGENT_TYPES` | 108-127 | Mantener como config estática |
| `api/routes/investigations.py` | `SIMULATED_INVESTIGATIONS` | 78-130 | Reemplazar por `CaseService` |
| `api/routes/investigations.py` | `SIMULATED_IOCS` | 132-138 | Reemplazar por tabla `iocs` |
| `api/routes/investigations.py` | `SIMULATED_EVIDENCE` | 140-146 | Reemplazar por tabla `evidence` |
| `api/routes/investigations.py` | `SIMULATED_TIMELINE` | 148-176 | Reemplazar por tabla `timeline_events` |
| `api/routes/investigations.py` | `SIMULATED_GRAPH` | 178-195 | Reemplazar por `GraphBuilder` |

---

## 🔄 OPCIÓN A: MIGRACIÓN GRADUAL (Recomendada)

### Fase 1: Base de Datos (Semana 1)
1. ✅ Verificar que tablas SQLite existen
2. Migrar datos mock a tablas iniciales
3. Crear seeders para datos de demostración

### Fase 2: Servicios (Semana 1-2)
1. Actualizar `AgentManager` para consultar DB
2. Actualizar `CaseService` para consultar DB
3. Implementar `EvidenceService` real

### Fase 3: Rutas (Semana 2)
1. Reemplazar `SIMULATED_*` por llamadas a servicios
2. Eliminar archivos mock de `api/mock/`
3. Actualizar tests

### Fase 4: Validación (Semana 2-3)
1. Tests de integración
2. Verificar flujo completo
3. Documentar endpoints actualizados

---

## ⚡ OPCIÓN B: MIGRACIÓN DIRECTA (Rápida)

### Ejecutar Todo en 1 Sprint
1. Eliminar archivos mock inmediatamente
2. Actualizar todas las rutas de golpe
3. Riesgo: Posibles errores si faltan datos

### Ventajas
- Rápido
- Sin código legacy

### Desventajas
- Mayor riesgo de bugs
- Requiere datos reales inmediatos

---

## 🎯 OPCIÓN C: HYBRID MODE (Flexible)

### Mantener Fallback
```python
async def get_agents():
    db_agents = await AgentManager.list_agents()
    if not db_agents:
        logger.warning("No agents in DB, using demo data")
        return DEMO_AGENTS  # Datos de demostración, no mock
    return db_agents
```

### Ventajas
- Funcional sin configuración
- Permite demo del producto
- Transición suave

### Desventajas
- Código adicional
- Puede ocultar problemas de configuración

---

## 📋 ARCHIVOS A MODIFICAR

### 1. Eliminar Mock Directory
```bash
rm -rf api/mock/
```

### 2. Actualizar Rutas

#### `api/routes/agents.py`
- Eliminar: `SIMULATED_AGENTS` (líneas 68-106)
- Reemplazar por: `from api.services.agent_manager import agent_manager`
- Actualizar endpoints para usar `agent_manager.list_agents()`

#### `api/routes/investigations.py`
- Eliminar: Todas las variables `SIMULATED_*` (líneas 78-195)
- Reemplazar por: Servicios de DB

### 3. Verificar Servicios Existentes

| Servicio | Estado | Usa DB Real |
|----------|--------|-------------|
| `dashboard_data.py` | ✅ Funcional | ✅ SQLite |
| `agent_manager.py` | ✅ Implementado | ⚠️ Pendiente conexión |
| `executor_engine.py` | ✅ Implementado | ⚠️ Pendiente conexión |
| `correlation_engine.py` | ✅ Implementado | ⚠️ Pendiente conexión |
| `soar_engine.py` | ✅ Implementado | ⚠️ Pendiente conexión |
| `graph_enricher.py` | ✅ Implementado | ⚠️ Pendiente conexión |

---

## 🚀 RECOMENDACIÓN FINAL

### Implementar OPCIÓN C (Hybrid Mode)

**Razón**: Permite demostración funcional mientras se completa la integración real.

### Pasos Inmediatos:
1. Crear `api/config/demo_data.py` con datos de demostración etiquetados
2. Eliminar `api/mock/` (datos obsoletos)
3. Actualizar rutas con fallback a demo data
4. Marcar endpoints con `"data_source": "demo"` cuando usen fallback
5. Logging cuando se usa demo data

### Comando de Verificación:
```bash
curl http://localhost:8080/api/agents/ | jq '.data_source'
# Debería mostrar "real" o "demo"
```

---

## 📁 ESTRUCTURA DE DOCUMENTACIÓN PROPUESTA

```
docs/
├── architecture/
│   ├── SYSTEM_OVERVIEW.md
│   ├── DATA_FLOW.md
│   └── SECURITY_MODEL.md
├── agents/
│   ├── RED_AGENT.md
│   ├── BLUE_AGENT.md
│   ├── PURPLE_AGENT.md
│   └── AGENT_MATRIX.md
├── playbooks/
│   ├── RED_PLAYBOOKS.md
│   ├── BLUE_PLAYBOOKS.md
│   ├── PURPLE_PLAYBOOKS.md
│   └── SOAR_INTEGRATION.md
├── api/
│   ├── ENDPOINTS_V41.md
│   ├── AUTHENTICATION.md
│   └── WEBSOCKETS.md
└── MOCK_DATA_ELIMINATION_PLAN.md  ← Este archivo
```

---

## ✅ CHECKLIST DE ELIMINACIÓN

- [ ] Crear `api/config/demo_data.py`
- [ ] Migrar datos útiles de mock a demo_data
- [ ] Actualizar `api/routes/agents.py`
- [ ] Actualizar `api/routes/investigations.py`
- [ ] Eliminar `api/mock/` directorio
- [ ] Actualizar tests
- [ ] Verificar endpoints con `data_source`
- [ ] Documentar cambios en CHANGELOG

---

**Autor**: MCP Forensics Team  
**Fecha**: 2025-12-05  
**Versión**: 4.1
