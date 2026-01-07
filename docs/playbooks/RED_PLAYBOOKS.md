# 📕 PLAYBOOKS RED TEAM - MCP v4.1

## Playbooks de Reconocimiento y Evaluación Ofensiva

---

## RED-01: Passive Recon Full Sweep

### Metadata
```yaml
id: RED-01
name: Passive Recon Full Sweep
version: 1.0
author: MCP Forensics
team: red
category: reconnaissance
risk_level: safe
estimated_duration: 15m
```

### Triggers
- `case_created`: Nuevo caso de investigación
- `domain_added`: Dominio agregado a investigación
- `ioc_domain_detected`: IOC de tipo dominio detectado

### Pre-conditions
- Dominio objetivo definido
- Caso activo
- Permisos de Red Operator

### Steps

```yaml
steps:
  - order: 1
    name: DNS Resolution
    action: tool_execute
    tool: dig
    parameters:
      query_type: ANY
      target: "{{domain}}"
    output: dns_records
    
  - order: 2
    name: Subdomain Enumeration (Passive)
    action: tool_execute
    tool: amass
    parameters:
      mode: passive
      domain: "{{domain}}"
    output: subdomains
    timeout: 300
    
  - order: 3
    name: Certificate Transparency
    action: api_call
    endpoint: https://crt.sh
    parameters:
      q: "%.{{domain}}"
      output: json
    output: certificates
    
  - order: 4
    name: WHOIS Lookup
    action: tool_execute
    tool: whois
    parameters:
      target: "{{domain}}"
    output: whois_data
    
  - order: 5
    name: Extract IPs
    action: data_processing
    input: 
      - dns_records
      - subdomains
    extractor: ip_addresses
    output: ip_list
    
  - order: 6
    name: Create IOCs
    action: create_iocs
    source: ip_list
    ioc_type: ip
    severity: medium
    auto_enrich: true
    
  - order: 7
    name: Update Attack Graph
    action: graph_update
    nodes:
      - type: domain
        value: "{{domain}}"
        status: analyzed
      - type: ip
        values: "{{ip_list}}"
        status: discovered
    edges:
      - from: "{{domain}}"
        to: "{{ip_list}}"
        relationship: resolves_to
        
  - order: 8
    name: Notify Blue Team
    action: notification
    channel: ir_team
    template: passive_recon_complete
    data:
      domain: "{{domain}}"
      subdomains_count: "{{subdomains.length}}"
      ips_found: "{{ip_list.length}}"
```

### Post-conditions
- IOCs creados para IPs descubiertas
- Attack Graph actualizado
- Blue Team notificado

### Output Schema
```json
{
  "domain": "example.com",
  "subdomains": ["www", "mail", "api"],
  "ip_addresses": ["1.2.3.4", "5.6.7.8"],
  "certificates": [...],
  "whois": {...},
  "graph_nodes_created": 15
}
```

---

## RED-02: Internal Active Recon (Safe Mode)

### Metadata
```yaml
id: RED-02
name: Internal Active Recon (Safe Mode)
version: 1.0
team: red
category: discovery
risk_level: low
estimated_duration: 30m
requires_approval: true
```

### Triggers
- `agent_connected_internal`: Agente Red conectado a red interna
- `investigation_type: internal_assessment`

### Pre-conditions
- Agente Red activo en red interna
- Autorización de escaneo interno
- Rate limiting configurado

### Steps

```yaml
steps:
  - order: 1
    name: Host Discovery
    action: tool_execute
    tool: nmap
    parameters:
      scan_type: ping_sweep
      target: "{{network_range}}"
      rate: 100  # packets per second (limited)
    output: live_hosts
    timeout: 600
    
  - order: 2
    name: Top Ports Scan
    action: tool_execute
    tool: nmap
    parameters:
      scan_type: syn
      ports: "21,22,23,25,53,80,110,139,143,443,445,993,995,3306,3389,5432,8080,8443"
      targets: "{{live_hosts}}"
      rate: 50
    output: port_scan
    timeout: 900
    
  - order: 3
    name: Service Detection
    action: tool_execute
    tool: nmap
    parameters:
      scan_type: service_version
      targets: "{{live_hosts}}"
      ports: "{{open_ports}}"
    output: services
    timeout: 600
    
  - order: 4
    name: Banner Grabbing
    action: custom_script
    script: banner_grab.py
    parameters:
      hosts: "{{live_hosts}}"
      ports: "{{open_ports}}"
    output: banners
    
  - order: 5
    name: TLS/SSL Check
    action: tool_execute
    tool: sslscan
    parameters:
      targets: "{{https_hosts}}"
    output: ssl_results
    condition: https_hosts.length > 0
    
  - order: 6
    name: Identify Legacy Services
    action: data_analysis
    input: services
    rules:
      - service_version < threshold
      - known_vulnerable_version
    output: legacy_findings
    
  - order: 7
    name: Create Host Nodes
    action: graph_update
    nodes:
      - type: host
        values: "{{live_hosts}}"
        metadata:
          services: "{{services}}"
          ssl_status: "{{ssl_results}}"
    
  - order: 8
    name: Report to Correlation
    action: send_signal
    target: correlation_engine
    signal_type: internal_recon_complete
    data:
      hosts_found: "{{live_hosts.length}}"
      services_detected: "{{services}}"
      vulnerabilities: "{{legacy_findings}}"
```

### Rate Limiting
```yaml
rate_limits:
  packets_per_second: 100
  max_concurrent_scans: 3
  cooldown_between_hosts: 50ms
  max_ports_per_host: 20
```

### Post-conditions
- Mapa de red interna creado
- Servicios legacy identificados
- Attack Graph enriquecido

---

## RED-03: Web Attack Surface Discovery

### Metadata
```yaml
id: RED-03
name: Web Attack Surface Discovery
version: 1.0
team: red
category: web_enumeration
risk_level: low
estimated_duration: 20m
```

### Triggers
- `web_asset_detected`: Activo web identificado
- `port_80_443_open`: Puerto web detectado

### Steps

```yaml
steps:
  - order: 1
    name: HTTP Header Analysis
    action: tool_execute
    tool: curl
    parameters:
      url: "{{target_url}}"
      options: "-I -L"
    output: headers
    
  - order: 2
    name: Technology Fingerprint
    action: tool_execute
    tool: whatweb
    parameters:
      target: "{{target_url}}"
      aggression: passive
    output: tech_stack
    
  - order: 3
    name: Directory Enumeration (Limited)
    action: tool_execute
    tool: gobuster
    parameters:
      mode: dir
      url: "{{target_url}}"
      wordlist: common-100.txt  # Lista pequeña
      threads: 5
    output: directories
    timeout: 300
    
  - order: 4
    name: Robots.txt Analysis
    action: http_request
    url: "{{target_url}}/robots.txt"
    output: robots
    continue_on_error: true
    
  - order: 5
    name: Security Headers Check
    action: data_analysis
    input: headers
    checks:
      - X-Frame-Options
      - X-Content-Type-Options
      - X-XSS-Protection
      - Strict-Transport-Security
      - Content-Security-Policy
    output: security_headers_report
    
  - order: 6
    name: Cookie Security Check
    action: data_analysis
    input: headers
    checks:
      - Secure flag
      - HttpOnly flag
      - SameSite attribute
    output: cookie_report
    
  - order: 7
    name: Identify Attack Vectors
    action: risk_assessment
    inputs:
      - tech_stack
      - directories
      - security_headers_report
      - cookie_report
    output: attack_vectors
    
  - order: 8
    name: Update Graph & Notify
    action: multi_action
    actions:
      - graph_update:
          node: web_application
          metadata: "{{tech_stack}}"
      - notification:
          channel: blue_team
          template: web_surface_analyzed
```

### Security Headers Scoring

| Header | Missing Score |
|--------|---------------|
| X-Frame-Options | +10 |
| X-Content-Type-Options | +5 |
| HSTS | +15 |
| CSP | +20 |

---

## RED-04: Credential Resilience Assessment

### Metadata
```yaml
id: RED-04
name: Credential Resilience Assessment
version: 1.0
team: red
category: credential_assessment
risk_level: medium
requires_approval: true
estimated_duration: 45m
```

### Triggers
- `auth_anomaly`: Anomalía de autenticación detectada
- `credential_ioc_detected`: IOC de credencial detectado
- `manual`: Solicitud manual con aprobación

### Steps

```yaml
steps:
  - order: 1
    name: Password Policy Review
    action: api_call
    target: azure_ad
    endpoint: /policies/authenticationMethodsPolicy
    output: password_policy
    
  - order: 2
    name: MFA Status Check
    action: api_call
    target: azure_ad
    endpoint: /users?$select=userPrincipalName,mfaDetail
    output: mfa_status
    
  - order: 3
    name: Identify Weak Accounts
    action: data_analysis
    input: mfa_status
    rules:
      - mfa_enabled: false
      - last_password_change > 90d
    output: weak_accounts
    
  - order: 4
    name: Safe Password Spray Simulation
    action: tool_execute
    tool: kerbrute
    parameters:
      mode: userenum  # Solo enumeración, NO password spray real
      domain: "{{domain}}"
      userlist: "{{target_users}}"
    output: valid_users
    # NOTA: En producción, esto sería un password spray rate-limited
    # con contraseñas comunes (max 3 intentos por cuenta)
    
  - order: 5
    name: Default Credentials Check
    action: credential_check
    targets: "{{services}}"
    credential_list: default_creds.txt
    max_attempts: 1
    output: default_cred_findings
    
  - order: 6
    name: Generate Risk Report
    action: report_generation
    template: credential_resilience
    data:
      policy: "{{password_policy}}"
      mfa_coverage: "{{mfa_status}}"
      weak_accounts: "{{weak_accounts}}"
      findings: "{{default_cred_findings}}"
    output: risk_report
    
  - order: 7
    name: Notify SOAR
    action: soar_trigger
    playbook: blue_credential_remediation
    data: "{{risk_report}}"
```

### Rate Limiting (Crítico)
```yaml
rate_limits:
  max_auth_attempts_per_account: 3
  cooldown_between_attempts: 30s
  max_accounts_per_hour: 50
  lockout_detection: true
  abort_on_lockout: true
```

---

## RED-05: Attack Path Hypothesis

### Metadata
```yaml
id: RED-05
name: Attack Path Hypothesis
version: 1.0
team: red
category: threat_modeling
risk_level: safe
estimated_duration: 10m
```

### Triggers
- `correlation_positive`: Correlación detecta patrón
- `multiple_iocs_related`: IOCs relacionados identificados

### Steps

```yaml
steps:
  - order: 1
    name: Gather Context
    action: data_collection
    sources:
      - attack_graph
      - ioc_store
      - correlation_events
      - tool_outputs
    output: context
    
  - order: 2
    name: Identify Entry Points
    action: graph_analysis
    input: context.attack_graph
    query: nodes.where(type in ['ip', 'domain'] and exposed = true)
    output: entry_points
    
  - order: 3
    name: Map Vulnerable Services
    action: graph_analysis
    input: context.attack_graph
    query: nodes.where(type = 'service' and vulnerable = true)
    output: vulnerable_services
    
  - order: 4
    name: Identify High-Value Targets
    action: graph_analysis
    input: context.attack_graph
    query: nodes.where(classification in ['critical', 'sensitive'])
    output: high_value_targets
    
  - order: 5
    name: Calculate Shortest Paths
    action: graph_algorithm
    algorithm: dijkstra_shortest_path
    source: entry_points
    target: high_value_targets
    weight: risk_score
    output: attack_paths
    
  - order: 6
    name: Apply MITRE ATT&CK Mapping
    action: mitre_mapping
    input: attack_paths
    output: mitre_mapped_paths
    
  - order: 7
    name: Score Attack Paths
    action: risk_scoring
    input: mitre_mapped_paths
    factors:
      - path_length
      - vulnerability_severity
      - detection_coverage
      - asset_criticality
    output: scored_paths
    
  - order: 8
    name: Create Hypothesis Nodes
    action: graph_update
    nodes:
      - type: attack_path_hypothesis
        data: "{{scored_paths}}"
        status: pending_validation
    
  - order: 9
    name: Notify Purple Team
    action: notification
    channel: purple_team
    template: attack_path_hypothesis
    priority: high
    data:
      paths: "{{scored_paths}}"
      recommended_action: validate_detection
```

### Output: Attack Path Hypothesis
```json
{
  "hypothesis_id": "APH-2025-001",
  "paths": [
    {
      "id": 1,
      "entry_point": "exposed_web_server",
      "target": "domain_controller",
      "steps": [
        {"tactic": "TA0001", "technique": "T1190", "node": "web_app"},
        {"tactic": "TA0002", "technique": "T1059", "node": "web_server"},
        {"tactic": "TA0008", "technique": "T1021", "node": "internal_server"},
        {"tactic": "TA0006", "technique": "T1003", "node": "domain_controller"}
      ],
      "risk_score": 8.5,
      "detection_coverage": 0.60,
      "recommendation": "Increase monitoring on web server"
    }
  ],
  "created_at": "2025-12-05T10:30:00Z",
  "status": "pending_validation"
}
```

---

## 📊 Resumen de Playbooks RED

| ID | Nombre | Risk | Auto | Duration |
|----|--------|:----:|:----:|----------|
| RED-01 | Passive Recon Full Sweep | Safe | ✅ | 15m |
| RED-02 | Internal Active Recon | Low | ⚠️ | 30m |
| RED-03 | Web Attack Surface Discovery | Low | ✅ | 20m |
| RED-04 | Credential Resilience Assessment | Medium | ⚠️ | 45m |
| RED-05 | Attack Path Hypothesis | Safe | ✅ | 10m |

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05
