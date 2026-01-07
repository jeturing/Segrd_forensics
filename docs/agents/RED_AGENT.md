# 🔴 MCP RED AGENT - Documentación Completa

## Visión General

El **Agente RED** del MCP es un componente especializado diseñado para ejecutar evaluaciones ofensivas controladas, simulación de tácticas MITRE ATT&CK y análisis de superficie de ataque bajo condiciones estrictamente autorizadas.

**NO realiza explotación, intrusión, escalada ni acciones destructivas.**

---

## 🎯 Objetivos

- Identificar vectores de ataque
- Exponer configuraciones débiles
- Emular tácticas de reconocimiento y enumeración
- Proveer inteligencia accionable al Blue Team
- Enriquecer la correlación de incidentes
- Actualizar el Attack Graph en tiempo real
- Colaborar con agentes Blue y Purple

---

## 🔒 Restricciones Operacionales

| Restricción | Descripción |
|-------------|-------------|
| ❌ No ejecuta código ofensivo | Sin payloads, shells, exploits |
| ❌ No explota vulnerabilidades | Solo detección, no explotación |
| ❌ No altera sistemas remotos | Read-only donde sea posible |
| ❌ No accede a datos sin permiso | Solo recursos autorizados |
| ❌ No realiza acciones de impacto | Sin DoS, sin destrucción |

---

## ✅ Capacidades Permitidas

### 1. Passive Recon (sin tocar objetivo)
- OSINT de dominios
- WHOIS / DNS / MX Discovery
- Subdomain enumeration (amass, subfinder)
- Certificate transparency (crt.sh)
- Metadata extraction (PDF, DOCX)
- Search leaks (HIBP)

### 2. Active Recon (Safe Mode)
- Port scanning (rate-limited)
- Service enumeration
- Version fingerprinting
- Banner grabbing
- SSL/TLS enumeration
- WAF detection

### 3. Web Attack Surface Discovery
- HTTP header analysis
- Framework fingerprinting
- Directory enumeration (safe)
- Cookie security check
- Technology stack detection

### 4. Credential Resilience Assessment
- Password policy validation
- MFA verification
- Password spraying (rate-limited, authorized)
- Default credentials check

### 5. Attack Path Hypothesis
- Correlación de servicios/puertos/IOCs
- Generación de rutas de ataque probables
- MITRE ATT&CK mapping
- Risk scoring

---

## 🔧 Herramientas Permitidas

### Por Categoría

| Categoría | Herramientas |
|-----------|-------------|
| Recon Pasivo | whois, dig, host, amass (passive), theHarvester |
| Recon Activo | nmap (rate-limited), whatweb, dnsenum |
| Web Enum | gobuster, dirb, nikto (safe mode) |
| Vuln Detection | nuclei (safe templates), wpscan (enum only) |
| SSL/TLS | sslscan, testssl.sh, sslyze |
| Credentials | kerbrute (enum only, rate-limited) |

### Niveles de Riesgo

```python
TOOLS_BY_RISK_LEVEL = {
    "SAFE": ["whois", "dig", "host", "nslookup", "ping"],
    "LOW": ["nmap", "whatweb", "dnsenum", "amass"],
    "MEDIUM": ["nikto", "nuclei", "wpscan"],
    "HIGH": ["hydra", "medusa"],  # Solo con autorización explícita
    "OFFENSIVE": ["msfconsole"]   # BLOQUEADO por defecto
}
```

---

## 📋 Playbooks RED Team

### RED-01: Passive Recon Full Sweep

**Trigger**: `case_created`, `domain_added`, `ioc_domain_detected`

**Steps**:
1. Resolver DNS base del dominio
2. Enumerar subdominios pasivos
3. Identificar proveedores de hosting
4. Identificar IP ranges
5. Descubrir certificados y servicios expuestos
6. Enviar señales al Correlation Engine
7. Actualizar Attack Graph
8. Crear hallazgos para el analista

**Output**: Mapa de exposición inicial

---

### RED-02: Internal Active Recon (Safe Mode)

**Trigger**: `agent_connected_internal`

**Steps**:
1. Identificar hosts activos (tasa limitada)
2. Verificar puertos comunes (top 20)
3. Identificar servicios visibles en banner
4. Verificar TLS/SSL versión
5. Detectar servicios legacy
6. Enriquecer Attack Graph

**Limitaciones**:
- No testea exploits
- No ejecuta payloads
- Rate limiting: 100 requests/min

---

### RED-03: Web Attack Surface Discovery

**Trigger**: `web_asset_detected`

**Steps**:
1. Analizar headers HTTP
2. Detectar frameworks y tecnologías
3. Enumerar rutas básicas
4. Detectar servidores sin seguridad
5. Detectar cookies inseguras
6. Mapear vectores potenciales
7. Enviar hallazgos al Blue Team

---

### RED-04: Credential Resilience Assessment

**Trigger**: `auth_anomaly`, `credential_ioc_detected`

**Steps**:
1. Validación de política de contraseñas
2. Simulación de password spraying (rate-limited)
3. Identificación de cuentas vulnerables
4. Validar MFA habilitado
5. Notificar al SOAR

**No ejecuta**:
- ❌ Fuerza bruta
- ❌ Ataques agresivos
- ❌ Bloqueo de cuentas

---

### RED-05: Attack Path Hypothesis

**Trigger**: `correlation_positive`

**Steps**:
1. Identificar cadena de ataque probable
2. Mapear ruta según ATT&CK
3. Generar "Attack Path Hypothesis"
4. Notificar Blue & Purple Agents
5. Crear nodo "Tactic Projection" en Graph

---

## 🔗 Integración con Otros Componentes

### SOAR Engine
- Cada playbook RED se registra en SOAR
- Validación de políticas del tenant
- Autorización antes de ejecutar
- Registro en auditoría

### Correlation Engine
- IOC relations
- Service exposure signals
- Weak configuration signals
- Attack path projections

### Graph Engine
- Crea nodos: `RED_AGENT_SIGNAL`, `ATTACK_PATH_HYPOTHESIS`
- Aristas: `Red Agent → Predicted Vector`

### WebSocket Channels
- `agent_red_updates`: Estado del agente
- `recon_progress`: Progreso de escaneos
- `attack_path_alerts`: Nuevas rutas detectadas

---

## 📊 Mapeo MITRE ATT&CK

### Tácticas Cubiertas

| Táctica | ID | Cobertura |
|---------|-----|-----------|
| Reconnaissance | TA0043 | ✅ Completa |
| Resource Development | TA0042 | ⚠️ Parcial |
| Initial Access | TA0001 | ⚠️ Simulado |
| Discovery | TA0007 | ✅ Completa |
| Credential Access | TA0006 | ⚠️ Simulado |

### Técnicas Implementadas

- T1595 - Active Scanning
- T1590 - Gather Victim Network Information
- T1589 - Gather Victim Identity Information
- T1592 - Gather Victim Host Information
- T1018 - Remote System Discovery
- T1046 - Network Service Discovery
- T1087 - Account Discovery

---

## 🚫 Lo que NO Incluye (Prohibido)

| Categoría | Detalles |
|-----------|----------|
| Explotación real | RCE, SQLi, LFI, RFI, buffer overflow |
| Payloads | Metasploit, msfvenom |
| Shells | Reverse shells, bind shells |
| Malware | Deployment, droppers |
| Elevación | Privilege escalation real |
| Lateral | Lateral movement real |
| Impacto | Ransomware, wiping, DoS |
| Fuerza bruta | Dictionary attacks agresivos |

---

## 📈 Métricas y Telemetría

```json
{
  "agent_id": "red-agent-001",
  "metrics": {
    "scans_completed": 45,
    "domains_analyzed": 12,
    "iocs_generated": 89,
    "attack_paths_identified": 3,
    "avg_scan_duration_sec": 180,
    "false_positive_rate": 0.05
  }
}
```

---

## 🔐 Seguridad del Agente

### Requisitos
- Firmado criptográficamente
- Certificado por tenant
- Canal TLS mutual
- RBAC: `RED_OPERATOR` role
- Aislamiento de entorno
- Sandbox execution

### Auditoría
- Cada acción registrada en `audit_log`
- Timeline del caso actualizado
- EvidenceLog (sin datos ofensivos)
- Attack Graph actualizado

---

## 📚 Referencias

- [MITRE ATT&CK Framework](https://attack.mitre.org/)
- [Kali Linux Tools](https://www.kali.org/tools/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05  
**Autor**: MCP Forensics Team
