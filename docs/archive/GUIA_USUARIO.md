# 🎯 Guía de Uso: Envío de Evidencia al Grafo de Ataque

## ⚡ Quick Start (30 segundos)

1. 🌐 Abre [http://localhost:9000/dashboard](http://localhost:9000/dashboard)
2. 📋 Busca y haz clic en caso **IR-2025-001**
3. 📊 Haz clic en botón azul **"📊 Ver en Grafo"**
4. ✅ ¡Los IOCs aparecen en el grafo automáticamente!

---

## 📚 Guía Completa

### 1. Preparación del Caso

**Requisitos**:
- ✅ Servidor FastAPI corriendo en puerto 9000
- ✅ Base de datos SQLite con casos
- ✅ Archivos de evidencia en `~/forensics-evidence/{case_id}/`

**Verificar estado**:
```bash
# Comprobar servidor
curl http://localhost:9000/health

# Listar evidencia disponible
ls ~/forensics-evidence/
```

### 2. Abrir Dashboard

```
1. En navegador, ir a: http://localhost:9000/dashboard
2. Ver panel izquierdo con lista de casos
3. Localizar "IR-2025-001" (o tu caso)
```

**Pantalla esperada**:
```
┌─────────────────────────────────────┐
│ 🛡️ MCP Forensics Dashboard          │
├─────────────────────────────────────┤
│ CASOS (3)                           │
│                                     │
│ ✓ IR-2025-001  [CRITICAL]  [inv]   │
│   Análisis de abuso de correo      │
│   Última actualización: hace 2h     │
│                                     │
│ ✓ IR-2024-999  [HIGH]      [open]  │
│   Intrusión en servidor             │
│                                     │
│ ✓ IR-2024-998  [LOW]       [closed]│
│   Malware potencial                 │
└─────────────────────────────────────┘
```

### 3. Hacer Clic en Caso

**Acción**: Haz clic en caso IR-2025-001

**Resultado**: Se abre modal con detalles del caso

```
┌──────────────────────────────────────┐
│ Caso: IR-2025-001                    │
│ ──────────────────────────────────── │
│ Estado: investigating 🔄             │
│ Prioridad: ⚠️ CRITICAL              │
│ Tipo de Amenaza: BEC (Business      │
│                   Email Compromise)  │
│ Asignado a: Unassigned              │
│ Creado: 2025-12-05 16:32:30         │
│ Actualizado: 2025-12-05 11:33:13    │
│                                      │
│ EVIDENCIA RECOLECTADA:               │
│ ├─ 📄 audit_logs.json               │
│ ├─ 📄 inbox_rules.json              │
│ ├─ 📄 oauth_consents.json (14 KB)   │
│ ├─ 📄 risky_signins.json            │
│ ├─ 📄 risky_users.json              │
│ ├─ 📄 signin_logs.json              │
│ ├─ 📄 users_analysis.json           │
│ └─ 📄 investigation_summary.json    │
│                                      │
│ ACCIONES:                            │
│ [🔍 Investigar] [📊 Ver en Grafo]   │
│ [✅ Cerrar] [📝 Nota]               │
└──────────────────────────────────────┘
```

### 4. Clic en "Ver en Grafo"

**Botón**: Azul con ícono de red (graph/diagram)

```
                    ↓ USUARIO HACE CLIC
                    ↓
        [📊 Ver en Grafo] ← AQUI
```

**Lo que ocurre internamente**:

```
1. Frontend: sendEvidenceToGraph("IR-2025-001")
   ↓
2. Cambia a pestaña "Grafo" automáticamente
   ↓
3. Llama: loadEvidenceToGraph("IR-2025-001")
   ↓
4. Fetch a: GET /api/dashboard/cases/IR-2025-001
   ↓
5. Backend extrae IOCs de archivos de evidencia
   ↓
6. Retorna IOCs con tipo, valor y severidad
   ↓
7. Frontend agrega nodos al Cytoscape
   ↓
8. Re-organiza grafo automáticamente
   ↓
9. Muestra notificación de éxito
```

### 5. Visualización en Grafo

**Grafo actualizado con IOCs**:

```
Attack Graph Visualization
┌─────────────────────────────────────┐
│  Admin Account                      │
│  admin@empresa.com                  │
│         🔴 (HIGH)                   │
│         │                           │
│         ├──→ 🔴 Email App           │
│         │    (OAuth Consent)        │
│         │                           │
│         ├──→ 🔴 SharePoint App      │
│         │    (EWS Access)           │
│         │                           │
│         └──→ 🟠 Forward Rule        │
│              (Suspicious)           │
│                                     │
│  📄 Archivos de Evidencia (Púrpura) │
│  ├─ 🟣 audit_logs.json             │
│  ├─ 🟣 oauth_consents.json         │
│  ├─ 🟣 inbox_rules.json            │
│  └─ 🟣 investigation_summary.json   │
└─────────────────────────────────────┘

Leyenda de Colores:
🔴 ROJO = Crítico/Alto (HIGH/CRITICAL severity)
🟠 NARANJA = Medio (MEDIUM severity)
🟢 VERDE = Bajo (LOW severity)
🟣 PÚRPURA = Archivo de Evidencia
```

### 6. Notificación de Éxito

**Aparece en esquina superior derecha**:

```
┌───────────────────────────────────┐
│ ✅ 📊 Evidencia agregada al grafo │
│    (8 IOCs, 8 archivos)          │
│                                   │
│ [×] Cerrar después de 3 segundos  │
└───────────────────────────────────┘
```

---

## 🔍 Tipos de IOCs Visualizados

### Aplicación OAuth (🔴 ROJO - HIGH)

**Origen**: `oauth_consents.json`

```
Nodo: [🔴 Email (2271cddb-5a4d-4d66-bcd9-79f4a4c8d3be)]
Detalles: Scope: EWS.AccessAsUser.All
Riesgo: Acceso a buzón de correo
```

**Por qué es riesgoso**: Aplicaciones con acceso a Mail/EWS pueden leer y enviar correos

---

### Regla de Buzón (🟠 NARANJA - MEDIUM)

**Origen**: `inbox_rules.json`

```
Nodo: [🟠 Forward to external]
Detalles: Reenvía correos a dirección externa
Riesgo: Exfiltración de datos potencial
```

**Por qué es riesgoso**: Reenrutamiento de correos = robo de información

---

### Dirección IP Sospechosa (🔴 ROJO - HIGH)

**Origen**: `risky_signins.json`

```
Nodo: [🔴 185.22.91.14]
Detalles: Inicio de sesión desde IP peligrosa
Usuario: admin@empresa.com
```

**Por qué es riesgosa**: IP conocida por actividad maliciosa

---

### Cuenta Comprometida (🔴 ROJO - CRITICAL)

**Origen**: `investigation_summary.json`

```
Nodo: [🔴 admin@empresa.com]
Detalles: Potencial compromiso detectado
Severidad: CRITICAL
```

**Por qué es crítico**: Confirmación de compromiso confirmado

---

## 🎮 Interacción con el Grafo

### Navegación

| Acción | Resultado |
|--------|-----------|
| **Scroll** | Zoom in/out en el grafo |
| **Click + Drag** | Mover nodos individuales |
| **Click nodo** | Ver detalles de IOC |
| **Right Click** | Menú contextual (si está disponible) |

### Ver Detalles de un IOC

Haz **doble clic** en un nodo para ver:

```
┌──────────────────────────────────┐
│ IOC Details                      │
├──────────────────────────────────┤
│ Tipo:        application         │
│ Valor:       Email               │
│ Severidad:   HIGH                │
│ Fuente:      oauth_consents.json │
│ Detalles:    Scope: EWS...       │
│                                  │
│ [Ver en Evidencia] [×]           │
└──────────────────────────────────┘
```

---

## ⚙️ Opciones Avanzadas

### Opción 1: Botón "Investigar"

Si haces clic en **🔍 Investigar** (amarillo):

```
✅ Actualiza estado del caso a "investigating"
✅ Registra en activity log
❌ NO envía automáticamente al grafo
   (usa "Ver en Grafo" para eso)
```

### Opción 2: Botón "Cerrar"

Si haces clic en **✅ Cerrar** (verde):

```
✅ Marca caso como "closed"
✅ Registra fecha de cierre
❌ El grafo permanece igual
```

### Opción 3: Botón "Nota"

Si haces clic en **📝 Nota** (azul):

```
1. Se abre prompt para ingresar nota
2. Ejemplo: "Cuenta admin comprometida confirmada"
3. Se guarda en base de datos
4. Aparece en activity log
```

---

## 🛠️ Solución de Problemas

### Problema: No veo IOCs en el grafo

**Causas posibles**:

1. ❌ Archivos de evidencia vacíos
   ```bash
   # Verificar
   ls -lah ~/forensics-evidence/IR-2025-001/m365_graph/
   
   # Solución: Ejecutar análisis para generar evidencia
   ```

2. ❌ Archivos no tienen formato JSON válido
   ```bash
   # Verificar
   python3 -m json.tool ~/forensics-evidence/IR-2025-001/m365_graph/oauth_consents.json
   
   # Si falla: Regenerar archivos
   ```

3. ❌ Servidor no responde
   ```bash
   # Verificar
   curl http://localhost:9000/health
   
   # Si falla: Reiniciar servidor
   cd ~/mcp-kali-forensics && uvicorn api.main:app --reload --host 0.0.0.0 --port 9000
   ```

### Problema: Grafo muy desordenado

**Solución**:

1. Haz clic derecho en grafo (si hay menú)
2. Busca opción "Re-layout" o "Reset Layout"
3. El sistema usa algoritmo **fcose** automáticamente

### Problema: Notificación no aparece

**Causas**:

1. Verifica consola del navegador (F12)
2. Mira si hay errores en rojo
3. Revisa logs del servidor: `tail -f logs/mcp-forensics.log`

---

## 📊 Estadísticas de Caso IR-2025-001

| Métrica | Valor |
|---------|-------|
| IOCs Totales | 8 |
| Severidad CRITICAL | 0 |
| Severidad HIGH | 6 (aplicaciones + IPs) |
| Severidad MEDIUM | 2 (reglas de buzón) |
| Severidad LOW | 0 |
| Archivos de Evidencia | 8 |
| Estado | investigating |
| Prioridad | critical |
| Tipo de Amenaza | BEC |

---

## 🔐 Seguridad y Privacidad

✅ **IOCs no se transmiten sin encripción**  
✅ **Datos sensibles (correos) no se muestran en grafo**  
✅ **Solo se visualizan IOCs (dominios, IPs, apps)**  
✅ **Acceso controlado por autenticación API**  

---

## 📚 Referencias y Documentación

Archivos relacionados en el repositorio:

- **EVIDENCE_TO_GRAPH_FLOW.md** - Arquitectura técnica completa
- **CAMBIOS_IMPLEMENTADOS.md** - Resumen de cambios de código
- **api/services/dashboard_data.py** - Lógica de extracción de IOCs
- **api/routes/dashboard.py** - Endpoint de casos
- **api/templates/dashboard.html** - UI del dashboard

---

## ✅ Checklist para Usar

- [ ] Servidor corriendo en puerto 9000
- [ ] Base de datos accesible
- [ ] Navegador abierto en http://localhost:9000/dashboard
- [ ] Caso IR-2025-001 visible en lista
- [ ] Hago clic en caso
- [ ] Modal con detalles abierta
- [ ] Veo archivos de evidencia listados
- [ ] Hago clic en "📊 Ver en Grafo"
- [ ] Se cambia a pestaña Grafo automáticamente
- [ ] Aparecen nodos coloreados
- [ ] Veo notificación de éxito
- [ ] ✅ ¡Grafo poblado con IOCs!

---

## 🎯 Casos de Uso

### Caso de Uso 1: Investigación Inicial
```
1. Abre dashboard
2. Ves caso nuevo: IR-2025-001
3. Haces clic → ver detalles
4. Haces clic "Ver en Grafo" → visualizar amenazas inmediatamente
5. Identificas patrones de ataque en el grafo
```

### Caso de Uso 2: Análisis Profundo
```
1. Abre grafo de caso IR-2025-001
2. Haces clic en nodo "Email App"
3. Ves detalles: "Scope: EWS.AccessAsUser.All"
4. Haces clic en "Ver en Evidencia"
5. Se abre archivo oauth_consents.json con contexto resaltado
```

### Caso de Uso 3: Reporte Ejecutivo
```
1. Visualizas grafo con todos los IOCs
2. Exportas grafo como imagen (próximamente)
3. Creas reporte con: IOCs, severidad, timeline
4. Presentas hallazgos a ejecutivos
```

---

## 🚀 Próximas Funciones

**En Desarrollo**:
- [ ] Exportar grafo como PDF/PNG
- [ ] Timeline interactiva de eventos
- [ ] Búsqueda avanzada de IOCs
- [ ] Relaciones entre IOCs
- [ ] Alertas en tiempo real
- [ ] Colaboración multi-usuario

---

## 📞 Soporte

**Problema**: ¿Necesitas ayuda?

1. 📖 Revisa la sección "Solución de Problemas" arriba
2. 🔍 Busca en logs: `tail -f ~/mcp-kali-forensics/logs/mcp-forensics.log`
3. 🧪 Ejecuta test: Ver archivo `EVIDENCE_TO_GRAPH_FLOW.md`

---

**Última actualización**: 2025-12-05  
**Versión**: 1.0  
**Estado**: ✅ Funcional
