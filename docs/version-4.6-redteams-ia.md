# 📗 Integración HexStrike AI en plataforma Red Team v4.6

Documento de validación e integración para incorporar **HexStrike AI MCP (v6.0)** como motor de automatización Red Team dentro de la plataforma Jeturing CORE / MCP Kali v4.6.

---

## 1) Validación rápida de la solución

- Arquitectura: MCP server en Python con agentes autónomos, 150+ herramientas ofensivas y endpoints REST (`/api/intelligence/*`, `/api/command`, `/api/processes/*`) + cliente MCP (`hexstrike_mcp.py`) vía FastMCP.
- Operación: despliegue local por `python3 hexstrike_server.py [--port 8888]`, health en `/health`, pruebas con `curl -X POST /api/intelligence/analyze-target`.
- Integraciones soportadas: 5ire, VS Code Copilot, Roo, Cursor, Claude Desktop y cualquier agente MCP; compatible con Chromium/Chrome para Browser Agent.
- Riesgos: alta superficie de ataque (ejecución arbitraria de herramientas), requiere aislamiento, monitoreo y control de permisos.

## 2) Encaje en la arquitectura Jeturing CORE (v4.6)

- Despliegue sugerido: contenedor dedicado `hexstrike-ai` detrás del API Gateway FastAPI actual, con red interna Docker; expone `:8888`.
- Orquestación: el servicio `executor` existente puede invocar HexStrike vía HTTP/MCP para tareas Red Team; streaming/logging sigue usando Redis y WS Router.
- AuthZ: envolver llamadas a HexStrike detrás de RBAC existente (`mcp:redteam:run`, `mcp:redteam:read`) y rate limiting; añadir allowlist de destinos por tenant.
- Evidencia: los outputs de HexStrike se guardan en `evidence/` y se indexan igual que las herramientas forenses (case_id, run_id, tool, severity).

## 3) Flujo operativo Red Team propuesto

1. Crear engagement Red Team (`/redteam/engagements`) asociado a `case_id`.
2. Registrar objetivos (dominios, CIDRs, apps) y reglas de alcance.
3. Selección de estrategia: pedir a HexStrike `/api/intelligence/select-tools` con `analysis_type` y contexto del caso.
4. Ejecución: lanzar `/api/command` o funciones específicas (ej. `nmap_scan`, `ffuf_scan`) vía `hexstrike_mcp.py` o REST; guardar `run_id`.
5. Monitoreo: consultar `/api/processes/list|status` y consumir logs consolidados en WS Router (enviar tail de stdout/stderr del proceso).
6. Resultados: parsear salidas (Nmap, Nuclei, FFUF, SQLMap) y normalizar a `findings` + `artifacts`; correlacionar con Attack Graph.
7. Reporting: generar tarjetas de vulnerabilidad y resumen ejecutivo; marcar FP/TP desde UI.

## 4) Diseño de API de integración (capa Jeturing)

- `POST /redteam/engagements`: crea engagement (scopes, owner, reglas de ROE).
- `POST /redteam/engagements/{id}/plan`: delega en HexStrike `/api/intelligence/select-tools` y guarda plan.
- `POST /redteam/runs`: body `{engagement_id, target, tool, params}` → invoca HexStrike (`/api/command` o función dedicada); responde `{run_id, hexstrike_pid}`.
- `GET /redteam/runs/{run_id}`: estado, PID remoto, métricas `/api/processes/status/{pid}`.
- `POST /redteam/runs/{run_id}/cancel`: proxear `/api/processes/terminate/{pid}`.
- `GET /redteam/findings?engagement_id=`: devuelve hallazgos normalizados (Nuclei → CWE/CVSS, SQLMap → dbms/leak, etc.).
- WebSocket `/ws/redteam/{run_id}`: reenviar logs provenientes del proceso HexStrike (usar cola Redis existente; opcional compresión zstd).

### Ejemplo de payload hacia HexStrike

```bash
curl -X POST http://hexstrike-ai:8888/api/intelligence/analyze-target \
  -H "Content-Type: application/json" \
  -d '{"target":"example.com","analysis_type":"comprehensive","tags":["bugbounty","external"]}'
```

## 5) Diseño de UI (frontend React)

- Vista Engagement: detalle de alcance, reglas de ROE, lista de objetivos y botones "Plan con HexStrike" y "Ejecutar playbook".
- Panel de Ejecución: tablero con tarjetas por run (estado, herramienta, tiempo, PID, scope), barra de progreso y viewer de logs en streaming.
- Hallazgos: tabla con filtros por severidad/CWE, acciones FP/TP, link a evidencia y nodos del Attack Graph; botón "Reproducir" que relanza el comando.
- Monitoreo: widget de telemetría `/api/telemetry` (CPU, RAM, procesos activos) y estado de cache `/api/cache/stats`.
- Auditoría: timeline por engagement con auditoría de quién lanzó qué y con qué parámetros (reutilizar componente de Investigations).

## 6) Diseño de datos / BDD

- `redteam_engagements(id, name, tenant_id, scope, rules_of_engagement, status, created_by, created_at)`
- `redteam_targets(id, engagement_id, type, value, tags, metadata)`
- `redteam_runs(id, engagement_id, target_id, tool, params, hexstrike_pid, status, started_at, finished_at, exit_code)`
- `redteam_findings(id, run_id, title, severity, cwe, cvss, description, evidence_path, recommendation, fp_flag)`
- `redteam_artifacts(id, run_id, kind, path, hash, size, tags)` para reportes, capturas y resultados crudos.
- Índices por `tenant_id`, `engagement_id`, `status` y `severity`; TTL opcional para artefactos grandes.

## 6.1) Convenciones de nombres (redteam-Segrd)

- Todos los artefactos y outputs se guardan con prefijo `redteam-Segrd` y sin nombres de herramientas. Ejemplo: `evidence/redteam-Segrd/RT-EXT-001/run-1002/output.json`.
- Los `run_id`/`finding_id` pueden conservar su estructura interna, pero los archivos/resultados exportables (reportes, logs, adjuntos WS) deben evitar nombres de herramienta explícitos.
- En UI, los listados muestran `redteam-Segrd <engagement/run>` como título del recurso; el detalle interna puede mencionar la herramienta en campos de metadata, no en el nombre visible/exportado.

## 7) Seguridad y compliance

- Ejecutar HexStrike en red aislada y namespace Docker separado; sin acceso a secretos del core.
- Implementar allowlist/denylist de objetivos y comprobación de autorización explícita antes de cada run.
- Registrar comandos efectivos enviados a HexStrike para trazabilidad y reprocesamiento.
- Autenticación mutua entre gateway y HexStrike (mTLS o token estático rotado).
- Validar sanitización de parámetros antes de proxear al MCP server para evitar command injection.

## 8) Despliegue y observabilidad

- Docker Compose: servicio `hexstrike-ai` con `ports: ["8888:8888"]` opcional solo en entornos de demo; en prod solo red interna.
- Healthcheck: `curl http://hexstrike-ai:8888/health` integrado en `start_services.sh`.
- Logs: redirigir stdout de contenedor a Loki/ELK; mapear `/logs/hexstrike` para retención corta.
- Métricas: scrap `/api/telemetry` para CPU/RAM/procesos y exponerlas a Prometheus.
- Backpressure: usar `LoggingQueue` existente con compresión zstd si el volumen de herramientas web es alto (FFUF/Nuclei).

## 9) Checklist de habilitación

- [ ] Contenedor HexStrike desplegado y aislado.
- [ ] Roles RBAC creados (`mcp:redteam:*`) y UI con guardas.
- [ ] Endpoints de integración (`/redteam/*`) disponibles con pruebas de contrato.
- [ ] Streaming de logs funcionando para runs HexStrike.
- [ ] Normalización de hallazgos (CWE/CVSS) y mapeo a Attack Graph.
- [ ] Auditoría de comandos y parámetros almacenada por engagement.

## 10) Próximos pasos

- Piloto interno (Semana 1): usar 1 dominio de prueba y 1 API interna; medir TTR (time-to-result), hallazgos vs baseline manual y estabilidad del streaming.
- Hardening (Semana 1-2): mTLS o token rotado entre gateway y HexStrike; validar allowlist/denylist y guardas RBAC en UI/Backend.
- API/Backend (Semana 2): implementar `/redteam/*` y contrato con HexStrike (`/api/command`, `/api/intelligence/*`, `/api/processes/*`); pruebas de contrato + timeouts.
- Frontend (Semana 2-3): vistas Engagement, Runs y Findings con streaming de logs; acción Reproducir y marcación FP/TP; telemetría básica.
- Normalización y Attack Graph (Semana 3): mapeo Nuclei/SQLMap/FFUF → CWE/CVSS; ingestión a grafo y timeline; export JSON para reportes.
- Operación y SRE (Semana 3): logs centralizados, dashboards de métricas `/api/telemetry`, alertas por tasa de fallos y por run colgado (PID sin progreso).
- Playbooks (Semana 4): plantillas recon/web/cloud que combinan HexStrike + herramientas nativas; parámetros seguros predefinidos por tenant.
- Release candidate (Semana 4): checklist completo, pruebas de regresión con 3 escenarios (externo, webapp, cloud), sign-off de seguridad.
- Evaluar migrar a v7.0 al estar disponible para habilitar deploy en Docker nativo y agentes adicionales; repetir piloto de compatibilidad.

## 11) Guía para integrar otra IA/cliente MCP

- Objetivo: habilitar cualquier LLM/IA compatible con FastMCP (Claude, GPT, Cursor, Roo, Copilot) para orquestar HexStrike de forma controlada.
- Configuración estándar: añadir servidor MCP en el cliente:
  - Comando: `python3 /path/to/hexstrike-ai/hexstrike_mcp.py --server http://hexstrike-ai:8888`
  - Timeout sugerido: 300s; puerto interno `8888` (no exponer público).
- Plantilla de prompt seguro (ejemplo):
  - Rol: "Eres un analista Red Team autorizado. Respeta el alcance: `scope`. Usa solo herramientas listadas y confirma antes de ejecutar acciones destructivas."
  - Input: `{target, scope, constraints, allowed_tools, rate_limit}`
  - Output esperado: plan paso a paso + comandos MCP (no shell directa) + confirmación final.
- Contexto mínimo a enviar:
  - Engagement + scope + ROE
  - Objetivos y credenciales temporales (si aplica)
  - Allowlist/denylist + límites de tiempo y concurrencia
- Guardas:
  - Validar que cada comando referencie `engagement_id` y `target_id`
  - Prohibir pipe a `bash -c` o shells externas; usar solo `/api/command` y funciones expuestas.
  - Límite de procesos simultáneos por tenant y por IA.
- Telemetría y control:
  - Registrar `prompt`, `tools usados`, `params`, `PID`, `run_id`, `duración`, `salida resumida`.
  - Alertar si un plan propone acciones fuera de alcance o sin mapeo a herramientas soportadas.

## 12) Plan de pruebas y KPIs

- Pruebas funcionales:
  - `POST /redteam/engagements` crea y valida reglas de alcance.
  - `POST /redteam/runs` invoca Nmap/Nuclei/FFUF y retorna `run_id + hexstrike_pid`.
  - WebSocket `/ws/redteam/{run_id}` entrega logs en menos de 3s desde inicio del proceso.
  - Cancelación `/redteam/runs/{run_id}/cancel` termina proceso en menos de 5s y marca estado.
- Pruebas de normalización:
  - Nuclei → CWE/CVSS y severidad consistente con UI.
  - SQLMap → DBMS detectado + flags de exfil posible.
  - FFUF → lista de paths válidos, sin false positives conocidos.
- Seguridad:
  - RBAC bloquea ejecución si falta `mcp:redteam:run`.
  - Allowlist rechaza targets fuera de alcance con 403 y auditoría.
  - Sanitización de parámetros: impedir `;`, `&&`, backticks en inputs de herramientas.
- Performance/fiabilidad:
  - TTR (time-to-result) Nmap top-1000: menor a 90s en red interna.
  - Tasa de fallos por herramienta menor a 5% en 10 ejecuciones consecutivas.
  - Streaming estable: sin más de 1% de mensajes perdidos en runs de 10 min.
- KPIs de producto:
  - Precisión de findings vs baseline manual mayor o igual a 90%.
  - Reducción de tiempo de ejecución end-to-end mayor o igual a 5x vs manual.
  - Cierre de FP/TP en UI menor a 2 clics; latencia de telemetría menor a 2s p95.

## 13) Ejemplos de payloads y contratos

### Crear engagement

```bash
POST /redteam/engagements
{
  "name": "RT-EXT-001",
  "tenant_id": "t-123",
  "scope": ["example.com", "api.example.com", "203.0.113.0/24"],
  "rules_of_engagement": ["no_prod_disruption", "no_persistence", "auth_required"],
  "owner": "alice",
  "tags": ["bugbounty","external"]
}
```

### Plan con HexStrike

```bash
POST /redteam/engagements/{id}/plan
{
  "analysis_type": "comprehensive",
  "targets": ["example.com"],
  "constraints": {"rate_limit_rps": 5, "max_parallel": 2},
  "preferred_tools": ["nmap_scan","nuclei_scan","ffuf_scan"]
}
```

### Run (ejemplo FFUF)

```bash
POST /redteam/runs
{
  "engagement_id": "RT-EXT-001",
  "target": "https://api.example.com",
  "tool": "ffuf_scan",
  "params": {
    "wordlist": "/lists/api-endpoints.txt",
    "extensions": "json,js",
    "threads": 20,
    "follow_redirects": true
  }
}
# Respuesta esperada:
{ "run_id": "rt-run-1001", "hexstrike_pid": 4321, "status": "running" }
```

### Hallazgo normalizado (Nuclei)

```json
{
  "id": "finding-9001",
  "run_id": "rt-run-1002",
  "tool": "nuclei",
  "title": "CVE-2023-XXXX - RCE",
  "severity": "critical",
  "cwe": "CWE-78",
  "cvss": 9.8,
  "description": "Remote command execution via vulnerable endpoint",
  "evidence_path": "evidence/RT-EXT-001/nuclei/run-1002/output.json",
  "recommendation": "Apply vendor patch; restrict endpoint",
  "fp_flag": false
}
```

### Evento de log en WebSocket

```json
{
  "run_id": "rt-run-1001",
  "pid": 4321,
  "ts": "2025-01-10T12:00:01Z",
  "level": "INFO",
  "message": "[ffuf] Found 200 /health",
  "compressed": false
}
```

### Estado de proceso HexStrike

```bash
GET /api/processes/status/4321
# Resumen esperado:
{ "pid": 4321, "status": "running", "cpu": 12.3, "memory_mb": 220, "uptime_s": 34 }
```

### Cancelar run

```bash
POST /redteam/runs/rt-run-1001/cancel
{ "reason": "user_request" }
# Esperado: 202 Accepted, estado del run → "cancelling" y luego "cancelled"
```

### Telemetría y cache

```bash
GET /api/telemetry
GET /api/cache/stats
```

### Ingesta al Attack Graph (normalizado)

```json
{
  "case_id": "RT-EXT-001",
  "run_id": "rt-run-1002",
  "nodes": [
    {"id": "host:api.example.com", "type": "host", "risk": "high"},
    {"id": "path:/admin", "type": "path", "risk": "critical"}
  ],
  "edges": [
    {"source": "host:api.example.com", "target": "path:/admin", "relation": "exposes"}
  ],
  "findings": [
    {"node": "path:/admin", "cwe": "CWE-79", "cvss": 8.2, "tool": "nuclei"}
  ]
}
```

## 14) Checklist de prompts seguros por playbook (para otra IA)

### Recon externo

- Contexto: dominio objetivo, ROE, rate-limit, allowlist CIDR.
- Herramientas permitidas: `subfinder`, `amass_enum`, `nmap_scan`, `httpx`, `nuclei_scan`.
- Prompt base: "Eres analista Red Team autorizado. Solo recon pasivo/activo liviano. Respeta rate-limit X rps. No hagas explotación ni fuzzing agresivo."

### Web app / API

- Contexto: dominio/API, credenciales de test si existen, restricciones de verbos y payloads.
- Herramientas permitidas: `ffuf_scan`, `gobuster_scan`, `wafw00f`, `sqlmap_scan` (solo si ROE lo permite), `nuclei_scan`.
- Prompt base: "Evalúa paths y vulnerabilidades comunes. Evita payloads destructivos. Confirma antes de SQLi o RCE. Incluye plan paso a paso y timeout por acción."

### Cloud (AWS/Azure/GCP) light

- Contexto: cuenta de test, regiones permitidas, políticas IAM temporales.
- Herramientas permitidas: `prowler_assess`, `scout_suite_audit`, `trivy_scan`, `kube_hunter_scan`.
- Prompt base: "Solo auditoría de configuración y enumeración segura. No crear/borrar recursos. Reporta hallazgos con referencias CIS/Mitre."

### Reglas generales

- Incluir `engagement_id` y `target_id` en cada comando.
- Prohibir shells arbitrarias; usar solo `/api/command` o funciones expuestas.
- Solicitar confirmación antes de acciones potencialmente disruptivas.
- Limitar concurrencia y duración total; abortar si supera cuotas.

## 15) Prompts completos (para orquestar otra IA)

### Prompt base (sistema)

```text
Eres un analista Red Team AUTORIZADO. Respeta el alcance: <scope/ROE>. 
Usa solo herramientas expuestas por HexStrike (MCP) y comandos HTTP `/api/command`.
Prohibe shells arbitrarias o payloads destructivos sin confirmación.
Incluye `engagement_id` y `target_id` en cada acción. Respeta rate-limit <X> rps y max_parallel <Y>.
Objetivo: plan paso a paso → solicitar confirmación → ejecutar → reportar hallazgos normalizados (CWE/CVSS).
```

### Prompt de recon externo (ejemplo completo)

```text
Alcance: example.com, api.example.com, 203.0.113.0/24. No DoS. Rate-limit 3 rps.
Planifica 3 fases: (1) enum subdominios, (2) puertos/top-1000, (3) fingerprint HTTP.
Usa solo: subfinder, amass_enum, nmap_scan (top 1000), httpx, nuclei_scan (plantillas low/medium).
Salida: lista de comandos MCP/HTTP con params claros y `engagement_id=RT-EXT-001`, `target_id` por host.
Confirma antes de ejecutar; luego pide lanzar secuencialmente.
```

### Prompt de web/API (fuzzing seguro)

```text
Objetivo: https://api.example.com (auth test). No RCE. SQLi solo si ROE lo permite y pides confirmación.
Herramientas: ffuf_scan (wordlist api-endpoints), wafw00f, nuclei_scan (api templates), sqlmap_scan (solo GET, time limit 120s).
Output: plan -> confirmar -> ejecutar por pasos. Forzar follow_redirects=false, threads<=20.
Normaliza hallazgos a CWE/CVSS. Registra `run_id` y `hexstrike_pid` para cada ejecución.
```

### Prompt de cloud (auditoría ligera)

```text
Cuenta AWS de prueba, solo lectura. Regiones permitidas: us-east-1, us-west-2.
Herramientas: prowler_assess, scout_suite_audit, trivy_scan (imágenes demo), kube_hunter_scan (cluster test).
No crear/borrar recursos. Objetivo: listar riesgos CIS, claves expuestas y puertos abiertos en clusters.
```

### Prompt de explotación controlada (requiere doble confirmación)

```text
Solo si hallazgo previo crítico. Solicita confirmación explícita antes de exploitation.
Herramientas: sqlmap_scan (GET/POST limit 120s), nuclei_scan exploit templates (solo si ROE=exploit_allowed).
Añade `dry_run=true` si disponible; si no, usa `--batch` prohibido. Reporta pasos y impacto esperado antes de ejecutar.
```

### Prompt de post-exploit seguro

```text
Solo sobre recursos propios de laboratorio. Objetivo: recopilar evidencia, NO persistir.
Acciones permitidas: proof-of-concept benigno, descarga limitada de prueba (máx 10 filas), screenshot o respuesta HTTP.
Registrar evidencia en `evidence/<engagement>/...` con hash y tamaño.
```

## 16) Mitigación de prompt/LLM injection

- No trusts externo: cualquier contenido de targets (HTML, headers, banners, WAF, API responses) es datos no confiables; no se inyecta directo en prompts. Resumir y sanitizar.
- Separar instrucciones: los prompts del sistema/seguridad nunca se construyen con texto de usuario/objetivo; sólo se pasan como contexto "read-only".
- Plantillas con placeholders: usar variables estrictas y validar que no contengan tokens como "ignore previous instructions", "/bin/sh", backticks.
- Límite de longitud: truncar o hash a mayor de 4KB de salida antes de llevar a LLM; adjuntar solo resúmenes (ej. top findings) en vez de logs completos.
- Roles fijos: siempre incluir rol "Analista Red Team AUTORIZADO" y un bloque de políticas (ROE, rate-limit, no shells) al inicio del prompt; nunca permitir que el modelo las reescriba.
- Validación previa a ejecución: si la IA propone comandos que no cumplan ROE/allowlist o incluyan pipes/shells, descartar y pedir nuevo plan.
- Auditoría: log de `prompt_in`, `context`, `commands_out` y validaciones aplicadas para detectar intentos de inyección.

## 17) Scripts de ejemplo (curl)

### Health/telemetría

```bash
curl -s http://hexstrike-ai:8888/health
curl -s http://hexstrike-ai:8888/api/telemetry
curl -s http://hexstrike-ai:8888/api/cache/stats
```

### Engagement y plan

```bash
curl -X POST http://gateway/redteam/engagements -H "Content-Type: application/json" -d @engagement.json
curl -X POST http://gateway/redteam/engagements/RT-EXT-001/plan -H "Content-Type: application/json" -d @plan.json
```

### Run y estado

```bash
curl -X POST http://gateway/redteam/runs -H "Content-Type: application/json" -d @run_ffuf.json
curl http://gateway/redteam/runs/rt-run-1001
curl http://hexstrike-ai:8888/api/processes/status/4321
```

### Cancelar y logs

```bash
curl -X POST http://gateway/redteam/runs/rt-run-1001/cancel -H "Content-Type: application/json" -d '{"reason":"user_request"}'
websocat ws://gateway/ws/redteam/rt-run-1001
```

## 18) Reglas automáticas de validación (backend)

- Bloqueos regex:
  - Pipes/shells: `;`, `&&`, `||`, `$(`, backticks en parámetros de herramientas.
  - Frases de inyección: `ignore previous`, `override instructions`, `run shell`.
  - Paths peligrosos: `/bin/sh`, `/bin/bash`, `/bin/zsh`, `powershell`.
- Longitud:
  - Máx prompt IA: 4000 caracteres, truncar con hash de contexto.
  - Máx params de comando: 1024 caracteres.
- Allowlist:
  - `tool` debe estar en catálogo permitido por tenant (`allowed_tools`).
  - `target` debe pertenecer a scope/allowlist declarada en engagement.
- Límites:
  - `max_parallel` por tenant (ej. 3) y timeout por run (ej. 600s).
- Auditoría:
  - Guardar `prompt_in`, `sanitized_context`, `command_out`, `validation_result`, `reason`.
  - Rechazar con 400/403 y mensaje "policy_blocked" si falla.

## 19) RBAC sugerido

### Roles

- `mcp:redteam:read`: ver engagements, runs, findings.
- `mcp:redteam:run`: crear runs y cancelarlos.
- `mcp:redteam:plan`: pedir plan a HexStrike.
- `mcp:redteam:admin`: configurar allowlist/denylist y quotas.

### Vistas/UI

- Engagements: requiere `read`; botón Plan requiere `plan`.
- Runs: ejecutar requiere `run`; cancelar requiere `run`.
- Findings/Graph: requiere `read`; export restricción a owner/tenant.

### Endpoints

- `/redteam/engagements*` → `read/plan/admin` según verbo.
- `/redteam/runs*` → `run` (POST), `read` (GET), `run` (cancel).
- `/ws/redteam/*` → `read`.

## 20) Snippet docker-compose (servicio hexstrike-ai)

```yaml
  hexstrike-ai:
    image: hexstrike-ai:6.0
    container_name: hexstrike-ai
    command: ["python3","/app/hexstrike_server.py","--port","8888"]
    networks:
      - internal
    ports:
      - "8888:8888"  # solo en demo; en prod quitar esta línea
    volumes:
      - ./logs/hexstrike:/logs
      - ./evidence/hexstrike:/evidence
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
```

## 21) Flujo E2E de prueba

1. Crear engagement (`/redteam/engagements`) con scope y ROE.
2. Generar plan (`/redteam/engagements/{id}/plan`) → esperar listado de herramientas y orden sugerido.
3. Ejecutar run FFUF/Nuclei (`/redteam/runs`) → recibir `run_id` y `hexstrike_pid`.
4. Monitorear logs en `/ws/redteam/{run_id}` y estado en `/redteam/runs/{run_id}` + `/api/processes/status/{pid}`.
5. Ver findings normalizados (`/redteam/findings?engagement_id=`) y grafo/timeline actualizados.
6. Cancelar un run de prueba y verificar estado `cancelled`.
7. Validar KPIs: TTR, precisión de findings, latencia WS, bloqueos de política (allowlist/RBAC).

## 22) Gestión de secretos/credenciales

- Variables en `.env` del gateway para tokens hacia HexStrike (si aplica) y claves internas.
- Rotación: tokens de servicio con validez corta; revocar tras piloto.
- Montar `~/.mcp/` o similar en contenedor solo si se requieren configuraciones de clientes MCP; evitar credenciales permanentes.
- No exponer claves en logs; redactar campos sensibles en auditoría.
