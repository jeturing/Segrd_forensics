"""
LLM Forensic Analyzer v4.5.0
============================
Pipeline avanzado de análisis forense con LLM para detección de patrones 
MITRE ATT&CK, explicación de cadenas de ataque y generación de reportes.

Features:
- Context Pack multi-evidencia
- Detección de tácticas/técnicas MITRE
- Análisis correlacional de grafo + timeline
- Generación de reporte ejecutivo y técnico
- Propuestas SOAR específicas
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from api.services.case_context_builder import CaseContextBuilder
from api.services.llm_provider import get_llm_manager
from api.config import settings

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Tipos de análisis disponibles"""
    QUICK = "quick"           # Clasificación rápida de severidad
    STANDARD = "standard"     # Análisis con recomendaciones
    DEEP = "deep"            # Análisis completo MITRE + reporte
    EXECUTIVE = "executive"   # Resumen ejecutivo


@dataclass
class MITRETechnique:
    """Técnica MITRE ATT&CK detectada"""
    technique_id: str        # T1566.001
    technique_name: str      # Spearphishing Attachment
    tactic: str             # Initial Access
    confidence: float       # 0.0 - 1.0
    evidence: List[str]     # Referencias a evidencia del caso
    description: str        # Explicación contextualizada


@dataclass
class AttackChain:
    """Cadena de ataque reconstruida"""
    chain_id: str
    start_time: Optional[str]
    end_time: Optional[str]
    stages: List[Dict[str, Any]]
    techniques: List[MITRETechnique]
    affected_entities: List[str]
    risk_score: int
    narrative: str


@dataclass
class SOARRecommendation:
    """Recomendación SOAR generada"""
    action_id: str
    action_type: str        # block, isolate, hunt, enrich, alert
    priority: str           # critical, high, medium, low
    target: str             # IP, user, endpoint, etc.
    playbook_id: Optional[str]
    reasoning: str
    automated: bool


@dataclass
class ForensicAnalysisResult:
    """Resultado completo del análisis forense"""
    case_id: str
    analysis_type: str
    generated_at: str
    
    # Resúmenes
    executive_summary: str
    technical_summary: str
    
    # MITRE ATT&CK
    attack_chain: Optional[AttackChain]
    techniques_detected: List[MITRETechnique]
    tactics_coverage: Dict[str, int]  # {tactic: count}
    
    # Risk Assessment
    overall_risk: str  # critical, high, medium, low
    risk_score: int
    risk_factors: List[str]
    
    # Recomendaciones
    soar_recommendations: List[SOARRecommendation]
    next_steps: List[str]
    
    # Metadata
    model_used: str
    context_tokens: int
    confidence_score: float


# MITRE ATT&CK Knowledge Base (subset for forensics)
MITRE_TACTICS = {
    "TA0001": "Initial Access",
    "TA0002": "Execution",
    "TA0003": "Persistence",
    "TA0004": "Privilege Escalation",
    "TA0005": "Defense Evasion",
    "TA0006": "Credential Access",
    "TA0007": "Discovery",
    "TA0008": "Lateral Movement",
    "TA0009": "Collection",
    "TA0010": "Exfiltration",
    "TA0011": "Command and Control",
    "TA0040": "Impact"
}

MITRE_TECHNIQUES_KEYWORDS = {
    "T1566": {"keywords": ["phishing", "spearphishing", "email", "attachment", "link"], "tactic": "TA0001"},
    "T1078": {"keywords": ["valid accounts", "credential", "login", "authentication"], "tactic": "TA0001"},
    "T1059": {"keywords": ["powershell", "cmd", "script", "command", "bash"], "tactic": "TA0002"},
    "T1053": {"keywords": ["scheduled task", "cron", "at job"], "tactic": "TA0003"},
    "T1547": {"keywords": ["registry", "startup", "run key", "boot"], "tactic": "TA0003"},
    "T1098": {"keywords": ["mailbox rule", "delegate", "forward", "permission"], "tactic": "TA0003"},
    "T1548": {"keywords": ["uac bypass", "sudo", "privilege"], "tactic": "TA0004"},
    "T1562": {"keywords": ["disable", "antivirus", "defender", "logging"], "tactic": "TA0005"},
    "T1110": {"keywords": ["brute force", "password spray", "credential stuff"], "tactic": "TA0006"},
    "T1003": {"keywords": ["dump", "lsass", "mimikatz", "credential"], "tactic": "TA0006"},
    "T1069": {"keywords": ["group", "discovery", "enum", "permission"], "tactic": "TA0007"},
    "T1021": {"keywords": ["rdp", "ssh", "remote", "lateral"], "tactic": "TA0008"},
    "T1114": {"keywords": ["email collection", "inbox", "mailbox"], "tactic": "TA0009"},
    "T1048": {"keywords": ["exfiltration", "upload", "transfer", "send"], "tactic": "TA0010"},
    "T1071": {"keywords": ["c2", "command control", "beacon", "callback"], "tactic": "TA0011"},
    "T1486": {"keywords": ["ransomware", "encrypt", "ransom"], "tactic": "TA0040"},
}


class LLMForensicAnalyzer:
    """
    Analizador forense avanzado con LLM
    """
    
    def __init__(self):
        self.context_builder = CaseContextBuilder()
        self._llm_manager = None
    
    async def _get_llm_manager(self):
        """Obtener LLM manager de forma lazy"""
        if self._llm_manager is None:
            self._llm_manager = await get_llm_manager()
        return self._llm_manager
    
    async def analyze_case(
        self,
        case_id: str,
        analysis_type: AnalysisType = AnalysisType.STANDARD,
        custom_prompt: Optional[str] = None
    ) -> ForensicAnalysisResult:
        """
        Ejecutar análisis forense completo con LLM
        
        Args:
            case_id: ID del caso a analizar
            analysis_type: Tipo de análisis (quick, standard, deep, executive)
            custom_prompt: Prompt adicional del usuario
            
        Returns:
            ForensicAnalysisResult con análisis completo
        """
        logger.info(f"🔬 Iniciando análisis forense LLM: {case_id} (tipo: {analysis_type})")
        
        try:
            # 1. Construir contexto del caso
            context = await self.context_builder.build_context(
                case_id,
                max_tokens=self._get_max_tokens(analysis_type)
            )
            
            # 2. Pre-análisis heurístico MITRE
            heuristic_techniques = self._detect_techniques_heuristic(context)
            
            # 3. Generar prompt según tipo de análisis
            prompt = self._build_analysis_prompt(
                context, 
                analysis_type, 
                heuristic_techniques,
                custom_prompt
            )
            
            # 4. Llamar al LLM
            llm_manager = await self._get_llm_manager()
            llm_response = await llm_manager.generate(
                prompt=prompt,
                max_tokens=self._get_response_tokens(analysis_type),
                temperature=0.3  # Bajo para análisis preciso
            )
            
            # 5. Parsear respuesta del LLM
            parsed_result = self._parse_llm_response(
                llm_response.text if hasattr(llm_response, 'text') else str(llm_response),
                case_id,
                analysis_type,
                heuristic_techniques
            )
            
            # 6. Agregar metadata
            parsed_result.model_used = llm_response.model if hasattr(llm_response, 'model') else "unknown"
            parsed_result.context_tokens = len(context) // 4  # Aproximación
            
            logger.info(f"✅ Análisis completado: {case_id} - Riesgo: {parsed_result.overall_risk}")
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"❌ Error en análisis forense: {e}", exc_info=True)
            # Retornar resultado fallback con análisis heurístico
            return self._create_fallback_result(case_id, analysis_type, str(e))
    
    def _get_max_tokens(self, analysis_type: AnalysisType) -> int:
        """Tokens máximos de contexto según tipo"""
        return {
            AnalysisType.QUICK: 4000,
            AnalysisType.STANDARD: 8000,
            AnalysisType.DEEP: 16000,
            AnalysisType.EXECUTIVE: 6000
        }.get(analysis_type, 8000)
    
    def _get_response_tokens(self, analysis_type: AnalysisType) -> int:
        """Tokens máximos de respuesta según tipo"""
        return {
            AnalysisType.QUICK: 500,
            AnalysisType.STANDARD: 1500,
            AnalysisType.DEEP: 3000,
            AnalysisType.EXECUTIVE: 1000
        }.get(analysis_type, 1500)
    
    def _detect_techniques_heuristic(self, context: str) -> List[MITRETechnique]:
        """
        Detección heurística de técnicas MITRE basada en keywords
        (Pre-análisis antes del LLM para enriquecer el prompt)
        """
        techniques = []
        context_lower = context.lower()
        
        for tech_id, info in MITRE_TECHNIQUES_KEYWORDS.items():
            matches = [kw for kw in info["keywords"] if kw in context_lower]
            if matches:
                confidence = min(len(matches) / len(info["keywords"]) + 0.3, 0.9)
                tactic_id = info["tactic"]
                
                techniques.append(MITRETechnique(
                    technique_id=tech_id,
                    technique_name=self._get_technique_name(tech_id),
                    tactic=MITRE_TACTICS.get(tactic_id, "Unknown"),
                    confidence=confidence,
                    evidence=[f"Keyword match: {', '.join(matches)}"],
                    description=f"Detected via keywords: {', '.join(matches)}"
                ))
        
        return techniques
    
    def _get_technique_name(self, tech_id: str) -> str:
        """Obtener nombre de técnica MITRE"""
        names = {
            "T1566": "Phishing",
            "T1078": "Valid Accounts",
            "T1059": "Command and Scripting Interpreter",
            "T1053": "Scheduled Task/Job",
            "T1547": "Boot or Logon Autostart Execution",
            "T1098": "Account Manipulation",
            "T1548": "Abuse Elevation Control Mechanism",
            "T1562": "Impair Defenses",
            "T1110": "Brute Force",
            "T1003": "OS Credential Dumping",
            "T1069": "Permission Groups Discovery",
            "T1021": "Remote Services",
            "T1114": "Email Collection",
            "T1048": "Exfiltration Over Alternative Protocol",
            "T1071": "Application Layer Protocol",
            "T1486": "Data Encrypted for Impact"
        }
        return names.get(tech_id, tech_id)
    
    def _build_analysis_prompt(
        self,
        context: str,
        analysis_type: AnalysisType,
        heuristic_techniques: List[MITRETechnique],
        custom_prompt: Optional[str]
    ) -> str:
        """Construir prompt de análisis según tipo"""
        
        # Base del prompt
        base_prompt = f"""You are an expert cybersecurity analyst specializing in incident response and digital forensics.
Analyze the following case evidence and provide a structured analysis.

=== CASE CONTEXT ===
{context}

=== PRE-DETECTED INDICATORS ===
MITRE Techniques potentially involved:
{self._format_heuristic_techniques(heuristic_techniques)}

"""
        
        # Instrucciones específicas por tipo
        if analysis_type == AnalysisType.QUICK:
            instructions = """
=== INSTRUCTIONS ===
Provide a QUICK assessment:
1. Overall risk level (critical/high/medium/low)
2. Top 3 concerns
3. Immediate action required (yes/no)

Format your response as JSON:
{"risk": "...", "concerns": [...], "immediate_action": true/false, "summary": "..."}
"""
        
        elif analysis_type == AnalysisType.EXECUTIVE:
            instructions = """
=== INSTRUCTIONS ===
Provide an EXECUTIVE SUMMARY suitable for management:
1. One-paragraph incident summary (non-technical)
2. Business impact assessment
3. Current status and containment
4. Recommended next steps

Format as clear prose, not technical jargon.
"""
        
        elif analysis_type == AnalysisType.DEEP:
            instructions = """
=== INSTRUCTIONS ===
Provide a DEEP forensic analysis:

1. ATTACK NARRATIVE
   - Reconstruct the attack timeline
   - Identify initial access vector
   - Map lateral movement
   
2. MITRE ATT&CK MAPPING
   - Confirm/refine pre-detected techniques
   - Identify additional techniques
   - Map complete kill chain
   
3. INDICATORS OF COMPROMISE
   - Extract all IOCs (IPs, domains, hashes, emails)
   - Categorize by confidence level
   
4. THREAT ACTOR ASSESSMENT
   - Known TTPs match
   - Attribution indicators (if any)
   - Sophistication level
   
5. RECOMMENDATIONS
   - Immediate containment actions
   - Eradication steps
   - Recovery procedures
   - Prevention measures

Format as structured JSON with sections.
"""
        
        else:  # STANDARD
            instructions = """
=== INSTRUCTIONS ===
Provide a STANDARD incident analysis:

1. EXECUTIVE SUMMARY (2-3 sentences)

2. TECHNICAL FINDINGS
   - Attack vector identified
   - Compromised assets
   - Data at risk

3. MITRE ATT&CK
   - Primary techniques used
   - Kill chain stage

4. RISK ASSESSMENT
   - Overall risk (critical/high/medium/low)
   - Risk factors

5. SOAR RECOMMENDATIONS
   - Top 3 automated actions to take
   - Priority order

Format as JSON:
{
  "executive_summary": "...",
  "technical_summary": "...",
  "techniques": [{"id": "...", "name": "...", "confidence": 0.X}],
  "risk": {"level": "...", "score": 0-100, "factors": [...]},
  "recommendations": [{"action": "...", "priority": "...", "target": "..."}]
}
"""
        
        full_prompt = base_prompt + instructions
        
        if custom_prompt:
            full_prompt += f"\n\n=== ADDITIONAL CONTEXT ===\n{custom_prompt}"
        
        return full_prompt
    
    def _format_heuristic_techniques(self, techniques: List[MITRETechnique]) -> str:
        """Formatear técnicas heurísticas para el prompt"""
        if not techniques:
            return "No techniques pre-detected."
        
        lines = []
        for t in techniques[:10]:  # Limitar a 10
            lines.append(f"- {t.technique_id} ({t.technique_name}): {t.tactic} [confidence: {t.confidence:.0%}]")
        return "\n".join(lines)
    
    def _parse_llm_response(
        self,
        response: str,
        case_id: str,
        analysis_type: AnalysisType,
        heuristic_techniques: List[MITRETechnique]
    ) -> ForensicAnalysisResult:
        """Parsear respuesta del LLM a estructura"""
        
        # Intentar parsear JSON
        json_data = None
        try:
            # Buscar JSON en la respuesta
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from LLM response, using text")
        
        # Extraer campos según tipo
        if json_data:
            executive_summary = json_data.get("executive_summary", json_data.get("summary", ""))
            technical_summary = json_data.get("technical_summary", "")
            risk_level = json_data.get("risk", {})
            if isinstance(risk_level, str):
                risk_level = {"level": risk_level, "score": self._risk_to_score(risk_level)}
            recommendations = json_data.get("recommendations", [])
            techniques_raw = json_data.get("techniques", [])
        else:
            # Fallback a texto
            executive_summary = response[:500] if len(response) > 500 else response
            technical_summary = response
            risk_level = {"level": "medium", "score": 50}
            recommendations = []
            techniques_raw = []
        
        # Convertir técnicas
        detected_techniques = heuristic_techniques.copy()
        for t in techniques_raw:
            if isinstance(t, dict) and t.get("id"):
                detected_techniques.append(MITRETechnique(
                    technique_id=t.get("id", ""),
                    technique_name=t.get("name", ""),
                    tactic=t.get("tactic", "Unknown"),
                    confidence=t.get("confidence", 0.7),
                    evidence=t.get("evidence", []),
                    description=t.get("description", "")
                ))
        
        # Convertir recomendaciones
        soar_recs = []
        for i, r in enumerate(recommendations):
            if isinstance(r, dict):
                soar_recs.append(SOARRecommendation(
                    action_id=f"REC-{i+1}",
                    action_type=r.get("type", "investigate"),
                    priority=r.get("priority", "medium"),
                    target=r.get("target", "N/A"),
                    playbook_id=r.get("playbook_id"),
                    reasoning=r.get("action", r.get("reasoning", "")),
                    automated=r.get("automated", False)
                ))
        
        # Calcular cobertura de tácticas
        tactics_coverage = {}
        for t in detected_techniques:
            tactic = t.tactic
            tactics_coverage[tactic] = tactics_coverage.get(tactic, 0) + 1
        
        return ForensicAnalysisResult(
            case_id=case_id,
            analysis_type=analysis_type.value,
            generated_at=datetime.utcnow().isoformat(),
            executive_summary=executive_summary,
            technical_summary=technical_summary,
            attack_chain=None,  # TODO: Implementar reconstrucción de cadena
            techniques_detected=detected_techniques,
            tactics_coverage=tactics_coverage,
            overall_risk=risk_level.get("level", "medium") if isinstance(risk_level, dict) else risk_level,
            risk_score=risk_level.get("score", 50) if isinstance(risk_level, dict) else 50,
            risk_factors=risk_level.get("factors", []) if isinstance(risk_level, dict) else [],
            soar_recommendations=soar_recs,
            next_steps=[r.reasoning for r in soar_recs[:5]],
            model_used="",
            context_tokens=0,
            confidence_score=0.75
        )
    
    def _risk_to_score(self, risk: str) -> int:
        """Convertir nivel de riesgo a score numérico"""
        return {
            "critical": 95,
            "high": 75,
            "medium": 50,
            "low": 25
        }.get(risk.lower(), 50)
    
    def _create_fallback_result(
        self,
        case_id: str,
        analysis_type: AnalysisType,
        error: str
    ) -> ForensicAnalysisResult:
        """Crear resultado fallback sin LLM"""
        return ForensicAnalysisResult(
            case_id=case_id,
            analysis_type=analysis_type.value,
            generated_at=datetime.utcnow().isoformat(),
            executive_summary=f"Análisis automático (sin IA): Error - {error}",
            technical_summary="El análisis LLM no está disponible. Revise manualmente la evidencia.",
            attack_chain=None,
            techniques_detected=[],
            tactics_coverage={},
            overall_risk="medium",
            risk_score=50,
            risk_factors=["LLM analysis unavailable"],
            soar_recommendations=[],
            next_steps=["Review evidence manually", "Check LLM service status"],
            model_used="fallback",
            context_tokens=0,
            confidence_score=0.3
        )
    
    def to_dict(self, result: ForensicAnalysisResult) -> Dict[str, Any]:
        """Convertir resultado a diccionario serializable"""
        return {
            "case_id": result.case_id,
            "analysis_type": result.analysis_type,
            "generated_at": result.generated_at,
            "executive_summary": result.executive_summary,
            "technical_summary": result.technical_summary,
            "attack_chain": asdict(result.attack_chain) if result.attack_chain else None,
            "techniques_detected": [asdict(t) for t in result.techniques_detected],
            "tactics_coverage": result.tactics_coverage,
            "overall_risk": result.overall_risk,
            "risk_score": result.risk_score,
            "risk_factors": result.risk_factors,
            "soar_recommendations": [asdict(r) for r in result.soar_recommendations],
            "next_steps": result.next_steps,
            "model_used": result.model_used,
            "context_tokens": result.context_tokens,
            "confidence_score": result.confidence_score
        }


# Singleton
llm_forensic_analyzer = LLMForensicAnalyzer()


async def analyze_case_deep(case_id: str) -> Dict[str, Any]:
    """Helper function para análisis profundo"""
    result = await llm_forensic_analyzer.analyze_case(case_id, AnalysisType.DEEP)
    return llm_forensic_analyzer.to_dict(result)


async def analyze_case_executive(case_id: str) -> Dict[str, Any]:
    """Helper function para resumen ejecutivo"""
    result = await llm_forensic_analyzer.analyze_case(case_id, AnalysisType.EXECUTIVE)
    return llm_forensic_analyzer.to_dict(result)
