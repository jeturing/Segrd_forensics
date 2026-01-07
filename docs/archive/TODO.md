# 📋 MCP Kali Forensics - TODO & Roadmap

> **Versión**: 3.1 | **Actualizado**: Diciembre 2024

---

## ✅ Completado (v3.1)

### Backend Infrastructure
- [x] SQLAlchemy ORM con modelos persistentes
- [x] Base de datos SQLite (`data/mcp_forensics.db`)
- [x] WebSocket Manager para tiempo real
- [x] IOC Store con CRUD completo
- [x] Investigation ↔ IOC linking bidireccional
- [x] Case management con timeline
- [x] Background tasks para análisis largo

### Frontend React
- [x] React 18 + Vite + Tailwind CSS
- [x] Dashboard con métricas en tiempo real
- [x] IOC Store UI completo
- [x] Investigation management
- [x] Mobile Agents panel
- [x] Attack Graph visualization
- [x] WebSocket client con auto-reconnect

### M365 Forensics
- [x] Sparrow 365 integration
- [x] Hawk integration
- [x] O365 Extractor integration
- [x] MSAL authentication
- [x] Graph API endpoints

### Endpoint Analysis
- [x] Loki Scanner wrapper
- [x] YARA engine integration
- [x] OSQuery client
- [x] Volatility 3 wrapper

### Credentials
- [x] HIBP API integration (rate-limited)
- [x] Local dumps scanning
- [x] Stealer logs analysis

---

## 🚧 En Progreso (v3.2)

### Alta Prioridad
- [ ] **PostgreSQL Migration** - Migrar de SQLite a PostgreSQL para producción
- [ ] **Redis Queue** - Celery/Redis para cola de tareas distribuidas
- [ ] **PDF Reports** - Generación automática de reportes PDF
- [ ] **SIEM Integration** - Conectores para Splunk/ELK/Sentinel

### Media Prioridad
- [ ] **Automated Playbooks** - Respuesta automatizada basada en IOC type
- [ ] **Threat Intelligence Feeds** - Integración con MISP, OTX, VirusTotal
- [ ] **Case Templates** - Templates predefinidos para tipos de incidente
- [ ] **Evidence Export** - Export en formatos forenses estándar (STIX, OpenIOC)

---

## 📅 Planificado (v4.0)

### Q1 2025
- [ ] **Multi-tenant Full** - Aislamiento completo por organización
- [ ] **RBAC Avanzado** - Roles granulares (Analyst, Lead, Admin)
- [ ] **Audit Trail** - Logs inmutables con firma digital
- [ ] **2FA/MFA** - Autenticación multifactor para acceso

### Q2 2025
- [ ] **ML Detection** - Modelos para detección de anomalías
- [ ] **Natural Language Search** - Búsqueda semántica en evidencia
- [ ] **Mobile App** - App iOS/Android para alertas
- [ ] **Slack/Teams Integration** - Notificaciones y comandos

---

## 🔒 Mejoras de Seguridad

### Próxima Release
- [ ] API Key rotation automática
- [ ] Secrets en HashiCorp Vault
- [ ] Evidence encryption at rest (AES-256)
- [ ] Digital signatures en reportes

### Futuro
- [ ] Zero Trust architecture
- [ ] Hardware Security Module (HSM) support
- [ ] SOC 2 Type II compliance
- [ ] FedRAMP authorization (si aplica)

---

## 🧪 Testing & Quality

- [ ] Unit tests coverage > 80%
- [ ] Integration tests para cada endpoint
- [ ] E2E tests con Playwright
- [ ] Performance benchmarks
- [ ] Security audit (OWASP)

---

## 📊 Métricas Actuales

| Métrica | Valor |
|---------|-------|
| Endpoints REST | 50+ |
| Modelos SQLAlchemy | 12 |
| Canales WebSocket | 5 |
| Herramientas forenses | 7 |
| Cobertura docs | 26 archivos |

---

## 💡 Ideas Backlog

- [ ] Chrome extension para captura de evidencia web
- [ ] VSCode extension para investigadores
- [ ] Jupyter notebooks para análisis ad-hoc
- [ ] GraphQL API alternativa
- [ ] Kubernetes Helm chart
- [ ] Terraform modules para cloud deployment

---

## 🐛 Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| HIBP rate limit en bulk | Open | Usar batch con delays |
| Volatility memory límite | Open | Procesar en chunks |
| WebSocket reconnect loop | Fixed v3.1 | - |

---

## 📝 Notas de Desarrollo

### Convenciones de Código
- Async/await para todas las operaciones I/O
- Type hints obligatorios
- Docstrings en formato Google
- Commits en formato Conventional Commits

### Branch Strategy
- `main` - Producción estable
- `develop` - Integración
- `feature/*` - Nuevas funcionalidades
- `hotfix/*` - Fixes urgentes

---

<div align="center">

*Actualizado automáticamente con cada release*

</div>
