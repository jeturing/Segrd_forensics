# 📧 HERRAMIENTAS DE FORENSE - MCP Kali Forensics

## Descripción General

Conjunto de herramientas especializadas en análisis forense de Exchange, Teams, OneDrive y automatización de respuesta a incidentes con capacidad de aprendizaje automático.

---

## 1. Microsoft Graph API (Forense Exchange/Teams/OneDrive)

**Propósito**: Extracción y análisis forense completo de datos M365

**Ubicación**: `tools/PnP-PowerShell/` o CLI standalone

**URL**: https://learn.microsoft.com/en-us/graph/api/overview

**Características**:
- Acceso a todos los datos de M365
- Queries complejas y correlación
- Análisis temporal de eventos
- Reconstrucción de acciones
- Exportación forense
- Integridad de datos verificable

### Instalación

```bash
# Opción 1: Microsoft Graph CLI (npm)
npm install -g @microsoft/msgraph-cli

# Opción 2: PowerShell
Install-Module Microsoft.Graph -Force
```

### Queries Forenses Típicas

```powershell
# 1. Obtener todos los emails de un usuario en rango de fechas
$filter = "createdDateTime ge 2025-01-01 and createdDateTime le 2025-12-07"
Get-MgUserMailFolderMessage -UserId user@domain.com -Filter $filter

# 2. Extrae emails específicos (posible compromiso)
Get-MgUserMailFolder -UserId user@domain.com | 
  Get-MgMailFolderMessage -Filter "from/emailAddress/address eq 'attacker@evil.com'"

# 3. Analizar forwarding rules malicioso
Get-MgUserMailFolderMessageRule -UserId user@domain.com |
  Where-Object { $_.Actions.Redirect -or $_.Actions.Forward }

# 4. Obtener activity logs de Teams
$filter = "createdDateTime ge 2025-01-01"
Get-MgTeamActivityMonthlyUserDetail -Period 'D7'

# 5. Analizar cambios en OneDrive
Get-MgDriveActivity -DriveId "drive-id" -Filter $filter

# 6. Buscar archivos sospechosos
Get-MgDriveItem -DriveId "drive-id" | 
  Where-Object { $_.Name -like "*.ps1" -or $_.Name -like "*.exe" }
```

### Análisis Forense Avanzado

```powershell
# Reconstruir acciones de usuario en Exchange
function Get-UserForensics {
    param(
        [string]$UserEmail,
        [datetime]$StartDate,
        [datetime]$EndDate
    )
    
    $logs = @()
    
    # 1. Emails enviados/recibidos
    $emails = Get-MgUserMailFolderMessage -UserId $UserEmail `
        -Filter "createdDateTime ge $StartDate and createdDateTime le $EndDate"
    
    # 2. Cambios en delegaciones
    $mailboxes = Get-MgUserMailboxSetting -UserId $UserEmail
    
    # 3. Reglas de forwarding
    $rules = Get-MgUserMailFolderMessageRule -UserId $UserEmail
    
    # 4. Acceso a buzones delegados
    $delegated = Get-MgUserMailFolderMessage -UserId $UserEmail `
        -Filter "from/emailAddress/address ne '$UserEmail'"
    
    return @{
        SendReceive = $emails
        Delegations = $mailboxes
        Rules = $rules
        DelegatedAccess = $delegated
    }
}
```

---

## 2. Cloud Katana

**Propósito**: IR automation con capacidad de auto-corrección y playbooks automatizados

**Ubicación**: `tools/Cloud_Katana/`

**URL**: https://github.com/Azure/Cloud_Katana

**Características**:
- Automatización de respuesta a incidentes
- Playbooks predefinidos
- Ejecución remota de comandos
- Quarantine automático
- Correlación de eventos
- Machine Learning para detección
- Auto-corrección de configuraciones

### Instalación

```bash
cd tools/Cloud_Katana
pip install -r requirements.txt

# O instalar como módulo Python
python setup.py install
```

### Playbooks Disponibles

```python
# playbooks/malware_response.py
"""
Playbook automático: Detección y aislamiento de malware
"""

class MalwareResponsePlaybook:
    async def execute(self, case_id, infected_user):
        """Ejecutar playbook de malware"""
        
        # 1. Detectar compromiso
        threats = await self.detect_threats(infected_user)
        
        # 2. Aislar usuario
        await self.isolate_user(infected_user)
        
        # 3. Terminar sesiones
        await self.terminate_sessions(infected_user)
        
        # 4. Reset de credenciales
        await self.reset_credentials(infected_user)
        
        # 5. Restaurar desde backup
        await self.restore_from_backup(infected_user)
        
        # 6. Notificar equipo de seguridad
        await self.notify_security_team(case_id, threats)
        
        return True
```

### Auto-Corrección Inteligente

```python
"""
Cloud Katana aprende de ejecutar playbooks y auto-corrige:
"""

async def auto_remediate(threat_detection):
    """Remediación automática basada en ML"""
    
    # 1. Analizar tipo de amenaza
    threat_type = ml_classifier.predict(threat_detection)
    
    # 2. Seleccionar playbook óptimo
    playbook = select_playbook(threat_type)
    
    # 3. Ejecutar con confianza del modelo
    confidence = ml_model.confidence_score(threat_type)
    
    if confidence > 0.95:
        # Alta confianza: ejecutar automáticamente
        result = await playbook.execute()
    elif confidence > 0.80:
        # Confianza media: ejecutar con validación
        result = await playbook.execute(require_approval=True)
    else:
        # Baja confianza: alertar al analista
        await alert_analyst(threat_detection)
    
    # 4. Aprender del resultado
    ml_model.learn_from_execution(result)
    
    return result
```

### Casos de Uso

```python
# Caso 1: Compromiso de cuenta
await cloud_katana.playbooks.account_compromise.execute({
    "username": "user@domain.com",
    "threat_score": 9.5,
    "detected_at": datetime.now()
})

# Caso 2: Movimiento lateral detectado
await cloud_katana.playbooks.lateral_movement.execute({
    "source_user": "compromised@domain.com",
    "target_resources": ["SharePoint", "Exchange"],
    "actions": ["isolate", "quarantine", "alert"]
})

# Caso 3: Exfiltración de datos
await cloud_katana.playbooks.data_exfiltration.execute({
    "user": "threat@domain.com",
    "affected_resources": ["/sites/Sensitive", "/teams/Executive"],
    "actions": ["block", "recover", "restore"]
})
```

---

## 3. Loki (YARA/Sigma Scanner)

**Propósito**: Escaneo forense de indicadores de compromiso (IOC)

**Ubicación**: `tools/Loki/`

**URL**: https://github.com/Neo23x0/Loki

**Características**:
- Detección basada en YARA/Sigma
- Análisis de procesos en memoria
- Escaneo de sistema de archivos
- Detección de comportamiento malicioso
- IOC intelligence
- Correlación de eventos

### Instalación

```bash
cd tools/Loki
pip install -r requirements.txt
```

### Escaneo Forense

```bash
# 1. Escaneo completo del sistema
python loki.py --noprocscan --dontwait --intense --path /home

# 2. Escaneo con output CSV
python loki.py --csv --path /home --output-file forensics.csv

# 3. Escaneo de directorio específico con reglas YARA
python loki.py --path /var/forensics --yara-dir /rules

# 4. Escaneo de memoria
python loki.py --noprocscan false --memdump-path /dumps
```

### Integración Forense

```python
"""
Uso en análisis forense con Cloud Katana
"""

async def forensic_scan(case_id: str, target_path: str):
    """Ejecutar escaneo forense completo"""
    
    # 1. Ejecutar Loki
    loki_results = await run_loki_scan(target_path)
    
    # 2. Analizar resultados
    iocs = parse_loki_output(loki_results)
    
    # 3. Correlacionar con activity logs
    activity = await get_activity_logs(case_id)
    
    # 4. Determinar impacto
    impact = correlate_iocs_with_activity(iocs, activity)
    
    # 5. Ejecutar playbook si es necesario
    if impact.severity > 8:
        await cloud_katana.execute_response_playbook(case_id, impact)
    
    return {
        "iocs": iocs,
        "activity": activity,
        "impact": impact,
        "remediation": "completed" if impact.severity > 8 else "manual_review"
    }
```

---

## 🤖 Machine Learning para Forense

### Auto-Corrección Basada en ML

```python
"""
Modelo de ML que aprende de ejecutar playbooks
"""

class ForensicML:
    async def predict_threat_response(self, detection):
        """Predecir mejor respuesta basada en historiales"""
        
        # 1. Extraer features
        features = extract_features(detection)
        
        # 2. Predecir con modelo
        threat_type = self.model.predict(features)
        confidence = self.model.predict_proba(features)
        
        # 3. Seleccionar playbook óptimo
        playbook = self.select_best_playbook(threat_type)
        
        # 4. Auto-ejecutar si confianza alta
        if confidence > 0.90:
            result = await playbook.auto_execute()
            
            # 5. Aprender del resultado
            self.model.partial_fit(features, result.success)
        
        return playbook

    async def learn_from_execution(self, execution_result):
        """Mejorar modelo con cada ejecución"""
        
        # Actualizar modelo con nuevos datos
        self.model.partial_fit(
            execution_result.features,
            execution_result.outcome
        )
        
        # Optimizar thresholds
        self.update_thresholds()
        
        # Ajustar playbooks
        self.optimize_playbooks()
```

---

## 📊 Comparativa de Herramientas Forenses

| Tool | Enfoque | Cobertura | Automatización |
|------|---------|-----------|----------------|
| **Graph API** | Datos M365 | Exchange/Teams/OneDrive | Manual |
| **Cloud Katana** | Respuesta | Incident Response | ✓ Automática |
| **Loki** | Malware | Filesystem/Memory | ✓ Automática |

---

## 🔄 Flujo de Análisis Forense

```
1. Detección de Incidente
   ↓
2. Graph API: Extracción de datos
   ↓
3. Loki: Escaneo de IOCs
   ↓
4. Correlación de Eventos
   ↓
5. Cloud Katana: Análisis ML
   ↓
6. Auto-Corrección Inteligente
   ↓
7. Playbook de Respuesta Automática
   ↓
8. Aprendizaje del Sistema
```

---

## 🎯 Casos de Uso Forenses

### Caso 1: Investigación de Compromiso de Cuenta

```python
# 1. Extracción
emails = await graph_api.get_user_emails(user_email, start_date, end_date)
activity = await graph_api.get_user_activity(user_email, start_date, end_date)

# 2. Análisis
suspicious_emails = filter_by_sender_domain(emails, "evil.com")
suspicious_activity = filter_by_anomaly(activity)

# 3. Detección
iocs = extract_iocs(suspicious_emails + suspicious_activity)
loki_matches = await loki_scan(iocs)

# 4. Respuesta Automática
if loki_matches.severity > 8:
    await cloud_katana.account_compromise_playbook.execute(
        username=user_email,
        threats=loki_matches
    )
```

### Caso 2: Investigación de Exfiltración

```python
# 1. Detectar acceso anómalo
async def detect_exfiltration(user_email, start_date):
    # Obtener acceso a OneDrive/SharePoint
    file_access = await graph_api.get_file_access_logs(
        user_email, 
        start_date
    )
    
    # Detectar descarga masiva
    bulk_downloads = filter_bulk_downloads(file_access)
    
    if bulk_downloads:
        # Ejecutar playbook de exfiltración
        await cloud_katana.data_exfiltration_playbook.execute({
            "user": user_email,
            "files": bulk_downloads,
            "action": "quarantine_and_restore"
        })
```

### Caso 3: Análisis de Cadena de Ataque

```python
# Reconstruir timeline de ataque
timeline = await reconstruct_attack_timeline(
    user_email,
    start_date,
    graph_api,
    loki
)

# Visualizar movimiento lateral
attack_graph = build_attack_graph(timeline)

# Auto-mitigar
await cloud_katana.mitigate_attack_chain(attack_graph)
```

---

## 🚨 Indicadores Forenses

### En Graph API
- [ ] Emails a dominios maliciosos
- [ ] Forwarding a cuentas externas
- [ ] Acceso a recursos no autorizados
- [ ] Activity logs con patrones anómalos

### En Loki
- [ ] Procesos maliciosos en memoria
- [ ] Archivos ejecutables sospechosos
- [ ] Cambios en archivos del sistema
- [ ] Network connections maliciosas

### En Cloud Katana (ML)
- [ ] Anomalía en patrón de login
- [ ] Velocidad de cambios anormal
- [ ] Acceso a múltiples recursos
- [ ] Comportamiento fuera de horario

---

## 🔗 Integración Completa con MCP

```python
async def forensic_investigation(case_id: str, incident_type: str, target_user: str):
    """Investigación forense completa integrada"""
    
    # 1. Extracción de datos
    investigation = {
        "case_id": case_id,
        "incident_type": incident_type,
        "target": target_user,
        "start_time": datetime.now()
    }
    
    # 2. Graph API: Extraer todos los datos
    graph_data = await graph_api.get_user_complete_data(
        target_user,
        days=90
    )
    
    # 3. Loki: Escanear IOCs
    ioc_scan = await loki.scan_for_iocs(graph_data)
    
    # 4. Cloud Katana: Análisis inteligente
    ml_analysis = await cloud_katana.ml_analyze(
        graph_data,
        ioc_scan
    )
    
    # 5. Auto-respuesta
    if ml_analysis.threat_level > 0.85:
        response = await cloud_katana.auto_execute_playbook(
            incident_type,
            ml_analysis
        )
        investigation["auto_response"] = response
    
    # 6. Reporting
    report = generate_forensic_report(
        graph_data,
        ioc_scan,
        ml_analysis
    )
    
    investigation["report"] = report
    investigation["end_time"] = datetime.now()
    
    return investigation
```

---

## 📚 Referencias

- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph)
- [Cloud Katana GitHub](https://github.com/Azure/Cloud_Katana)
- [Loki GitHub](https://github.com/Neo23x0/Loki)
- [Forensic Analysis Best Practices](https://docs.microsoft.com/en-us/microsoft-365/compliance)

---

**Categoría**: FORENSE  
**Status**: ✓ Documentado  
**ML Capabilities**: ✓ Auto-correction  
**Automation**: ✓ Complete  
**Última Actualización**: 2025-12-07
