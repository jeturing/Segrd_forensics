"""
Graph Routes - API endpoints para grafos de incidentes y clasificación de casos
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

from api.services.graph_builder import graph_builder, CaseGraph

router = APIRouter(prefix="/forensics", tags=["Attack Graph"])


class CaseClassificationRequest(BaseModel):
    """Request para clasificar un caso"""
    classification: Literal["REAL", "FALSE_POSITIVE"]
    notes: Optional[str] = None


class ClassificationResponse(BaseModel):
    """Response de clasificación"""
    case_id: str
    classification: str
    classified_at: str
    notes: Optional[str] = None


# Store classifications in memory (should be persisted to DB)
case_classifications = {}


@router.get("/graph/{case_id}", response_model=CaseGraph)
async def get_case_graph(case_id: str):
    """
    Obtener el grafo de ataque para un caso específico
    
    Construye un grafo con:
    - Nodos: usuarios, IPs, dispositivos, IOCs, reglas de correo, apps OAuth
    - Aristas: relaciones entre entidades (LOGON_FROM, FORWARDED_TO, etc.)
    - Risk score: puntuación de riesgo 0-100
    
    El grafo se construye a partir de la evidencia forense en:
    {EVIDENCE_DIR}/{case_id}/
    """
    try:
        graph = graph_builder.build_case_graph(case_id)
        
        # Add classification if exists
        if case_id in case_classifications:
            graph.classification = case_classifications[case_id]["classification"]
        
        return graph
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error construyendo grafo: {str(e)}")


@router.post("/case/{case_id}/classify", response_model=ClassificationResponse)
async def classify_case(case_id: str, request: CaseClassificationRequest):
    """
    Clasificar un caso como Incidente Real o Falso Positivo
    
    Esta clasificación se usa para:
    - Reportes ejecutivos y técnicos
    - Métricas de efectividad
    - Entrenamiento de modelos de detección
    """
    case_classifications[case_id] = {
        "classification": request.classification,
        "notes": request.notes,
        "classified_at": datetime.utcnow().isoformat()
    }
    
    return ClassificationResponse(
        case_id=case_id,
        classification=request.classification,
        classified_at=case_classifications[case_id]["classified_at"],
        notes=request.notes
    )


@router.get("/case/{case_id}/classification")
async def get_case_classification(case_id: str):
    """Obtener la clasificación actual de un caso"""
    if case_id not in case_classifications:
        return {"case_id": case_id, "classification": None}
    
    return {
        "case_id": case_id,
        **case_classifications[case_id]
    }


@router.get("/report/executive/{case_id}")
async def get_executive_report(case_id: str):
    """
    Generar payload para reporte ejecutivo
    
    Incluye:
    - Resumen del incidente
    - Impacto empresarial
    - Recomendaciones de alto nivel
    - Clasificación (Real/FP)
    """
    try:
        graph = graph_builder.build_case_graph(case_id)
        classification = case_classifications.get(case_id, {})
        
        # Count by severity
        critical = sum(1 for n in graph.nodes if n.severity == "critical")
        high = sum(1 for n in graph.nodes if n.severity == "high")
        
        # Count by type
        users_affected = sum(1 for n in graph.nodes if n.type == "user")
        iocs_found = sum(1 for n in graph.nodes if n.type == "ioc")
        rules_found = sum(1 for n in graph.nodes if n.type == "mailbox_rule")
        
        # Determine impact level
        if graph.risk_score >= 75 or critical > 0:
            impact = "CRÍTICO"
        elif graph.risk_score >= 50 or high > 0:
            impact = "ALTO"
        elif graph.risk_score >= 25:
            impact = "MEDIO"
        else:
            impact = "BAJO"
        
        return {
            "report_type": "executive",
            "case_id": case_id,
            "generated_at": datetime.utcnow().isoformat(),
            "classification": classification.get("classification", "Sin clasificar"),
            "summary": {
                "risk_score": graph.risk_score,
                "impact_level": impact,
                "users_affected": users_affected,
                "iocs_detected": iocs_found,
                "malicious_rules": rules_found,
                "total_entities": len(graph.nodes),
                "total_relationships": len(graph.edges)
            },
            "key_findings": _generate_key_findings(graph),
            "recommendations": _generate_recommendations(graph),
            "timeline": {
                "detection_date": datetime.utcnow().isoformat(),
                "analysis_complete": datetime.utcnow().isoformat()
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/technical/{case_id}")
async def get_technical_report(case_id: str):
    """
    Generar payload para reporte técnico
    
    Incluye:
    - Detalle completo de IOCs
    - Timeline de eventos
    - Cadena de ataque
    - Artefactos recolectados
    """
    try:
        graph = graph_builder.build_case_graph(case_id)
        classification = case_classifications.get(case_id, {})
        
        # Group nodes by type
        nodes_by_type = {}
        for node in graph.nodes:
            if node.type not in nodes_by_type:
                nodes_by_type[node.type] = []
            nodes_by_type[node.type].append({
                "id": node.id,
                "label": node.label,
                "severity": node.severity,
                "metadata": node.metadata
            })
        
        # Extract IOCs
        iocs = []
        for node in graph.nodes:
            if node.type == "ioc":
                iocs.append({
                    "type": node.metadata.get("source", "unknown"),
                    "value": node.label,
                    "severity": node.severity,
                    "details": node.metadata
                })
            elif node.type == "ip" and node.severity in ["critical", "high"]:
                iocs.append({
                    "type": "ip",
                    "value": node.label,
                    "severity": node.severity,
                    "details": node.metadata
                })
        
        return {
            "report_type": "technical",
            "case_id": case_id,
            "generated_at": datetime.utcnow().isoformat(),
            "classification": classification.get("classification", "Sin clasificar"),
            "risk_assessment": {
                "score": graph.risk_score,
                "critical_findings": sum(1 for n in graph.nodes if n.severity == "critical"),
                "high_findings": sum(1 for n in graph.nodes if n.severity == "high"),
                "medium_findings": sum(1 for n in graph.nodes if n.severity == "medium"),
                "low_findings": sum(1 for n in graph.nodes if n.severity == "low")
            },
            "entities": nodes_by_type,
            "relationships": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.relation
                }
                for e in graph.edges
            ],
            "indicators_of_compromise": iocs,
            "attack_chain": _build_attack_chain(graph),
            "mitre_techniques": _map_to_mitre(graph),
            "evidence_artifacts": {
                "sparrow": f"~/forensics-evidence/{case_id}/sparrow/",
                "hawk": f"~/forensics-evidence/{case_id}/hawk/",
                "loki": f"~/forensics-evidence/{case_id}/loki/",
                "yara": f"~/forensics-evidence/{case_id}/yara/"
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _generate_key_findings(graph: CaseGraph) -> list:
    """Genera hallazgos clave para el reporte ejecutivo"""
    findings = []
    
    # Check for external forwarding
    forwarding_rules = [n for n in graph.nodes if n.type == "mailbox_rule" and n.severity == "critical"]
    if forwarding_rules:
        findings.append(f"Se detectaron {len(forwarding_rules)} reglas de reenvío externo sospechosas")
    
    # Check for risky OAuth apps
    risky_apps = [n for n in graph.nodes if n.type == "oauth_app" and n.severity in ["critical", "high"]]
    if risky_apps:
        findings.append(f"Se identificaron {len(risky_apps)} aplicaciones OAuth con permisos excesivos")
    
    # Check for suspicious IPs
    suspicious_ips = [n for n in graph.nodes if n.type == "ip" and n.severity in ["critical", "high"]]
    if suspicious_ips:
        findings.append(f"Se detectaron {len(suspicious_ips)} IPs sospechosas en los inicios de sesión")
    
    # Check for IOCs
    iocs = [n for n in graph.nodes if n.type == "ioc"]
    if iocs:
        findings.append(f"Se encontraron {len(iocs)} indicadores de compromiso (IOCs)")
    
    # Check for compromised users
    compromised_users = [n for n in graph.nodes if n.type == "user" and n.severity in ["critical", "high"]]
    if compromised_users:
        findings.append(f"Se identificaron {len(compromised_users)} usuarios potencialmente comprometidos")
    
    if not findings:
        findings.append("No se encontraron hallazgos críticos en este análisis")
    
    return findings


def _generate_recommendations(graph: CaseGraph) -> list:
    """Genera recomendaciones basadas en los hallazgos"""
    recommendations = []
    
    # Check severity levels
    critical_count = sum(1 for n in graph.nodes if n.severity == "critical")
    
    if critical_count > 0:
        recommendations.append("URGENTE: Iniciar proceso de contención inmediata")
        recommendations.append("Revocar sesiones activas de usuarios afectados")
        recommendations.append("Bloquear IPs sospechosas en el firewall")
    
    # Check for forwarding rules
    if any(n.type == "mailbox_rule" for n in graph.nodes):
        recommendations.append("Revisar y eliminar reglas de reenvío sospechosas")
        recommendations.append("Auditar todas las reglas de buzón de la organización")
    
    # Check for OAuth apps
    if any(n.type == "oauth_app" for n in graph.nodes):
        recommendations.append("Revocar consentimientos de aplicaciones sospechosas")
        recommendations.append("Implementar políticas de consentimiento de apps más restrictivas")
    
    # General recommendations
    recommendations.append("Habilitar autenticación multifactor (MFA) para todos los usuarios")
    recommendations.append("Revisar logs de auditoría de los últimos 90 días")
    recommendations.append("Actualizar contraseñas de usuarios afectados")
    
    return recommendations


def _build_attack_chain(graph: CaseGraph) -> list:
    """Construye la cadena de ataque basada en las relaciones del grafo"""
    chain = []
    
    # Look for common attack patterns
    # 1. Initial Access (suspicious login)
    suspicious_logins = [e for e in graph.edges if e.relation == "LOGON_FROM"]
    if suspicious_logins:
        chain.append({
            "phase": "Initial Access",
            "technique": "Valid Accounts / Phishing",
            "details": f"{len(suspicious_logins)} eventos de inicio de sesión detectados"
        })
    
    # 2. Persistence (mailbox rules)
    persistence = [e for e in graph.edges if e.relation == "CREATED"]
    if persistence:
        chain.append({
            "phase": "Persistence",
            "technique": "Email Forwarding Rule",
            "details": "Reglas de reenvío configuradas para exfiltración"
        })
    
    # 3. Credential Access (OAuth consent)
    oauth = [e for e in graph.edges if e.relation == "CONSENTED"]
    if oauth:
        chain.append({
            "phase": "Credential Access",
            "technique": "OAuth Application Abuse",
            "details": f"{len(oauth)} aplicaciones con acceso concedido"
        })
    
    # 4. Collection/Exfiltration
    iocs = [n for n in graph.nodes if n.type == "ioc"]
    if iocs:
        chain.append({
            "phase": "Collection/Exfiltration",
            "technique": "Data Collection",
            "details": f"{len(iocs)} artefactos maliciosos detectados"
        })
    
    return chain


def _map_to_mitre(graph: CaseGraph) -> list:
    """Mapea hallazgos a técnicas MITRE ATT&CK"""
    techniques = []
    
    # Check for different indicators and map to MITRE
    for node in graph.nodes:
        if node.type == "ip" and node.severity in ["critical", "high"]:
            techniques.append({
                "id": "T1078",
                "name": "Valid Accounts",
                "tactic": "Initial Access"
            })
        
        if node.type == "mailbox_rule":
            techniques.append({
                "id": "T1114.003",
                "name": "Email Forwarding Rule",
                "tactic": "Collection"
            })
        
        if node.type == "oauth_app":
            techniques.append({
                "id": "T1550.001",
                "name": "Application Access Token",
                "tactic": "Credential Access"
            })
        
        if node.type == "ioc":
            if "malware" in node.label.lower() or "yara" in node.label.lower():
                techniques.append({
                    "id": "T1059",
                    "name": "Command and Scripting Interpreter",
                    "tactic": "Execution"
                })
    
    # Remove duplicates
    seen = set()
    unique_techniques = []
    for t in techniques:
        if t["id"] not in seen:
            unique_techniques.append(t)
            seen.add(t["id"])
    
    return unique_techniques
