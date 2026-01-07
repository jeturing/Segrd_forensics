# 📗 PLAYBOOKS PURPLE TEAM - MCP v4.1

## Playbooks de Coordinación y Validación

---

## PURPLE-01: Red/Blue Sync Cycle (RBS Cycle)

### Metadata
```yaml
id: PURPLE-01
name: Red/Blue Sync Cycle (RBS Cycle)
version: 1.0
author: MCP Forensics
team: purple
category: coordination
risk_level: safe
estimated_duration: 15m
auto_execute: true
schedule: "0 */12 * * *"  # Cada 12 horas
```

### Triggers
- `investigation_start`: Nueva investigación iniciada
- `scheduled`: Cada 12 horas
- `status_in_progress`: Caso cambia a "In Progress"
- `manual`: Solicitud manual

### Steps

```yaml
steps:
  - order: 1
    name: Gather Red Agent Signals
    action: query_signals
    source: red_agent
    timeframe: last_12h
    output: red_signals
    
  - order: 2
    name: Gather Blue Agent Findings
    action: query_findings
    source: blue_agent
    timeframe: last_12h
    output: blue_findings
    
  - order: 3
    name: Correlate Attack Vectors
    action: correlation
    inputs:
      - red_signals.attack_paths
      - red_signals.exposed_services
      - blue_findings.detected_threats
      - blue_findings.mitigations
    output: correlated_vectors
    
  - order: 4
    name: Identify Detection Gaps
    action: gap_analysis
    compare:
      simulated: red_signals.attack_paths
      detected: blue_findings.detected_threats
    output: detection_gaps
    
  - order: 5
    name: Generate Exposure Map
    action: exposure_mapping
    data:
      total_vectors: correlated_vectors.count
      detected: blue_findings.detected_threats.count
      mitigated: blue_findings.mitigations.count
    calculations:
      detection_coverage: detected / total_vectors
      mitigation_coverage: mitigated / total_vectors
      residual_risk: total_vectors - mitigated
    output: exposure_map
    
  - order: 6
    name: Update Attack Graph
    action: graph_update
    nodes:
      - type: purple_correlation
        data: correlated_vectors
      - type: detection_gap
        data: detection_gaps
    edges:
      - from: red_signal
        to: blue_finding
        relationship: correlated
        
  - order: 7
    name: Prioritize Mitigations
    action: prioritization
    input: detection_gaps
    factors:
      - attack_path_criticality
      - asset_value
      - ease_of_exploitation
      - detection_difficulty
    output: prioritized_mitigations
    
  - order: 8
    name: Generate Sync Report
    action: report_generation
    template: rbs_cycle_report
    data:
      exposure_map: "{{exposure_map}}"
      gaps: "{{detection_gaps}}"
      recommendations: "{{prioritized_mitigations}}"
    output: sync_report
    
  - order: 9
    name: Notify Teams
    action: multi_notification
    channels:
      - target: ir_team
        template: exposure_summary
      - target: soc
        template: detection_gaps
      - target: blue_agent
        template: mitigation_priorities
```

### Output: Exposure Map
```json
{
  "case_id": "IR-2025-001",
  "sync_cycle": "2025-12-05T12:00:00Z",
  "exposure_map": {
    "total_attack_vectors": 15,
    "detected_by_blue": 12,
    "mitigated": 10,
    "detection_coverage_pct": 80.0,
    "mitigation_coverage_pct": 66.7,
    "residual_risk_count": 5,
    "critical_gaps": 2
  },
  "top_gaps": [
    {"vector": "encoded_powershell", "priority": 1},
    {"vector": "wmi_lateral", "priority": 2}
  ],
  "recommendations": [
    "Enable ScriptBlock Logging",
    "Add WMI monitoring rules"
  ]
}
```

---

## PURPLE-02: Validate Blue Mitigations

### Metadata
```yaml
id: PURPLE-02
name: Validate Blue Mitigations
version: 1.0
team: purple
category: validation
risk_level: low
estimated_duration: 10m
```

### Triggers
- `blue_containment_executed`: Blue Agent ejecuta contención
- `policy_requires_validation`: Política exige validación
- `manual`: Solicitud manual

### Steps

```yaml
steps:
  - order: 1
    name: Get Mitigation Details
    action: query
    source: blue_agent
    query: 
      type: mitigation
      id: "{{mitigation_id}}"
    output: mitigation_details
    
  - order: 2
    name: Verify IOC Block
    action: validation_test
    test_type: ioc_block
    target: "{{mitigation_details.blocked_iocs}}"
    method:
      - dns_resolution_attempt
      - connection_attempt
    expected: blocked
    output: ioc_block_result
    
  - order: 3
    name: Verify MFA Enforcement
    action: validation_test
    test_type: mfa_check
    target: "{{mitigation_details.user}}"
    method:
      - query_auth_methods
      - verify_enforcement_policy
    expected: mfa_required
    output: mfa_result
    
  - order: 4
    name: Controlled Access Attempt
    action: safe_test
    test_type: access_validation
    description: "Intento controlado de acceso para verificar bloqueo"
    target: "{{mitigation_details.resource}}"
    method: simulated_access
    credentials: test_credentials  # Credenciales de prueba
    expected: access_denied
    output: access_test_result
    
  - order: 5
    name: Confirm Vector Closure
    action: analysis
    inputs:
      - ioc_block_result
      - mfa_result
      - access_test_result
    logic:
      all_passed: all tests return expected
      partial: some tests pass
      failed: critical tests fail
    output: validation_status
    
  - order: 6
    name: Document Result
    action: evidence_record
    case_id: "{{case_id}}"
    record:
      type: mitigation_validation
      mitigation_id: "{{mitigation_id}}"
      tests_performed:
        - ioc_block: "{{ioc_block_result}}"
        - mfa_check: "{{mfa_result}}"
        - access_test: "{{access_test_result}}"
      overall_status: "{{validation_status}}"
      validated_by: purple_agent
      timestamp: "{{now}}"
      
  - order: 7
    name: Update Graph Status
    action: graph_update
    query: "mitigation_id = '{{mitigation_id}}'"
    update:
      validated: true
      validation_status: "{{validation_status}}"
      
  - order: 8
    name: Notify Based on Result
    action: conditional_notification
    conditions:
      - if: validation_status == "all_passed"
        channel: blue_agent
        template: mitigation_validated
      - if: validation_status == "failed"
        channel: [ir_lead, blue_agent]
        template: mitigation_failed
        priority: high
```

---

## PURPLE-03: Simulated Attack Path

### Metadata
```yaml
id: PURPLE-03
name: Simulated Attack Path
version: 1.0
team: purple
category: attack_simulation
risk_level: low
requires_approval: true
estimated_duration: 30m
```

### Triggers
- `attack_path_hypothesis_created`: Red Agent crea hipótesis
- `high_risk_path_detected`: Ruta de alto riesgo detectada
- `manual`: Solicitud manual con aprobación

### Pre-conditions
- Attack Path Hypothesis disponible
- Aprobación de IR Lead
- Blue Agent activo para validar detección

### Steps

```yaml
steps:
  - order: 1
    name: Get Attack Path Hypothesis
    action: query
    source: attack_graph
    query:
      type: attack_path_hypothesis
      status: pending_validation
    output: attack_path
    
  - order: 2
    name: Request Approval
    action: approval_request
    approvers: [ir_lead]
    details:
      path: "{{attack_path}}"
      steps_to_simulate: "{{attack_path.steps}}"
      risk_assessment: "{{attack_path.risk_score}}"
    timeout: 1800  # 30 minutos
    output: approval
    
  - order: 3
    name: Notify Blue Agent to Monitor
    action: notification
    channel: blue_agent
    template: simulation_starting
    data:
      case_id: "{{case_id}}"
      monitoring_required: true
      # NO incluir detalles específicos para no sesgar
    
  - order: 4
    name: Simulate Step 1 - Initial Access
    action: safe_simulation
    step: "{{attack_path.steps[0]}}"
    simulation_type: non_destructive
    log_all: true
    output: step1_result
    wait: 30  # Esperar detección
    
  - order: 5
    name: Check Blue Detection - Step 1
    action: query_detection
    source: blue_agent
    timeframe: last_60s
    expected_detection: "{{attack_path.steps[0].expected_alert}}"
    output: detection1_result
    
  - order: 6
    name: Simulate Remaining Steps
    action: loop
    items: "{{attack_path.steps[1:]}}"
    for_each:
      - safe_simulation:
          step: "{{item}}"
          simulation_type: non_destructive
      - wait: 30
      - query_detection:
          expected: "{{item.expected_alert}}"
    output: simulation_results
    
  - order: 7
    name: Calculate Detection Rate
    action: calculation
    formula: |
      detected = sum(1 for r in simulation_results if r.detected)
      total = len(simulation_results)
      rate = detected / total
    output: detection_rate
    
  - order: 8
    name: Apply MITRE Impact Rating
    action: mitre_analysis
    input: simulation_results
    mapping:
      - technique: "{{step.technique}}"
        detected: "{{step.detected}}"
        time_to_detect: "{{step.ttd}}"
    output: mitre_rating
    
  - order: 9
    name: Generate Hardening Recommendations
    action: recommendation_engine
    input:
      gaps: simulation_results.where(detected == false)
      mitre: mitre_rating
    output: hardening_recommendations
    
  - order: 10
    name: Create Validation Report
    action: report_generation
    template: attack_simulation_report
    data:
      path: "{{attack_path}}"
      simulation_results: "{{simulation_results}}"
      detection_rate: "{{detection_rate}}"
      mitre_rating: "{{mitre_rating}}"
      recommendations: "{{hardening_recommendations}}"
    output: validation_report
    
  - order: 11
    name: Update Attack Path Status
    action: graph_update
    node: "{{attack_path.id}}"
    update:
      status: validated
      detection_rate: "{{detection_rate}}"
      recommendations: "{{hardening_recommendations}}"
```

### Safe Simulation Types

| Type | Description | Impact |
|------|-------------|--------|
| `dns_query` | Resolver dominio malicioso | None |
| `http_request` | Request a URL sospechosa | None |
| `auth_attempt` | Intento de auth (fail esperado) | None |
| `file_access` | Lectura de archivo honeypot | None |
| `process_spawn` | Proceso benigno con nombre sospechoso | Low |

---

## PURPLE-04: Exposure Reduction Planner

### Metadata
```yaml
id: PURPLE-04
name: Exposure Reduction Planner
version: 1.0
team: purple
category: risk_management
risk_level: safe
estimated_duration: 20m
```

### Triggers
- `high_exposure_case`: Caso con exposición alta (>50%)
- `external_attacks_detected`: Ataques externos detectados
- `weekly_schedule`: Planificación semanal
- `manual`: Solicitud manual

### Steps

```yaml
steps:
  - order: 1
    name: Load Attack Graph
    action: graph_query
    query: |
      MATCH (n)
      WHERE n.case_id = '{{case_id}}'
      RETURN n
    output: attack_graph
    
  - order: 2
    name: Identify Critical Nodes
    action: graph_analysis
    input: attack_graph
    algorithm: centrality
    metrics:
      - betweenness_centrality
      - pagerank
      - degree_centrality
    filter: node.criticality >= high
    output: critical_nodes
    
  - order: 3
    name: Calculate Shortest Attack Paths
    action: graph_algorithm
    algorithm: all_shortest_paths
    source: nodes.where(type == 'entry_point')
    target: nodes.where(classification == 'crown_jewel')
    output: attack_paths
    
  - order: 4
    name: Identify Chokepoints
    action: chokepoint_analysis
    input: attack_paths
    description: "Nodos que si se protegen bloquean múltiples rutas"
    output: chokepoints
    
  - order: 5
    name: Calculate Risk Reduction Impact
    action: impact_analysis
    for_each: chokepoints
    calculate:
      paths_blocked: count paths through node
      risk_reduction: sum(path.risk_score) for blocked paths
      implementation_cost: estimate from mitigation_type
      roi: risk_reduction / implementation_cost
    output: mitigation_impacts
    
  - order: 6
    name: Prioritize Mitigations
    action: prioritization
    input: mitigation_impacts
    sort_by: roi DESC
    limit: 10
    output: prioritized_plan
    
  - order: 7
    name: Generate SOC Action Plan
    action: plan_generation
    template: exposure_reduction_plan
    data:
      critical_nodes: "{{critical_nodes}}"
      chokepoints: "{{chokepoints}}"
      prioritized_actions: "{{prioritized_plan}}"
    format: actionable_steps
    output: soc_plan
    
  - order: 8
    name: Deliver to Jeturing CORE
    action: api_call
    target: jeturing_core
    endpoint: /api/plans/exposure-reduction
    method: POST
    body:
      case_id: "{{case_id}}"
      plan: "{{soc_plan}}"
      priority: high
    output: core_delivery
    
  - order: 9
    name: Schedule Follow-up
    action: schedule_task
    task: PURPLE-04
    delay: 7d
    parameters:
      case_id: "{{case_id}}"
      compare_with: "{{exposure_baseline}}"
```

### Output: Exposure Reduction Plan
```json
{
  "plan_id": "ERP-2025-001",
  "case_id": "IR-2025-001",
  "created_at": "2025-12-05T10:00:00Z",
  "current_exposure": {
    "attack_paths": 15,
    "critical_nodes": 5,
    "exposure_score": 7.8
  },
  "prioritized_actions": [
    {
      "rank": 1,
      "action": "Enable MFA on VPN",
      "chokepoint": "vpn_gateway",
      "paths_blocked": 8,
      "risk_reduction": 45,
      "estimated_effort": "4h",
      "roi_score": 9.2
    },
    {
      "rank": 2,
      "action": "Patch Exchange Server",
      "chokepoint": "mail_server",
      "paths_blocked": 5,
      "risk_reduction": 35,
      "estimated_effort": "8h",
      "roi_score": 7.5
    }
  ],
  "projected_improvement": {
    "exposure_score_after": 4.2,
    "reduction_pct": 46
  }
}
```

---

## PURPLE-05: Autonomous Tuning Engine

### Metadata
```yaml
id: PURPLE-05
name: Autonomous Tuning Engine
version: 1.0
team: purple
category: optimization
risk_level: safe
estimated_duration: 30m
schedule: "0 3 * * 0"  # Domingos 3AM
```

### Triggers
- `inconsistent_signals`: Señales RED/BLUE inconsistentes
- `high_false_positive_rate`: FP rate > 10%
- `scheduled`: Semanal
- `manual`: Solicitud manual

### Steps

```yaml
steps:
  - order: 1
    name: Collect Performance Metrics
    action: metrics_collection
    sources:
      - correlation_engine.rules
      - blue_agent.detections
      - analyst_feedback
    timeframe: last_30d
    output: performance_data
    
  - order: 2
    name: Calculate Rule Accuracy
    action: accuracy_analysis
    for_each: performance_data.rules
    calculate:
      true_positives: analyst_confirmed == true
      false_positives: analyst_confirmed == false
      precision: tp / (tp + fp)
      recall: tp / (tp + fn)
      f1_score: 2 * (precision * recall) / (precision + recall)
    output: rule_accuracy
    
  - order: 3
    name: Identify Low-Precision Rules
    action: filter
    input: rule_accuracy
    condition: precision < 0.85 OR f1_score < 0.80
    output: rules_to_tune
    
  - order: 4
    name: Analyze False Positives
    action: fp_analysis
    input: rules_to_tune
    for_each:
      - extract_common_patterns
      - identify_exception_candidates
      - calculate_threshold_adjustment
    output: tuning_recommendations
    
  - order: 5
    name: Update Thresholds
    action: threshold_update
    target: correlation_engine
    updates:
      - rule_id: "{{rule.id}}"
        current_threshold: "{{rule.threshold}}"
        new_threshold: "{{rule.recommended_threshold}}"
        reason: "{{rule.tuning_reason}}"
    require_approval: true
    output: threshold_updates
    
  - order: 6
    name: Update IOC Scoring
    action: ioc_scoring_update
    analysis:
      - stale_iocs: last_match > 90d
      - high_fp_iocs: fp_rate > 0.20
      - low_confidence: confidence < 0.50
    updates:
      - decrease_score: stale_iocs
      - flag_review: high_fp_iocs
      - archive: low_confidence AND no_recent_match
    output: ioc_updates
    
  - order: 7
    name: Retrain ML Models
    action: ml_training
    condition: ml_accuracy < 0.85
    models:
      - anomaly_detection
      - behavior_analysis
    training_data: last_30d_labeled
    validation_split: 0.2
    output: ml_training_result
    
  - order: 8
    name: Deploy Updates
    action: deployment
    condition: all_validations_pass
    targets:
      - correlation_engine: threshold_updates
      - ioc_store: ioc_updates
      - ml_service: ml_training_result
    rollback_on_failure: true
    output: deployment_result
    
  - order: 9
    name: Generate Tuning Report
    action: report_generation
    template: autonomous_tuning_report
    data:
      rules_analyzed: "{{rule_accuracy.length}}"
      rules_tuned: "{{threshold_updates.length}}"
      iocs_updated: "{{ioc_updates.length}}"
      ml_retrained: "{{ml_training_result.retrained}}"
      expected_improvement:
        precision: "+{{improvement.precision}}%"
        fp_reduction: "-{{improvement.fp_reduction}}%"
    output: tuning_report
    
  - order: 10
    name: Notify Teams
    action: notification
    channel: security_engineering
    template: tuning_complete
    data:
      summary: "{{tuning_report.summary}}"
      changes_made: "{{tuning_report.changes}}"
```

### Tuning Rules Configuration
```yaml
tuning_rules:
  precision_threshold: 0.85
  recall_threshold: 0.80
  f1_threshold: 0.80
  
  threshold_adjustments:
    - condition: "false_positive_rate > 0.15"
      action: "increase_threshold"
      adjustment: "+20%"
      
    - condition: "false_positive_rate > 0.10"
      action: "increase_threshold"
      adjustment: "+10%"
      
    - condition: "false_negative_rate > 0.20"
      action: "decrease_threshold"
      adjustment: "-15%"
      
    - condition: "no_matches_30d AND enabled"
      action: "flag_for_review"
      
  ml_retrain_conditions:
    - accuracy < 0.85
    - drift_score > 0.15
    - new_labeled_samples > 1000
```

---

## 📊 Resumen de Playbooks PURPLE

| ID | Nombre | Risk | Auto | Duration |
|----|--------|:----:|:----:|----------|
| PURPLE-01 | Red/Blue Sync Cycle | Safe | ✅ | 15m |
| PURPLE-02 | Validate Blue Mitigations | Low | ✅ | 10m |
| PURPLE-03 | Simulated Attack Path | Low | ⚠️ | 30m |
| PURPLE-04 | Exposure Reduction Planner | Safe | ✅ | 20m |
| PURPLE-05 | Autonomous Tuning Engine | Safe | ✅ | 30m |

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05
