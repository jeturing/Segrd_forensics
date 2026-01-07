# 📊 MATRIZ DE CAPACIDADES - Agentes RED/BLUE/PURPLE

## Comparación Completa v4.1

---

## 🎯 Capacidades por Agente

| Capacidad | Red Agent | Blue Agent | Purple Agent |
|-----------|:---------:|:----------:|:------------:|
| **Reconocimiento** | | | |
| Passive recon | ✅ | ✅ | ✅ |
| Active recon (safe mode) | ✅ | ✅ | ✅ |
| Web attack surface mapping | ✅ | ✅ | ✅ |
| Vulnerability detection (safe) | ✅ | ✅ | ✅ |
| **Evaluación de Credenciales** | | | |
| Credential policy assessment | ✅ | ✅ | ✅ |
| Password spraying (safe) | ✅ | ❌ | ✅ |
| HIBP check | ❌ | ✅ | ✅ |
| MFA validation | ❌ | ✅ | ✅ |
| **Análisis de Endpoints** | | | |
| IOC scanning | ❌ | ✅ | ✅ |
| YARA scanning | ❌ | ✅ | ✅ |
| Loki scanning | ❌ | ✅ | ✅ |
| OSQuery live | ❌ | ✅ | ✅ |
| Memory forensics | ❌ | ✅ | ⚠️ |
| **Análisis de Logs** | | | |
| Log forensic extraction | ❌ | ✅ | ✅ |
| Timeline reconstruction | ❌ | ✅ | ✅ |
| M365 forensic analysis | ❌ | ✅ | ✅ |
| **Inteligencia** | | | |
| Attack path hypothesis | ✅ | ❌ | ✅ |
| Threat prediction | ✅ | ✅ | ✅ |
| Correlation analysis | ⚠️ | ✅ | ✅ |
| **Respuesta** | | | |
| Mitigation suggestion | ❌ | ✅ | ✅ |
| Mitigation validation | ❌ | ❌ | ✅ |
| Containment execution | ❌ | ✅ | ⚠️ |
| **Automatización** | | | |
| SOAR playbooks | ✅ | ✅ | ✅ |
| Automated tuning | ❌ | ❌ | ✅ |
| **Evidencia** | | | |
| Evidence management | ❌ | ✅ | ✅ |
| Chain of custody | ❌ | ✅ | ✅ |
| Report generation | ⚠️ | ✅ | ✅ |

**Leyenda**: ✅ Completo | ⚠️ Parcial | ❌ No disponible

---

## 🔧 Herramientas por Agente

| Herramienta | Red | Blue | Purple | Categoría |
|-------------|:---:|:----:|:------:|-----------|
| nmap | ✅ | ⚠️ | ✅ | Recon |
| whatweb | ✅ | ❌ | ✅ | Recon |
| amass | ✅ | ❌ | ✅ | Recon |
| gobuster | ✅ | ❌ | ✅ | Web Enum |
| nikto | ✅ | ❌ | ✅ | Vuln Scan |
| nuclei | ✅ | ✅ | ✅ | Vuln Scan |
| YARA | ❌ | ✅ | ✅ | Malware |
| Loki | ❌ | ✅ | ✅ | Malware |
| Volatility | ❌ | ✅ | ⚠️ | Memory |
| OSQuery | ❌ | ✅ | ✅ | Endpoint |
| Sparrow | ❌ | ✅ | ✅ | M365 |
| Hawk | ❌ | ✅ | ✅ | M365 |
| tcpdump | ❌ | ✅ | ⚠️ | Network |

---

## 📋 Playbooks por Equipo

### Red Team Playbooks
| ID | Nombre | Trigger | Auto |
|----|--------|---------|:----:|
| RED-01 | Passive Recon Full Sweep | case_created, domain_added | ✅ |
| RED-02 | Internal Active Recon | agent_connected_internal | ⚠️ |
| RED-03 | Web Attack Surface Discovery | web_asset_detected | ✅ |
| RED-04 | Credential Resilience Assessment | auth_anomaly | ⚠️ |
| RED-05 | Attack Path Hypothesis | correlation_positive | ✅ |

### Blue Team Playbooks
| ID | Nombre | Trigger | Auto |
|----|--------|---------|:----:|
| BLUE-01 | Host Compromise Initial Triage | ioc_detected | ✅ |
| BLUE-02 | Malware Presence Assessment | suspicious_hash | ✅ |
| BLUE-03 | Memory Forensics Lite | process_anomaly | ⚠️ |
| BLUE-04 | Lateral Movement Detection | multi_location_access | ✅ |
| BLUE-05 | Network Threat Hunting | c2_ioc_detected | ✅ |
| BLUE-06 | Credential Compromise Validation | hibp_match | ✅ |
| BLUE-07 | Containment Automation | host_compromised | ⚠️ |

### Purple Team Playbooks
| ID | Nombre | Trigger | Auto |
|----|--------|---------|:----:|
| PURPLE-01 | Red/Blue Sync Cycle | investigation_start | ✅ |
| PURPLE-02 | Validate Blue Mitigations | containment_executed | ✅ |
| PURPLE-03 | Simulated Attack Path | attack_path_created | ⚠️ |
| PURPLE-04 | Exposure Reduction Planner | high_exposure_case | ✅ |
| PURPLE-05 | Autonomous Tuning Engine | high_fp_rate | ✅ |

**Leyenda**: ✅ Automático | ⚠️ Requiere aprobación

---

## 🔒 Niveles de Acceso

| Recurso | Red | Blue | Purple | Admin |
|---------|:---:|:----:|:------:|:-----:|
| IOC Store (Read) | ✅ | ✅ | ✅ | ✅ |
| IOC Store (Write) | ❌ | ✅ | ✅ | ✅ |
| Cases (Read) | ✅ | ✅ | ✅ | ✅ |
| Cases (Write) | ⚠️ | ✅ | ✅ | ✅ |
| Evidence (Read) | ❌ | ✅ | ✅ | ✅ |
| Evidence (Write) | ❌ | ✅ | ⚠️ | ✅ |
| Attack Graph (Read) | ✅ | ✅ | ✅ | ✅ |
| Attack Graph (Write) | ✅ | ✅ | ✅ | ✅ |
| Tool Execution (Low) | ✅ | ✅ | ✅ | ✅ |
| Tool Execution (Medium) | ✅ | ✅ | ✅ | ✅ |
| Tool Execution (High) | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Tool Execution (Offensive) | ❌ | ❌ | ❌ | ⚠️ |
| Containment Actions | ❌ | ✅ | ⚠️ | ✅ |
| User Management | ❌ | ❌ | ❌ | ✅ |
| System Config | ❌ | ❌ | ❌ | ✅ |

**Leyenda**: ✅ Permitido | ⚠️ Con aprobación | ❌ Denegado

---

## 🎯 Mapeo MITRE ATT&CK

| Táctica | ID | Red | Blue | Purple |
|---------|-----|:---:|:----:|:------:|
| Reconnaissance | TA0043 | ✅ | ⚠️ | ✅ |
| Resource Development | TA0042 | ⚠️ | ❌ | ⚠️ |
| Initial Access | TA0001 | ⚠️ | ✅ | ✅ |
| Execution | TA0002 | ❌ | ✅ | ⚠️ |
| Persistence | TA0003 | ❌ | ✅ | ✅ |
| Privilege Escalation | TA0004 | ❌ | ✅ | ⚠️ |
| Defense Evasion | TA0005 | ❌ | ✅ | ✅ |
| Credential Access | TA0006 | ⚠️ | ✅ | ✅ |
| Discovery | TA0007 | ✅ | ✅ | ✅ |
| Lateral Movement | TA0008 | ❌ | ✅ | ⚠️ |
| Collection | TA0009 | ❌ | ✅ | ⚠️ |
| Command and Control | TA0011 | ❌ | ✅ | ⚠️ |
| Exfiltration | TA0010 | ❌ | ✅ | ⚠️ |
| Impact | TA0040 | ❌ | ✅ | ⚠️ |

**Leyenda**: ✅ Detecta/Simula | ⚠️ Parcial | ❌ No aplica

---

## 📊 Flujo de Colaboración

```
┌────────────────────────────────────────────────────────────┐
│                    COLLABORATION FLOW                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   RED AGENT                PURPLE AGENT            BLUE AGENT
│   ─────────                ────────────            ──────────
│       │                         │                       │
│       │  Attack Signals         │  Validation          │
│       ├────────────────────────►├──────────────────────►│
│       │                         │                       │
│       │                         │  Detection Results   │
│       │◄────────────────────────┼◄──────────────────────┤
│       │                         │                       │
│       │  Path Hypothesis        │  Mitigation Actions  │
│       ├────────────────────────►├◄──────────────────────┤
│       │                         │                       │
│       │                         │  Tuning Feedback     │
│       │◄────────────────────────┼──────────────────────►│
│       │                         │                       │
│       ▼                         ▼                       ▼
│   ┌──────────────────────────────────────────────────────┐│
│   │                    ATTACK GRAPH                      ││
│   └──────────────────────────────────────────────────────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🔄 Estados de Agente

| Estado | Descripción | Red | Blue | Purple |
|--------|-------------|:---:|:----:|:------:|
| `online` | Conectado y activo | ✅ | ✅ | ✅ |
| `offline` | Desconectado | ✅ | ✅ | ✅ |
| `busy` | Ejecutando tarea | ✅ | ✅ | ✅ |
| `maintenance` | En mantenimiento | ✅ | ✅ | ✅ |
| `error` | Error de conexión | ✅ | ✅ | ✅ |
| `quarantine` | Aislado por seguridad | ❌ | ✅ | ⚠️ |

---

## 📈 KPIs por Equipo

### Red Team KPIs
- Vectores de ataque identificados
- Attack paths generados
- Tiempo promedio de recon
- Cobertura de superficie

### Blue Team KPIs
- IOCs detectados
- Tiempo de detección (MTTD)
- Tiempo de contención (MTTC)
- Falsos positivos rate
- Evidencia recolectada

### Purple Team KPIs
- Validaciones completadas
- Gaps de detección encontrados
- Mejora de cobertura %
- Reglas ajustadas
- Reducción de exposición %

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05  
**Autor**: MCP Forensics Team
