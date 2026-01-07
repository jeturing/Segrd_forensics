"""
SOAR Intelligence Engine v4.3
Motor de inteligencia para orquestación automatizada de respuesta.

Integra:
- LLM Studio (Jeturing AI Platform) con fallback automático
- Phi-4 Local para clasificación inteligente
- AgentQueue para orquestación de acciones
- Playbooks automáticos basados en patrones

Produce:
- Severidad normalizada con scoring
- Acciones sugeridas priorizadas
- Tags de inteligencia
- Prioridad recomendada
- Enriquecimiento automático
- IOC extraction
"""

from typing import Dict, List
from datetime import datetime
import logging
import asyncio
from enum import Enum

from api.services.agent_queue import agent_queue
from api.services.llm_local import llm_local

logger = logging.getLogger(__name__)


class ThreatCategory(str, Enum):
    CREDENTIAL_THEFT = "credential_theft"
    OAUTH_ABUSE = "oauth_abuse"
    MALICIOUS_FORWARDING = "malicious_forwarding"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFILTRATION = "data_exfiltration"
    RANSOMWARE = "ransomware"
    PERSISTENCE = "persistence"
    PHISHING = "phishing"
    BEC = "business_email_compromise"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    INVESTIGATE = "investigate"
    BLOCK = "block"
    QUARANTINE = "quarantine"
    RESET_CREDENTIALS = "reset_credentials"
    REVOKE_SESSIONS = "revoke_sessions"
    DISABLE_ACCOUNT = "disable_account"
    NOTIFY = "notify"
    ESCALATE = "escalate"
    DOCUMENT = "document"
    MONITOR = "monitor"


class SOARIntelligenceEngine:
    """
    Motor principal de SOAR Intelligence.
    
    Analiza hallazgos usando IA y produce recomendaciones
    accionables que pueden ejecutarse automáticamente.
    """
    
    # Mapeo de severidad a prioridad numérica
    PRIORITY_MAP = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4
    }
    
    # Acciones automáticas por severidad
    AUTO_ACTIONS = {
        "critical": [
            ActionType.REVOKE_SESSIONS,
            ActionType.DISABLE_ACCOUNT,
            ActionType.BLOCK,
            ActionType.ESCALATE,
            ActionType.NOTIFY
        ],
        "high": [
            ActionType.RESET_CREDENTIALS,
            ActionType.INVESTIGATE,
            ActionType.NOTIFY,
            ActionType.MONITOR
        ],
        "medium": [
            ActionType.INVESTIGATE,
            ActionType.MONITOR,
            ActionType.DOCUMENT
        ],
        "low": [
            ActionType.MONITOR,
            ActionType.DOCUMENT
        ]
    }
    
    # Patrones para categorización de amenazas
    THREAT_PATTERNS = {
        ThreatCategory.CREDENTIAL_THEFT: [
            "password spray", "brute force", "credential dump",
            "mimikatz", "token theft", "pass the hash"
        ],
        ThreatCategory.OAUTH_ABUSE: [
            "oauth", "consent", "app permission", "illicit consent",
            "malicious app", "scope abuse"
        ],
        ThreatCategory.MALICIOUS_FORWARDING: [
            "forward rule", "inbox rule", "delegate", "redirect",
            "mail flow", "external forward"
        ],
        ThreatCategory.PRIVILEGE_ESCALATION: [
            "admin role", "global admin", "privilege", "elevation",
            "role assignment", "pim"
        ],
        ThreatCategory.LATERAL_MOVEMENT: [
            "lateral", "rdp", "psexec", "wmi", "winrm",
            "remote execution", "pivot"
        ],
        ThreatCategory.DATA_EXFILTRATION: [
            "exfiltration", "data loss", "download", "export",
            "bulk access", "sharepoint sync"
        ],
        ThreatCategory.RANSOMWARE: [
            "ransomware", "encrypt", "ransom", "locker",
            "cryptolocker", ".locked"
        ],
        ThreatCategory.PHISHING: [
            "phishing", "spear phishing", "credential harvest",
            "fake login", "spoofed"
        ],
        ThreatCategory.BEC: [
            "bec", "ceo fraud", "wire transfer", "invoice fraud",
            "impersonation", "executive impersonation"
        ]
    }

    def __init__(self):
        self.llm = llm_local
        self.queue = agent_queue
        
    def _categorize_threat(self, findings: Dict) -> List[ThreatCategory]:
        """Categoriza la amenaza basándose en patrones"""
        text = str(findings).lower()
        categories = []
        
        for category, patterns in self.THREAT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    categories.append(category)
                    break
        
        if not categories:
            categories.append(ThreatCategory.UNKNOWN)
        
        return categories
    
    def _derive_tags(self, findings: Dict, severity: str, categories: List[ThreatCategory]) -> List[str]:
        """Deriva tags de inteligencia del hallazgo"""
        text = str(findings).lower()
        tags = []
        
        # Tags de categorías
        for cat in categories:
            tags.append(cat.value)
        
        # Tags de severidad
        if severity in ["critical", "high"]:
            tags.append("urgent")
        
        # Tags específicos basados en contenido
        if "azure" in text or "m365" in text or "microsoft" in text:
            tags.append("cloud")
            tags.append("m365")
        
        if "user" in text or "account" in text:
            tags.append("identity")
        
        if "token" in text:
            tags.append("token_abuse")
        
        if "impossible" in text and "travel" in text:
            tags.append("impossible_travel")
        
        if "new" in text and "device" in text:
            tags.append("new_device")
        
        if "mfa" in text.lower():
            tags.append("mfa_related")
        
        if "admin" in text:
            tags.append("admin_activity")
        
        return list(set(tags))  # Eliminar duplicados
    
    def _generate_action_plan(
        self,
        severity: str,
        categories: List[ThreatCategory],
        recommendations: List[str]
    ) -> List[Dict]:
        """Genera plan de acciones priorizado"""
        actions = []
        
        # Acciones automáticas según severidad
        auto_action_types = self.AUTO_ACTIONS.get(severity, [])
        
        for i, action_type in enumerate(auto_action_types):
            actions.append({
                "order": i + 1,
                "type": action_type.value,
                "priority": severity,
                "auto_execute": severity == "critical" and action_type in [
                    ActionType.REVOKE_SESSIONS,
                    ActionType.NOTIFY
                ],
                "description": self._get_action_description(action_type),
                "requires_approval": action_type in [
                    ActionType.DISABLE_ACCOUNT,
                    ActionType.BLOCK
                ]
            })
        
        # Añadir recomendaciones del LLM como acciones adicionales
        for i, rec in enumerate(recommendations):
            actions.append({
                "order": len(auto_action_types) + i + 1,
                "type": ActionType.INVESTIGATE.value,
                "priority": severity,
                "auto_execute": False,
                "description": rec,
                "requires_approval": True
            })
        
        return actions
    
    def _get_action_description(self, action_type: ActionType) -> str:
        """Obtiene descripción de una acción"""
        descriptions = {
            ActionType.INVESTIGATE: "Iniciar investigación detallada",
            ActionType.BLOCK: "Bloquear acceso/IP/aplicación sospechosa",
            ActionType.QUARANTINE: "Poner en cuarentena archivo/correo",
            ActionType.RESET_CREDENTIALS: "Resetear contraseña del usuario",
            ActionType.REVOKE_SESSIONS: "Revocar todas las sesiones activas",
            ActionType.DISABLE_ACCOUNT: "Deshabilitar cuenta temporalmente",
            ActionType.NOTIFY: "Notificar al equipo de seguridad",
            ActionType.ESCALATE: "Escalar a CISO/Purple Team",
            ActionType.DOCUMENT: "Documentar hallazgo en el caso",
            ActionType.MONITOR: "Configurar monitoreo activo"
        }
        return descriptions.get(action_type, "Acción no especificada")
    
    def _calculate_risk_score(
        self,
        severity: str,
        categories: List[ThreatCategory],
        confidence: float,
        ioc_count: int
    ) -> int:
        """Calcula score de riesgo compuesto (0-100)"""
        base_scores = {
            "critical": 90,
            "high": 70,
            "medium": 50,
            "low": 25
        }
        
        score = base_scores.get(severity, 40)
        
        # Ajustar por número de categorías de amenaza
        score += min(len(categories) * 3, 10)
        
        # Ajustar por confianza del LLM
        score = int(score * (confidence / 100))
        
        # Bonus por IOCs encontrados
        score += min(ioc_count * 2, 10)
        
        return min(max(score, 0), 100)
    
    def analyze_findings(self, findings: Dict) -> Dict:
        """
        Analiza hallazgos usando Phi-4 y produce:
        - Severidad normalizada
        - Acciones recomendadas priorizadas
        - Tags de inteligencia
        - Prioridad recomendada
        - Plan de respuesta
        
        Args:
            findings: Diccionario con hallazgos a analizar
            
        Returns:
            Dict con análisis completo y recomendaciones
        """
        # Análisis con LLM
        ai_result = self.llm.analyze(findings)
        
        severity = ai_result["classification"]
        confidence = ai_result.get("confidence_score", 50.0)
        iocs = ai_result.get("iocs_extracted", [])
        recommendations = ai_result["recommendations"]["actions"]
        
        # Categorizar amenaza
        categories = self._categorize_threat(findings)
        
        # Derivar tags
        tags = self._derive_tags(findings, severity, categories)
        
        # Generar plan de acciones
        action_plan = self._generate_action_plan(severity, categories, recommendations)
        
        # Calcular risk score
        risk_score = self._calculate_risk_score(
            severity, categories, confidence, len(iocs)
        )
        
        enriched = {
            "severity": severity,
            "priority": self.PRIORITY_MAP.get(severity, 4),
            "risk_score": risk_score,
            "confidence_score": confidence,
            "threat_categories": [c.value for c in categories],
            "tags": tags,
            "iocs_extracted": iocs,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "justification": ai_result["recommendations"]["justification"],
            "analyzed_at": datetime.utcnow().isoformat(),
            "llm_used": ai_result.get("llm_used", False)
        }
        
        logger.info(
            f"🧠 SOAR Analysis: severity={severity}, risk_score={risk_score}, "
            f"categories={[c.value for c in categories]}"
        )
        
        return enriched
    
    async def analyze_findings_async(self, findings: Dict) -> Dict:
        """Versión asíncrona del análisis (usa LLM real si está disponible)"""
        ai_result = await self.llm.analyze_async(findings)
        
        severity = ai_result["classification"]
        confidence = ai_result.get("confidence_score", 50.0)
        iocs = ai_result.get("iocs_extracted", [])
        recommendations = ai_result.get("recommendations", {}).get("actions", [])
        
        categories = self._categorize_threat(findings)
        tags = self._derive_tags(findings, severity, categories)
        action_plan = self._generate_action_plan(severity, categories, recommendations)
        risk_score = self._calculate_risk_score(severity, categories, confidence, len(iocs))
        
        return {
            "severity": severity,
            "priority": self.PRIORITY_MAP.get(severity, 4),
            "risk_score": risk_score,
            "confidence_score": confidence,
            "threat_categories": [c.value for c in categories],
            "tags": tags,
            "iocs_extracted": iocs,
            "recommendations": recommendations,
            "action_plan": action_plan,
            "justification": ai_result.get("recommendations", {}).get(
                "justification", "Análisis automático"
            ),
            "analyzed_at": datetime.utcnow().isoformat(),
            "llm_used": ai_result.get("llm_used", False)
        }
    
    async def queue_response_actions(
        self,
        analysis: Dict,
        case_id: str,
        auto_execute_critical: bool = False
    ) -> List[str]:
        """
        Encola acciones de respuesta basadas en el análisis.
        
        Args:
            analysis: Resultado de analyze_findings
            case_id: ID del caso
            auto_execute_critical: Si es True, ejecuta acciones críticas automáticamente
            
        Returns:
            Lista de task_ids encolados
        """
        task_ids = []
        
        for action in analysis.get("action_plan", []):
            if action.get("auto_execute") and auto_execute_critical:
                # Encolar para ejecución automática
                task_id = await self.queue.add_task(
                    task_func=self._execute_action,
                    agent_type="blue",  # Acciones defensivas van a Blue Team
                    priority="critical" if analysis["severity"] == "critical" else "high",
                    case_id=case_id,
                    action=action
                )
                task_ids.append(task_id)
                logger.info(f"🤖 Auto-ejecutando acción: {action['type']}")
            else:
                # Solo registrar para aprobación manual
                logger.info(f"📋 Acción pendiente de aprobación: {action['type']}")
        
        return task_ids
    
    async def _execute_action(self, action: Dict) -> Dict:
        """
        Ejecuta una acción de respuesta.
        NOTA: Esta es una implementación stub. En producción,
        se conectaría a APIs reales (Azure AD, Exchange, etc.)
        """
        action_type = action.get("type")
        
        # Stub: log y retornar éxito
        logger.info(f"⚡ Ejecutando acción {action_type}: {action.get('description')}")
        
        # Simular ejecución
        await asyncio.sleep(0.5)
        
        return {
            "action_type": action_type,
            "status": "completed",
            "executed_at": datetime.utcnow().isoformat(),
            "message": f"Acción {action_type} ejecutada exitosamente (stub)"
        }
    
    async def enrich_from_investigation(
        self,
        investigation_id: str,
        findings: List[Dict]
    ) -> Dict:
        """
        Enriquece múltiples hallazgos de una investigación.
        
        Args:
            investigation_id: ID de la investigación
            findings: Lista de hallazgos a analizar
            
        Returns:
            Resumen consolidado con todos los análisis
        """
        analyses = []
        all_iocs = []
        all_tags = set()
        max_severity = "low"
        total_risk = 0
        
        for finding in findings:
            analysis = await self.analyze_findings_async(finding)
            analyses.append(analysis)
            
            all_iocs.extend(analysis.get("iocs_extracted", []))
            all_tags.update(analysis.get("tags", []))
            total_risk += analysis.get("risk_score", 0)
            
            # Track max severity
            severity_order = ["low", "medium", "high", "critical"]
            if severity_order.index(analysis["severity"]) > severity_order.index(max_severity):
                max_severity = analysis["severity"]
        
        # Consolidar
        avg_risk = total_risk // len(findings) if findings else 0
        
        return {
            "investigation_id": investigation_id,
            "findings_analyzed": len(findings),
            "max_severity": max_severity,
            "average_risk_score": avg_risk,
            "total_iocs": len(all_iocs),
            "unique_iocs": len(set(ioc["value"] for ioc in all_iocs)),
            "all_tags": list(all_tags),
            "individual_analyses": analyses,
            "consolidated_at": datetime.utcnow().isoformat()
        }


# Instancia singleton
soar_engine = SOARIntelligenceEngine()
