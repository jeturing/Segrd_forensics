# Integración Backend: ForensicAnalysis + Consola Automatizada

## Resumen de Cambios Necesarios

El frontend ahora espera que el backend:

1. ✅ Genere IDs únicos `FA-YYYY-XXXXX` para cada análisis
2. ✅ Retorne logs progresivos para la consola
3. ✅ Solicite decisiones interactivas cuando sea necesario
4. ✅ Registre opciones de extracción y decisiones del usuario
5. ✅ Almacene todo en modelo `ForensicAnalysis`

## 1. Modelo ForensicAnalysis (Requerido)

### Ubicación
`api/models/forensic_analysis.py` (CREAR)

### Estructura SQL

```sql
CREATE TABLE forensic_analysis (
    id VARCHAR(20) PRIMARY KEY,                    -- FA-2025-00001
    case_id VARCHAR(50) NOT NULL,                 -- IR-2024-001
    tool_name VARCHAR(100) NOT NULL,              -- sparrow, hawk, o365_extractor
    category VARCHAR(50) NOT NULL,                -- BÁSICO, RECONOCIMIENTO, etc
    status VARCHAR(20) NOT NULL,                  -- queued, running, waiting_decision, completed, failed, partial
    findings JSONB,                               -- Array de hallazgos
    executed_by VARCHAR(255),                     -- Usuario que ejecutó
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    evidence_ids JSONB,                           -- Array de CaseEvidence IDs
    user_decisions JSONB,                         -- [{"question": "...", "answer": true, "timestamp": "..."}]
    extraction_options JSONB,                     -- {"includeInactive": true, ...}
    error_message TEXT,
    FOREIGN KEY (case_id) REFERENCES cases(id)
);
```

### Clase SQLAlchemy

```python
# api/models/forensic_analysis.py

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
import uuid

class ForensicAnalysis(Base):
    __tablename__ = 'forensic_analyses'
    
    id = Column(String(20), primary_key=True)                    # FA-2025-00001
    case_id = Column(String(50), ForeignKey('cases.id'), nullable=False)
    tool_name = Column(String(100), nullable=False)             # sparrow, hawk, etc
    category = Column(String(50), nullable=False)               # BÁSICO, RECONOCIMIENTO
    status = Column(String(20), default='queued')               # queued, running, completed, failed
    
    findings = Column(JSON, default=list)                       # Array de hallazgos
    executed_by = Column(String(255))                           # Usuario
    executed_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    evidence_ids = Column(JSON, default=list)                   # Array de IDs
    user_decisions = Column(JSON, default=list)                 # [{"question": "...", "answer": true}]
    extraction_options = Column(JSON, default=dict)             # {"includeInactive": true}
    
    error_message = Column(Text, nullable=True)
    
    # Relaciones
    case = relationship('Case', back_populates='analyses')
    
    @staticmethod
    def generate_id():
        """Genera IDs como FA-2025-00001, FA-2025-00002, etc."""
        from datetime import datetime
        year = datetime.utcnow().year % 100  # 25 para 2025
        # En producción, usar counter BD en lugar de uuid
        import random
        counter = random.randint(1, 99999)
        return f"FA-{2000 + year}-{counter:05d}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'tool_name': self.tool_name,
            'category': self.category,
            'status': self.status,
            'findings': self.findings,
            'executed_by': self.executed_by,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'evidence_ids': self.evidence_ids,
            'user_decisions': self.user_decisions,
            'extraction_options': self.extraction_options,
            'error_message': self.error_message
        }
```

## 2. Endpoint: POST /forensics/m365/analyze

### Request Esperado

```json
{
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "case_id": "IR-2024-001",
  "scope": ["sparrow", "hawk", "azurehound"],
  "target_users": ["user@empresa.com", "user2@empresa.com"],
  "extraction_options": {
    "includeInactive": true,
    "includeExternal": false,
    "includeArchived": true,
    "includeDeleted": false
  },
  "days_back": 90,
  "priority": "high"
}
```

### Response Inmediata

```json
{
  "status": "queued",
  "analysis_id": "FA-2025-00001",
  "case_id": "IR-2024-001",
  "task_id": "task-abc-123-def",
  "message": "Análisis iniciado exitosamente"
}
```

### Implementación

```python
# api/routes/m365.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import logging
from datetime import datetime

router = APIRouter(prefix="/forensics", tags=["M365 Forensics"])

class AnalyzeRequest(BaseModel):
    tenant_id: str
    case_id: str
    scope: List[str]
    target_users: Optional[List[str]] = []
    extraction_options: Optional[Dict] = None
    days_back: Optional[int] = 90
    priority: Optional[str] = "medium"

@router.post("/m365/analyze")
async def analyze_m365(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Inicia análisis forense M365 y retorna análisis_id."""
    
    try:
        # 1. Validar caso existe
        case = await db.get_case(request.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Caso no encontrado")
        
        # 2. Generar análisis ID
        analysis_id = ForensicAnalysis.generate_id()
        
        # 3. Crear registro ForensicAnalysis
        analysis = ForensicAnalysis(
            id=analysis_id,
            case_id=request.case_id,
            tool_name=','.join(request.scope),  # Para referencia rápida
            category='MIXED',  # Múltiples categorías
            status='queued',
            executed_by=get_current_user(),  # Del JWT
            extraction_options=request.extraction_options or {},
            findings=[]
        )
        await db.add(analysis)
        await db.commit()
        
        # 4. Agregar tarea en background
        background_tasks.add_task(
            execute_m365_analysis_with_logging,
            analysis_id=analysis_id,
            case_id=request.case_id,
            scope=request.scope,
            target_users=request.target_users,
            extraction_options=request.extraction_options,
            tenant_id=request.tenant_id,
            days_back=request.days_back
        )
        
        return {
            "status": "queued",
            "analysis_id": analysis_id,
            "case_id": request.case_id,
            "task_id": f"task-{analysis_id}",
            "message": f"Análisis {analysis_id} iniciado"
        }
    
    except Exception as e:
        logger.error(f"Error iniciando análisis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

## 3. Función de Ejecución: execute_m365_analysis_with_logging

### Ubicación
`api/services/m365.py`

### Implementación

```python
# api/services/m365.py

import asyncio
from datetime import datetime
from .logging_queue import LoggingQueue

async def execute_m365_analysis_with_logging(
    analysis_id: str,
    case_id: str,
    scope: List[str],
    target_users: List[str],
    extraction_options: Dict,
    tenant_id: str,
    days_back: int
):
    """
    Ejecuta análisis forense con logs streaming y decisiones interactivas.
    """
    
    start_time = datetime.utcnow()
    analysis = await db.get_forensic_analysis(analysis_id)
    
    try:
        # Actualizar estado
        analysis.status = 'running'
        analysis.executed_at = datetime.utcnow()
        await db.update(analysis)
        
        # Iniciar cola de logs
        log_queue = LoggingQueue()
        await log_queue.add({
            'type': 'info',
            'message': f'Iniciando análisis forense para caso {case_id}...'
        })
        await log_queue.add({
            'type': 'info',
            'message': f'Herramientas: {len(scope)} seleccionadas'
        })
        
        if target_users:
            await log_queue.add({
                'type': 'info',
                'message': f'Usuarios objetivo: {len(target_users)}'
            })
        
        # Mostrar opciones de extracción habilitadas
        enabled_options = []
        if extraction_options.get('includeInactive'):
            enabled_options.append('Usuarios inactivos')
        if extraction_options.get('includeExternal'):
            enabled_options.append('Usuarios externos')
        if extraction_options.get('includeArchived'):
            enabled_options.append('Buzones archivados')
        if extraction_options.get('includeDeleted'):
            enabled_options.append('Objetos eliminados')
        
        if enabled_options:
            await log_queue.add({
                'type': 'info',
                'message': f'Opciones activas: {", ".join(enabled_options)}'
            })
        
        # Ejecutar cada tool
        findings = {}
        evidence_ids = []
        user_decisions = []
        
        for tool in scope:
            await log_queue.add({
                'type': 'info',
                'message': f'Ejecutando: {tool}...'
            })
            
            try:
                # 1. Verificar si se necesita decisión
                if tool == 'o365_extractor' and not extraction_options.get('includeArchived'):
                    # ESPERAR DECISIÓN DEL USUARIO
                    decision = await wait_for_user_decision(
                        analysis_id=analysis_id,
                        question="¿Incluir buzones archivados en extracción?",
                        tool=tool,
                        timeout=300  # 5 minutos
                    )
                    
                    user_decisions.append({
                        'question': '¿Incluir buzones archivados?',
                        'answer': decision,
                        'timestamp': datetime.utcnow().isoformat(),
                        'tool': tool
                    })
                    
                    if decision:
                        extraction_options['includeArchived'] = True
                        await log_queue.add({
                            'type': 'success',
                            'message': f'Usuario respondió: ✅ SÍ - Incluirá buzones archivados'
                        })
                    else:
                        await log_queue.add({
                            'type': 'success',
                            'message': f'Usuario respondió: ❌ NO - Extracción rápida'
                        })
                
                # 2. Ejecutar tool
                tool_result = await run_forensic_tool(
                    tool_name=tool,
                    case_id=case_id,
                    tenant_id=tenant_id,
                    target_users=target_users,
                    extraction_options=extraction_options,
                    days_back=days_back
                )
                
                # 3. Log de éxito
                findings[tool] = tool_result.get('findings', [])
                await log_queue.add({
                    'type': 'success',
                    'message': f'✅ {tool} completado - {len(findings[tool])} hallazgos'
                })
                
                # 4. Registrar evidencia generada
                if tool_result.get('evidence_files'):
                    for evidence in tool_result['evidence_files']:
                        evidence_id = await create_case_evidence(
                            case_id=case_id,
                            tool_name=tool,
                            file_path=evidence['path'],
                            description=evidence.get('description', ''),
                            mime_type=evidence.get('mime_type', 'application/json')
                        )
                        evidence_ids.append(evidence_id)
            
            except Exception as e:
                await log_queue.add({
                    'type': 'error',
                    'message': f'❌ {tool} falló: {str(e)[:100]}'
                })
                # Continuar con siguiente tool en lugar de fallar todo
                findings[tool] = []
        
        # Actualizar análisis completado
        analysis.status = 'completed'
        analysis.completed_at = datetime.utcnow()
        analysis.duration_seconds = int(
            (analysis.completed_at - analysis.executed_at).total_seconds()
        )
        analysis.findings = findings
        analysis.evidence_ids = evidence_ids
        analysis.user_decisions = user_decisions
        
        await db.update(analysis)
        
        await log_queue.add({
            'type': 'success',
            'message': f'✅ Análisis completado en {analysis.duration_seconds} segundos'
        })
        await log_queue.add({
            'type': 'info',
            'message': f'Total de evidencia: {len(evidence_ids)} archivos'
        })
    
    except Exception as e:
        logger.error(f"Error en análisis {analysis_id}: {e}", exc_info=True)
        
        analysis.status = 'failed'
        analysis.error_message = str(e)
        analysis.completed_at = datetime.utcnow()
        analysis.duration_seconds = int(
            (analysis.completed_at - analysis.executed_at).total_seconds()
        )
        
        await db.update(analysis)
        
        await log_queue.add({
            'type': 'error',
            'message': f'❌ Análisis falló: {str(e)[:200]}'
        })
```

## 4. Endpoint: GET /forensics/m365/status/{analysis_id}

Para que frontend pueda pooling del progreso:

```python
@router.get("/m365/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """Retorna estado actual del análisis con logs nuevos."""
    
    analysis = await db.get_forensic_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    # Obtener logs nuevos desde último request del cliente
    logs = await get_logs_since(
        analysis_id=analysis_id,
        since_timestamp=request.query_params.get('since')
    )
    
    # Si hay decisión pendiente
    pending_decision = None
    if analysis.status == 'waiting_for_decision':
        pending_decision = await get_pending_decision(analysis_id)
    
    return {
        "status": analysis.status,
        "analysis_id": analysis.id,
        "case_id": analysis.case_id,
        "current_tool": analysis.current_tool,
        "progress_percentage": calculate_progress(analysis),
        "logs": logs,
        "pending_decision": pending_decision,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "duration_seconds": analysis.duration_seconds,
        "findings_count": len(analysis.findings) if analysis.findings else 0,
        "evidence_count": len(analysis.evidence_ids) if analysis.evidence_ids else 0
    }
```

## 5. Endpoint: POST /forensics/m365/decision/{analysis_id}

Para que el usuario pueda responder decisiones interactivas:

```python
class DecisionRequest(BaseModel):
    answer: bool
    decision_id: str

@router.post("/m365/decision/{analysis_id}")
async def submit_decision(analysis_id: str, decision: DecisionRequest):
    """Registra la decisión del usuario y continúa análisis."""
    
    analysis = await db.get_forensic_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    
    if analysis.status != 'waiting_for_decision':
        raise HTTPException(status_code=400, detail="Análisis no está esperando decisión")
    
    # Guardar decisión
    analysis.user_decisions.append({
        'decision_id': decision.decision_id,
        'answer': decision.answer,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Actualizar options basado en respuesta
    if decision.answer:
        analysis.extraction_options['includeArchived'] = True
    
    # Cambiar estado a running nuevamente
    analysis.status = 'running'
    await db.update(analysis)
    
    # Continuar análisis desde donde se pausó
    background_tasks.add_task(
        resume_analysis,
        analysis_id=analysis_id
    )
    
    return {
        "status": "resumed",
        "message": "Análisis reanudado"
    }
```

## 6. Cola de Logs (Streaming)

### Ubicación
`api/services/logging_queue.py` (CREAR)

```python
import asyncio
from typing import Dict, List
from datetime import datetime
from collections import defaultdict

class LoggingQueue:
    """Cola de logs para streaming a frontend vía WebSocket o polling."""
    
    _queues: Dict[str, List] = defaultdict(list)
    
    def __init__(self, analysis_id: str = None):
        self.analysis_id = analysis_id
    
    async def add(self, log_entry: Dict):
        """Agrega log a la cola."""
        log_entry['timestamp'] = datetime.utcnow().isoformat()
        self._queues[self.analysis_id].append(log_entry)
        logger.info(f"[{self.analysis_id}] {log_entry['type']}: {log_entry['message']}")
    
    async def get_since(self, since_timestamp: str = None) -> List:
        """Obtiene logs desde timestamp específico."""
        if not since_timestamp:
            return self._queues[self.analysis_id]
        
        return [
            log for log in self._queues[self.analysis_id]
            if log['timestamp'] >= since_timestamp
        ]
    
    @staticmethod
    async def clear(analysis_id: str):
        """Limpia logs de un análisis."""
        LoggingQueue._queues[analysis_id] = []
```

## 7. Actualizar Modelo Case

Agregar relación a ForensicAnalysis:

```python
# api/models/case.py

class Case(Base):
    # ... campos existentes ...
    
    # Nueva relación
    analyses = relationship('ForensicAnalysis', back_populates='case', cascade='all, delete-orphan')
```

## 8. Rutas de Actualización

Agregar a `api/routes/__init__.py`:

```python
from .m365 import router as m365_router

# En app.include_router():
app.include_router(m365_router)
```

## 9. Migración BD

Crear migración:

```sql
-- migrations/0005_forensic_analysis.sql

CREATE TABLE IF NOT EXISTS forensic_analyses (
    id VARCHAR(20) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    findings JSONB DEFAULT '[]',
    executed_by VARCHAR(255),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    evidence_ids JSONB DEFAULT '[]',
    user_decisions JSONB DEFAULT '[]',
    extraction_options JSONB DEFAULT '{}',
    error_message TEXT,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    INDEX idx_case_id (case_id),
    INDEX idx_status (status),
    INDEX idx_executed_at (executed_at)
);
```

## 10. Variables de Entorno

Agregar a `.env`:

```bash
# Análisis
FORENSICS_LOG_QUEUE_MAX_SIZE=1000
FORENSICS_DECISION_TIMEOUT=300
FORENSICS_ANALYSIS_TIMEOUT=3600
FORENSICS_ENABLE_STREAMING_LOGS=true
```

## Testing

### Test 1: Crear análisis

```bash
curl -X POST http://localhost:8080/forensics/m365/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "xxx",
    "case_id": "IR-2024-001",
    "scope": ["sparrow", "hawk"],
    "extraction_options": {
      "includeInactive": true,
      "includeArchived": false
    }
  }'

# Esperado: 
# {
#   "status": "queued",
#   "analysis_id": "FA-2025-00001"
# }
```

### Test 2: Pooling de progreso

```bash
curl http://localhost:8080/forensics/m365/status/FA-2025-00001

# Esperado:
# {
#   "status": "running",
#   "logs": [
#     {"type": "info", "message": "Iniciando..."},
#     {"type": "success", "message": "✅ Sparrow completado"}
#   ]
# }
```

### Test 3: Responder decisión

```bash
curl -X POST http://localhost:8080/forensics/m365/decision/FA-2025-00001 \
  -H "Content-Type: application/json" \
  -d '{
    "answer": true,
    "decision_id": "decision-123"
  }'
```

---

**Próximas Fases**:
1. Implementar WebSocket para logs en tiempo real (vs polling)
2. Agregar compresión de logs antiguos
3. Implementar replay de análisis desde snapshots
4. Integrar con threat intelligence para auto-flagging
