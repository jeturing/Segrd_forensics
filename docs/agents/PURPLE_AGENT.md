# 🟣 MCP PURPLE AGENT - Documentación Completa

## Visión General

El **Agente PURPLE** del MCP es el coordinador inteligente que une las capacidades de los equipos RED y BLUE para optimizar defensas, validar mitigaciones y simular ataques controlados con verificación de detección.

**Rol**: Validación continua de controles de seguridad.

---

## 🎯 Objetivos

- Sincronizar hallazgos RED y BLUE
- Validar que mitigaciones funcionan
- Simular rutas de ataque realistas
- Planificar reducción de exposición
- Ajustar umbrales y reglas automáticamente
- Mejorar detección mediante feedback

---

## ✅ Capacidades

### 1. Red/Blue Synchronization
- Correlacionar señales de ambos equipos
- Generar "Exposure Map"
- Identificar gaps de detección
- Priorizar mitigaciones

### 2. Mitigation Validation
- Verificar bloqueos de IOC
- Confirmar MFA activado
- Intentos controlados de acceso
- Documentar resultados

### 3. Attack Path Simulation
- Simular pasos seguros (sin explotación)
- Validar detección por Blue Team
- Aplicar MITRE Impact Rating
- Generar recomendaciones de hardening

### 4. Exposure Reduction
- Analizar Attack Graph completo
- Identificar nodos críticos
- Identificar rutas cortas de ataque
- Producir plan para SOC

### 5. Autonomous Tuning
- Detectar reglas con baja precisión
- Ajustar umbrales recomendados
- Actualizar scoring de IOCs
- Entrenar modelos ML ligeros

---

## 📋 Playbooks PURPLE Team

### PURPLE-01: Red/Blue Sync Cycle (RBS Cycle)

**Trigger**: `investigation_start`, `every_12h`, `status_in_progress`

**Steps**:
1. Obtener señales de Red Agent
2. Obtener hallazgos de Blue Agent
3. Correlación de vectores comunes
4. Generar "Exposure Map"
5. Actualizar Attack Graph
6. Recomendar mitigación priorizada

---

### PURPLE-02: Validate Blue Mitigations

**Trigger**: `blue_containment_executed`, `policy_requires_validation`

**Steps**:
1. Verificar bloqueo de IOC funciona
2. Validar MFA activado
3. Intento controlado de acceso (safe)
4. Confirmar cierre del vector
5. Documentar resultado automático

---

### PURPLE-03: Simulated Attack Path

**Trigger**: `attack_path_hypothesis_created`

**Steps**:
1. Simular pasos seguros (sin explotación)
2. Validar detección por Blue Team
3. Confirmar vulnerabilidades reales
4. Aplicar MITRE Impact Rating
5. Crear recomendación de hardening

---

### PURPLE-04: Exposure Reduction Planner

**Trigger**: `high_exposure_case`, `external_attacks_detected`

**Steps**:
1. Analizar Attack Graph completo
2. Identificar nodos críticos
3. Identificar rutas cortas de ataque
4. Priorizar mitigaciones
5. Producir plan para SOC
6. Entregar a Jeturing CORE

---

### PURPLE-05: Autonomous Tuning Engine

**Trigger**: `inconsistent_signals`, `high_false_positive_rate`

**Steps**:
1. Detectar reglas con baja precisión
2. Ajustar umbrales recomendados
3. Actualizar scoring de IOCs
4. Reconstruir correlaciones
5. Entrenar modelo ML ligero
6. Publicar nueva versión de reglas

---

## 🔄 Ciclo Purple Team

```
┌──────────────────────────────────────────────────────────┐
│                    PURPLE TEAM CYCLE                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐  │
│   │   RED   │ ──────► │ PURPLE  │ ◄────── │  BLUE   │  │
│   │  Agent  │         │  Agent  │         │  Agent  │  │
│   └────┬────┘         └────┬────┘         └────┬────┘  │
│        │                   │                   │       │
│        │    Attack         │    Detection      │       │
│        │    Signals        │    Validation     │       │
│        │                   │                   │       │
│        ▼                   ▼                   ▼       │
│   ┌─────────────────────────────────────────────────┐ │
│   │              CORRELATION ENGINE                  │ │
│   └─────────────────────────────────────────────────┘ │
│                         │                              │
│                         ▼                              │
│   ┌─────────────────────────────────────────────────┐ │
│   │              ATTACK GRAPH UPDATE                │ │
│   └─────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🔗 Integración con Componentes

### Red Agent
- Recibe: Attack Path Hypotheses
- Envía: Validation requests
- Sincroniza: Vectores detectados

### Blue Agent
- Recibe: Detection confirmations
- Envía: Mitigation validation requests
- Sincroniza: Hallazgos forenses

### SOAR Engine
- Orquesta playbooks Purple
- Escala según resultados
- Documenta validaciones

### Correlation Engine
- Recibe alertas correladas
- Mejora reglas basado en feedback
- Ajusta ML heuristics

### Graph Engine
- Crea nodos: `PURPLE_CORRELATION`, `MITIGATION_ACTION`
- Aristas: `Purple Agent → Correlated Insight`

---

## 📊 Métricas Purple Team

```json
{
  "agent_id": "purple-agent-001",
  "metrics": {
    "validations_completed": 89,
    "mitigations_confirmed": 76,
    "detection_gaps_found": 13,
    "rules_tuned": 25,
    "attack_paths_simulated": 8,
    "exposure_reduction_pct": 45
  }
}
```

---

## 📈 Exposure Map

El Purple Agent genera un "Exposure Map" que incluye:

| Métrica | Descripción |
|---------|-------------|
| Total Attack Vectors | Vectores identificados por Red |
| Detected by Blue | Vectores que Blue puede detectar |
| Detection Gap | Vectores no detectados |
| Mitigated | Vectores con mitigación activa |
| Residual Risk | Vectores sin protección |

### Ejemplo
```json
{
  "case_id": "IR-2025-001",
  "exposure_map": {
    "total_vectors": 15,
    "detected_by_blue": 12,
    "detection_gap": 3,
    "mitigated": 10,
    "residual_risk": 5,
    "detection_coverage_pct": 80,
    "mitigation_coverage_pct": 67
  }
}
```

---

## 🎯 Validación de Controles

### Proceso de Validación

1. **Red Agent** identifica vector de ataque
2. **Purple Agent** solicita validación
3. **Blue Agent** intenta detectar (sin saberlo)
4. **Purple Agent** compara resultados
5. Si no detectado → Gap identificado
6. Si detectado → Control validado

### Tipos de Validación

| Tipo | Descripción |
|------|-------------|
| IOC Blocking | Verificar que IOC está bloqueado |
| MFA Enforcement | Verificar que MFA está activo |
| Alert Generation | Verificar que alerta se genera |
| Containment Speed | Tiempo hasta contención |
| False Positive Rate | Tasa de falsos positivos |

---

## 🔧 Tuning Automático

### Reglas de Ajuste

```yaml
tuning_rules:
  - condition: "false_positive_rate > 0.10"
    action: "increase_threshold"
    adjustment: "+15%"
  
  - condition: "detection_rate < 0.80"
    action: "decrease_threshold"
    adjustment: "-10%"
  
  - condition: "ml_accuracy < 0.85"
    action: "retrain_model"
    data_window: "30d"
```

### ML Feedback Loop

1. Recolectar verdaderos positivos/negativos
2. Actualizar features del modelo
3. Reentrenar con nuevos datos
4. Validar precisión
5. Desplegar si mejora

---

## 📋 Reporting

### Reporte Purple Team Semanal

```markdown
## Purple Team Report - Week 49/2025

### Validations Summary
- Total validations: 45
- Successful: 38 (84%)
- Gaps found: 7 (16%)

### Detection Coverage
- Before: 72%
- After tuning: 85%
- Improvement: +13%

### Top Gaps Identified
1. Encoded PowerShell not detected (3 cases)
2. Lateral movement via WMI (2 cases)
3. Registry persistence (2 cases)

### Recommendations
1. Enable PowerShell ScriptBlock logging
2. Add WMI monitoring rules
3. Increase registry auditing
```

---

## 🔐 Seguridad

- Acceso a ambos contextos (Red/Blue)
- Aislamiento de datos sensibles
- Auditoría completa
- Rol requerido: `PURPLE_OPERATOR`
- Aprobación para simulaciones

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05  
**Autor**: MCP Forensics Team
