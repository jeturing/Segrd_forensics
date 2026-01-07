"""
MCP v4.1 - Correlation Engine
Motor de correlación para detección de amenazas.
Incluye: Sigma rules, ML heuristics, pattern matching, alerting.
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging


from api.database import get_db_context
from api.models.tools import (
    CorrelationRule, CorrelationEvent, CorrelationSeverity, CorrelationRuleType
)

logger = logging.getLogger(__name__)


# =============================================================================
# SIGMA RULES - BUILT-IN
# =============================================================================

BUILTIN_SIGMA_RULES = [
    {
        "id": "SIGMA-001",
        "title": "Suspicious PowerShell Encoded Command",
        "description": "Detects PowerShell with encoded command parameter",
        "author": "MCP Forensics",
        "severity": CorrelationSeverity.HIGH.value,
        "mitre_tactics": ["TA0002", "TA0005"],  # Execution, Defense Evasion
        "mitre_techniques": ["T1059.001", "T1027"],
        "logsource": {
            "category": "process_creation",
            "product": "windows"
        },
        "detection": {
            "selection": {
                "Image|endswith": "\\powershell.exe",
                "CommandLine|contains|all": ["-enc", "-e ", "-ec ", "-encodedcommand"]
            },
            "condition": "selection"
        },
        "tags": ["powershell", "encoded", "obfuscation"]
    },
    {
        "id": "SIGMA-002",
        "title": "Mimikatz Execution Detected",
        "description": "Detects Mimikatz credential theft tool",
        "severity": CorrelationSeverity.CRITICAL.value,
        "mitre_tactics": ["TA0006"],  # Credential Access
        "mitre_techniques": ["T1003.001"],
        "logsource": {
            "category": "process_creation",
            "product": "windows"
        },
        "detection": {
            "selection": {
                "CommandLine|contains": ["sekurlsa::", "kerberos::", "lsadump::"]
            },
            "condition": "selection"
        },
        "tags": ["mimikatz", "credential_theft", "lsass"]
    },
    {
        "id": "SIGMA-003",
        "title": "Lateral Movement via PsExec",
        "description": "Detects PsExec usage for lateral movement",
        "severity": CorrelationSeverity.MEDIUM.value,
        "mitre_tactics": ["TA0008"],  # Lateral Movement
        "mitre_techniques": ["T1021.002", "T1570"],
        "logsource": {
            "category": "process_creation",
            "product": "windows"
        },
        "detection": {
            "selection": {
                "Image|endswith": ["\\psexec.exe", "\\psexec64.exe"],
                "CommandLine|contains": ["\\\\" ]
            },
            "condition": "selection"
        },
        "tags": ["psexec", "lateral_movement", "remote_execution"]
    },
    {
        "id": "SIGMA-004",
        "title": "Suspicious Office Child Process",
        "description": "Detects Office applications spawning suspicious child processes",
        "severity": CorrelationSeverity.HIGH.value,
        "mitre_tactics": ["TA0001", "TA0002"],  # Initial Access, Execution
        "mitre_techniques": ["T1566.001", "T1204.002"],
        "logsource": {
            "category": "process_creation",
            "product": "windows"
        },
        "detection": {
            "selection_parent": {
                "ParentImage|endswith": [
                    "\\winword.exe", "\\excel.exe", "\\powerpnt.exe",
                    "\\outlook.exe", "\\msaccess.exe"
                ]
            },
            "selection_child": {
                "Image|endswith": [
                    "\\cmd.exe", "\\powershell.exe", "\\wscript.exe",
                    "\\cscript.exe", "\\mshta.exe", "\\certutil.exe"
                ]
            },
            "condition": "selection_parent and selection_child"
        },
        "tags": ["office", "macro", "phishing"]
    },
    {
        "id": "SIGMA-005",
        "title": "Azure AD Suspicious Sign-In Pattern",
        "description": "Detects impossible travel or risky sign-ins in Azure AD",
        "severity": CorrelationSeverity.MEDIUM.value,
        "mitre_tactics": ["TA0001", "TA0006"],
        "mitre_techniques": ["T1078.004"],
        "logsource": {
            "category": "azure_signin",
            "product": "azure"
        },
        "detection": {
            "selection": {
                "properties.status.errorCode": 0,
                "properties.riskLevelDuringSignIn|contains": ["high", "medium"]
            },
            "condition": "selection"
        },
        "tags": ["azure", "signin", "identity"]
    },
    {
        "id": "SIGMA-006",
        "title": "O365 Mailbox Rule Modification",
        "description": "Detects suspicious inbox rule creation for email forwarding",
        "severity": CorrelationSeverity.MEDIUM.value,
        "mitre_tactics": ["TA0009"],  # Collection
        "mitre_techniques": ["T1114.003"],
        "logsource": {
            "category": "o365_audit",
            "product": "o365"
        },
        "detection": {
            "selection": {
                "Operation": "New-InboxRule",
                "Parameters|contains": ["ForwardTo", "ForwardAsAttachmentTo", "RedirectTo"]
            },
            "condition": "selection"
        },
        "tags": ["o365", "email", "forwarding", "bec"]
    },
    {
        "id": "SIGMA-007",
        "title": "LSASS Memory Dump",
        "description": "Detects tools dumping LSASS process memory",
        "severity": CorrelationSeverity.CRITICAL.value,
        "mitre_tactics": ["TA0006"],
        "mitre_techniques": ["T1003.001"],
        "logsource": {
            "category": "process_creation",
            "product": "windows"
        },
        "detection": {
            "selection_process": {
                "CommandLine|contains": ["lsass", "procdump", "comsvcs.dll"]
            },
            "selection_file": {
                "TargetFilename|endswith": [".dmp", ".dump"]
            },
            "condition": "selection_process or selection_file"
        },
        "tags": ["lsass", "memory_dump", "credential_theft"]
    },
    {
        "id": "SIGMA-008",
        "title": "WMI Persistence Detection",
        "description": "Detects WMI event subscription for persistence",
        "severity": CorrelationSeverity.HIGH.value,
        "mitre_tactics": ["TA0003"],  # Persistence
        "mitre_techniques": ["T1546.003"],
        "logsource": {
            "category": "wmi_event",
            "product": "windows"
        },
        "detection": {
            "selection": {
                "EventType": ["__EventConsumer", "__EventFilter", "__FilterToConsumerBinding"]
            },
            "condition": "selection"
        },
        "tags": ["wmi", "persistence", "event_subscription"]
    }
]


# =============================================================================
# ML HEURISTICS - PATTERN DEFINITIONS
# =============================================================================

HEURISTIC_PATTERNS = [
    {
        "id": "HEUR-001",
        "name": "High Frequency Login Failures",
        "description": "Multiple failed logins from same source in short time",
        "category": "brute_force",
        "threshold": 10,
        "window_minutes": 5,
        "severity": CorrelationSeverity.MEDIUM.value,
        "pattern": {
            "event_type": "login_failed",
            "group_by": ["source_ip", "target_user"],
            "count_threshold": 10
        }
    },
    {
        "id": "HEUR-002",
        "name": "Unusual Geographic Access",
        "description": "Access from unusual geographic location",
        "category": "anomaly",
        "severity": CorrelationSeverity.MEDIUM.value,
        "pattern": {
            "event_type": "login_success",
            "anomaly_field": "geo_country",
            "baseline_days": 30
        }
    },
    {
        "id": "HEUR-003",
        "name": "Mass File Download",
        "description": "Large number of files downloaded in short period",
        "category": "data_exfil",
        "threshold": 100,
        "window_minutes": 15,
        "severity": CorrelationSeverity.HIGH.value,
        "pattern": {
            "event_type": "file_download",
            "group_by": ["user_id"],
            "count_threshold": 100
        }
    },
    {
        "id": "HEUR-004",
        "name": "Port Scan Detected",
        "description": "Multiple connection attempts to different ports",
        "category": "reconnaissance",
        "threshold": 50,
        "window_minutes": 2,
        "severity": CorrelationSeverity.MEDIUM.value,
        "pattern": {
            "event_type": "network_connection",
            "group_by": ["source_ip"],
            "distinct_field": "dest_port",
            "count_threshold": 50
        }
    },
    {
        "id": "HEUR-005",
        "name": "Privilege Escalation Attempt",
        "description": "User attempting to access resources above their role",
        "category": "privilege_escalation",
        "severity": CorrelationSeverity.HIGH.value,
        "pattern": {
            "event_type": "access_denied",
            "group_by": ["user_id"],
            "resource_pattern": ["admin", "root", "sudo", "sensitive"]
        }
    }
]


# =============================================================================
# CORRELATION ENGINE
# =============================================================================

class CorrelationEngine:
    """
    Motor de correlación que combina:
    - Sigma rules (pattern matching)
    - ML heuristics (anomaly detection)
    - Threshold-based alerts
    """
    
    def __init__(self):
        self.sigma_rules: Dict[str, Dict] = {}
        self.heuristics: Dict[str, Dict] = {}
        self.event_buffer: List[Dict] = []
        self.buffer_max_size = 10000
        self.initialized = False
    
    async def initialize(self):
        """Inicializa motor con reglas predefinidas"""
        if self.initialized:
            return
        
        # Cargar Sigma rules a BD
        with get_db_context() as db:
            for rule_data in BUILTIN_SIGMA_RULES:
                existing = db.query(CorrelationRule).filter(
                    CorrelationRule.id == rule_data["id"]
                ).first()
                
                if not existing:
                    rule = CorrelationRule(
                        id=rule_data["id"],
                        name=rule_data["title"],
                        description=rule_data["description"],
                        rule_type=CorrelationRuleType.SIGMA.value,
                        severity=rule_data["severity"],
                        logsource=rule_data.get("logsource", {}),
                        detection=rule_data["detection"],
                        mitre_tactics=rule_data.get("mitre_tactics", []),
                        mitre_techniques=rule_data.get("mitre_techniques", []),
                        tags=rule_data.get("tags", []),
                        is_enabled=True,
                        is_builtin=True
                    )
                    db.add(rule)
                    logger.info(f"📜 Loaded Sigma rule: {rule_data['title']}")
            
            # Cargar heuristics
            for heur_data in HEURISTIC_PATTERNS:
                existing = db.query(CorrelationRule).filter(
                    CorrelationRule.id == heur_data["id"]
                ).first()
                
                if not existing:
                    rule = CorrelationRule(
                        id=heur_data["id"],
                        name=heur_data["name"],
                        description=heur_data["description"],
                        rule_type=CorrelationRuleType.HEURISTIC.value,
                        severity=heur_data["severity"],
                        detection={
                            "pattern": heur_data["pattern"],
                            "threshold": heur_data.get("threshold"),
                            "window_minutes": heur_data.get("window_minutes")
                        },
                        tags=[heur_data["category"]],
                        is_enabled=True,
                        is_builtin=True
                    )
                    db.add(rule)
                    logger.info(f"🧠 Loaded heuristic: {heur_data['name']}")
            
            db.commit()
        
        # Cache en memoria
        await self._load_rules_to_cache()
        self.initialized = True
        logger.info("✅ Correlation Engine initialized")
    
    async def _load_rules_to_cache(self):
        """Carga reglas activas a memoria para correlación rápida"""
        with get_db_context() as db:
            sigma_rules = db.query(CorrelationRule).filter(
                CorrelationRule.rule_type == CorrelationRuleType.SIGMA.value,
                CorrelationRule.is_enabled == True
            ).all()
            
            for rule in sigma_rules:
                self.sigma_rules[rule.id] = {
                    "id": rule.id,
                    "name": rule.name,
                    "severity": rule.severity,
                    "logsource": rule.logsource,
                    "detection": rule.detection,
                    "mitre_tactics": rule.mitre_tactics,
                    "mitre_techniques": rule.mitre_techniques
                }
            
            heur_rules = db.query(CorrelationRule).filter(
                CorrelationRule.rule_type == CorrelationRuleType.HEURISTIC.value,
                CorrelationRule.is_enabled == True
            ).all()
            
            for rule in heur_rules:
                self.heuristics[rule.id] = {
                    "id": rule.id,
                    "name": rule.name,
                    "severity": rule.severity,
                    "detection": rule.detection
                }
    
    # -------------------------------------------------------------------------
    # EVENT INGESTION
    # -------------------------------------------------------------------------
    
    async def ingest_event(
        self,
        event: Dict[str, Any],
        source: str = "unknown",
        case_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Ingesta un evento y ejecuta correlación.
        
        Args:
            event: Evento normalizado
            source: Fuente del evento (wazuh, siem, tool_output, etc.)
            case_id: ID del caso asociado
        
        Returns:
            Lista de alertas generadas
        """
        if not self.initialized:
            await self.initialize()
        
        # Normalizar evento
        normalized = self._normalize_event(event, source)
        
        # Guardar en buffer
        self.event_buffer.append(normalized)
        if len(self.event_buffer) > self.buffer_max_size:
            self.event_buffer = self.event_buffer[-self.buffer_max_size:]
        
        # Persistir evento
        event_id = await self._persist_event(normalized, case_id)
        
        # Ejecutar correlación
        alerts = []
        
        # 1. Sigma rules
        sigma_matches = await self._evaluate_sigma_rules(normalized)
        for match in sigma_matches:
            alert = await self._create_alert(
                rule_id=match["rule_id"],
                event_id=event_id,
                matched_data=match,
                case_id=case_id
            )
            alerts.append(alert)
        
        # 2. Heuristics (requieren múltiples eventos)
        heur_matches = await self._evaluate_heuristics(normalized)
        for match in heur_matches:
            alert = await self._create_alert(
                rule_id=match["rule_id"],
                event_id=event_id,
                matched_data=match,
                case_id=case_id
            )
            alerts.append(alert)
        
        return alerts
    
    async def ingest_batch(
        self,
        events: List[Dict],
        source: str = "unknown",
        case_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingesta batch de eventos"""
        total_alerts = []
        
        for event in events:
            alerts = await self.ingest_event(event, source, case_id)
            total_alerts.extend(alerts)
        
        return {
            "events_processed": len(events),
            "alerts_generated": len(total_alerts),
            "alerts": total_alerts
        }
    
    def _normalize_event(self, event: Dict, source: str) -> Dict:
        """Normaliza evento a formato común (OTel-inspired)"""
        normalized = {
            "id": str(uuid.uuid4()),
            "timestamp": event.get("timestamp") or datetime.utcnow().isoformat(),
            "source": source,
            "event_type": event.get("event_type") or event.get("type") or "unknown",
            "severity": event.get("severity") or "info",
            "host": {
                "name": event.get("hostname") or event.get("host", {}).get("name"),
                "ip": event.get("host_ip") or event.get("host", {}).get("ip")
            },
            "user": {
                "name": event.get("username") or event.get("user", {}).get("name"),
                "id": event.get("user_id") or event.get("user", {}).get("id")
            },
            "process": {
                "name": event.get("process_name") or event.get("Image"),
                "pid": event.get("pid"),
                "command_line": event.get("command_line") or event.get("CommandLine"),
                "parent_name": event.get("parent_process") or event.get("ParentImage")
            },
            "network": {
                "source_ip": event.get("source_ip") or event.get("src_ip"),
                "dest_ip": event.get("dest_ip") or event.get("dst_ip"),
                "source_port": event.get("source_port"),
                "dest_port": event.get("dest_port")
            },
            "file": {
                "path": event.get("file_path") or event.get("TargetFilename"),
                "hash": event.get("file_hash")
            },
            "geo": {
                "country": event.get("geo_country"),
                "city": event.get("geo_city")
            },
            "raw": event  # Preservar original
        }
        
        return normalized
    
    async def _persist_event(self, event: Dict, case_id: Optional[str]) -> str:
        """Persiste evento en BD"""
        with get_db_context() as db:
            db_event = CorrelationEvent(
                id=event["id"],
                timestamp=datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                    if isinstance(event["timestamp"], str) else event["timestamp"],
                source=event["source"],
                event_type=event["event_type"],
                severity=event["severity"],
                host_name=event["host"]["name"],
                host_ip=event["host"]["ip"],
                user_name=event["user"]["name"],
                user_id=event["user"]["id"],
                process_name=event["process"]["name"],
                process_command=event["process"]["command_line"],
                source_ip=event["network"]["source_ip"],
                dest_ip=event["network"]["dest_ip"],
                file_path=event["file"]["path"],
                geo_country=event["geo"]["country"],
                raw_event=event["raw"],
                case_id=case_id
            )
            db.add(db_event)
            db.commit()
            
            return event["id"]
    
    # -------------------------------------------------------------------------
    # SIGMA RULE EVALUATION
    # -------------------------------------------------------------------------
    
    async def _evaluate_sigma_rules(self, event: Dict) -> List[Dict]:
        """Evalúa evento contra todas las Sigma rules"""
        matches = []
        
        for rule_id, rule in self.sigma_rules.items():
            # Verificar logsource
            if not self._check_logsource(event, rule.get("logsource", {})):
                continue
            
            # Evaluar detección
            detection = rule.get("detection", {})
            if self._evaluate_detection(event, detection):
                matches.append({
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "severity": rule["severity"],
                    "mitre_tactics": rule.get("mitre_tactics", []),
                    "mitre_techniques": rule.get("mitre_techniques", []),
                    "matched_fields": self._get_matched_fields(event, detection)
                })
                
                logger.info(f"🎯 Sigma match: {rule['name']}")
        
        return matches
    
    def _check_logsource(self, event: Dict, logsource: Dict) -> bool:
        """Verifica si el evento coincide con el logsource de la regla"""
        if not logsource:
            return True
        
        event_source = event.get("source", "")
        event_type = event.get("event_type", "")
        
        # Mapeo simplificado
        source_mapping = {
            "process_creation": ["process", "sysmon", "endpoint"],
            "azure_signin": ["azure", "m365", "entra"],
            "o365_audit": ["o365", "m365", "exchange"],
            "wmi_event": ["wmi", "sysmon"],
            "network_connection": ["network", "firewall", "netflow"]
        }
        
        category = logsource.get("category", "")
        if category:
            valid_sources = source_mapping.get(category, [category])
            if not any(s in event_source.lower() or s in event_type.lower() 
                      for s in valid_sources):
                return False
        
        return True
    
    def _evaluate_detection(self, event: Dict, detection: Dict) -> bool:
        """Evalúa lógica de detección de una Sigma rule"""
        condition = detection.get("condition", "")
        
        # Evaluar cada selección
        selection_results = {}
        
        for key, criteria in detection.items():
            if key == "condition":
                continue
            
            # Evaluar selección
            matched = self._evaluate_selection(event, criteria)
            selection_results[key] = matched
        
        # Evaluar condición
        return self._evaluate_condition(condition, selection_results)
    
    def _evaluate_selection(self, event: Dict, criteria: Dict) -> bool:
        """Evalúa una selección individual"""
        if not criteria:
            return False
        
        all_match = True
        
        for field_spec, expected in criteria.items():
            # Parsear field y modifier
            parts = field_spec.split("|")
            field_name = parts[0]
            modifiers = parts[1:] if len(parts) > 1 else []
            
            # Obtener valor del evento
            actual_value = self._get_field_value(event, field_name)
            if actual_value is None:
                all_match = False
                continue
            
            # Aplicar modificadores y comparar
            if not self._compare_with_modifiers(actual_value, expected, modifiers):
                all_match = False
        
        return all_match
    
    def _get_field_value(self, event: Dict, field_name: str) -> Any:
        """Obtiene valor de campo del evento (soporta notación anidada)"""
        # Mapeo de nombres Sigma a estructura normalizada
        field_mapping = {
            "Image": ("process", "name"),
            "CommandLine": ("process", "command_line"),
            "ParentImage": ("process", "parent_name"),
            "TargetFilename": ("file", "path"),
            "User": ("user", "name"),
            "SourceIp": ("network", "source_ip"),
            "DestinationIp": ("network", "dest_ip"),
            "EventType": ("event_type",),
            "Operation": ("event_type",)
        }
        
        if field_name in field_mapping:
            path = field_mapping[field_name]
            value = event
            for key in path:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        
        # Buscar en estructura anidada
        if "." in field_name:
            parts = field_name.split(".")
            value = event
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        
        # Buscar en raw
        raw = event.get("raw", {})
        return raw.get(field_name)
    
    def _compare_with_modifiers(
        self,
        actual: Any,
        expected: Any,
        modifiers: List[str]
    ) -> bool:
        """Compara valores aplicando modificadores Sigma"""
        if actual is None:
            return False
        
        actual_str = str(actual).lower()
        
        # Lista de valores esperados
        if not isinstance(expected, list):
            expected = [expected]
        
        for exp in expected:
            exp_str = str(exp).lower()
            matched = False
            
            if "endswith" in modifiers:
                matched = actual_str.endswith(exp_str)
            elif "startswith" in modifiers:
                matched = actual_str.startswith(exp_str)
            elif "contains" in modifiers:
                if "all" in modifiers:
                    # Todos deben coincidir
                    matched = all(e.lower() in actual_str for e in expected)
                    if matched:
                        return True
                else:
                    matched = exp_str in actual_str
            elif "re" in modifiers:
                matched = bool(re.search(exp, str(actual), re.IGNORECASE))
            else:
                matched = actual_str == exp_str
            
            if matched:
                return True
        
        return False
    
    def _evaluate_condition(self, condition: str, results: Dict[str, bool]) -> bool:
        """Evalúa condición lógica (selection, selection1 and selection2, etc.)"""
        if not condition:
            # Si no hay condición, cualquier selección True es match
            return any(results.values())
        
        # Reemplazar nombres de selección con valores booleanos
        expr = condition
        for name, value in results.items():
            expr = expr.replace(name, str(value))
        
        # Reemplazar operadores
        expr = expr.replace(" and ", " and ")
        expr = expr.replace(" or ", " or ")
        expr = expr.replace(" not ", " not ")
        
        try:
            return eval(expr)
        except:
            # Si hay error, verificar si alguna selección matched
            return any(results.values())
    
    def _get_matched_fields(self, event: Dict, detection: Dict) -> Dict:
        """Obtiene campos que hicieron match"""
        matched = {}
        
        for key, criteria in detection.items():
            if key == "condition":
                continue
            if not isinstance(criteria, dict):
                continue
            
            for field_spec, _ in criteria.items():
                field_name = field_spec.split("|")[0]
                value = self._get_field_value(event, field_name)
                if value:
                    matched[field_name] = value
        
        return matched
    
    # -------------------------------------------------------------------------
    # HEURISTIC EVALUATION
    # -------------------------------------------------------------------------
    
    async def _evaluate_heuristics(self, event: Dict) -> List[Dict]:
        """Evalúa evento contra heurísticas (requieren histórico)"""
        matches = []
        
        for heur_id, heur in self.heuristics.items():
            detection = heur.get("detection", {})
            pattern = detection.get("pattern", {})
            
            # Verificar tipo de evento
            if pattern.get("event_type") and event["event_type"] != pattern["event_type"]:
                continue
            
            # Evaluar según tipo de patrón
            if "count_threshold" in pattern:
                matched = await self._evaluate_count_heuristic(event, heur)
                if matched:
                    matches.append({
                        "rule_id": heur_id,
                        "rule_name": heur["name"],
                        "severity": heur["severity"],
                        "matched_count": matched.get("count", 0)
                    })
            
            elif "anomaly_field" in pattern:
                matched = await self._evaluate_anomaly_heuristic(event, heur)
                if matched:
                    matches.append({
                        "rule_id": heur_id,
                        "rule_name": heur["name"],
                        "severity": heur["severity"],
                        "anomaly_value": matched.get("value")
                    })
        
        return matches
    
    async def _evaluate_count_heuristic(
        self,
        event: Dict,
        heur: Dict
    ) -> Optional[Dict]:
        """Evalúa heurística basada en conteo"""
        detection = heur.get("detection", {})
        pattern = detection.get("pattern", {})
        
        threshold = detection.get("threshold", 10)
        window_minutes = detection.get("window_minutes", 5)
        group_by = pattern.get("group_by", [])
        
        # Contar eventos similares en ventana de tiempo
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        # Filtrar buffer por ventana y grupo
        matching_events = []
        for buffered in self.event_buffer:
            # Verificar timestamp
            buf_time = buffered.get("timestamp")
            if isinstance(buf_time, str):
                buf_time = datetime.fromisoformat(buf_time.replace("Z", "+00:00"))
            if buf_time < window_start:
                continue
            
            # Verificar grupo
            group_match = True
            for field in group_by:
                event_val = self._get_field_value(event, field)
                buf_val = self._get_field_value(buffered, field)
                if event_val != buf_val:
                    group_match = False
                    break
            
            if group_match:
                matching_events.append(buffered)
        
        if len(matching_events) >= threshold:
            return {"count": len(matching_events)}
        
        return None
    
    async def _evaluate_anomaly_heuristic(
        self,
        event: Dict,
        heur: Dict
    ) -> Optional[Dict]:
        """Evalúa heurística de anomalía"""
        detection = heur.get("detection", {})
        pattern = detection.get("pattern", {})
        
        anomaly_field = pattern.get("anomaly_field")
        baseline_days = pattern.get("baseline_days", 30)
        
        current_value = self._get_field_value(event, anomaly_field)
        if not current_value:
            return None
        
        # Consultar baseline histórico
        with get_db_context() as db:
            baseline_start = datetime.utcnow() - timedelta(days=baseline_days)
            user_id = event.get("user", {}).get("id") or event.get("user", {}).get("name")
            
            if not user_id:
                return None
            
            # Obtener valores históricos únicos para este usuario
            historical = db.query(CorrelationEvent).filter(
                CorrelationEvent.user_name == user_id,
                CorrelationEvent.timestamp >= baseline_start
            ).all()
            
            historical_values = set()
            for h_event in historical:
                raw = h_event.raw_event or {}
                if anomaly_field == "geo_country":
                    val = h_event.geo_country
                else:
                    val = raw.get(anomaly_field)
                if val:
                    historical_values.add(val)
        
        # Si el valor actual no está en el histórico, es anomalía
        if historical_values and current_value not in historical_values:
            return {"value": current_value, "baseline": list(historical_values)}
        
        return None
    
    # -------------------------------------------------------------------------
    # ALERT CREATION
    # -------------------------------------------------------------------------
    
    async def _create_alert(
        self,
        rule_id: str,
        event_id: str,
        matched_data: Dict,
        case_id: Optional[str]
    ) -> Dict:
        """Crea alerta de correlación"""
        alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
        
        with get_db_context() as db:
            # Obtener regla
            rule = db.query(CorrelationRule).filter(
                CorrelationRule.id == rule_id
            ).first()
            
            alert = CorrelationAlert(
                id=alert_id,
                rule_id=rule_id,
                event_id=event_id,
                severity=matched_data.get("severity", CorrelationSeverity.MEDIUM.value),
                title=f"[{matched_data.get('severity', 'MEDIUM').upper()}] {matched_data.get('rule_name', 'Unknown Rule')}",
                description=rule.description if rule else "Correlation match detected",
                matched_fields=matched_data.get("matched_fields", {}),
                mitre_tactics=matched_data.get("mitre_tactics", []),
                mitre_techniques=matched_data.get("mitre_techniques", []),
                case_id=case_id,
                status="new"
            )
            db.add(alert)
            
            # Actualizar contador de la regla
            if rule:
                rule.match_count += 1
                rule.last_match_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"🚨 Alert created: {alert_id} - {alert.title}")
            
            return {
                "alert_id": alert_id,
                "rule_id": rule_id,
                "severity": alert.severity,
                "title": alert.title,
                "mitre_tactics": alert.mitre_tactics,
                "mitre_techniques": alert.mitre_techniques
            }
    
    # -------------------------------------------------------------------------
    # TOOL OUTPUT CORRELATION
    # -------------------------------------------------------------------------
    
    async def correlate_tool_output(
        self,
        execution_id: str,
        tool_id: str,
        output: str,
        case_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Correlaciona output de herramienta con reglas.
        Extrae eventos del output y los procesa.
        """
        if not self.initialized:
            await self.initialize()
        
        # Convertir output a eventos según herramienta
        events = self._extract_events_from_output(tool_id, output)
        
        # Procesar eventos
        all_alerts = []
        for event in events:
            event["source"] = f"tool:{tool_id}"
            event["execution_id"] = execution_id
            alerts = await self.ingest_event(event, f"tool:{tool_id}", case_id)
            all_alerts.extend(alerts)
        
        return all_alerts
    
    def _extract_events_from_output(self, tool_id: str, output: str) -> List[Dict]:
        """Extrae eventos estructurados del output de herramientas"""
        events = []
        
        # Loki output - alertas
        if tool_id == "loki":
            for line in output.split("\n"):
                if "[ALERT]" in line or "[WARNING]" in line:
                    severity = "high" if "[ALERT]" in line else "medium"
                    events.append({
                        "event_type": "malware_detection",
                        "severity": severity,
                        "description": line,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # YARA output - matches
        elif tool_id == "yara":
            for line in output.split("\n"):
                if line.strip() and not line.startswith("0x"):
                    parts = line.split(" ", 1)
                    if len(parts) >= 2:
                        events.append({
                            "event_type": "yara_match",
                            "severity": "high",
                            "rule_name": parts[0],
                            "file_path": parts[1] if len(parts) > 1 else "",
                            "timestamp": datetime.utcnow().isoformat()
                        })
        
        # Nmap output - hosts/ports
        elif tool_id == "nmap":
            # Parsear hosts y puertos abiertos
            current_host = None
            for line in output.split("\n"):
                if "Nmap scan report for" in line:
                    parts = line.split(" ")
                    current_host = parts[-1].strip("()")
                elif "/tcp" in line or "/udp" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        port = parts[0].split("/")[0]
                        state = parts[1]
                        service = parts[2]
                        events.append({
                            "event_type": "open_port",
                            "host_ip": current_host,
                            "dest_port": port,
                            "port_state": state,
                            "service": service,
                            "timestamp": datetime.utcnow().isoformat()
                        })
        
        # Sparrow/Hawk output - signins
        elif tool_id in ["sparrow", "hawk"]:
            # Intentar parsear CSV o buscar patrones
            if "Suspicious" in output or "Risky" in output:
                events.append({
                    "event_type": "suspicious_signin",
                    "severity": "high",
                    "description": output[:500],
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return events
    
    # -------------------------------------------------------------------------
    # RULE MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def run_rule(
        self,
        rule_id: str,
        context_data: Dict
    ) -> Dict[str, Any]:
        """Ejecuta una regla específica contra datos de contexto"""
        if not self.initialized:
            await self.initialize()
        
        # Obtener regla
        rule = self.sigma_rules.get(rule_id) or self.heuristics.get(rule_id)
        if not rule:
            return {"matched": False, "error": "Rule not found"}
        
        # Crear evento desde contexto
        event = self._normalize_event(context_data, "manual_check")
        
        # Evaluar según tipo
        if rule_id.startswith("SIGMA"):
            matches = await self._evaluate_sigma_rules(event)
            matched = any(m["rule_id"] == rule_id for m in matches)
        else:
            matches = await self._evaluate_heuristics(event)
            matched = any(m["rule_id"] == rule_id for m in matches)
        
        return {
            "matched": matched,
            "rule_id": rule_id,
            "matches": matches
        }
    
    def get_rules(
        self,
        rule_type: Optional[str] = None,
        is_enabled: bool = True
    ) -> List[Dict]:
        """Obtiene reglas de correlación"""
        with get_db_context() as db:
            query = db.query(CorrelationRule)
            
            if rule_type:
                query = query.filter(CorrelationRule.rule_type == rule_type)
            if is_enabled:
                query = query.filter(CorrelationRule.is_enabled == True)
            
            rules = query.all()
            
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "type": r.rule_type,
                    "severity": r.severity,
                    "mitre_tactics": r.mitre_tactics,
                    "mitre_techniques": r.mitre_techniques,
                    "tags": r.tags,
                    "is_enabled": r.is_enabled,
                    "match_count": r.match_count,
                    "last_match": r.last_match_at.isoformat() if r.last_match_at else None
                }
                for r in rules
            ]
    
    async def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        """Habilita/deshabilita una regla"""
        with get_db_context() as db:
            rule = db.query(CorrelationRule).filter(
                CorrelationRule.id == rule_id
            ).first()
            
            if rule:
                rule.is_enabled = enabled
                db.commit()
                
                # Actualizar cache
                await self._load_rules_to_cache()
                
                return True
            
            return False
    
    def get_alerts(
        self,
        case_id: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Obtiene alertas de correlación"""
        with get_db_context() as db:
            query = db.query(CorrelationAlert)
            
            if case_id:
                query = query.filter(CorrelationAlert.case_id == case_id)
            if severity:
                query = query.filter(CorrelationAlert.severity == severity)
            if status:
                query = query.filter(CorrelationAlert.status == status)
            
            alerts = query.order_by(
                CorrelationAlert.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "id": a.id,
                    "rule_id": a.rule_id,
                    "severity": a.severity,
                    "title": a.title,
                    "description": a.description,
                    "mitre_tactics": a.mitre_tactics,
                    "mitre_techniques": a.mitre_techniques,
                    "status": a.status,
                    "created_at": a.created_at.isoformat()
                }
                for a in alerts
            ]


# =============================================================================
# SINGLETON
# =============================================================================

correlation_engine = CorrelationEngine()
