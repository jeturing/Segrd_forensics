# Integración LLM Studio + Dynamic Model Manager v4.3

**Estado**: ✅ Completa  
**Fecha**: 7 de diciembre de 2024  
**Versión**: v4.3  
**Tipo**: Backend + Frontend Integration

---

## 📚 Resumen Ejecutivo

Esta implementación integra **LLM Studio (Jeturing AI Platform)** con el sistema MCP Kali Forensics, proporcionando capacidades de inteligencia artificial para análisis forense automatizado mediante un sistema de **proveedores múltiples con fallback automático**.

### Arquitectura de 3 Niveles

```
┌─────────────────────────────────────────────────────────────┐
│                   LLM Provider Manager                      │
│                      (Singleton)                            │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼──────┐
│  LLM Studio    │  │  Phi-4 Local   │  │   Offline   │
│   (Primary)    │  │   (Fallback)   │  │ (Emergency) │
│                │  │                │  │             │
│ OpenAI-compat  │  │ Pattern-based  │  │ Rules-based │
│ Phi-4 Model    │  │ Local compute  │  │ No AI req.  │
│ 100.101.115.5  │  │ CPU/RAM only   │  │ Always avail│
│                │  │                │  │             │
│ Timeout: 40s   │  │ Fast response  │  │ Instant     │
└────────────────┘  └────────────────┘  └─────────────┘
```

### Capacidades Implementadas

- ✅ **Multi-Provider Manager**: Gestión de 3 proveedores LLM con cambio dinámico
- ✅ **Automatic Fallback**: Si LLM Studio no responde → Phi-4 Local → Offline
- ✅ **Health Monitoring**: Verificación continua de salud de proveedores
- ✅ **Statistics Tracking**: Métricas de uso, errores y latencia por proveedor
- ✅ **API REST Completa**: 8 endpoints para configuración y gestión
- ✅ **SOAR Intelligence Integration**: Integrado con motor de análisis forense
- ✅ **React Management Panel**: Panel de configuración en frontend
- ✅ **Authentication**: API protegida con API Key validation

---

## 🏗️ Arquitectura Técnica

### Backend Components

#### 1. LLM Provider Manager (`api/services/llm_provider.py`)

**Clase Principal: `LLMProviderManager`**

```python
class LLMProviderManager:
    """
    Orquestador central de proveedores LLM con fallback automático
    """
    def __init__(self):
        self.active_provider = "llm_studio"  # Default
        self.providers = {
            "llm_studio": {...},  # OpenAI-compatible API
            "phi4_local": Phi4Local(),  # Pattern-based local
            "offline": OfflineLLM()  # Rules-based engine
        }
        self.statistics = {...}  # Per-provider stats
    
    async def generate(self, prompt: str, context: Dict) -> Dict:
        """
        Main entry point con fallback automático:
        1. Intenta con provider activo
        2. Si falla (timeout/error), intenta siguiente en cadena
        3. Retorna respuesta con metadata (provider usado, latencia)
        """
```

**Proveedores Implementados:**

1. **LLM Studio (Primary)**
   - URL: `http://100.101.115.5:2714/v1/completions`
   - Formato: OpenAI-compatible
   - Modelo: Phi-4
   - Timeout: 40 segundos
   - Autenticación: Bearer token (opcional)

2. **Phi4Local (Fallback)**
   - Ejecución: Local (CPU/RAM)
   - Método: Pattern matching para clasificación de severidad
   - Respuesta: < 1 segundo
   - Patrones: "critical", "high", "medium", "low" keywords

3. **OfflineLLM (Emergency)**
   - Sin AI: Rules-based engine
   - Evaluación: Conteo de hallazgos críticos
   - Siempre disponible
   - Respuesta instantánea

#### 2. API Router (`api/routes/llm_settings.py`)

**Endpoints Implementados:**

| Endpoint | Método | Descripción | Auth |
|----------|--------|-------------|------|
| `/api/v41/llm/status` | GET | Estado completo del sistema LLM | ✓ |
| `/api/v41/llm/provider` | POST | Cambiar proveedor activo | ✓ |
| `/api/v41/llm/test` | POST | Test con prompt personalizado | ✓ |
| `/api/v41/llm/health` | GET | Health check de todos los proveedores | ✓ |
| `/api/v41/llm/statistics` | GET | Métricas de uso por proveedor | ✓ |
| `/api/v41/llm/analyze` | POST | Análisis SOAR con LLM | ✓ |
| `/api/v41/llm/models` | GET | Lista de modelos disponibles | ✓ |
| `/api/v41/llm/reset-stats` | POST | Reiniciar estadísticas | ✓ |

**Ejemplo Request:**

```bash
curl -X POST http://localhost:8080/api/v41/llm/test \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analiza estos hallazgos forenses y clasifica severidad",
    "context": {
      "findings": ["Lateral movement detected", "Malicious PowerShell"],
      "timestamp": "2024-12-07T13:00:00Z"
    }
  }'
```

**Ejemplo Response:**

```json
{
  "response": {
    "provider": "llm_studio",
    "output": "Análisis: Severidad CRÍTICA. Movimiento lateral indica...",
    "latency": 2.35,
    "model": "phi-4"
  }
}
```

#### 3. SOAR Intelligence Integration (`api/services/soar_intelligence.py`)

**Actualización v4.3:**

```python
# ANTES (v1.0):
from api.services.llm_local import generate_local

# AHORA (v4.3):
from api.services.llm_provider import llm_manager

# Uso en análisis:
result = await llm_manager.generate(
    prompt=f"Analiza estos hallazgos: {findings}",
    context={"case_id": case_id, "severity": "high"}
)
```

**Capacidades SOAR + LLM:**

- 🔍 **Severity Classification**: Clasifica hallazgos automáticamente
- 📋 **Action Recommendation**: Sugiere acciones de respuesta
- 🎯 **IOC Extraction**: Extrae indicadores de compromiso
- 🧠 **Threat Intelligence**: Enriquecimiento contextual
- 📊 **Correlation Analysis**: Correlaciona eventos relacionados

---

### Frontend Components

#### 1. React Panel (`frontend-react/src/components/Settings/LLMSettings.jsx`)

**Características:**

- **Estado del Sistema**: Display de proveedor activo y salud global
- **Cambio de Proveedor**: Botones para switch manual entre proveedores
- **Estadísticas de Uso**: Requests, errores, latencia por proveedor
- **Test de Modelo**: Interfaz para probar prompts personalizados
- **Health Monitoring**: Estado de cada proveedor en tiempo real
- **Configuración**: Visualización de parámetros de cada modelo

**Screenshot:**

```
┌─────────────────────────────────────────────────────┐
│ 🧠 Configuración de IA (LLM)                       │
│ Gestión de modelos, proveedores y configuración    │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 📊 Estado del Sistema                              │
│ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ Proveedor   │ │ Estado Global│ │ Total Reqs   │ │
│ │ ☁️ LLM     │ │ 🟢 Saludable │ │ 1,234        │ │
│ │   Studio    │ │              │ │              │ │
│ └─────────────┘ └──────────────┘ └──────────────┘ │
│                                                     │
│ 🔄 Proveedores LLM                                 │
│ ┌──────────────────────────────────────────────┐  │
│ │ ☁️ LLM Studio                      [ACTIVO]  │  │
│ │ Jeturing AI Platform - Phi-4                 │  │
│ │ http://100.101.115.5:2714        ✓ Disponible│  │
│ └──────────────────────────────────────────────┘  │
│ ┌──────────────────────────────────────────────┐  │
│ │ 💻 Phi-4 Local                               │  │
│ │ Pattern-based local model (fallback)         │  │
│ │                                  ✓ Disponible│  │
│ └──────────────────────────────────────────────┘  │
│ ┌──────────────────────────────────────────────┐  │
│ │ 📋 Offline Engine                            │  │
│ │ Rules-based engine (no AI required)          │  │
│ │                                  ✓ Disponible│  │
│ └──────────────────────────────────────────────┘  │
│                                                     │
│ 💡 Fallback automático: Si LLM Studio no responde, │
│    el sistema cambiará automáticamente a Phi-4     │
│                                                     │
│ 🧪 Test de Modelo LLM                              │
│ ┌──────────────────────────────────────────────┐  │
│ │ Prompt: ________________________________     │  │
│ │         ________________________________     │  │
│ │         ________________________________     │  │
│ │ [🚀 Ejecutar Test]                           │  │
│ └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Acceso:**
- URL: `/settings/llm`
- Menú: Settings → LLM Configuration
- Permisos: Requiere autenticación de usuario

---

## 🔧 Configuración

### Variables de Entorno (`.env.local`)

```bash
# ============================================
# LLM STUDIO INTEGRATION (v4.3)
# ============================================

# Proveedor activo: llm_studio, phi4_local, offline
LLM_PROVIDER=llm_studio

# LLM Studio (Jeturing AI Platform)
LLM_STUDIO_URL=http://100.101.115.5:2714/v1/completions
LLM_STUDIO_API_KEY=
LLM_STUDIO_MODEL=phi-4
LLM_STUDIO_TIMEOUT=40

# Phi-4 Local (Fallback)
PHI4_LOCAL_ENABLED=true

# Offline Mode (Emergency fallback)
OFFLINE_LLM_ENABLED=true
```

### Backend Settings (`api/config.py`)

```python
class Settings(BaseSettings):
    # ...existing settings...
    
    # ============================================================================
    # LLM STUDIO INTEGRATION (v4.3)
    # ============================================================================
    LLM_PROVIDER: str = "llm_studio"
    LLM_STUDIO_URL: str = "http://100.101.115.5:2714/v1/completions"
    LLM_STUDIO_API_KEY: Optional[str] = None
    LLM_STUDIO_MODEL: str = "phi-4"
    LLM_STUDIO_TIMEOUT: int = 40
    PHI4_LOCAL_ENABLED: bool = True
    OFFLINE_LLM_ENABLED: bool = True
```

---

## 🚀 Uso y Ejemplos

### 1. Verificar Estado del Sistema

```bash
curl -X GET http://localhost:8080/api/v41/llm/status \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "active_provider": "llm_studio",
  "available_providers": [
    {
      "name": "llm_studio",
      "description": "LLM Studio - Jeturing AI Platform (Phi-4)",
      "status": "available",
      "url": "http://100.101.115.5:2714/v1/completions"
    },
    {
      "name": "phi4_local",
      "description": "Phi-4 Local - Pattern-based analysis",
      "status": "available"
    },
    {
      "name": "offline",
      "description": "Offline - Rules-based engine",
      "status": "available"
    }
  ],
  "configuration": {
    "llm_studio": {
      "model": "phi-4",
      "timeout": 40,
      "url": "http://100.101.115.5:2714/v1/completions"
    }
  }
}
```

### 2. Cambiar Proveedor Activo

```bash
curl -X POST http://localhost:8080/api/v41/llm/provider \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "phi4_local",
    "reason": "LLM Studio no disponible temporalmente"
  }'
```

### 3. Test de Modelo con Prompt Personalizado

```bash
curl -X POST http://localhost:8080/api/v41/llm/test \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analiza estos eventos de seguridad y determina la severidad:\n- Múltiples intentos de login fallidos\n- PowerShell execution con flags ofuscados\n- Conexión a IP conocida como C2",
    "context": {
      "case_id": "IR-2025-001",
      "timestamp": "2024-12-07T13:00:00Z"
    }
  }'
```

**Response:**

```json
{
  "response": {
    "provider": "llm_studio",
    "output": "ANÁLISIS DE SEVERIDAD: CRÍTICA\n\nHallazgos:\n1. Login fallidos múltiples → Posible ataque de fuerza bruta\n2. PowerShell ofuscado → Alta probabilidad de malware\n3. Conexión a C2 conocido → Confirmación de compromiso\n\nRECOMENDACIONES:\n- Aislar sistema inmediatamente\n- Capturar memoria y disco para análisis forense\n- Revisar lateral movement en red\n- Verificar persistencia en sistema",
    "latency": 3.45,
    "model": "phi-4",
    "timestamp": "2024-12-07T13:05:23Z"
  }
}
```

### 4. Análisis SOAR con LLM

```bash
curl -X POST http://localhost:8080/api/v41/llm/analyze \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "IR-2025-001",
    "evidence": {
      "type": "endpoint_scan",
      "findings": [
        "Suspicious process: cmd.exe spawned from word.exe",
        "Network connection to 192.168.1.50:4444",
        "Registry persistence: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
      ]
    }
  }'
```

**Response:**

```json
{
  "analysis": {
    "severity": "CRITICAL",
    "confidence": 0.95,
    "iocs": [
      {
        "type": "process",
        "value": "cmd.exe",
        "context": "Spawned from word.exe (suspicious)"
      },
      {
        "type": "ip",
        "value": "192.168.1.50:4444",
        "context": "Potential C2 communication"
      },
      {
        "type": "registry",
        "value": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        "context": "Persistence mechanism"
      }
    ],
    "recommended_actions": [
      "Isolate affected endpoint immediately",
      "Block network communication to 192.168.1.50",
      "Capture memory dump for analysis",
      "Check for lateral movement",
      "Review email attachments for initial compromise vector"
    ],
    "provider_used": "llm_studio",
    "processing_time": 2.89
  }
}
```

### 5. Health Check

```bash
curl -X GET http://localhost:8080/api/v41/llm/health \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "health": {
    "overall": "healthy",
    "providers": {
      "llm_studio": {
        "status": "healthy",
        "response_time": 1.23
      },
      "phi4_local": {
        "status": "healthy",
        "response_time": 0.05
      },
      "offline": {
        "status": "healthy",
        "response_time": 0.001
      }
    },
    "timestamp": "2024-12-07T13:10:00Z"
  }
}
```

### 6. Estadísticas de Uso

```bash
curl -X GET http://localhost:8080/api/v41/llm/statistics \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "llm_statistics": {
    "llm_studio": {
      "requests": 1234,
      "errors": 3,
      "avg_latency": 2.45
    },
    "phi4_local": {
      "requests": 45,
      "errors": 0,
      "avg_latency": 0.12
    },
    "offline": {
      "requests": 2,
      "errors": 0,
      "avg_latency": 0.001
    }
  },
  "timestamp": "2024-12-07T13:15:00Z"
}
```

---

## 📊 Flujo de Fallback Automático

```
┌─────────────────────────────────────────────────────┐
│  Usuario/Sistema solicita análisis LLM             │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  LLMProviderManager.generate()                     │
│  Provider activo: llm_studio                       │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
       ┌────────────────────────────┐
       │  Intenta con LLM Studio    │
       └────────────┬───────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ✅ Success            ❌ Timeout/Error
         │                     │
         │                     ▼
         │         ┌────────────────────────┐
         │         │ Intenta Phi-4 Local    │
         │         └──────────┬─────────────┘
         │                    │
         │         ┌──────────┴──────────┐
         │         │                     │
         │    ✅ Success            ❌ Error
         │         │                     │
         │         │                     ▼
         │         │         ┌────────────────────┐
         │         │         │ Intenta Offline    │
         │         │         └──────────┬─────────┘
         │         │                    │
         │         │                ✅ Always works
         │         │                    │
         └─────────┴────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Retorna respuesta con metadata:                   │
│  - provider_used: "llm_studio" | "phi4_local" ...  │
│  - latency: 2.45                                   │
│  - output: "Análisis completo..."                  │
└─────────────────────────────────────────────────────┘
```

**Logging durante Fallback:**

```
[INFO] 🧠 LLMProviderManager: Attempting generation with llm_studio
[ERROR] ❌ llm_studio failed: Timeout after 40s
[INFO] 🔄 Falling back to phi4_local
[INFO] ✅ phi4_local succeeded in 0.12s
```

---

## 🔒 Seguridad

### Autenticación API

Todos los endpoints LLM requieren API Key validation:

```python
@router.get("/status")
async def get_status(api_key: str = Depends(verify_api_key)):
    # Endpoint protegido
```

### Variables Sensibles

- **LLM_STUDIO_API_KEY**: Nunca hardcodeada, siempre desde variables de entorno
- **API_KEY**: Requerida en headers para acceso a endpoints
- **Bearer tokens**: Manejados por llm_provider con logging sanitizado

### Rate Limiting

**Implementado a nivel de provider:**

```python
# En llm_provider.py
if time.time() - self.statistics["llm_studio"]["last_request"] < 1.0:
    await asyncio.sleep(1.0)  # Throttle requests
```

---

## 🧪 Testing

### Test Manual con curl

```bash
# 1. Verificar salud
curl -X GET http://localhost:8080/api/v41/llm/health \
  -H "X-API-Key: your-key"

# 2. Test de modelo
curl -X POST http://localhost:8080/api/v41/llm/test \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test prompt", "context": {}}'

# 3. Cambiar a fallback
curl -X POST http://localhost:8080/api/v41/llm/provider \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"provider": "phi4_local", "reason": "Testing fallback"}'
```

### Test Automático (Python)

```python
import requests

API_URL = "http://localhost:8080/api/v41/llm"
API_KEY = "your-api-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Test 1: Status check
response = requests.get(f"{API_URL}/status", headers=HEADERS)
assert response.status_code == 200
status = response.json()
assert status["active_provider"] in ["llm_studio", "phi4_local", "offline"]

# Test 2: Generate with prompt
test_prompt = {
    "prompt": "Classify severity: malicious PowerShell detected",
    "context": {"case_id": "TEST-001"}
}
response = requests.post(f"{API_URL}/test", headers=HEADERS, json=test_prompt)
assert response.status_code == 200
result = response.json()
assert "response" in result
assert "provider" in result["response"]
assert "output" in result["response"]

# Test 3: Fallback behavior
# Simular timeout cambiando a offline
requests.post(
    f"{API_URL}/provider",
    headers=HEADERS,
    json={"provider": "offline", "reason": "Test fallback"}
)
response = requests.post(f"{API_URL}/test", headers=HEADERS, json=test_prompt)
result = response.json()
assert result["response"]["provider"] == "offline"

print("✅ All tests passed")
```

---

## 📈 Monitoring y Observabilidad

### Logs Estructurados

```python
# Formato de logs
[2024-12-07 13:00:00] [INFO] 🧠 LLMProviderManager: generate() called with provider=llm_studio
[2024-12-07 13:00:02] [INFO] ✅ llm_studio response received (latency=2.35s)
[2024-12-07 13:00:02] [INFO] 📊 Statistics updated: requests=1235, errors=3
```

### Métricas Disponibles

**Por Provider:**
- `requests`: Total de requests procesados
- `errors`: Total de errores/timeouts
- `avg_latency`: Latencia promedio en segundos
- `last_request`: Timestamp de último request

**Acceso:**
```bash
curl http://localhost:8080/api/v41/llm/statistics -H "X-API-Key: key"
```

### Alertas Recomendadas

**Configurar alertas cuando:**
- Error rate > 10% en 5 minutos → Revisar conectividad a LLM Studio
- Latencia > 10s promedio → Considerar aumentar timeout
- Fallback usage > 50% → LLM Studio podría estar degradado

---

## 🔄 Actualizaciones Futuras (Roadmap)

### v4.4 (Planificado)

- [ ] **Model Switching**: Cambiar modelo sin cambiar proveedor
- [ ] **Fine-tuning Integration**: Usar modelos fine-tuned específicos de forense
- [ ] **Prompt Templates**: Biblioteca de prompts optimizados
- [ ] **Batch Processing**: Procesar múltiples análisis en batch
- [ ] **WebSocket Updates**: Push notifications de análisis completados

### v4.5 (Futuro)

- [ ] **Multi-Model Consensus**: Usar múltiples modelos y combinar resultados
- [ ] **Cost Tracking**: Monitoreo de costos por provider (si aplicable)
- [ ] **A/B Testing**: Comparar outputs de diferentes modelos
- [ ] **Custom Providers**: API para registrar proveedores externos

---

## 🐛 Troubleshooting

### Problema: LLM Studio no responde

**Síntomas:**
```
[ERROR] ❌ llm_studio failed: Timeout after 40s
[INFO] 🔄 Falling back to phi4_local
```

**Solución:**
1. Verificar conectividad: `curl http://100.101.115.5:2714/health`
2. Revisar logs de LLM Studio en servidor
3. Aumentar timeout: `LLM_STUDIO_TIMEOUT=60` en `.env.local`
4. Confirmar que modelo Phi-4 está cargado en servidor

### Problema: Phi-4 Local no funciona

**Síntomas:**
```
[ERROR] ❌ phi4_local failed: Pattern matching error
```

**Solución:**
1. Verificar que `PHI4_LOCAL_ENABLED=true` en `.env.local`
2. Revisar implementación de `Phi4Local.generate()` en `llm_provider.py`
3. Validar que el prompt contiene keywords esperados

### Problema: Frontend no muestra panel LLM

**Síntomas:**
- URL `/settings/llm` muestra error 404
- Panel no aparece en menú Settings

**Solución:**
1. Verificar import en `App.jsx`: `import LLMSettings from './components/Settings/LLMSettings'`
2. Confirmar ruta registrada: `<Route path="settings/llm" element={<LLMSettings />} />`
3. Verificar que componente existe: `ls frontend-react/src/components/Settings/LLMSettings.jsx`
4. Rebuild frontend: `cd frontend-react && npm run build`

### Problema: API devuelve 401 Unauthorized

**Síntomas:**
```json
{"detail": "Invalid API Key"}
```

**Solución:**
1. Verificar que header incluye: `X-API-Key: your-key`
2. Confirmar API key válida en backend: `api/config.py` → `API_KEY`
3. Revisar middleware: `api/middleware/auth.py` → `verify_api_key()`

---

## 📚 Referencias

### Documentación Relacionada

- [SOAR Intelligence Engine](./SOAR_INTELLIGENCE.md)
- [API Reference](./API.md)
- [Configuration Guide](../installation/CONFIGURATION.md)
- [Frontend Development](../frontend/DEVELOPMENT.md)

### Enlaces Externos

- [LLM Studio Documentation](http://100.101.115.5:2714/docs)
- [Phi-4 Model Card](https://huggingface.co/microsoft/phi-4)
- [OpenAI API Format](https://platform.openai.com/docs/api-reference)

### Código Fuente

- Backend Provider: `api/services/llm_provider.py`
- Backend Router: `api/routes/llm_settings.py`
- Frontend Panel: `frontend-react/src/components/Settings/LLMSettings.jsx`
- Configuration: `api/config.py`
- Environment: `.env.local`

---

**Última actualización**: 7 de diciembre de 2024  
**Mantenedor**: MCP Kali Forensics Team  
**Versión**: v4.3  
**Estado**: ✅ Producción Ready
