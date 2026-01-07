# 🏗️ Arquitectura: Casos vs Análisis Forenses

## 📋 Situación Actual

### Estructura Existente
```
Case (CASE-2025-XXXXX)
├── evidences: List[CaseEvidence]
├── notes: List[CaseNote]
└── metadata: legal_hold, chain_of_custody, etc.
```

Cuando ejecutas análisis M365:
- ✅ Se crea/vincula a un caso existente
- ✅ Los hallazgos se guardan
- ❓ Pero NO se tiene un registro del análisis mismo

---

## 🤔 Pregunta de Arquitectura

**¿Qué debería ocurrir cuando ejecutas un análisis forense?**

### Opción A: Crear entrada de análisis independiente (RECOMENDADO)

```
Case (CASE-2025-001)
│
├── ForensicAnalysis (FA-2025-001)
│   ├── status: "completed"
│   ├── tool: "sparrow"
│   ├── timestamp: 2025-12-07 10:30
│   ├── findings: [...hallazgos...]
│   ├── evidence_ids: [EVD-001, EVD-002]  ← referencia a evidencia
│   └── metadata: duration, version, etc.
│
├── ForensicAnalysis (FA-2025-002)
│   ├── status: "completed"
│   ├── tool: "hawk"
│   ├── timestamp: 2025-12-07 10:35
│   └── findings: [...]
│
└── CaseEvidence
    ├── EVD-001: sparrow_report.json
    ├── EVD-002: hawk_analysis.csv
    └── EVD-003: m365_extractor_logs.xlsx
```

**Ventajas:**
- ✅ Auditoría completa: qué herramientas se ejecutaron y cuándo
- ✅ Trazabilidad: comparar resultados de análisis múltiples
- ✅ Reproducibilidad: re-ejecutar análisis y comparar
- ✅ Correlación: ver relación entre hallazgos de herramientas
- ✅ Gestión: filtrar por tipo de análisis

### Opción B: Solo agregar hallazgos al caso

```
Case (CASE-2025-001)
├── findings: [
│   {
│       "tool": "sparrow",
│       "timestamp": "2025-12-07 10:30",
│       "finding": "Sign-in riesgoso detectado",
│       "user": "admin@empresa.com"
│   },
│   {
│       "tool": "hawk",
│       "timestamp": "2025-12-07 10:35",
│       "finding": "Regla de reenvío sospechosa",
│       "mailbox": "shared@empresa.com"
│   }
│ ]
└── evidence_count: 2
```

**Ventajas:**
- ✅ Más simple
- ✅ Menos overhead de BD

**Desventajas:**
- ❌ No hay registro del análisis (solo resultados)
- ❌ Imposible saber si el análisis falló parcialmente
- ❌ No se puede re-ejecutar y comparar
- ❌ Difícil auditar qué herramientas se usaron

---

## 🎯 RECOMENDACIÓN: Opción A

### Razones:

1. **Forensics es iterativo**: Ejecutas múltiples herramientas, algunas fallan, re-ejecutas...
2. **Auditoría**: Necesitas saber: ¿Cuándo? ¿Qué herramienta? ¿Qué versión? ¿Quién lo ejecutó?
3. **Correlación**: "Estos dos hallazgos vinieron del mismo análisis de Sparrow del 07/12"
4. **Re-ejecución**: "Ejecuta de nuevo Hawk para comparar resultados"
5. **Alertas**: "Este análisis se ejecutó 5 veces y siempre encontró lo mismo → crítico"

---

## 🛠️ Implementación Propuesta

### 1. Nuevo Modelo: `ForensicAnalysis`

```python
# api/models/forensic_analysis.py

class ForensicAnalysis(Base):
    """Registro de un análisis forense ejecutado"""
    __tablename__ = "forensic_analyses"
    
    id = Column(String(50), primary_key=True)  # FA-2025-00001
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    
    # Identificación
    tool_name = Column(String(100), nullable=False)  # sparrow, hawk, etc.
    analysis_type = Column(String(50), nullable=False)  # m365_forensic, endpoint, credential
    
    # Status
    status = Column(String(30), default="queued")  # queued/running/completed/failed
    progress = Column(Integer, default=0)  # 0-100%
    
    # Configuración
    config = Column(JSON, nullable=True)  # {'days_back': 90, 'scope': [...]}
    parameters = Column(JSON, nullable=True)  # {'target_users': [...]}
    
    # Resultados
    findings_count = Column(Integer, default=0)
    findings = Column(JSON, nullable=True)  # Array de hallazgos
    
    # Auditoría
    executed_by = Column(String(100), nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Evidencia
    evidence_files = Column(JSON, nullable=True)  # Referencias a archivos generados
    evidence_ids = Column(JSON, nullable=True)  # IDs de CaseEvidence creados
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2. Flujo de Ejecución

```python
# Cuando el usuario presiona "Iniciar análisis"

1. Crear ForensicAnalysis
   analysis = ForensicAnalysis(
       case_id="CASE-2025-001",
       tool_name="sparrow",
       status="queued"
   )
   
2. Ejecutar en background
   status = "running"
   progress = 0%
   
3. Cada herramienta genera archivos
   - sparrow_results.json
   - sparrow_alerts.csv
   
4. Guardar como CaseEvidence
   evidence = CaseEvidence(
       case_id="CASE-2025-001",
       name="sparrow_results.json",
       file_path="/var/evidence/CASE-2025-001/sparrow_results.json"
   )
   analysis.evidence_ids.append(evidence.id)
   
5. Procesar hallazgos
   findings = parse_sparrow_output(results)
   analysis.findings = findings
   analysis.findings_count = len(findings)
   analysis.status = "completed"
```

### 3. API Endpoints

```python
# Obtener análisis de un caso
GET /forensics/case/{case_id}/analyses
→ Lista todos los análisis ejecutados para este caso

# Obtener detalles de un análisis
GET /forensics/analyses/{analysis_id}
→ Hallazgos, configuración, duración, etc.

# Re-ejecutar un análisis
POST /forensics/analyses/{analysis_id}/retry
→ Crea nuevo ForensicAnalysis con misma configuración

# Comparar dos análisis
GET /forensics/analyses/{analysis_id_1}/compare/{analysis_id_2}
→ Muestra diferencias entre hallazgos
```

---

## 📊 Dashboard Impact

### Antes
```
Caso IR-2025-001
├── Hallazgos: 45
├── Evidencia: 12 archivos
└── ??? (¿Cuándo se ejecutó? ¿Qué versión de Sparrow?)
```

### Después
```
Caso IR-2025-001
├── Análisis Ejecutados: 4
│   ├── Sparrow (2025-12-07 10:30) ✓ 15 hallazgos
│   ├── Hawk (2025-12-07 10:35) ✓ 8 hallazgos
│   ├── Monkey365 (2025-12-07 10:40) ✓ 12 hallazgos
│   └── Graph (2025-12-07 10:45) ✗ Error: timeout
├── Evidencia: 12 archivos
│   ├── sparrow_results.json (FA-001)
│   ├── hawk_analysis.csv (FA-002)
│   └── monkey365_report.html (FA-003)
└── Hallazgos Totales: 35 ✓ + 1 ✗ falló
```

---

## ✅ Recomendación Final

**Implementar Opción A con ForensicAnalysis:**

1. ✅ Mantiene trazabilidad completa
2. ✅ Permite auditoria forense
3. ✅ Soporta análisis iterativos
4. ✅ Facilita comparación y correlación
5. ✅ Prepara para SLA y reportes

**Próximo paso**: Implementar modelo `ForensicAnalysis` y actualizar endpoints de m365.py para vincular análisis a casos

---

**¿Estás de acuerdo con esta arquitectura? Si es así, implemento el modelo y los endpoints.**
