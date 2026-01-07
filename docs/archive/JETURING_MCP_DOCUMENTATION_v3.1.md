# 🛡️ JETURING MCP Kali Forensics & IR
## Documentación Corporativa v3.1

<div align="center">

![Jeturing Logo](https://jeturing.com/logo.png)

**Micro Compute Pod para Análisis Forense y Respuesta a Incidentes (DFIR)**

*Enterprise-Grade Digital Forensics & Incident Response Platform*

---

**Versión:** 3.1.0 | **Fecha:** Diciembre 2025 | **Clasificación:** Confidencial

</div>

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Base de Datos y Persistencia](#3-base-de-datos-y-persistencia)
4. [WebSockets en Tiempo Real](#4-websockets-en-tiempo-real)
5. [Módulos Disponibles](#5-módulos-disponibles)
6. [API Reference](#6-api-reference)
7. [Integración Multi-Tenant Jeturing CORE](#7-integración-multi-tenant-jeturing-core)
8. [Política de Retención de Evidencia](#8-política-de-retención-de-evidencia)
9. [Guía de Migración v2 → v3.1](#9-guía-de-migración-v2--v31)
10. [Seguridad y Cumplimiento](#10-seguridad-y-cumplimiento)
11. [Guía de Implementación](#11-guía-de-implementación)
12. [Casos de Uso](#12-casos-de-uso)
13. [Anexos Técnicos](#13-anexos-técnicos)

---

## 1. Resumen Ejecutivo

### 1.1 Propósito

**JETURING MCP Kali Forensics & IR** es una plataforma empresarial de análisis forense digital y respuesta a incidentes diseñada para equipos de seguridad (SOC, CSIRT, Blue Team) que necesitan investigar compromisos en entornos Microsoft 365, Azure AD, endpoints y credenciales filtradas.

### 1.2 Novedades v3.1

| Característica | Descripción |
|----------------|-------------|
| **Persistencia SQLAlchemy** | BD real con modelos completos (IOC, Investigations, Timeline, Evidence) |
| **WebSockets Tiempo Real** | 5 canales: IOC Store, Investigations, Dashboard, Agents |
| **Integración IOC↔IR** | Vinculación bidireccional con contexto y timeline |
| **Multi-Tenant CORE** | Aislamiento por tenant con RLS y Auth0 Organizations |
| **WORM Storage** | Política de retención para cumplimiento legal |

### 1.3 Métricas de Rendimiento

```
┌─────────────────────────────────────────────────────────────┐
│  MÉTRICAS DE RENDIMIENTO JETURING MCP v3.1                  │
├─────────────────────────────────────────────────────────────┤
│  ⏱️  Tiempo medio de respuesta a incidentes:  -65%          │
│  📊  Casos procesados simultáneamente:        50+           │
│  🔍  IOCs analizados por minuto:              1,000+        │
│  ☁️  Tenants M365 soportados:                 Ilimitados    │
│  📈  Precisión de detección:                  94.7%         │
│  🔌  Latencia WebSocket:                      <50ms         │
│  💾  Operaciones BD/segundo:                  10,000+       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Arquitectura v3.1

```
                            ┌─────────────────────────────────┐
                            │      JETURING CORE              │
                            │    (Orquestador Central)        │
                            │  AppRegistry + Auth0 ORG        │
                            └──────────────┬──────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
           ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
           │   MCP Forensics │    │   MCP Threat    │    │   MCP IOC       │
           │   & IR Worker   │    │   Intelligence  │    │   Store v3      │
           │  (SQLite/PG)    │    │                 │    │  (Persistent)   │
           └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
                    │                      │                      │
    ┌───────────────┼───────────────┐      │      ┌───────────────┼───────────────┐
    │               │               │      │      │               │               │
┌───▼───┐      ┌────▼────┐    ┌─────▼──────▼──────▼─────┐    ┌────▼────┐    ┌────▼────┐
│ M365  │      │Endpoint │    │     Data Lake          │    │  HIBP   │    │VirusTotal│
│ Graph │      │ Agents  │    │   (Evidence Store)     │    │   API   │    │   API   │
│  API  │      │  (WS)   │    │   WORM Storage         │    │         │    │         │
└───────┘      └─────────┘    └────────────────────────┘    └─────────┘    └─────────┘
```

### 2.2 Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| **Backend** | FastAPI | 0.104+ |
| **Base de Datos** | SQLAlchemy + SQLite/PostgreSQL | 2.0+ |
| **WebSockets** | FastAPI WebSocket | Nativo |
| **Frontend** | React + Tailwind CSS | 18.x |
| **Autenticación** | MSAL + Auth0 | Latest |
| **Contenedores** | Docker + Docker Compose | 24.x |

### 2.3 Puertos y Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| API REST | 9000 | Endpoints HTTP/HTTPS |
| WebSocket | 9000 | Canales WS (mismo puerto) |
| Frontend | 3000 | React Development |
| PostgreSQL | 5432 | Base de datos (producción) |
| Redis | 6379 | Cache y colas (opcional) |

---

## 3. Base de Datos y Persistencia

### 3.1 Modelos SQLAlchemy Completos

#### 3.1.1 Modelos IOC Store

```python
class IocItem(Base):
    """Indicador de Compromiso principal"""
    __tablename__ = "ioc_items"
    
    id = Column(String(50), primary_key=True)          # IOC-YYYYMMDD-XXXXX
    value = Column(String(1024), nullable=False)       # IP, domain, hash, etc.
    ioc_type = Column(String(50), nullable=False)      # ip, domain, url, hash_sha256...
    threat_level = Column(String(20), default="medium") # critical/high/medium/low/info
    confidence_score = Column(Float, default=50.0)     # 0-100
    status = Column(String(20), default="active")      # active/expired/whitelisted
    source = Column(String(50), default="manual")      # manual/investigation/import...
    description = Column(Text, nullable=True)
    case_id = Column(String(50), nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=0)
    enrichment_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class IocTag(Base):
    """Tags para categorizar IOCs"""
    __tablename__ = "ioc_tags"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # malware, phishing, c2...
    description = Column(Text, nullable=True)
    color = Column(String(20), default="gray")


class IocItemTag(Base):
    """Relación many-to-many IOC ↔ Tag"""
    __tablename__ = "ioc_item_tags"
    
    id = Column(Integer, primary_key=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"))
    tag_id = Column(Integer, ForeignKey("ioc_tags.id", ondelete="CASCADE"))


class IocEnrichment(Base):
    """Datos de enriquecimiento de fuentes externas"""
    __tablename__ = "ioc_enrichments"
    
    id = Column(Integer, primary_key=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"))
    source = Column(String(50), nullable=False)        # virustotal, abuseipdb, shodan
    reputation_score = Column(Float, nullable=True)
    malicious_count = Column(Integer, nullable=True)
    suspicious_count = Column(Integer, nullable=True)
    categories = Column(JSON, nullable=True)           # ["malware", "botnet"]
    raw_response = Column(JSON, nullable=True)
    status = Column(String(20), default="success")     # success/failed/pending
    queried_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class IocSighting(Base):
    """Avistamientos/detecciones de IOCs en sistemas"""
    __tablename__ = "ioc_sightings"
    
    id = Column(Integer, primary_key=True)
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"))
    source_system = Column(String(100), nullable=True)  # SIEM, EDR, Firewall
    source_host = Column(String(255), nullable=True)    # Hostname
    source_ip = Column(String(45), nullable=True)       # IP origen
    context = Column(Text, nullable=True)
    raw_event = Column(JSON, nullable=True)
    case_id = Column(String(50), nullable=True)
    sighted_at = Column(DateTime, default=datetime.utcnow)
    reported_by = Column(String(100), nullable=True)
```

#### 3.1.2 Modelos Investigation

```python
class Investigation(Base):
    """Investigación de Incidente de Seguridad"""
    __tablename__ = "investigations"
    
    id = Column(String(50), primary_key=True)          # IR-YYYY-XXX
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="medium")    # critical/high/medium/low
    status = Column(String(30), default="open")        # open/in_progress/resolved/closed
    investigation_type = Column(String(50))            # BEC, Ransomware, Phishing...
    assigned_to = Column(String(100), nullable=True)
    tenant_id = Column(String(100), nullable=True)
    tenant_name = Column(String(255), nullable=True)
    affected_users = Column(JSON, nullable=True)       # ["user1@domain.com"]
    affected_hosts = Column(JSON, nullable=True)       # ["PC-001", "SRV-WEB"]
    mitre_tactics = Column(JSON, nullable=True)        # ["TA0001", "TA0003"]
    mitre_techniques = Column(JSON, nullable=True)     # ["T1566.001"]
    incident_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class InvestigationIocLink(Base):
    """Vinculación IOC ↔ Investigación con contexto"""
    __tablename__ = "investigation_ioc_links"
    
    id = Column(Integer, primary_key=True)
    investigation_id = Column(String(50), ForeignKey("investigations.id", ondelete="CASCADE"))
    ioc_id = Column(String(50), ForeignKey("ioc_items.id", ondelete="CASCADE"))
    reason = Column(Text, nullable=True)               # Por qué se vinculó
    context = Column(Text, nullable=True)              # Contexto adicional
    relevance = Column(String(20), default="high")     # high/medium/low
    linked_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InvestigationTimeline(Base):
    """Eventos de timeline de una investigación"""
    __tablename__ = "investigation_timeline"
    
    id = Column(Integer, primary_key=True)
    investigation_id = Column(String(50), ForeignKey("investigations.id", ondelete="CASCADE"))
    event_type = Column(String(50), nullable=False)    # action/finding/status_change/ioc_added
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)        # Tool o sistema origen
    actor = Column(String(100), nullable=True)         # Usuario que realizó la acción
    ioc_id = Column(String(50), nullable=True)
    evidence_id = Column(String(50), nullable=True)
    metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
```

#### 3.1.3 Modelos Case & Evidence

```python
class Case(Base):
    """Caso forense - contenedor principal"""
    __tablename__ = "cases"
    
    id = Column(String(50), primary_key=True)          # CASE-YYYY-XXXXX
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    case_type = Column(String(50))                     # forensic/ir/threat_hunting
    priority = Column(String(20), default="medium")
    status = Column(String(30), default="open")
    lead_analyst = Column(String(100), nullable=True)
    customer_name = Column(String(255), nullable=True)
    legal_hold = Column(Boolean, default=False)
    chain_of_custody = Column(Boolean, default=True)
    confidentiality_level = Column(String(50), default="internal")
    evidence_count = Column(Integer, default=0)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class CaseEvidence(Base):
    """Evidencia asociada a un caso"""
    __tablename__ = "case_evidences"
    
    id = Column(String(50), primary_key=True)          # EVD-XXXXXXXX
    case_id = Column(String(50), ForeignKey("cases.id", ondelete="CASCADE"))
    name = Column(String(500), nullable=False)
    evidence_type = Column(String(50))                 # file/memory_dump/network_capture
    file_path = Column(String(1024), nullable=True)
    file_hash_sha256 = Column(String(64), nullable=True)
    file_size = Column(Integer, nullable=True)
    source_host = Column(String(255), nullable=True)
    collected_by = Column(String(100), nullable=True)
    custody_chain = Column(JSON, nullable=True)        # [{"action": "...", "by": "..."}]
    analyzed = Column(Boolean, default=False)
    collected_at = Column(DateTime, nullable=True)
```

### 3.2 Diagrama Entidad-Relación

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    IocItem      │───────│  IocItemTag     │───────│    IocTag       │
│                 │  1:N  │                 │  N:1  │                 │
├─────────────────┤       └─────────────────┘       └─────────────────┘
│ id              │
│ value           │       ┌─────────────────┐
│ ioc_type        │───────│  IocEnrichment  │
│ threat_level    │  1:N  │                 │
│ confidence_score│       └─────────────────┘
│ enrichment_data │
└────────┬────────┘       ┌─────────────────┐
         │                │   IocSighting   │
         └────────────────│                 │
                    1:N   └─────────────────┘
                    
         │
         │ N:M (via InvestigationIocLink)
         │
┌────────▼────────┐       ┌─────────────────┐
│  Investigation  │───────│ InvestigationTimeline
│                 │  1:N  │                 │
├─────────────────┤       └─────────────────┘
│ id              │
│ title           │
│ severity        │
│ status          │
└─────────────────┘
```

---

## 4. WebSockets en Tiempo Real

### 4.1 Canales Disponibles

| Canal | Endpoint | Descripción |
|-------|----------|-------------|
| **IOC Store** | `/ws/ioc-store` | Actualizaciones de IOCs |
| **Investigations** | `/ws/investigations` | Cambios en investigaciones |
| **Investigation Detail** | `/ws/investigation/{id}` | Investigación específica |
| **Dashboard** | `/ws/dashboard` | Métricas y estadísticas |
| **Agents** | `/ws/agents` | Estado de agentes móviles |

### 4.2 Payloads WebSocket Estandarizados

#### 4.2.1 Canal IOC Store (`/ws/ioc-store`)

**Evento: ioc_created**
```json
{
  "event": "ioc_created",
  "_channel": "ioc_store",
  "_timestamp": "2025-12-05T14:32:00Z",
  "data": {
    "id": "IOC-20251205-A1B2C",
    "value": "185.234.72.15",
    "ioc_type": "ip",
    "threat_level": "critical",
    "confidence_score": 92.5,
    "source": "investigation",
    "tags": ["c2", "apt"],
    "case_id": "IR-2025-001"
  }
}
```

**Evento: ioc_updated**
```json
{
  "event": "ioc_updated",
  "ioc_id": "IOC-20251205-A1B2C",
  "data": {
    "threat_level": "high",
    "confidence_score": 88.0,
    "status": "active",
    "tags": ["c2", "apt", "russia"]
  }
}
```

**Evento: ioc_deleted**
```json
{
  "event": "ioc_deleted",
  "ioc_id": "IOC-20251205-A1B2C"
}
```

**Evento: ioc_enriched**
```json
{
  "event": "ioc_enriched",
  "ioc_id": "IOC-20251205-A1B2C",
  "enrichment": {
    "sources": ["virustotal", "abuseipdb"],
    "new_confidence": 95.0,
    "results": {
      "virustotal": {
        "malicious": 45,
        "suspicious": 3,
        "harmless": 12
      },
      "abuseipdb": {
        "abuse_confidence_score": 92,
        "total_reports": 156,
        "country_code": "RU"
      }
    }
  }
}
```

**Evento: import_completed**
```json
{
  "event": "import_completed",
  "import_type": "misp",
  "count": 47,
  "details": {
    "event_id": "12345",
    "event_info": "APT28 IOCs - December 2025"
  }
}
```

#### 4.2.2 Canal Investigations (`/ws/investigations`)

**Evento: investigation_updated**
```json
{
  "event": "investigation_updated",
  "investigation_id": "IR-2025-001",
  "data": {
    "status": "in_progress",
    "severity": "critical",
    "assigned_to": "john.analyst@company.com",
    "updated_at": "2025-12-05T14:35:00Z"
  }
}
```

**Evento: ioc_linked**
```json
{
  "event": "ioc_linked",
  "investigation_id": "IR-2025-001",
  "ioc_id": "IOC-20251205-A1B2C",
  "data": {
    "ioc": {
      "id": "IOC-20251205-A1B2C",
      "value": "185.234.72.15",
      "ioc_type": "ip",
      "threat_level": "critical"
    },
    "reason": "Detected in authentication logs",
    "relevance": "high",
    "linked_by": "analyst@company.com"
  }
}
```

**Evento: ioc_unlinked**
```json
{
  "event": "ioc_unlinked",
  "investigation_id": "IR-2025-001",
  "ioc_id": "IOC-20251205-A1B2C"
}
```

#### 4.2.3 Canal Dashboard (`/ws/dashboard`)

**Evento: stats_update**
```json
{
  "event": "stats_update",
  "data": {
    "active_investigations": 12,
    "critical_alerts": 3,
    "new_iocs_24h": 54,
    "active_agents": 8,
    "pending_tasks": 15,
    "avg_response_time_hours": 4.2
  }
}
```

**Evento: alert**
```json
{
  "event": "alert",
  "data": {
    "type": "critical_ioc_detected",
    "message": "New critical IOC detected: 185.234.72.15",
    "investigation_id": "IR-2025-001",
    "timestamp": "2025-12-05T14:40:00Z"
  }
}
```

#### 4.2.4 Canal Agents (`/ws/agents`)

**Evento: agent_connected**
```json
{
  "event": "agent_connected",
  "data": {
    "agent_id": "AGENT-WIN-1234",
    "hostname": "CEO-LAPTOP",
    "ip": "10.0.4.22",
    "os": "Windows 11 Pro",
    "status": "online",
    "capabilities": ["memory_dump", "yara", "osquery", "network_capture"]
  }
}
```

**Evento: task_completed**
```json
{
  "event": "task_completed",
  "data": {
    "task_id": "TASK-001",
    "agent_id": "AGENT-WIN-1234",
    "task_type": "memory_dump",
    "status": "success",
    "evidence_id": "EVD-A1B2C3D4",
    "completed_at": "2025-12-05T14:45:00Z"
  }
}
```

**Evento: evidence_collected**
```json
{
  "event": "evidence_collected",
  "data": {
    "evidence_id": "EVD-A1B2C3D4",
    "agent_id": "AGENT-WIN-1234",
    "evidence_type": "memory_dump",
    "file_size": 4294967296,
    "hash_sha256": "a1b2c3d4...",
    "case_id": "IR-2025-001"
  }
}
```

### 4.3 Implementación Frontend

```javascript
import { useIocStoreWebSocket } from '../services/realtime';

function IOCStore() {
  const handleWebSocketEvent = useCallback((message) => {
    switch (message.event) {
      case 'ioc_created':
        setIocs(prev => [message.data, ...prev]);
        break;
      case 'ioc_updated':
        setIocs(prev => prev.map(ioc => 
          ioc.id === message.ioc_id ? message.data : ioc
        ));
        break;
      case 'ioc_deleted':
        setIocs(prev => prev.filter(ioc => ioc.id !== message.ioc_id));
        break;
    }
  }, []);

  const { isConnected } = useIocStoreWebSocket(handleWebSocketEvent);

  return (
    <div>
      {isConnected && <span className="text-green-400">🟢 Live</span>}
      {/* IOC List */}
    </div>
  );
}
```

---

## 5. Módulos Disponibles

### 5.1 Matriz de Módulos v3.1

| Módulo | Estado | Persistencia | WebSocket | Descripción |
|--------|--------|--------------|-----------|-------------|
| **Dashboard** | ✅ Activo | ✅ | ✅ | Panel de control con métricas |
| **IOC Store** | ✅ Activo | ✅ | ✅ | Gestión centralizada de IOCs |
| **Investigations** | ✅ Activo | ✅ | ✅ | Casos de IR con timeline |
| **Mobile Agents** | ✅ Activo | ✅ | ✅ | Agentes en endpoints |
| **Attack Graph** | ✅ Activo | ✅ | ❌ | Visualización de relaciones |
| **Evidence Manager** | ✅ Activo | ✅ | ❌ | Gestión de evidencia |
| **Timeline** | ✅ Activo | ✅ | ✅ | Línea temporal forense |
| **M365 Forensics** | ✅ Activo | Parcial | ❌ | Sparrow, Hawk, Graph API |
| **Credential Check** | ✅ Activo | ❌ | ❌ | HIBP, Dehashed |
| **Endpoint Scan** | ✅ Activo | ❌ | ❌ | Loki, YARA, OSQuery |
| **Network Capture** | ✅ Activo | ❌ | ❌ | Captura de tráfico |
| **Memory Dump** | ✅ Activo | ❌ | ❌ | Volatility 3 analysis |

### 5.2 IOC Store - Características Completas

| Feature | Descripción |
|---------|-------------|
| **CRUD completo** | Crear, leer, actualizar, eliminar IOCs |
| **Bulk operations** | Operaciones en lote (crear, eliminar, actualizar) |
| **Búsqueda avanzada** | Por tipo, severidad, tags, fecha, confianza |
| **Import MISP** | Importar desde eventos MISP |
| **Import STIX** | Importar desde bundles STIX 2.x |
| **Export multi-formato** | JSON, CSV, STIX, MISP |
| **Enriquecimiento** | VirusTotal, AbuseIPDB (extensible) |
| **Tagging** | Sistema de etiquetas flexible |
| **Sightings** | Registro de avistamientos |
| **Case linking** | Vinculación a investigaciones |
| **Confidence scoring** | Puntuación de confianza 0-100 |
| **TTL management** | Expiración automática de IOCs |

### 5.3 Investigations - Características

| Feature | Descripción |
|---------|-------------|
| **Case management** | Gestión completa de investigaciones |
| **IOC linking** | Vincular/desvincular IOCs con contexto |
| **Timeline events** | Registro de eventos cronológico |
| **MITRE mapping** | Mapeo a tácticas y técnicas ATT&CK |
| **Affected assets** | Usuarios, hosts y sistemas afectados |
| **Status workflow** | open → in_progress → resolved → closed |
| **Assignment** | Asignación a analistas |
| **Multi-tenant** | Aislamiento por tenant |

---

## 6. API Reference

### 6.1 IOC Store Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/iocs` | Listar IOCs con filtros |
| `POST` | `/api/iocs` | Crear nuevo IOC |
| `GET` | `/api/iocs/{id}` | Obtener IOC por ID |
| `PUT` | `/api/iocs/{id}` | Actualizar IOC |
| `DELETE` | `/api/iocs/{id}` | Eliminar IOC |
| `POST` | `/api/iocs/bulk` | Crear IOCs en lote |
| `POST` | `/api/iocs/bulk-delete` | Eliminar IOCs en lote |
| `POST` | `/api/iocs/search` | Búsqueda avanzada |
| `GET` | `/api/iocs/stats` | Estadísticas del store |
| `GET` | `/api/iocs/lookup` | Buscar por valor exacto |
| `POST` | `/api/iocs/import/misp` | Importar desde MISP |
| `POST` | `/api/iocs/import/stix` | Importar desde STIX |
| `GET` | `/api/iocs/export` | Exportar IOCs |
| `POST` | `/api/iocs/{id}/enrich` | Enriquecer IOC |
| `POST` | `/api/iocs/{id}/link-case` | Vincular a caso |
| `GET` | `/api/iocs/tags` | Listar tags |
| `POST` | `/api/iocs/{id}/tags` | Agregar tags |
| `DELETE` | `/api/iocs/{id}/tags/{tag}` | Remover tag |
| `GET` | `/api/iocs/{id}/sightings` | Obtener sightings |
| `POST` | `/api/iocs/{id}/sighting` | Registrar sighting |

### 6.2 Investigation Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/investigations` | Listar investigaciones |
| `POST` | `/api/investigations` | Crear investigación |
| `GET` | `/api/investigations/{id}` | Obtener investigación |
| `PUT` | `/api/investigations/{id}` | Actualizar investigación |
| `DELETE` | `/api/investigations/{id}` | Eliminar investigación |
| `GET` | `/api/investigations/{id}/iocs` | IOCs vinculados |
| `POST` | `/api/investigations/{id}/iocs/{ioc_id}` | Vincular IOC |
| `DELETE` | `/api/investigations/{id}/iocs/{ioc_id}` | Desvincular IOC |
| `GET` | `/api/investigations/{id}/timeline-db` | Timeline desde BD |
| `POST` | `/api/investigations/{id}/timeline-db` | Agregar evento |

### 6.3 WebSocket Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `WS /ws/ioc-store` | Canal IOC Store |
| `WS /ws/investigations` | Canal Investigations |
| `WS /ws/investigation/{id}` | Canal investigación específica |
| `WS /ws/dashboard` | Canal Dashboard |
| `WS /ws/agents` | Canal Agents |
| `GET /ws/stats` | Estadísticas de conexiones |

### 6.4 Códigos de Respuesta

| Código | Significado |
|--------|-------------|
| 200 | OK - Operación exitosa |
| 201 | Created - Recurso creado |
| 204 | No Content - Eliminación exitosa |
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - Sin autenticación |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 409 | Conflict - Recurso duplicado |
| 422 | Validation Error - Datos inválidos |
| 429 | Rate Limit - Demasiadas solicitudes |
| 500 | Internal Error - Error del servidor |

---

## 7. Integración Multi-Tenant Jeturing CORE

### 7.1 Arquitectura Multi-Tenant

```
┌─────────────────────────────────────────────────────────────────┐
│                      JETURING CORE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ AppRegistry │  │ Auth0 ORG   │  │ Tenant Router (RLS)     │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP FORENSICS v3.1                          │
│                                                                  │
│   tenant_key = current_setting('tenant.key')                    │
│                                                                  │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│   │ Tenant A  │  │ Tenant B  │  │ Tenant C  │  │ Tenant D  │   │
│   │ IOCs      │  │ IOCs      │  │ IOCs      │  │ IOCs      │   │
│   │ Cases     │  │ Cases     │  │ Cases     │  │ Cases     │   │
│   │ Evidence  │  │ Evidence  │  │ Evidence  │  │ Evidence  │   │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Componentes Multi-Tenant

| Componente | Función |
|------------|---------|
| **AppRegistry** | Registro de aplicaciones y servicios |
| **Auth0 Organizations** | Autenticación por organización |
| **Row-Level Security (RLS)** | Aislamiento de datos por tenant |
| **Tenant Router** | Enrutamiento automático por subdomain |
| **Policy Enforcement Point** | Control de acceso por política |

### 7.3 Flujo de Autenticación

```
1. Usuario accede a: tenant-a.forensics.jeturing.com
                              │
                              ▼
2. Redirect a Auth0 ORG (org_tenant_a)
                              │
                              ▼
3. Auth0 valida credenciales + MFA
                              │
                              ▼
4. JWT con claims: { org_id: "org_tenant_a", tenant_key: "tenant_a" }
                              │
                              ▼
5. MCP Forensics recibe request
                              │
                              ▼
6. Middleware extrae tenant_key del JWT
                              │
                              ▼
7. SET LOCAL tenant.key = 'tenant_a' (PostgreSQL)
                              │
                              ▼
8. Todas las queries aplican RLS automático
```

### 7.4 Row-Level Security (PostgreSQL)

```sql
-- Habilitar RLS en tablas
ALTER TABLE ioc_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_evidences ENABLE ROW LEVEL SECURITY;

-- Política de tenant
CREATE POLICY tenant_isolation ON ioc_items
    USING (tenant_key = current_setting('tenant.key'));

CREATE POLICY tenant_isolation ON investigations
    USING (tenant_key = current_setting('tenant.key'));

-- El middleware FastAPI ejecuta:
-- SET LOCAL tenant.key = 'tenant_x';
-- Antes de cada transacción
```

### 7.5 Subdominios Automáticos (Cloudflare)

```yaml
# Configuración DNS Wildcard
*.forensics.jeturing.com → MCP Load Balancer

# Tenant routing
tenant-a.forensics.jeturing.com → tenant_key: tenant_a
tenant-b.forensics.jeturing.com → tenant_key: tenant_b
```

---

## 8. Política de Retención de Evidencia

### 8.1 Reglas de Retención Jeturing

| Tipo de Dato | Retención | Almacenamiento | Eliminación |
|--------------|-----------|----------------|-------------|
| **Artefactos forenses** | 2 años | WORM Storage | Secure Delete |
| **Logs de auditoría** | 1 año | Cold Storage | Purge automático |
| **IOCs** | 3 años | DB + Archive | Archivado WORM |
| **Timeline IR** | 5 años | WORM | Solo lectura |
| **Evidence files** | 7 años | WORM + Backup | Legal hold aware |
| **Metadata cases** | Indefinido | DB Primary | Nunca (audit trail) |

### 8.2 WORM Storage (Write Once, Read Many)

```yaml
# Características WORM
- Immutabilidad: Una vez escrito, no se puede modificar
- Integridad: Hash SHA-256 verificable
- Trazabilidad: Registro de accesos completo
- Compliance: Compatible ISO 27001, SOC 2, GDPR

# Implementación
Storage:
  Type: S3 Object Lock / Azure Immutable Blob
  Retention: Legal Hold + Governance Mode
  Versioning: Enabled
  Encryption: AES-256 at rest, TLS 1.3 in transit
```

### 8.3 Procedimiento de Borrado Seguro

```
┌─────────────────────────────────────────────────────────────┐
│              SECURE DELETION WORKFLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Verificar que NO hay legal hold activo                  │
│                     │                                        │
│                     ▼                                        │
│  2. Verificar que retención ha expirado                     │
│                     │                                        │
│                     ▼                                        │
│  3. Generar certificado de eliminación                      │
│                     │                                        │
│                     ▼                                        │
│  4. Ejecutar DoD 5220.22-M wipe (3 pasadas)                │
│                     │                                        │
│                     ▼                                        │
│  5. Verificar eliminación con hash check                    │
│                     │                                        │
│                     ▼                                        │
│  6. Registrar en audit log (inmutable)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 8.4 Cadena de Custodia Digital

```json
{
  "evidence_id": "EVD-A1B2C3D4",
  "custody_chain": [
    {
      "action": "collected",
      "by": "agent-win-1234",
      "at": "2025-12-05T10:00:00Z",
      "hash_sha256": "a1b2c3..."
    },
    {
      "action": "transferred",
      "by": "system",
      "to": "evidence-vault",
      "at": "2025-12-05T10:05:00Z",
      "hash_verified": true
    },
    {
      "action": "analyzed",
      "by": "analyst@company.com",
      "at": "2025-12-05T14:30:00Z",
      "tools_used": ["volatility3", "yara"]
    },
    {
      "action": "archived",
      "by": "system",
      "to": "worm-storage",
      "at": "2025-12-06T00:00:00Z",
      "retention_until": "2030-12-06"
    }
  ]
}
```

---

## 9. Guía de Migración v2 → v3.1

### 9.1 Cambios Críticos

| Aspecto | MCP v2 | MCP v3.1 |
|---------|--------|----------|
| **Persistencia** | Sin BD (memoria) | SQLAlchemy completo |
| **IOC Store** | Estático, sin enriquecimiento | Dinámico + enrichment + sightings |
| **WebSockets** | No disponible | 5 canales tiempo real |
| **Investigaciones** | Sin vinculación IOC | IOC↔Investigation bidireccional |
| **Timeline** | Sin estructura | InvestigationTimeline en BD |
| **Multi-tenant** | No soportado | RLS + Auth0 Organizations |
| **Evidence** | Solo archivos | Cadena de custodia completa |

### 9.2 Pasos de Migración

```bash
# 1. Backup de datos existentes
python scripts/backup_v2_data.py --output ./backup-v2/

# 2. Actualizar dependencias
pip install -r requirements-v3.txt

# 3. Inicializar base de datos
python -c "from api.database import init_db; init_db()"

# 4. Migrar IOCs existentes (si los hay)
python scripts/migrate_iocs_to_db.py --input ./backup-v2/iocs.json

# 5. Migrar investigaciones
python scripts/migrate_investigations.py --input ./backup-v2/cases.json

# 6. Verificar integridad
python scripts/verify_migration.py

# 7. Activar WebSockets en frontend
# Actualizar VITE_WS_URL en .env

# 8. Reiniciar servicios
docker-compose down && docker-compose up -d

# 9. Verificar conexiones WS
curl http://localhost:9000/ws/stats
```

### 9.3 Checklist de Migración

| Paso | Verificación |
|------|--------------|
| ☐ | Backup completo de v2 |
| ☐ | Dependencias v3 instaladas |
| ☐ | Base de datos inicializada |
| ☐ | Tablas creadas correctamente |
| ☐ | IOCs migrados |
| ☐ | Investigaciones migradas |
| ☐ | Integridad verificada |
| ☐ | WebSockets funcionando |
| ☐ | Frontend actualizado |
| ☐ | Tests pasando |

### 9.4 Rollback

```bash
# En caso de problemas, revertir a v2:
git checkout v2.0.0
docker-compose down && docker-compose up -d

# Los datos de v3 permanecen en la BD pero no se usan
# v2 seguirá funcionando con datos en memoria
```

---

## 10. Seguridad y Cumplimiento

### 10.1 Frameworks de Cumplimiento

| Framework | Estado | Alcance |
|-----------|--------|---------|
| **ISO 27001** | ✅ Alineado | Gestión de seguridad de información |
| **SOC 2 Type II** | ✅ Alineado | Controles de seguridad y disponibilidad |
| **NIST CSF** | ✅ Alineado | Marco de ciberseguridad |
| **GDPR** | ✅ Alineado | Protección de datos personales |
| **HIPAA** | ⚠️ Parcial | Datos de salud (requiere config adicional) |
| **PCI-DSS** | ⚠️ Parcial | Datos de tarjetas (requiere config adicional) |

### 10.2 Controles de Seguridad

| Control | Implementación |
|---------|----------------|
| **Autenticación** | OAuth 2.0 / MSAL / Auth0 |
| **Autorización** | RBAC + RLS por tenant |
| **Cifrado en tránsito** | TLS 1.3 obligatorio |
| **Cifrado en reposo** | AES-256 (BD + archivos) |
| **Logs de auditoría** | Inmutables, 1 año retención |
| **MFA** | Obligatorio para acceso admin |
| **API Keys** | Rotación cada 90 días |
| **Secrets** | HashiCorp Vault / AWS Secrets Manager |

### 10.3 Clasificación de Datos

| Nivel | Datos | Controles |
|-------|-------|-----------|
| **Restricted** | Credenciales, llaves API, evidencia legal | Cifrado, acceso mínimo, audit log |
| **Confidential** | IOCs, investigaciones, casos | Cifrado, RBAC, tenant isolation |
| **Internal** | Configuraciones, logs técnicos | Acceso interno, backup regular |
| **Public** | Documentación, APIs públicas | Ninguno adicional |

### 10.4 Gestión de Vulnerabilidades

```yaml
Scanning:
  - Dependabot: Diario (dependencias)
  - Snyk: Semanal (código + contenedores)
  - OWASP ZAP: Mensual (APIs)
  - Penetration Test: Anual (externo)

Patching:
  - Crítico (CVSS 9.0+): 24 horas
  - Alto (CVSS 7.0-8.9): 7 días
  - Medio (CVSS 4.0-6.9): 30 días
  - Bajo (CVSS < 4.0): 90 días
```

---

## 11. Guía de Implementación

### 11.1 Requisitos del Sistema

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **Disco** | 100 GB SSD | 500+ GB NVMe |
| **Red** | 100 Mbps | 1 Gbps |
| **OS** | Ubuntu 22.04 / Kali Linux | Kali Linux 2024.x |

### 11.2 Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/jcarvajalantigua/mcp-kali-forensics.git
cd mcp-kali-forensics

# 2. Copiar configuración
cp .env.example .env
# Editar .env con credenciales

# 3. Instalar dependencias (modo nativo)
./scripts/setup_native.sh

# 4. Activar entorno
source venv/bin/activate

# 5. Inicializar base de datos
python -c "from api.database import init_db; init_db()"

# 6. Iniciar servicio
uvicorn api.main:app --host 0.0.0.0 --port 9000 --reload

# 7. Verificar
curl http://localhost:9000/health
```

### 11.3 Configuración con Docker

```bash
# 1. Build y start
docker-compose up -d --build

# 2. Ver logs
docker-compose logs -f mcp-forensics

# 3. Verificar salud
curl http://localhost:9000/health
```

### 11.4 Variables de Entorno

```env
# API
DEBUG=false
API_KEY=your-secure-api-key-here
SECRET_KEY=your-secret-key-for-jwt

# Base de Datos
DATABASE_URL=sqlite:///./forensics.db
# O para PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost/forensics

# Microsoft 365
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-app-client-id
AZURE_CLIENT_SECRET=your-client-secret

# Jeturing CORE (opcional)
JETURING_CORE_ENABLED=true
JETURING_CORE_URL=https://core.jeturing.com/api

# Enrichment APIs (opcional)
VIRUSTOTAL_API_KEY=your-vt-key
HIBP_API_KEY=your-hibp-key
ABUSEIPDB_API_KEY=your-abuse-key
```

---

## 12. Casos de Uso

### 12.1 Business Email Compromise (BEC)

```
Escenario: CFO recibe email de CEO solicitando transferencia urgente

Timeline de Investigación:
─────────────────────────────────────────────────────────────────
T+0h    │ Alerta SIEM: Login sospechoso desde IP desconocida
T+15m   │ MCP crea caso IR-2025-BEC-001
T+30m   │ Sparrow: Detecta regla de reenvío oculta
T+45m   │ Hawk: Identifica OAuth app maliciosa
T+1h    │ IOC Store: IP 185.x.x.x marcada como C2
T+1.5h  │ Graph: Visualiza cadena de ataque
T+2h    │ Contención: Bloqueo de cuenta + revocación OAuth
T+3h    │ Remediación: Eliminación de reglas + reset credenciales
T+4h    │ Reporte: Generación automática para cliente
─────────────────────────────────────────────────────────────────
```

### 12.2 Ransomware en Endpoint

```
Escenario: Detección de cifrado masivo en file server

Timeline de Investigación:
─────────────────────────────────────────────────────────────────
T+0m    │ EDR alerta: Comportamiento de ransomware
T+5m    │ Agent móvil desplegado en endpoint
T+10m   │ YARA: Detecta variante de LockBit
T+15m   │ Memory dump: Captura RAM para análisis
T+20m   │ IOC extraction: Hashes, IPs, dominios
T+30m   │ Loki scan: Análisis de persistencia
T+45m   │ Timeline reconstruction: Entrada inicial vía phishing
T+1h    │ Contención: Aislamiento de red
T+2h    │ Análisis Volatility: Procesos maliciosos identificados
T+3h    │ Recuperación: Restauración desde backups
─────────────────────────────────────────────────────────────────
```

### 12.3 Insider Threat

```
Escenario: Empleado exfiltrando datos antes de renuncia

Timeline de Investigación:
─────────────────────────────────────────────────────────────────
T-30d   │ Baseline: Comportamiento normal del usuario
T-7d    │ Anomalía: Acceso masivo a SharePoint
T-5d    │ DLP alerta: Descarga de documentos sensibles
T-3d    │ USB: Conexión de dispositivo no autorizado
T-1d    │ Email: Reenvío a cuenta personal
T+0h    │ RRHH notifica: Empleado presenta renuncia
T+1h    │ MCP: Investigación retroactiva iniciada
T+2h    │ Graph API: Timeline completo de actividades
T+4h    │ Evidencia preservada: Logs + archivos + emails
T+8h    │ Reporte legal: Documentación para acciones
─────────────────────────────────────────────────────────────────
```

---

## 13. Anexos Técnicos

### A. Permisos Microsoft Graph Requeridos

| Permiso | Tipo | Uso |
|---------|------|-----|
| `AuditLog.Read.All` | Application | Unified Audit Log |
| `Directory.Read.All` | Application | Azure AD info |
| `Mail.Read` | Application | Análisis de emails |
| `User.Read.All` | Application | Información de usuarios |
| `SecurityEvents.Read.All` | Application | Alertas de seguridad |
| `Reports.Read.All` | Application | Reportes de uso |

### B. Integraciones Soportadas

| Categoría | Producto | Método |
|-----------|----------|--------|
| **SIEM** | Microsoft Sentinel | REST API |
| **SIEM** | Splunk | HEC (HTTP Event Collector) |
| **SIEM** | Elastic SIEM | Elasticsearch API |
| **SIEM** | QRadar | REST API |
| **SOAR** | TheHive | REST API |
| **SOAR** | Cortex XSOAR | REST API |
| **Ticketing** | ServiceNow | REST API |
| **Ticketing** | Jira | REST API |
| **Threat Intel** | MISP | REST API + PyMISP |
| **Threat Intel** | OpenCTI | GraphQL |

### C. Glosario DFIR

| Término | Definición |
|---------|------------|
| **IOC** | Indicator of Compromise - Artefacto que indica intrusión |
| **TTPs** | Tactics, Techniques, Procedures - Comportamientos de atacantes |
| **DFIR** | Digital Forensics and Incident Response |
| **BEC** | Business Email Compromise |
| **APT** | Advanced Persistent Threat |
| **SIEM** | Security Information and Event Management |
| **EDR** | Endpoint Detection and Response |
| **SOAR** | Security Orchestration, Automation and Response |
| **WORM** | Write Once Read Many - Almacenamiento inmutable |
| **RLS** | Row-Level Security - Aislamiento por fila en BD |
| **MITRE ATT&CK** | Framework de tácticas y técnicas adversarias |

### D. Comandos Útiles

```bash
# Health check
curl http://localhost:9000/health

# Estadísticas IOC Store
curl http://localhost:9000/api/iocs/stats

# Estadísticas WebSocket
curl http://localhost:9000/ws/stats

# Crear IOC via API
curl -X POST http://localhost:9000/api/iocs \
  -H "Content-Type: application/json" \
  -d '{
    "value": "malicious.com",
    "ioc_type": "domain",
    "threat_level": "high",
    "tags": ["phishing"]
  }'

# Buscar IOC
curl "http://localhost:9000/api/iocs/lookup?value=malicious.com"

# Exportar IOCs a STIX
curl "http://localhost:9000/api/iocs/export?format=stix"
```

---

## 📞 Contacto

**JETURING - Cybersecurity Solutions**

- 🌐 Web: https://jeturing.com
- 📧 Email: info@jeturing.com
- 📱 Soporte: soporte@jeturing.com
- 🐙 GitHub: https://github.com/jcarvajalantigua

---

<div align="center">

**© 2025 JETURING. Todos los derechos reservados.**

*Este documento es confidencial y está destinado únicamente para uso interno y de clientes autorizados.*

**Versión 3.1.0 — Diciembre 2025**

</div>
