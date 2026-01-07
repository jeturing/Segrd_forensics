"""
Router para gestión de casos forenses
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import json
import os
from api.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Directorio para almacenar datos de casos (usa settings.EVIDENCE_DIR centralizado)
CASES_DATA_DIR = settings.EVIDENCE_DIR / "cases-data"
CASES_DATA_DIR.mkdir(parents=True, exist_ok=True)

class CaseStatus(BaseModel):
    """Estado de un caso"""
    case_id: str
    type: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    created_at: datetime
    updated_at: datetime
    progress_percentage: int
    current_step: Optional[str] = None
    estimated_completion: Optional[datetime] = None

class CaseReport(BaseModel):
    """Reporte completo de un caso"""
    case_id: str
    type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    metadata: dict
    results: Optional[dict] = None
    summary: Optional[dict] = None
    error: Optional[str] = None
    evidence_files: List[str] = []

@router.get("/{case_id}/status")
async def get_case_status(case_id: str):
    """
    Obtiene el estado actual de un caso con progreso detallado
    """
    from api.services.cases import get_case_status_detailed
    
    try:
        case_status = await get_case_status_detailed(case_id)
        
        if case_status:
            return case_status
        
        # Si no existe en memoria, retornar estado inicial
        return {
            "case_id": case_id,
            "type": "forensics",
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "progress_percentage": 0,
            "current_step": "En cola",
            "current_tool": None,
            "completed_tools": [],
            "scope": [],
            "evidence_count": 0,
            "error": None
        }
    except Exception as e:
        logger.error(f"❌ Error al obtener estado del caso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_id}/report", response_model=CaseReport)
async def get_case_report(case_id: str):
    """
    Obtiene el reporte completo de un caso
    
    Incluye todos los resultados, evidencia recolectada y recomendaciones
    """
    try:
        # TODO: Implementar consulta a base de datos
        return {
            "case_id": case_id,
            "type": "m365_forensics",
            "status": "completed",
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "metadata": {},
            "results": {},
            "summary": {},
            "evidence_files": []
        }
    except Exception as e:
        logger.error(f"❌ Error al obtener reporte: {e}")
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

@router.get("/", response_model=List[CaseStatus])
async def list_cases(
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    case_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Lista todos los casos con filtros opcionales
    """
    try:
        # TODO: Implementar consulta a base de datos
        return []
    except Exception as e:
        logger.error(f"❌ Error al listar casos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{case_id}")
async def delete_case(case_id: str):
    """
    Elimina un caso y toda su evidencia asociada
    
    ⚠️ ADVERTENCIA: Esta acción es irreversible
    """
    try:
        # TODO: Implementar eliminación de caso y evidencia
        logger.warning(f"🗑️ Eliminando caso {case_id}")
        return {
            "message": f"Case {case_id} deleted successfully",
            "deleted_at": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"❌ Error al eliminar caso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{case_id}/cancel")
async def cancel_case(case_id: str):
    """
    Cancela un caso en ejecución
    """
    try:
        # TODO: Implementar cancelación de tareas en background
        logger.info(f"⏸️ Cancelando caso {case_id}")
        return {
            "message": f"Case {case_id} cancelled",
            "cancelled_at": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"❌ Error al cancelar caso: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Threat Intelligence Integration
# =============================================================================

class ThreatIntelResult(BaseModel):
    """Modelo para resultados de Threat Intelligence"""
    analysis_type: str  # ip, email, domain, url
    target: str
    result: Dict[str, Any]
    threat_level: Optional[str] = None
    indicators: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}


class GraphNode(BaseModel):
    """Nodo para el grafo de ataque"""
    id: str
    label: str
    type: str
    threatLevel: Optional[str] = None
    riskScore: Optional[int] = None
    indicators: Optional[List[str]] = []
    recommendations: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[str] = None


@router.post("/{case_id}/threat-intel")
async def save_threat_intel_to_case(case_id: str, data: ThreatIntelResult):
    """
    Guarda resultados de Threat Intelligence en un caso
    
    Los resultados se almacenan y se crea un nodo para el grafo de ataque
    """
    try:
        # Ruta del archivo JSON del caso
        case_file = os.path.join(CASES_DATA_DIR, f"{case_id}_threat_intel.json")
        
        # Cargar datos existentes
        existing_data = []
        if os.path.exists(case_file):
            with open(case_file, 'r') as f:
                existing_data = json.load(f)
        
        # Crear nodo para el grafo
        node_id = f"threat_{data.analysis_type}_{data.target.replace('.', '_').replace('@', '_')}"
        
        # Determinar nivel de amenaza
        threat_level = data.threat_level or "medium"
        if data.analysis_type == "ip" and data.result.get("risk_score", 0) >= 60:
            threat_level = "critical" if data.result.get("risk_score", 0) >= 80 else "high"
        elif data.analysis_type == "email" and data.result.get("breaches_found", 0) >= 3:
            threat_level = "critical" if data.result.get("breaches_found", 0) >= 5 else "high"
        
        # Crear registro
        record = {
            "id": node_id,
            "case_id": case_id,
            "analysis_type": data.analysis_type,
            "target": data.target,
            "result": data.result,
            "threat_level": threat_level,
            "indicators": data.indicators or [],
            "metadata": data.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "graph_node": {
                "id": node_id,
                "label": data.target,
                "type": f"threat_{data.analysis_type}",
                "threatLevel": threat_level,
                "indicators": data.indicators or [],
                "metadata": data.metadata or {}
            }
        }
        
        existing_data.append(record)
        
        # Guardar
        with open(case_file, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        logger.info(f"✅ Threat Intel guardado en caso {case_id}: {data.target}")
        
        return {
            "success": True,
            "case_id": case_id,
            "analysis_id": node_id,
            "threat_level": threat_level,
            "message": "Análisis guardado y nodo creado para el grafo"
        }
    
    except Exception as e:
        logger.error(f"❌ Error guardando threat intel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/threat-intel")
async def get_case_threat_intel(case_id: str):
    """
    Obtiene todos los resultados de Threat Intelligence de un caso
    """
    try:
        case_file = os.path.join(CASES_DATA_DIR, f"{case_id}_threat_intel.json")
        
        if not os.path.exists(case_file):
            return {
                "case_id": case_id,
                "analyses": [],
                "total": 0
            }
        
        with open(case_file, 'r') as f:
            data = json.load(f)
        
        return {
            "case_id": case_id,
            "analyses": data,
            "total": len(data)
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo threat intel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/graph")
async def get_case_graph(case_id: str):
    """
    Obtiene el grafo de ataque completo del caso
    
    Incluye nodos base + nodos de Threat Intelligence + datos reales de M365
    """
    try:
        nodes = []
        edges = []
        
        # =====================================================
        # 1. CARGAR DATOS REALES DE ANÁLISIS M365
        # =====================================================
        # Buscar en múltiples ubicaciones posibles
        possible_paths = [
            settings.EVIDENCE_DIR / case_id / "m365_graph",
            Path("/home/hack/mcp-kali-forensics/forensics-evidence") / case_id / "m365_graph",
            Path("/home/hack/mcp-kali-forensics/evidence") / case_id / "m365_graph",
        ]
        
        m365_evidence_path = None
        for path in possible_paths:
            if path.exists():
                m365_evidence_path = path
                logger.info(f"📁 Encontrada evidencia M365 en: {path}")
                break
        
        if m365_evidence_path and m365_evidence_path.exists():
            # Cargar usuarios analizados
            users_file = m365_evidence_path / "users_analysis.json"
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users = json.load(f)
                for user in users:
                    node_id = f"user_{user.get('id', 'unknown')}"
                    nodes.append({
                        "id": node_id,
                        "label": user.get("upn") or user.get("mail") or user.get("displayName"),
                        "type": "user",
                        "displayName": user.get("displayName"),
                        "email": user.get("mail"),
                        "enabled": user.get("enabled"),
                        "created": user.get("created"),
                        "lastSignIn": user.get("lastSignIn"),
                        "threatLevel": "info"
                    })
            
            # Cargar OAuth consents (aplicaciones con acceso)
            oauth_file = m365_evidence_path / "oauth_consents.json"
            user_nodes_ids = [n["id"] for n in nodes if n.get("type") == "user"]
            
            if oauth_file.exists():
                with open(oauth_file, 'r') as f:
                    oauth_apps = json.load(f)
                
                # Permisos de alto riesgo para clasificación
                high_risk_scopes = [
                    "Mail.ReadWrite", "Mail.Send", "Files.ReadWrite.All", 
                    "Sites.FullControl.All", "Directory.ReadWrite.All",
                    "User.ReadWrite.All", "Application.ReadWrite.All",
                    "RoleManagement.ReadWrite.Directory", "MailboxSettings.ReadWrite",
                    "EWS.AccessAsUser.All", "IMAP.AccessAsUser.All", "SMTP.Send",
                    "offline_access", "user_impersonation"
                ]
                medium_risk_scopes = [
                    "Mail.Read", "Files.Read.All", "Sites.ReadWrite.All",
                    "Calendars.ReadWrite", "Contacts.ReadWrite", "People.Read.All"
                ]
                
                # Agrupar por app
                apps_seen = {}
                for consent in oauth_apps:
                    app_id = consent.get("clientId")
                    app_name = consent.get("appDisplayName") or f"App-{app_id[:8] if app_id else 'unknown'}"
                    
                    if app_id not in apps_seen:
                        apps_seen[app_id] = {
                            "scopes": set(),
                            "name": app_name,
                            "consent_type": consent.get("consentType"),
                            "principals": set(),
                            "resource_ids": set()
                        }
                    
                    scopes = consent.get("scope", "").split()
                    apps_seen[app_id]["scopes"].update(scopes)
                    if consent.get("principalId"):
                        apps_seen[app_id]["principals"].add(consent.get("principalId"))
                    if consent.get("resourceId"):
                        apps_seen[app_id]["resource_ids"].add(consent.get("resourceId"))
                
                # Crear nodos de apps OAuth con análisis de riesgo
                for app_id, app_data in apps_seen.items():
                    scopes_list = list(app_data["scopes"])
                    
                    # Calcular nivel de riesgo basado en permisos
                    high_risk_count = sum(1 for s in scopes_list if any(hr in s for hr in high_risk_scopes))
                    medium_risk_count = sum(1 for s in scopes_list if any(mr in s for mr in medium_risk_scopes))
                    
                    if high_risk_count >= 3 or "FullControl" in str(scopes_list):
                        threat_level = "critical"
                        risk_analysis = f"⚠️ CRÍTICO: {high_risk_count} permisos de alto riesgo detectados"
                    elif high_risk_count >= 1:
                        threat_level = "high"
                        risk_analysis = f"🔴 Alto riesgo: Permisos sensibles ({high_risk_count} críticos)"
                    elif medium_risk_count >= 2:
                        threat_level = "medium"
                        risk_analysis = f"🟡 Riesgo medio: {medium_risk_count} permisos moderados"
                    else:
                        threat_level = "low"
                        risk_analysis = "🟢 Bajo riesgo: Permisos básicos"
                    
                    # Clasificar tipo de app
                    app_category = "unknown"
                    app_lower = app_data["name"].lower()
                    if any(x in app_lower for x in ["mail", "email", "outlook", "gmail"]):
                        app_category = "email_client"
                    elif any(x in app_lower for x in ["sharepoint", "onedrive", "files"]):
                        app_category = "file_access"
                    elif any(x in app_lower for x in ["teams", "slack", "chat"]):
                        app_category = "communication"
                    elif any(x in app_lower for x in ["adobe", "pdf", "reader"]):
                        app_category = "document"
                    elif any(x in app_lower for x in ["ai", "copilot", "assistant"]):
                        app_category = "ai_tool"
                    
                    node_id = f"oauth_app_{app_id}"
                    nodes.append({
                        "id": node_id,
                        "label": app_data["name"],
                        "type": "process",
                        "scopes": scopes_list[:10],  # Limitar para UI
                        "scopesSummary": f"{len(scopes_list)} permisos",
                        "allScopes": scopes_list,
                        "consentType": app_data["consent_type"],
                        "threatLevel": threat_level,
                        "scopeCount": len(scopes_list),
                        "riskAnalysis": risk_analysis,
                        "category": app_category,
                        "highRiskCount": high_risk_count,
                        "isAllPrincipals": app_data["consent_type"] == "AllPrincipals"
                    })
                    
                    # CONECTAR app con TODOS los usuarios del tenant
                    for user_id in user_nodes_ids:
                        edges.append({
                            "source": user_id,
                            "target": node_id,
                            "type": "connected_to",
                            "label": f"OAuth ({threat_level})"
                        })
            
            # Cargar summary para crear nodo central del caso
            summary_file = m365_evidence_path / "investigation_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                
                risk_score = summary.get("summary", {}).get("risk_score", 0)
                threat_level = "critical" if risk_score > 70 else "high" if risk_score > 40 else "medium" if risk_score > 20 else "low"
                
                # Nodo central del tenant
                tenant_node_id = f"tenant_{case_id}"
                nodes.append({
                    "id": tenant_node_id,
                    "label": "Tenant M365",
                    "type": "domain",
                    "riskScore": risk_score,
                    "threatLevel": threat_level,
                    "collections": summary.get("collections", {}),
                    "criticalFindings": summary.get("summary", {}).get("critical_findings", {}),
                    "riskAnalysis": f"Score: {risk_score}/100 - {summary.get('summary', {}).get('critical_findings', {})}"
                })
                
                # Conectar usuarios al tenant
                for node in nodes:
                    if node.get("type") == "user":
                        edges.append({
                            "source": tenant_node_id,
                            "target": node["id"],
                            "type": "connected_to",
                            "label": "Member"
                        })
                
                # Conectar apps de alto riesgo directamente al tenant
                for node in nodes:
                    if node.get("type") == "process" and node.get("threatLevel") in ["critical", "high"]:
                        edges.append({
                            "source": tenant_node_id,
                            "target": node["id"],
                            "type": "connected_to",
                            "label": f"⚠️ {node.get('threatLevel', 'risk').upper()}"
                        })
            
            # Cargar sign-in logs
            signin_file = m365_evidence_path / "signin_logs.json"
            if signin_file.exists():
                with open(signin_file, 'r') as f:
                    signins = json.load(f)
                for signin in signins[:20]:  # Limitar a 20
                    ip = signin.get("ipAddress")
                    if ip:
                        node_id = f"ip_{ip.replace('.', '_')}"
                        if not any(n.get("id") == node_id for n in nodes):
                            nodes.append({
                                "id": node_id,
                                "label": ip,
                                "type": "ip",
                                "location": signin.get("location", {}),
                                "threatLevel": "medium" if signin.get("riskState") != "none" else "info"
                            })
                        # Conectar IP con usuario
                        user_upn = signin.get("userPrincipalName")
                        user_node = next((n for n in nodes if n.get("label") == user_upn), None)
                        if user_node:
                            edges.append({
                                "source": node_id,
                                "target": user_node["id"],
                                "type": "logged_in",
                                "label": "Sign-in"
                            })
        
        # =====================================================
        # 2. CARGAR NODOS DE THREAT INTELLIGENCE
        # =====================================================
        threat_intel_file = os.path.join(CASES_DATA_DIR, f"{case_id}_threat_intel.json")
        if os.path.exists(threat_intel_file):
            with open(threat_intel_file, 'r') as f:
                threat_data = json.load(f)
            
            for item in threat_data:
                if "graph_node" in item:
                    node = item["graph_node"]
                    node["timestamp"] = item.get("created_at")
                    node["riskScore"] = item.get("result", {}).get("risk_score", 0)
                    node["recommendations"] = item.get("result", {}).get("recommendations", [])
                    nodes.append(node)
        
        # =====================================================
        # 3. CARGAR GRAFO BASE MANUAL (si existe)
        # =====================================================
        base_graph_file = os.path.join(CASES_DATA_DIR, f"{case_id}_graph.json")
        if os.path.exists(base_graph_file):
            with open(base_graph_file, 'r') as f:
                base_graph = json.load(f)
            nodes.extend(base_graph.get("nodes", []))
            edges.extend(base_graph.get("edges", []))
        
        # =====================================================
        # 4. CREAR EDGES ENTRE THREAT INTEL Y NODOS BASE
        # =====================================================
        threat_nodes = [n for n in nodes if n.get("type", "").startswith("threat_")]
        base_nodes = [n for n in nodes if not n.get("type", "").startswith("threat_")]
        
        for threat_node in threat_nodes:
            threat_label = threat_node.get("label", "").lower()
            for base_node in base_nodes:
                base_label = base_node.get("label", "").lower()
                if threat_label and base_label and (threat_label in base_label or base_label in threat_label):
                    edges.append({
                        "source": base_node["id"],
                        "target": threat_node["id"],
                        "type": "threat_analysis",
                        "label": "Análisis de Amenaza"
                    })
        
        return {
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "threat_intel_nodes": len(threat_nodes),
                "base_nodes": len(base_nodes),
                "m365_nodes": len([n for n in nodes if n.get("type") in ["user", "process", "domain"]]),
                "total_edges": len(edges)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo grafo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{case_id}/graph/node")
async def add_graph_node(case_id: str, node: GraphNode):
    """
    Agrega un nodo manualmente al grafo del caso
    """
    try:
        graph_file = os.path.join(CASES_DATA_DIR, f"{case_id}_graph.json")
        
        # Cargar grafo existente
        graph = {"nodes": [], "edges": []}
        if os.path.exists(graph_file):
            with open(graph_file, 'r') as f:
                graph = json.load(f)
        
        # Agregar nodo
        node_dict = node.dict()
        node_dict["timestamp"] = datetime.utcnow().isoformat()
        graph["nodes"].append(node_dict)
        
        # Guardar
        with open(graph_file, 'w') as f:
            json.dump(graph, f, indent=2)
        
        return {
            "success": True,
            "node_id": node.id,
            "message": "Nodo agregado al grafo"
        }
    
    except Exception as e:
        logger.error(f"❌ Error agregando nodo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINT DE ENRIQUECIMIENTO CON IA
# =====================================================

class EnrichmentRequest(BaseModel):
    """Request para enriquecimiento con IA"""
    graph_data: Optional[Dict] = None
    focus_nodes: Optional[List[str]] = None  # IDs de nodos específicos a analizar
    analysis_type: str = "full"  # full, oauth, users, connections

@router.post("/{case_id}/graph/enrich")
async def enrich_graph_with_ai(case_id: str, request: EnrichmentRequest):
    """
    Enriquece el grafo de ataque con análisis de IA.
    
    Usa LLM para:
    - Clasificar riesgos de OAuth apps
    - Detectar patrones de ataque
    - Sugerir conexiones adicionales
    - Generar recomendaciones por nodo
    """
    try:
        from api.services.llm_provider import LLMProviderManager
        
        logger.info(f"🤖 Iniciando enriquecimiento IA para caso {case_id}")
        
        # Obtener grafo actual si no se proporciona
        if not request.graph_data:
            # Reutilizar lógica del endpoint de grafo
            graph_response = await get_case_graph(case_id)
            graph_data = graph_response
        else:
            graph_data = request.graph_data
        
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if not nodes:
            return {"success": False, "error": "No hay nodos para enriquecer"}
        
        # Inicializar LLM
        llm = LLMProviderManager()
        await llm.get_available_models()
        
        if not llm.active_model:
            logger.warning("⚠️ No hay modelo LLM disponible")
            return {
                "success": False,
                "error": "No hay modelo LLM disponible. Verifique LM Studio.",
                "fallback_enrichment": _generate_fallback_enrichment(nodes, edges)
            }
        
        logger.info(f"🎯 Usando modelo: {llm.active_model.id}")
        
        # Preparar contexto para el LLM
        oauth_apps = [n for n in nodes if n.get("type") == "process"]
        users = [n for n in nodes if n.get("type") == "user"]
        
        enrichment_results = {
            "case_id": case_id,
            "model_used": llm.active_model.id,
            "nodes_analyzed": len(nodes),
            "enriched_nodes": [],
            "new_connections": [],
            "attack_patterns": [],
            "risk_summary": {},
            "recommendations": []
        }
        
        # =====================================================
        # ANÁLISIS DE OAUTH APPS CON IA
        # =====================================================
        if oauth_apps and request.analysis_type in ["full", "oauth"]:
            oauth_summary = []
            for app in oauth_apps[:10]:  # Limitar a 10 apps para evitar tokens excesivos
                oauth_summary.append({
                    "name": app.get("label"),
                    "scopes": app.get("allScopes", app.get("scopes", []))[:15],
                    "consent_type": app.get("consentType"),
                    "current_threat_level": app.get("threatLevel"),
                    "high_risk_count": app.get("highRiskCount", 0)
                })
            
            oauth_prompt = f"""Analiza las siguientes aplicaciones OAuth de Microsoft 365 desde una perspectiva de seguridad:

APLICACIONES:
{json.dumps(oauth_summary, indent=2, ensure_ascii=False)}

USUARIOS AFECTADOS: {len(users)}

Proporciona un análisis JSON con la siguiente estructura:
{{
    "app_classifications": [
        {{
            "app_name": "nombre",
            "risk_level": "critical|high|medium|low",
            "justification": "razón del nivel de riesgo",
            "attack_potential": "descripción del potencial de ataque",
            "mitre_techniques": ["T1xxx", "T1yyy"],
            "recommended_action": "acción recomendada"
        }}
    ],
    "attack_patterns": [
        {{
            "pattern_name": "nombre del patrón",
            "description": "descripción",
            "apps_involved": ["app1", "app2"],
            "confidence": 0.0-1.0
        }}
    ],
    "overall_risk": "critical|high|medium|low",
    "executive_summary": "resumen ejecutivo en español",
    "immediate_actions": ["acción 1", "acción 2"]
}}

Responde SOLO con el JSON, sin texto adicional."""

            system_prompt = """Eres un analista de seguridad especializado en Microsoft 365 y OAuth.
Evalúa los permisos de aplicaciones, detecta patrones de ataque y clasifica riesgos.
Conoces técnicas como consent phishing, token theft, y abuso de APIs de Microsoft Graph.
Responde siempre en español."""

            try:
                result = await llm.generate(
                    prompt=oauth_prompt,
                    system_prompt=system_prompt,
                    max_tokens=2000,
                    temperature=0.3
                )
                
                if result.get("success"):
                    # LLM provider devuelve "content", no "text"
                    response_text = result.get("content", "") or result.get("text", "")
                    logger.info(f"📝 Respuesta LLM recibida: {len(response_text)} chars")
                    
                    # Intentar parsear JSON de la respuesta
                    try:
                        # Limpiar posibles marcadores de código
                        cleaned = response_text.strip()
                        if cleaned.startswith("```json"):
                            cleaned = cleaned[7:]
                        if cleaned.startswith("```"):
                            cleaned = cleaned[3:]
                        if cleaned.endswith("```"):
                            cleaned = cleaned[:-3]
                        
                        ai_analysis = json.loads(cleaned)
                        
                        # Actualizar clasificaciones de nodos
                        for classification in ai_analysis.get("app_classifications", []):
                            app_name = classification.get("app_name")
                            # Buscar nodo correspondiente
                            for node in nodes:
                                if node.get("label") == app_name or app_name in node.get("label", ""):
                                    node["ai_analysis"] = {
                                        "risk_level": classification.get("risk_level"),
                                        "justification": classification.get("justification"),
                                        "attack_potential": classification.get("attack_potential"),
                                        "mitre_techniques": classification.get("mitre_techniques", []),
                                        "recommended_action": classification.get("recommended_action")
                                    }
                                    enrichment_results["enriched_nodes"].append({
                                        "node_id": node.get("id"),
                                        "node_label": node.get("label"),
                                        "ai_analysis": node["ai_analysis"]
                                    })
                        
                        # Agregar patrones de ataque
                        enrichment_results["attack_patterns"] = ai_analysis.get("attack_patterns", [])
                        enrichment_results["risk_summary"] = {
                            "overall_risk": ai_analysis.get("overall_risk"),
                            "executive_summary": ai_analysis.get("executive_summary"),
                            "immediate_actions": ai_analysis.get("immediate_actions", [])
                        }
                        
                    except json.JSONDecodeError as je:
                        logger.warning(f"⚠️ No se pudo parsear JSON de IA: {je}")
                        enrichment_results["raw_analysis"] = response_text
                        
            except Exception as e:
                logger.error(f"❌ Error en análisis OAuth con IA: {e}")
        
        # =====================================================
        # DETECTAR CONEXIONES ADICIONALES
        # =====================================================
        if request.analysis_type in ["full", "connections"]:
            # Identificar apps con permisos similares que podrían estar relacionadas
            app_scopes = {}
            for app in oauth_apps:
                scopes = set(app.get("allScopes", app.get("scopes", [])))
                app_scopes[app.get("id")] = scopes
            
            # Buscar apps con scopes compartidos (posible cadena de ataque)
            for i, (app1_id, scopes1) in enumerate(app_scopes.items()):
                for app2_id, scopes2 in list(app_scopes.items())[i+1:]:
                    shared = scopes1.intersection(scopes2)
                    if len(shared) >= 3:  # 3+ scopes compartidos
                        # Verificar si ya existe conexión
                        existing = any(
                            (e["source"] == app1_id and e["target"] == app2_id) or
                            (e["source"] == app2_id and e["target"] == app1_id)
                            for e in edges
                        )
                        if not existing:
                            new_edge = {
                                "source": app1_id,
                                "target": app2_id,
                                "type": "related_scopes",
                                "label": f"🔗 {len(shared)} permisos comunes",
                                "ai_inferred": True,
                                "shared_scopes": list(shared)[:5]
                            }
                            edges.append(new_edge)
                            enrichment_results["new_connections"].append(new_edge)
        
        # =====================================================
        # GENERAR RECOMENDACIONES CONSOLIDADAS
        # =====================================================
        critical_apps = [n for n in nodes if n.get("ai_analysis", {}).get("risk_level") == "critical" or n.get("threatLevel") == "critical"]
        high_apps = [n for n in nodes if n.get("ai_analysis", {}).get("risk_level") == "high" or n.get("threatLevel") == "high"]
        
        recommendations = []
        if critical_apps:
            recommendations.append({
                "priority": "CRÍTICA",
                "action": f"Revocar acceso inmediato a {len(critical_apps)} aplicaciones de riesgo crítico",
                "apps": [a.get("label") for a in critical_apps[:5]]
            })
        if high_apps:
            recommendations.append({
                "priority": "ALTA",
                "action": f"Revisar y validar {len(high_apps)} aplicaciones de alto riesgo",
                "apps": [a.get("label") for a in high_apps[:5]]
            })
        if any(n.get("consentType") == "AllPrincipals" for n in oauth_apps):
            recommendations.append({
                "priority": "ALTA",
                "action": "Revisar permisos de aplicaciones con consentimiento a nivel de tenant (AllPrincipals)",
                "apps": [n.get("label") for n in oauth_apps if n.get("consentType") == "AllPrincipals"][:5]
            })
        
        enrichment_results["recommendations"] = recommendations
        
        # Cerrar sesión LLM
        await llm.close()
        
        return {
            "success": True,
            "enrichment": enrichment_results,
            "enriched_graph": {
                "nodes": nodes,
                "edges": edges
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error en enriquecimiento IA: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _generate_fallback_enrichment(nodes: List[Dict], edges: List[Dict]) -> Dict:
    """Genera enriquecimiento básico sin IA"""
    HIGH_RISK_SCOPES = {
        "Sites.FullControl.All", "Mail.ReadWrite", "Files.ReadWrite.All",
        "Directory.ReadWrite.All", "User.ReadWrite.All", "Mail.Send",
        "MailboxSettings.ReadWrite", "Calendars.ReadWrite"
    }
    
    critical_count = 0
    high_count = 0
    
    for node in nodes:
        if node.get("type") == "process":
            scopes = set(node.get("allScopes", node.get("scopes", [])))
            high_risk = scopes.intersection(HIGH_RISK_SCOPES)
            
            if len(high_risk) >= 4:
                node["threatLevel"] = "critical"
                critical_count += 1
            elif len(high_risk) >= 2:
                node["threatLevel"] = "high"
                high_count += 1
    
    return {
        "critical_apps": critical_count,
        "high_risk_apps": high_count,
        "analysis_type": "rule-based (no AI)",
        "recommendation": "Configure LM Studio para análisis con IA"
    }
