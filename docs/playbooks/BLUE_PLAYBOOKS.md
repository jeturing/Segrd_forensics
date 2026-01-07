# 📘 PLAYBOOKS BLUE TEAM - MCP v4.1

## Playbooks de Respuesta a Incidentes y Análisis Forense

---

## BLUE-01: Host Compromise Initial Triage

### Metadata
```yaml
id: BLUE-01
name: Host Compromise Initial Triage
version: 1.0
author: MCP Forensics
team: blue
category: incident_response
risk_level: safe
estimated_duration: 10m
auto_execute: true
```

### Triggers
- `ioc_detected`: IOC detectado en endpoint
- `red_agent_signal`: Señal del Red Agent
- `auth_anomaly`: Evento de autenticación sospechosa
- `siem_alert`: Alerta del SIEM

### Steps

```yaml
steps:
  - order: 1
    name: Collect Host Metadata
    action: tool_execute
    tool: osquery
    parameters:
      query: |
        SELECT hostname, uuid, cpu_brand, physical_memory, 
               hardware_vendor, hardware_model
        FROM system_info
    output: host_info
    
  - order: 2
    name: Get Top Processes
    action: tool_execute
    tool: osquery
    parameters:
      query: |
        SELECT p.pid, p.name, p.path, p.cmdline, 
               p.resident_size, p.user_time
        FROM processes p
        ORDER BY p.resident_size DESC
        LIMIT 30
    output: processes
    
  - order: 3
    name: Extract Network Connections
    action: tool_execute
    tool: osquery
    parameters:
      query: |
        SELECT p.pid, p.name, s.local_address, s.local_port,
               s.remote_address, s.remote_port, s.state
        FROM process_open_sockets s
        JOIN processes p ON s.pid = p.pid
        WHERE s.remote_address != ''
    output: network_connections
    
  - order: 4
    name: Check Scheduled Tasks
    action: tool_execute
    tool: osquery
    parameters:
      query: |
        SELECT name, action, path, enabled, last_run_time
        FROM scheduled_tasks
        WHERE enabled = 1
    output: scheduled_tasks
    
  - order: 5
    name: Check Running Services
    action: tool_execute
    tool: osquery
    parameters:
      query: |
        SELECT name, display_name, status, start_type, path
        FROM services
        WHERE status = 'RUNNING'
    output: services
    
  - order: 6
    name: Validate Hashes in IOC Store
    action: ioc_lookup
    input: processes.path
    hash_type: sha256
    output: ioc_matches
    
  - order: 7
    name: Calculate Host Risk Score
    action: risk_calculation
    factors:
      - ioc_matches.count * 30
      - suspicious_connections.count * 20
      - unsigned_processes.count * 10
      - recent_scheduled_tasks.count * 15
    output: host_risk_score
    
  - order: 8
    name: Update Investigation Timeline
    action: timeline_update
    case_id: "{{case_id}}"
    events:
      - type: triage_started
        data: host_info
      - type: iocs_checked
        data: ioc_matches
      - type: risk_calculated
        data: host_risk_score
        
  - order: 9
    name: Determine Next Actions
    action: decision
    conditions:
      - if: host_risk_score >= 80
        then: trigger_containment
      - if: host_risk_score >= 50
        then: deep_analysis
      - else: monitor
    output: recommended_action
```

### Output: Host Risk Report
```json
{
  "host_id": "WORKSTATION-01",
  "host_risk_score": 75,
  "findings": {
    "ioc_matches": 2,
    "suspicious_connections": 3,
    "unsigned_processes": 5
  },
  "recommended_action": "deep_analysis",
  "timeline_updated": true
}
```

---

## BLUE-02: Malware Presence Assessment

### Metadata
```yaml
id: BLUE-02
name: Malware Presence Assessment
version: 1.0
team: blue
category: malware_analysis
risk_level: safe
estimated_duration: 15m
```

### Triggers
- `suspicious_hash`: Hash sospechoso detectado
- `ml_anomaly`: Anomalía detectada por ML
- `av_alert`: Alerta de antivirus

### Steps

```yaml
steps:
  - order: 1
    name: YARA Scan - Safe Ruleset
    action: tool_execute
    tool: yara
    parameters:
      rules: /opt/forensics-tools/yara-rules/safe/
      target: "{{scan_path}}"
      options: "-r -w"
    output: yara_results
    timeout: 600
    
  - order: 2
    name: Loki IOC Scan
    action: tool_execute
    tool: loki
    parameters:
      path: "{{scan_path}}"
      intense: true
      noprocscan: true
    output: loki_results
    timeout: 900
    
  - order: 3
    name: Check Persistence Mechanisms
    action: multi_query
    queries:
      - name: registry_run
        tool: osquery
        query: |
          SELECT * FROM registry 
          WHERE key LIKE '%\Run%' 
          OR key LIKE '%\RunOnce%'
      - name: startup_items
        tool: osquery
        query: SELECT * FROM startup_items
      - name: services
        tool: osquery
        query: |
          SELECT * FROM services 
          WHERE start_type = 'AUTO_START'
    output: persistence_checks
    
  - order: 4
    name: Calculate Malware Confidence Score
    action: scoring
    inputs:
      yara_matches: yara_results.matches.length
      loki_alerts: loki_results.alerts.length
      loki_warnings: loki_results.warnings.length
      persistence_found: persistence_checks.suspicious.length
    weights:
      yara_critical: 40
      yara_high: 25
      loki_alert: 30
      loki_warning: 10
      persistence: 20
    output: malware_confidence_score
    
  - order: 5
    name: Register IOCs
    action: create_iocs
    condition: malware_confidence_score >= 50
    sources:
      - yara_results.hashes
      - loki_results.iocs
    auto_enrich: true
    
  - order: 6
    name: Link to Investigation
    action: evidence_link
    case_id: "{{case_id}}"
    evidence:
      - type: yara_report
        file: "{{yara_results.report_path}}"
      - type: loki_report
        file: "{{loki_results.report_path}}"
      
  - order: 7
    name: Decision & Notification
    action: decision_notify
    conditions:
      - if: malware_confidence_score >= 80
        action: trigger_containment
        notify: [soc, ir_team]
        priority: critical
      - if: malware_confidence_score >= 50
        action: escalate
        notify: [ir_team]
        priority: high
```

### YARA Rules Categories
| Category | Description | Alert Level |
|----------|-------------|-------------|
| `gen_malware` | Generic malware signatures | High |
| `apt_indicators` | APT group indicators | Critical |
| `ransomware` | Ransomware families | Critical |
| `webshells` | Web shell indicators | High |
| `miners` | Cryptocurrency miners | Medium |

---

## BLUE-03: Memory Forensics Lite

### Metadata
```yaml
id: BLUE-03
name: Memory Forensics Lite
version: 1.0
team: blue
category: memory_forensics
risk_level: low
estimated_duration: 30m
requires_approval: true
```

### Triggers
- `process_anomaly`: Proceso anómalo detectado
- `attack_path_predicted`: Red Agent predice ruta de ataque
- `injection_suspected`: Sospecha de inyección de código

### Steps

```yaml
steps:
  - order: 1
    name: Capture Memory Metadata
    action: tool_execute
    tool: volatility3
    parameters:
      plugin: windows.info
      memory_file: "{{memory_dump}}"
    output: memory_info
    
  - order: 2
    name: List Processes
    action: tool_execute
    tool: volatility3
    parameters:
      plugin: windows.pslist
      memory_file: "{{memory_dump}}"
    output: process_list
    
  - order: 3
    name: Detect Hidden Processes
    action: tool_execute
    tool: volatility3
    parameters:
      plugin: windows.psscan
      memory_file: "{{memory_dump}}"
    output: psscan_results
    
  - order: 4
    name: Check for Code Injection
    action: tool_execute
    tool: volatility3
    parameters:
      plugin: windows.malfind
      memory_file: "{{memory_dump}}"
    output: malfind_results
    
  - order: 5
    name: Extract Network Connections
    action: tool_execute
    tool: volatility3
    parameters:
      plugin: windows.netscan
      memory_file: "{{memory_dump}}"
    output: network_artifacts
    
  - order: 6
    name: Identify Suspicious Patterns
    action: analysis
    inputs:
      - process_list
      - psscan_results
      - malfind_results
    rules:
      - hidden_process: psscan not in pslist
      - code_injection: malfind.protection contains 'RWX'
      - suspicious_parent: parent_process in known_bad_parents
    output: suspicious_findings
    
  - order: 7
    name: Send to SOAR
    action: soar_signal
    signal_type: memory_analysis_complete
    data:
      findings: suspicious_findings
      severity: calculated
      
  - order: 8
    name: Update Attack Graph
    action: graph_update
    nodes:
      - type: suspicious_process
        values: suspicious_findings.processes
        metadata:
          injection_detected: true
```

---

## BLUE-04: Lateral Movement Detection

### Metadata
```yaml
id: BLUE-04
name: Lateral Movement Detection
version: 1.0
team: blue
category: threat_hunting
risk_level: safe
estimated_duration: 20m
```

### Triggers
- `no_mfa_login`: Login sin MFA detectado
- `multi_location_access`: Acceso desde múltiples ubicaciones
- `smb_auth_anomaly`: Anomalía en autenticación SMB

### Steps

```yaml
steps:
  - order: 1
    name: Query M365 Sign-in Logs
    action: api_call
    target: microsoft_graph
    endpoint: /auditLogs/signIns
    parameters:
      $filter: "createdDateTime ge {{start_time}}"
      $top: 500
    output: signin_logs
    
  - order: 2
    name: Analyze Login Patterns
    action: analysis
    input: signin_logs
    checks:
      - impossible_travel: location_change_speed > 500_km_per_hour
      - multiple_failures_then_success: failures >= 5 && success
      - unusual_time: hour not in user_normal_hours
      - new_device: device_id not in known_devices
    output: login_anomalies
    
  - order: 3
    name: Check Remote Connections
    action: tool_execute
    tool: osquery
    parameters:
      query: |
        SELECT * FROM logged_in_users
        WHERE host != 'localhost'
        UNION
        SELECT * FROM process_open_sockets
        WHERE remote_port IN (445, 3389, 5985, 5986, 135)
    output: remote_connections
    
  - order: 4
    name: Analyze SMB/WinRM Traffic
    action: log_analysis
    sources:
      - windows_security_log
      - event_ids: [4624, 4625, 4648, 4672]
    timeframe: last_24h
    output: auth_events
    
  - order: 5
    name: Detect Lateral Movement Sequence
    action: sequence_detection
    input: auth_events
    patterns:
      - name: pass_the_hash
        sequence:
          - event_4624_type_3
          - event_4672
          - new_process_creation
      - name: remote_service_creation
        sequence:
          - event_4624_type_3
          - event_7045
    output: lateral_patterns
    
  - order: 6
    name: Mark Affected Nodes
    action: graph_update
    nodes:
      - type: host
        values: lateral_patterns.source_hosts
        status: lateral_movement_source
      - type: host
        values: lateral_patterns.target_hosts
        status: lateral_movement_target
    edges:
      - from: source_hosts
        to: target_hosts
        relationship: lateral_movement
        timestamp: detected_at
        
  - order: 7
    name: Recommend Mitigation
    action: generate_recommendations
    based_on: lateral_patterns
    recommendations:
      - enable_mfa
      - disable_ntlm
      - segment_network
      - increase_monitoring
```

---

## BLUE-05: Network Threat Hunting

### Metadata
```yaml
id: BLUE-05
name: Network Threat Hunting
version: 1.0
team: blue
category: network_forensics
risk_level: low
estimated_duration: 15m
```

### Triggers
- `suspicious_traffic`: Tráfico sospechoso detectado
- `c2_ioc_detected`: IOC de C2 detectado
- `dns_anomaly`: Anomalía DNS detectada

### Steps

```yaml
steps:
  - order: 1
    name: Capture Traffic Sample
    action: tool_execute
    tool: tcpdump
    parameters:
      interface: "{{interface}}"
      duration: 10  # segundos
      filter: "{{bpf_filter}}"
      output_file: /tmp/capture.pcap
    output: pcap_file
    
  - order: 2
    name: Extract DNS Queries
    action: tool_execute
    tool: tshark
    parameters:
      input: "{{pcap_file}}"
      filter: "dns"
      fields: ["dns.qry.name", "dns.a", "ip.src", "ip.dst"]
    output: dns_queries
    
  - order: 3
    name: Check Against Threat Intel
    action: threat_intel_lookup
    input: dns_queries.domains
    sources:
      - alienvault_otx
      - virustotal
      - abuse_ch
    output: threat_matches
    
  - order: 4
    name: Detect Beaconing
    action: beacon_detection
    input: pcap_file
    parameters:
      min_interval: 30
      max_interval: 3600
      jitter_tolerance: 0.2
    output: beacon_candidates
    
  - order: 5
    name: Identify Suspicious Connections
    action: connection_analysis
    input: pcap_file
    rules:
      - high_frequency_dns: queries_per_minute > 100
      - long_connections: duration > 3600
      - unusual_ports: port not in common_ports
      - high_data_ratio: upload/download > 1
    output: suspicious_connections
    
  - order: 6
    name: Create Network IOCs
    action: create_iocs
    sources:
      - threat_matches
      - beacon_candidates
      - suspicious_connections
    ioc_types: [ip, domain, url]
    
  - order: 7
    name: Alert Red Agent
    action: notification
    channel: red_agent
    template: network_threat_detected
    data:
      c2_candidates: beacon_candidates
      suspicious_domains: threat_matches
```

---

## BLUE-06: Credential Compromise Validation

### Metadata
```yaml
id: BLUE-06
name: Credential Compromise Validation
version: 1.0
team: blue
category: credential_security
risk_level: safe
estimated_duration: 10m
```

### Triggers
- `hibp_match`: Coincidencia en HIBP
- `suspicious_user_activity`: Actividad sospechosa del usuario
- `dark_web_alert`: Alerta de dark web

### Steps

```yaml
steps:
  - order: 1
    name: Check MFA Status
    action: api_call
    target: microsoft_graph
    endpoint: /users/{{user_id}}/authentication/methods
    output: auth_methods
    
  - order: 2
    name: Get Active Sessions
    action: api_call
    target: microsoft_graph
    endpoint: /users/{{user_id}}/signInActivity
    output: sessions
    
  - order: 3
    name: Check OAuth Consents
    action: api_call
    target: microsoft_graph
    endpoint: /users/{{user_id}}/oauth2PermissionGrants
    output: oauth_grants
    
  - order: 4
    name: Analyze Session Risk
    action: analysis
    input: sessions
    checks:
      - suspicious_location
      - unusual_time
      - new_device
      - multiple_failed_then_success
    output: session_risk
    
  - order: 5
    name: Revoke Tokens if High Risk
    action: conditional_action
    condition: session_risk.score >= 70
    actions:
      - api_call:
          target: microsoft_graph
          endpoint: /users/{{user_id}}/revokeSignInSessions
          method: POST
      - notification:
          channel: user
          template: sessions_revoked
    output: revocation_result
    
  - order: 6
    name: Force Password Reset
    action: conditional_action
    condition: hibp_match == true OR session_risk.score >= 80
    actions:
      - api_call:
          target: microsoft_graph
          endpoint: /users/{{user_id}}
          method: PATCH
          body: {"passwordProfile": {"forceChangePasswordNextSignIn": true}}
    output: password_reset_result
    
  - order: 7
    name: Generate User Risk Score
    action: risk_calculation
    factors:
      - hibp_breach: 30
      - no_mfa: 25
      - suspicious_oauth: 20
      - session_anomaly: 25
    output: user_risk_score
    
  - order: 8
    name: Update Timeline
    action: timeline_update
    events:
      - type: credential_check
      - type: remediation_applied
        data:
          tokens_revoked: revocation_result
          password_reset: password_reset_result
```

---

## BLUE-07: Containment Automation

### Metadata
```yaml
id: BLUE-07
name: Containment Automation
version: 1.0
team: blue
category: containment
risk_level: medium
requires_approval: true
estimated_duration: 5m
```

### Triggers
- `host_compromised_confirmed`: Host confirmado como comprometido (Confidence > 80%)
- `active_malware`: Malware activo detectado
- `data_exfiltration`: Exfiltración de datos detectada

### Pre-conditions
- Aprobación de IR Lead (para hosts críticos)
- Política de contención definida

### Steps

```yaml
steps:
  - order: 1
    name: Verify Containment Approval
    action: approval_check
    approvers: [ir_lead, soc_manager]
    timeout: 300  # 5 minutos
    auto_approve_conditions:
      - malware_confidence >= 95
      - active_exfiltration == true
    output: approval_status
    
  - order: 2
    name: Isolate Host
    action: containment_action
    condition: approval_status == approved
    type: network_isolation
    target: "{{host_id}}"
    method: 
      - firewall_block
      - vlan_quarantine
    output: isolation_result
    
  - order: 3
    name: Disable User Account
    action: api_call
    target: microsoft_graph
    endpoint: /users/{{user_id}}
    method: PATCH
    body: {"accountEnabled": false}
    output: account_disabled
    
  - order: 4
    name: Revoke OAuth Tokens
    action: api_call
    target: microsoft_graph
    endpoint: /users/{{user_id}}/revokeSignInSessions
    method: POST
    output: tokens_revoked
    
  - order: 5
    name: Block IOCs at Perimeter
    action: firewall_update
    target: perimeter_firewall
    rules:
      - block_ip: "{{malicious_ips}}"
      - block_domain: "{{malicious_domains}}"
    output: firewall_updated
    
  - order: 6
    name: Notify Purple Agent
    action: notification
    channel: purple_agent
    template: containment_executed
    data:
      host: "{{host_id}}"
      actions_taken: [isolation, account_disabled, tokens_revoked]
      
  - order: 7
    name: Chain of Custody Record
    action: evidence_record
    case_id: "{{case_id}}"
    record:
      type: containment_action
      timestamp: "{{now}}"
      actor: blue_agent
      actions: 
        - isolation_result
        - account_disabled
        - tokens_revoked
        - firewall_updated
      hash: "{{actions_hash}}"
```

### Containment Actions Available

| Action | Risk | Reversible | Approval |
|--------|:----:|:----------:|:--------:|
| Network Isolation | High | ✅ | Required |
| Account Disable | Medium | ✅ | Auto (P0) |
| Token Revocation | Low | ❌ | Auto |
| IOC Block | Low | ✅ | Auto |
| Process Kill | Medium | ❌ | Required |

---

## 📊 Resumen de Playbooks BLUE

| ID | Nombre | Risk | Auto | Duration |
|----|--------|:----:|:----:|----------|
| BLUE-01 | Host Compromise Initial Triage | Safe | ✅ | 10m |
| BLUE-02 | Malware Presence Assessment | Safe | ✅ | 15m |
| BLUE-03 | Memory Forensics Lite | Low | ⚠️ | 30m |
| BLUE-04 | Lateral Movement Detection | Safe | ✅ | 20m |
| BLUE-05 | Network Threat Hunting | Low | ✅ | 15m |
| BLUE-06 | Credential Compromise Validation | Safe | ✅ | 10m |
| BLUE-07 | Containment Automation | Medium | ⚠️ | 5m |

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05
