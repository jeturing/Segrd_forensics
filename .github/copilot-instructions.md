# Copilot Instructions

## Project Overview

**MCP Kali Forensics & IR Worker** - Micro Compute Pod especializado en análisis forense y respuesta a incidentes para Microsoft 365, Azure AD, endpoints comprometidos y credenciales filtradas.

Este MCP automatiza investigaciones forenses usando herramientas enterprise (Sparrow, Hawk, O365 Extractor, Loki, YARA) ejecutándose **nativamente en Kali Linux/WSL** sin Docker, con integración a Jeturing CORE.

**Arquitectura**: FastAPI backend + Kali Linux tooling (nativo) + Ejecución directa en host + Jeturing CORE integration
**Modo de Ejecución**: Nativo en Kali/WSL (sin overhead de Docker), ideal para WSL2 en Windows
**Configuración M365**: Automatizada con scripts que buscan tenant y crean App Registration usando credenciales de usuario

## Architecture & Key Components

```
mcp-kali-forensics/
├── api/                      # FastAPI application
│   ├── main.py              # Entry point, lifespan events, CORS
│   ├── config.py            # Pydantic Settings (env vars, paths)
│   ├── routes/              # REST endpoints
│   │   ├── m365.py         # Sparrow, Hawk, O365 Extractor
│   │   ├── credentials.py  # HIBP, Dehashed, stealer logs
│   │   ├── endpoint.py     # Loki, YARA, OSQuery, Volatility
│   │   └── cases.py        # Case management, status, reports
│   ├── services/            # Business logic
│   │   └── m365.py         # PowerShell integration wrappers
│   └── middleware/
│       └── auth.py         # API Key validation
├── tools/                   # Tool wrappers (future)
├── scripts/
│   └── install.sh          # Auto-installer for Kali
├── Dockerfile              # Kali-based container
├── docker-compose.yml      # Orchestration with PostgreSQL/Redis
└── evidence/               # Case artifacts (gitignored)
```

**Key Integration Points:**
- **Jeturing CORE**: MCP registers via `/api/mcp/forensics/dispatch`
- **M365 Tools**: Executes PowerShell scripts via asyncio subprocess
- **Evidence Chain**: All results stored in `~/forensics-evidence/{case_id}/` (user home)
- **Tools Location**: `/opt/forensics-tools/` (system-wide, read-only)
- **Database**: SQLite local `./forensics.db` (no PostgreSQL/Docker needed)

## Development Workflow

### Setup (Nativo en Kali/WSL - Recomendado)
```bash
# Ejecutar instalador nativo (instala todo automáticamente)
cd /home/hack/mcp-kali-forensics
chmod +x scripts/setup_native.sh
./scripts/setup_native.sh

# Activar entorno virtual
source venv/bin/activate

# Configurar credenciales M365 automáticamente
cd scripts
./setup_m365_interactive.sh  # Abre navegador para login (compatible con MFA)
# O: ./setup_m365.py          # Usuario/password directo (solo sin MFA)

# Verificar conexión
./test_m365_connection.py

# Iniciar servicio (modo desarrollo)
cd ..
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080

# O configurar como servicio systemd (producción)
sudo cp scripts/mcp-forensics.service /etc/systemd/system/
sudo systemctl enable mcp-forensics
sudo systemctl start mcp-forensics
```

### Setup (Docker - Solo si necesitas aislamiento)
```bash
# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f mcp-forensics
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:8080/health

# API docs (Swagger)
open http://localhost:8080/docs

# Test M365 analysis (requires valid API key)
curl -X POST http://localhost:8080/forensics/m365/analyze \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"xxx","case_id":"IR-2024-001","scope":["sparrow"]}'

# Test credential check
curl -X POST http://localhost:8080/forensics/credentials/check \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"case_id":"IR-001","emails":["test@empresa.com"],"check_hibp":true}'

# Test endpoint scan
curl -X POST http://localhost:8080/forensics/endpoint/scan \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"case_id":"IR-002","hostname":"PC-TEST","actions":["yara","loki"]}'
```

### Debugging
- **API logs**: `tail -f logs/mcp-forensics.log` (grep por emoji para filtrar: 🔍, ✅, ❌)
- **Tool output**: Check `/var/evidence/{case_id}/{tool}/` for raw CSV/JSON results
- **PowerShell errors**: Enable DEBUG=true in .env to see full stderr
- **Tool verification**: Run `./scripts/check_tools.sh` to verify all tools are installed

## Project Conventions

### Code Style
- **Async-first**: All I/O operations use `async/await` (tool execution, file operations)
- **Background tasks**: Long-running forensic analysis runs via `BackgroundTasks`, not blocking endpoints
- **Error handling**: Log with context, update case status to "failed", never expose internal paths to API responses
- **Tool wrappers**: Always wrap external tools (Sparrow, Hawk) in try/except, capture stdout/stderr

### File Organization
- **Feature-based routes**: Each forensic domain (m365, credentials, endpoint) has its own router
- **Service layer**: Business logic lives in `api/services/`, routers stay thin
- **Evidence isolation**: Each case gets `{EVIDENCE_DIR}/{case_id}/{tool}/` directory
- **No secrets in code**: All credentials via environment variables or `.env`

### Naming Conventions
- **Case IDs**: Format `IR-YYYY-NNN` (e.g., `IR-2024-001`)
- **API endpoints**: `/forensics/{domain}/{action}` (e.g., `/forensics/m365/analyze`)
- **Tool result keys**: Use snake_case matching tool output (e.g., `suspicious_sign_ins`)
- **Log prefixes**: Emoji + action (e.g., `logger.info("🦅 Executing Sparrow...")`)

## Integration Points

### External Dependencies
- **Sparrow 365**: PowerShell scripts in `/opt/forensics-tools/Sparrow/`, requires Azure AD permissions
- **Hawk**: PowerShell module, needs `ExchangeOnlineManagement` installed
- **O365 Extractor**: Python script, extracts Unified Audit Logs via Graph API
- **HIBP API**: Rate-limited (1 req/1.5s per email), requires API key from haveibeenpwned.com
- **Microsoft Graph**: MSAL authentication, requires app registration with `AuditLog.Read.All`, `User.Read.All`

### Tool Execution Pattern
All external tools follow this pattern (IMPLEMENTED):
```python
# 1. Validate tool exists
if not tool_path.exists():
    raise Exception(f"Tool not found. Run scripts/install.sh")

# 2. Create evidence directory
evidence_path = EVIDENCE_DIR / case_id / "tool_name"
evidence_path.mkdir(parents=True, exist_ok=True)

# 3. Execute via asyncio subprocess with timeout
process = await asyncio.create_subprocess_exec(
    *cmd, stdout=PIPE, stderr=PIPE
)
try:
    stdout, stderr = await asyncio.wait_for(
        process.communicate(), 
        timeout=300  # 5 minutes
    )
except asyncio.TimeoutError:
    process.kill()
    raise Exception("Tool timeout")

# 4. Check return code
if process.returncode != 0:
    logger.error(f"Tool failed: {stderr.decode()[:200]}")
    # Don't raise immediately - some tools use non-zero for warnings

# 5. Parse output (CSV/JSON/text) and return structured data
results = parse_tool_output(stdout.decode(), stderr.decode())
return results
```

### Real Command Examples (FUNCTIONAL)

**Loki Scanner:**
```bash
python3 /opt/forensics-tools/Loki/loki.py \
  --noprocscan --dontwait --intense --csv \
  --path /tmp --path /home
```

**YARA:**
```bash
yara -r -w -s \
  /opt/forensics-tools/yara-rules/gen_malware.yar \
  /target/path
```

**OSQuery:**
```bash
osqueryi --json \
  "SELECT pid, name, path, cmdline FROM processes"
```

**Volatility 3:**
```bash
vol.py -f memory.dmp windows.pslist
vol.py -f memory.dmp windows.netscan
vol.py -f memory.dmp windows.malfind
```

**Sparrow:**
```bash
pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File /opt/forensics-tools/Sparrow/Sparrow.ps1 \
  -TenantId xxx -DaysToSearch 90 -OutputPath /var/evidence/case-001/
```

### Jeturing CORE Communication
- **Registration**: POST to `{JETURING_CORE_URL}/api/registry/mcp` on startup
- **Task dispatch**: CORE sends tasks to `/forensics/dispatch` (not yet implemented)
- **Status updates**: MCP calls CORE webhook when case status changes

## Key Files & Patterns

### Critical Files
- **`api/main.py`**: Lifespan events (startup registration, tool verification), exception handlers
- **`api/routes/m365.py`**: Example of background task pattern - see `execute_m365_analysis()`
- **`api/services/m365.py`**: Shows how to wrap PowerShell tools - see `run_sparrow_analysis()`
- **`api/config.py`**: Pydantic Settings pattern - all env vars defined here
- **`scripts/install.sh`**: Reference for tool installation paths and dependencies

### Pattern: Adding New Tool Integration (WORKING EXAMPLE)

See `api/services/endpoint.py` for complete examples. Pattern:

1. **Add wrapper in `api/services/{domain}.py`:**
   ```python
   async def run_new_tool(
       case_id: str,
       hostname: str,
       **kwargs
   ) -> Dict:
       try:
           # 1. Validate tool installation
           tool_path = settings.TOOLS_DIR / "new_tool" / "tool.py"
           if not tool_path.exists():
               raise Exception("Tool not installed")
           
           # 2. Create evidence directory
           evidence_path = EVIDENCE_DIR / case_id / "new_tool"
           evidence_path.mkdir(parents=True, exist_ok=True)
           
           # 3. Build command
           cmd = ["python3", str(tool_path), "--option", "value"]
           
           # 4. Execute with timeout
           process = await asyncio.create_subprocess_exec(
               *cmd, stdout=PIPE, stderr=PIPE
           )
           stdout, stderr = await asyncio.wait_for(
               process.communicate(), timeout=600
           )
           
           # 5. Parse output
           results = parse_new_tool_output(stdout.decode())
           
           return {"status": "completed", "results": results}
       
       except Exception as e:
           logger.error(f"❌ Error: {e}", exc_info=True)
           return {"status": "failed", "error": str(e)}
   
   def parse_new_tool_output(output: str) -> Dict:
       # Parse CSV, JSON, or text output
       # Return structured dict
       pass
   ```

2. **Add endpoint in `api/routes/{domain}.py`:**
   ```python
   @router.post("/new-analysis")
   async def analyze_with_new_tool(
       request: NewToolRequest,
       background_tasks: BackgroundTasks
   ):
       case = await create_case({...})
       background_tasks.add_task(
           execute_new_tool_analysis,
           request.case_id,
           request.hostname
       )
       return {"case_id": request.case_id, "status": "queued"}
   
   async def execute_new_tool_analysis(case_id, hostname):
       try:
           await update_case_status(case_id, "running")
           results = await run_new_tool(case_id, hostname)
           await update_case_status(case_id, "completed", results=results)
       except Exception as e:
           await update_case_status(case_id, "failed", error=str(e))
   ```

3. **Add to installation script:**
   ```bash
   # In scripts/quick_install.sh
   git clone https://github.com/org/new-tool.git /opt/forensics-tools/new-tool
   ```

## Common Pitfalls

### PowerShell Execution
❌ **Don't** run PowerShell scripts directly without proper subprocess handling  
✅ **Do** use `asyncio.create_subprocess_exec()` with proper error handling

### Evidence Paths
❌ **Don't** use relative paths for evidence storage  
✅ **Do** use `EVIDENCE_DIR / case_id / tool_name` pattern from config

### Background Tasks
❌ **Don't** await background tasks in route handlers (blocks response)  
✅ **Do** use FastAPI's `BackgroundTasks` and update case status asynchronously

### API Keys
❌ **Don't** hardcode API keys or commit `.env` files  
✅ **Do** use `settings.API_KEY` from config.py, provide `.env.example`

### Tool Output Parsing
❌ **Don't** assume tool output format is stable  
✅ **Do** wrap parsing in try/except, handle missing CSV/JSON files gracefully

### Case Status Updates
❌ **Don't** forget to update case status on failure  
✅ **Do** use try/except blocks that call `update_case_status(case_id, "failed", error=str(e))`

### Docker Permissions
- Tools in `/opt/forensics-tools` must be readable by `forensics` user (UID 1000)
- Evidence directory needs write permissions for container user
- Don't run container as root unless absolutely necessary (use `cap_add` for specific capabilities)

### Tool Output Formats (DOCUMENTED)

**Sparrow** generates:
- CSV files: `{TenantName}_*.csv` (sign-ins, audit logs, OAuth apps)
- HTML reports (optional)
- Parse with: `csv.DictReader()`

**Hawk** generates:
- CSV files in subdirectories by investigation type
- XML files for detailed reports
- Parse with: `csv.DictReader()` and `xml.etree.ElementTree`

**Loki** output:
- Text with `[ALERT]` and `[WARNING]` markers
- Optional CSV with `--csv`
- Parse by regex matching alert patterns

**YARA** output:
- Format: `RuleName FilePath`
- Strings: `0xOFFSET:$name: "content"`
- Parse line-by-line, split by spaces

**OSQuery** output:
- JSON with `--json` flag
- Parse with: `json.loads()`

**Volatility** output:
- Tab-separated tabular format
- Headers in first line
- Parse by splitting on `\t`

### Rate Limiting (IMPLEMENTED)

**HIBP API** has strict limits:
```python
_last_hibp_request = 0
_hibp_rate_limit = 1.5  # seconds

# Before each request:
current_time = time.time()
if current_time - _last_hibp_request < _hibp_rate_limit:
    await asyncio.sleep(_hibp_rate_limit - (current_time - _last_hibp_request))
_last_hibp_request = time.time()
```

Don't parallelize HIBP requests - they MUST be sequential.

---

## Documentation Management (v4.2)

### 📚 Structure
All documentation is organized in `/docs/` folder with 16 themed subdirectories:
```
/docs/
├── getting-started/        ← New users entry point
├── installation/           ← Setup & deployment guides
├── backend/               ← API endpoints & services
├── frontend/              ← React UI & components
├── architecture/          ← System design & flows
├── security/              ← Auth & credentials
├── deployment/            ← Production configuration
├── reference/             ← Troubleshooting & FAQ
├── agents/                ← Agent documentation
├── playbooks/             ← SOAR automation
├── tools/                 ← Forensic tools reference
└── archive/               ← Deprecated documentation
```

### 🎯 Key Documents
- **START HERE**: `/docs/README.md` - Master index with role-based navigation
- **MANAGEMENT**: `/docs/DOCUMENTATION_MANAGEMENT_GUIDE.md` - How to maintain docs
- **EXAMPLES**: `/docs/DOCUMENTATION_MANAGEMENT_GUIDE.md` contains templates

### ✅ Rules for Documentation
**DO:**
- ✅ Place all .md files in `/docs/` (never in root)
- ✅ Create folder-specific README.md for navigation
- ✅ Use relative links: `[Link](../reference/FAQ.md)`
- ✅ Add state labels: ✅ (done), 🔄 (WIP), ⚠️ (warning), 🔒 (locked)
- ✅ Include date and version in new documents
- ✅ Link to related docs for cross-referencing
- ✅ Archive obsolete docs (don't delete)

**DON'T:**
- ❌ Create loose .md files in project root
- ❌ Use absolute paths or hardcoded links
- ❌ Remove old docs without archiving first
- ❌ Skip updating README.md in folders
- ❌ Create documentation without knowing folder placement
- ❌ Reference external URLs for internal references

### 🚀 When Adding New Documentation
1. Decide which category it belongs to (use `/docs/README.md` matrix)
2. Create file in appropriate folder
3. Add link to folder's README.md
4. Update master `/docs/README.md` if needed
5. Use template from DOCUMENTATION_MANAGEMENT_GUIDE.md
6. Test all relative links work
7. Commit with message: `docs: add [topic] in [folder]`

### 📖 User Roles & Navigation
- **New User**: Start at `/docs/README.md` → getting-started
- **Developer**: Backend at `/docs/backend/API.md`, Frontend at `/docs/frontend/`
- **Admin**: Installation at `/docs/installation/`, Deploy at `/docs/deployment/`
- **Security Officer**: `/docs/security/` for auth & credentials
- **DevOps**: `/docs/deployment/` for production setup

### 🔍 Finding Documentation
**By Problem**: See search matrix in `/docs/README.md`  
**By Role**: See role-based navigation in `/docs/README.md`  
**By Tool**: See `/docs/tools/INDEX.md` for forensic tools  
**Troubleshooting**: Always check `/docs/reference/TROUBLESHOOTING.md` first  

### 📝 State Labels (Use in Headers)
- **✅ Completa**: Documentation complete and tested
- **🔄 En Progreso**: Active development/updates
- **⚠️ Advertencia**: Outdated or needs review
- **🔒 Archivado**: Deprecated, reference only

### 💾 Maintenance Tasks
- **Add new doc**: Consult `/docs/DOCUMENTATION_MANAGEMENT_GUIDE.md`
- **Update existing**: Keep date/version current
- **Remove old**: Move to `/docs/archive/` (never delete)
- **Reorganize**: Edit folder READMEs to reflect changes
- **Verify links**: Use markdown link checker tool monthly

### 🎓 Learning Resources
- **How to structure docs**: `/docs/DOCUMENTATION_MANAGEMENT_GUIDE.md`
- **All available docs**: `/docs/README.md` (master index)
- **This project status**: `/home/hack/mcp-kali-forensics/REORGANIZATION_STATUS_FINAL.md`

---

**Learn more**: https://aka.ms/vscode-instructions-docs
