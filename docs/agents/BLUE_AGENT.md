# 🔵 MCP BLUE AGENT - Documentación Completa

## Visión General

El **Agente BLUE** del MCP es el componente defensivo especializado en detección, contención, verificación, análisis forense y mitigación automatizada de incidentes de seguridad.

**Enfocado en DFIR (Digital Forensics and Incident Response).**

---

## 🎯 Objetivos

- Detectar indicadores de compromiso (IOCs)
- Contener amenazas activas
- Recolectar evidencia forense
- Analizar comportamiento malicioso
- Generar reportes de incidentes
- Integrar con SOAR para automatización
- Colaborar con agentes Red y Purple

---

## ✅ Capacidades

### 1. Host Forensics
- Recolección de metadatos del host
- Análisis de procesos en ejecución
- Extracción de conexiones de red
- Validación de hashes en IOC Store
- Revisión de tareas programadas
- Análisis de servicios del sistema

### 2. Malware Analysis
- Escaneo YARA con reglas personalizadas
- Escaneo Loki para IOCs conocidos
- Identificación de persistencias
- Cálculo de "MalwareConfidenceScore"
- Registro automático de IOCs

### 3. Memory Forensics
- Dump parcial seguro (metadatos)
- Extracción de módulos cargados
- Identificación de patrones sospechosos
- Integración con Volatility 3

### 4. Network Analysis
- Captura temporal de tráfico
- Identificación de patrones anómalos
- Verificación en Threat Intel
- Detección de comunicaciones C2

### 5. Credential Validation
- Verificación HIBP
- Estado MFA
- Sesiones activas
- Revocación de tokens

### 6. Containment
- Aislamiento de hosts
- Deshabilitar cuentas
- Bloqueo de IOCs
- Revocar tokens OAuth

---

## 🔧 Herramientas Integradas

| Herramienta | Uso | Categoría |
|-------------|-----|-----------|
| YARA | Escaneo de malware por firmas | Malware |
| Loki | Scanner de IOCs | Malware |
| Volatility 3 | Análisis de memoria | Memory |
| OSQuery | Consultas de sistema | Endpoint |
| Sparrow | Análisis M365 | Cloud |
| Hawk | Investigación Exchange | Cloud |
| tcpdump | Captura de tráfico | Network |

---

## 📋 Playbooks BLUE Team

### BLUE-01: Host Compromise Initial Triage

**Trigger**: `ioc_detected`, `red_signal`, `auth_anomaly`

**Steps**:
1. Recolectar metadatos del host
2. Obtener top procesos por CPU/RAM
3. Extraer conexiones de red
4. Validar hashes en IOC Store
5. Revisar tareas programadas
6. Revisar servicios recientes
7. Generar "HostRiskScore"
8. Actualizar Timeline IR

**Output**: Evaluación del estado de compromiso

---

### BLUE-02: Malware Presence Assessment

**Trigger**: `suspicious_hash`, `ml_correlation`

**Steps**:
1. Ejecutar YARA safe ruleset
2. Ejecutar Loki safe scan
3. Identificar persistencias comunes
4. Calcular "MalwareConfidenceScore"
5. Registrar IOCs detectados
6. Asociar a investigación

---

### BLUE-03: Memory Forensics Lite

**Trigger**: `process_anomaly`, `attack_path_predicted`

**Steps**:
1. Dump parcial seguro
2. Extraer lista de módulos
3. Identificar patrones sospechosos
4. Enviar señales al SOAR
5. Actualizar Attack Graph

---

### BLUE-04: Lateral Movement Detection

**Trigger**: `no_mfa`, `multi_location_access`

**Steps**:
1. Correlación con M365 logs
2. Verificar conexiones SMB/WinRM
3. Analizar logs de autenticación
4. Detectar secuencia de movimiento lateral
5. Marcar nodos en Attack Graph
6. Recomendar mitigación

---

### BLUE-05: Network Threat Hunting

**Trigger**: `suspicious_traffic`, `c2_ioc_detected`

**Steps**:
1. Captura temporal (5-10 segundos)
2. Identificación de patrones anómalos
3. Verificar destinos en Threat Intel
4. Generar "SuspiciousNetworkActivity"
5. Crear hallazgo en investigación
6. Alertar al Red Agent

---

### BLUE-06: Credential Compromise Validation

**Trigger**: `hibp_match`, `suspicious_user_activity`

**Steps**:
1. Validar estado MFA
2. Revisar sesiones activas
3. Revocar tokens si aplica
4. Forzar rotación de credenciales
5. Actualizar timeline
6. Generar "UserRiskScore"

---

### BLUE-07: Containment Automation

**Trigger**: `host_compromised_confirmed` (Confidence > 80%)

**Steps**:
1. Aislar host (según política)
2. Deshabilitar cuenta afectada
3. Revocar tokens OAuth
4. Bloquear IOCs detectados
5. Notificar al Purple Agent
6. Registrar en cadena de custodia

---

## 🔗 Integración con Componentes

### SOAR Engine
- Ejecución automática de playbooks
- Validación de políticas
- Escalamiento automático
- Notificaciones

### Correlation Engine
- Recibe señales de correlación
- Procesa alertas Sigma
- Detecta anomalías ML
- Genera IOCs automáticos

### Graph Engine
- Crea nodos: `BLUE_AGENT_FINDING`, `CONTAINMENT_ACTION`
- Aristas: `Blue Agent → Detected Compromise`

### IOC Store
- Consulta IOCs conocidos
- Registra nuevos IOCs
- Enriquece con Threat Intel

---

## 📊 Métricas y Telemetría

```json
{
  "agent_id": "blue-agent-001",
  "metrics": {
    "hosts_analyzed": 156,
    "malware_detected": 12,
    "iocs_registered": 234,
    "containments_executed": 5,
    "avg_triage_time_min": 15,
    "false_positive_rate": 0.02
  }
}
```

---

## 🔒 Capacidades de Contención

| Acción | Descripción | Riesgo | Requiere Aprobación |
|--------|-------------|--------|---------------------|
| Block IOC | Bloquear IP/dominio | Bajo | No |
| Disable Account | Deshabilitar usuario | Medio | Sí (P1+) |
| Revoke Tokens | Invalidar sesiones | Bajo | No |
| Isolate Host | Aislar de red | Alto | Sí |
| Force Password Reset | Cambio de contraseña | Medio | No |

---

## 🚀 Casos de Uso

### Caso 1: Email Compromise
1. SOAR detecta regla de reenvío sospechosa
2. Blue Agent ejecuta Sparrow
3. Detecta OAuth apps maliciosas
4. Revoca tokens
5. Crea IOCs
6. Notifica al usuario

### Caso 2: Ransomware Detection
1. YARA detecta encryptor
2. Blue Agent calcula MalwareScore
3. Aísla host inmediatamente
4. Recolecta evidencia
5. Notifica al SOC

### Caso 3: Credential Leak
1. HIBP match detectado
2. Blue Agent verifica MFA
3. Fuerza password reset
4. Revoca tokens activos
5. Monitorea actividad

---

## 📈 Integración M365/Azure

### APIs Utilizadas
- Microsoft Graph API
- Azure AD Sign-in Logs
- Office 365 Unified Audit Log
- Exchange Online Management

### Permisos Requeridos
```
AuditLog.Read.All
User.Read.All
Directory.Read.All
SecurityEvents.Read.All
Mail.Read (para análisis de buzón)
```

---

## 🔐 Seguridad del Agente

- Ejecución en sandbox
- Principio de mínimo privilegio
- Auditoría completa de acciones
- Separación de entornos
- Cifrado de evidencia

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05  
**Autor**: MCP Forensics Team
