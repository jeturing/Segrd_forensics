"""
Dashboard routes for web interface - REAL DATA
v4.5.0: Legacy HTML dashboard removed, redirects to React frontend
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from api.services.dashboard_data import dashboard_data
from api.config import settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class CreateCaseRequest(BaseModel):
    case_id: str
    title: str
    priority: str = "medium"
    threat_type: Optional[str] = None
    description: Optional[str] = None


class AddIOCRequest(BaseModel):
    case_id: str
    ioc_type: str
    value: str
    severity: str
    source: str
    description: Optional[str] = None


@router.get("/")
async def dashboard_page(request: Request):
    """
    Redirect to React frontend dashboard.
    Legacy HTML dashboard removed in v4.5.0
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)


@router.get("/stats")
async def get_dashboard_stats():
    """Get dashboard statistics - REAL DATA"""
    
    # Obtener estadísticas reales de casos
    cases_stats = dashboard_data.get_cases_stats()
    
    # Obtener estadísticas de IOCs
    iocs_stats = dashboard_data.get_iocs_stats()
    
    # Obtener actividad reciente
    recent_activity = dashboard_data.get_recent_activity(limit=10)
    
    # Generar timeline de casos (últimos 30 días)
    dates = []
    counts = []
    if cases_stats["timeline"]["dates"]:
        dates = cases_stats["timeline"]["dates"]
        counts = cases_stats["timeline"]["counts"]
    else:
        # Si no hay datos, mostrar los últimos 30 días vacíos
        for i in range(30):
            date = (datetime.now() - timedelta(days=30-i)).strftime("%Y-%m-%d")
            dates.append(date)
            counts.append(0)
    
    # Preparar distribución de amenazas
    threat_types = list(cases_stats.get("by_threat", {}).keys()) or ["Sin datos"]
    threat_counts = list(cases_stats.get("by_threat", {}).values()) or [0]
    
    # Formatear actividad reciente
    formatted_activity = []
    for activity in recent_activity:
        action_type = activity.get("action_type", "unknown")
        icon_map = {
            "case_created": {"icon": "plus", "color": "blue"},
            "ioc_detected": {"icon": "bug", "color": "red"},
            "analysis_started": {"icon": "play", "color": "yellow"},
            "analysis_completed": {"icon": "check", "color": "green"},
            "case_closed": {"icon": "check-circle", "color": "green"}
        }
        icon_info = icon_map.get(action_type, {"icon": "info", "color": "gray"})
        
        formatted_activity.append({
            "type": action_type,
            "message": activity.get("message", ""),
            "timestamp": activity.get("timestamp", ""),
            "case_id": activity.get("case_id"),
            "icon": icon_info["icon"],
            "color": icon_info["color"]
        })
    
    return {
        "active_cases": cases_stats.get("active", 0),
        "closed_cases": cases_stats.get("closed", 0),
        "alerts": cases_stats.get("by_priority", {}).get("critical", 0) + cases_stats.get("by_priority", {}).get("high", 0),
        "iocs": iocs_stats.get("total", 0),
        "cases_timeline": {
            "dates": dates,
            "counts": counts
        },
        "threats": {
            "types": threat_types,
            "counts": threat_counts
        },
        "recent_activity": formatted_activity,
        "data_source": "real"  # Indicador de que son datos reales
    }


@router.get("/cases/list")
async def get_cases_list():
    """Get all cases - REAL DATA"""
    cases = dashboard_data.get_all_cases()
    return cases


@router.get("/cases/summary")
async def get_cases_summary():
    """Get summary of all cases - REAL DATA"""
    stats = dashboard_data.get_cases_stats()
    return {
        "total": stats.get("total", 0),
        "active": stats.get("active", 0),
        "closed": stats.get("closed", 0),
        "by_priority": stats.get("by_priority", {}),
        "by_status": stats.get("by_status", {}),
        "data_source": "real"
    }


@router.post("/cases/create")
async def create_new_case(request: CreateCaseRequest):
    """Create a new case - REAL"""
    result = dashboard_data.create_case(
        case_id=request.case_id,
        title=request.title,
        priority=request.priority,
        threat_type=request.threat_type,
        description=request.description
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/iocs/latest")
async def get_latest_iocs():
    """Get latest detected IOCs - REAL DATA"""
    iocs = dashboard_data.get_latest_iocs(limit=20)
    return iocs


@router.get("/iocs/stats")
async def get_iocs_statistics():
    """Get IOC statistics - REAL DATA"""
    return dashboard_data.get_iocs_stats()


@router.post("/iocs/add")
async def add_new_ioc(request: AddIOCRequest):
    """Add a new IOC - REAL"""
    result = dashboard_data.add_ioc(
        case_id=request.case_id,
        ioc_type=request.ioc_type,
        value=request.value,
        severity=request.severity,
        source=request.source,
        description=request.description
    )
    return result


@router.get("/tools/status")
async def get_tools_status():
    """Get status of forensic tools - REAL DATA"""
    return dashboard_data.get_tools_status()


@router.get("/m365/tenant-info")
async def get_m365_tenant_info():
    """Get Microsoft 365 tenant information - REAL DATA"""
    org = await dashboard_data.get_m365_organization()
    users = await dashboard_data.get_m365_users_count()
    
    if not org:
        return {
            "connected": False,
            "error": "No se pudo conectar a Microsoft 365. Verificar credenciales."
        }
    
    return {
        "connected": True,
        "tenant_id": dashboard_data.m365_tenant_id,
        "organization": org.get("display_name", "Desconocido"),
        "domains": org.get("verified_domains", []),
        "users": users,
        "data_source": "real"
    }


@router.post("/m365/sync")
async def sync_m365_data():
    """Sincronizar datos del tenant M365"""
    # Sincronizar info del tenant
    tenant_result = await dashboard_data.sync_tenant_info()
    
    # Sincronizar usuarios
    users_result = await dashboard_data.sync_m365_users()
    
    return {
        "tenant_sync": tenant_result,
        "users_sync": users_result,
        "data_source": "real"
    }


@router.get("/m365/users")
async def get_m365_users():
    """Obtener usuarios de M365 (desde cache local)"""
    users = dashboard_data.get_m365_users_from_cache()
    
    if not users:
        # Si no hay cache, sincronizar primero
        await dashboard_data.sync_m365_users()
        users = dashboard_data.get_m365_users_from_cache()
    
    return {
        "count": len(users),
        "users": users,
        "data_source": "real"
    }


@router.get("/m365/risky-signins")
async def get_risky_signins():
    """Get risky sign-ins from Azure AD - REAL DATA"""
    signins = await dashboard_data.get_m365_risky_signins(days=7)
    return {
        "count": len(signins),
        "signins": signins[:20],  # Limitar a 20
        "data_source": "real"
    }


@router.get("/m365/risky-users")
async def get_risky_users():
    """Get risky users from Azure AD Identity Protection - REAL DATA"""
    token = await dashboard_data.get_m365_token()
    if not token:
        return {"count": 0, "users": [], "error": "No se pudo obtener token"}
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/identityProtection/riskyUsers",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                users = response.json().get("value", [])
                return {
                    "count": len(users),
                    "users": users[:20],
                    "data_source": "real"
                }
            elif response.status_code == 403:
                return {"count": 0, "users": [], "error": "Requiere licencia Azure AD P2"}
    except Exception as e:
        return {"count": 0, "users": [], "error": str(e)}
    
    return {"count": 0, "users": []}


@router.get("/m365/audit-logs")
async def get_audit_logs(days: int = 7):
    """Get Azure AD audit logs - REAL DATA"""
    logs = await dashboard_data.get_m365_audit_logs(days=days)
    return {
        "count": len(logs),
        "logs": logs[:50],  # Limitar a 50
        "data_source": "real"
    }


@router.get("/evidence/stats")
async def get_evidence_stats():
    """Get evidence storage statistics - REAL DATA"""
    return dashboard_data.get_evidence_stats()


@router.get("/evidence/{case_id}")
async def get_case_evidence(case_id: str):
    """Get evidence for a specific case - REAL DATA"""
    evidence = dashboard_data.get_case_evidence(case_id)
    if not evidence.get("exists"):
        raise HTTPException(status_code=404, detail=f"No se encontró evidencia para el caso {case_id}")
    return evidence


@router.get("/activity/recent")
async def get_recent_activity(limit: int = 20):
    """Get recent activity - REAL DATA"""
    return dashboard_data.get_recent_activity(limit=limit)


@router.get("/threats/timeline")
async def get_threats_timeline():
    """Get threat detection timeline - REAL DATA"""
    # Obtener IOCs agrupados por hora
    iocs = dashboard_data.get_latest_iocs(limit=100)
    
    # Agrupar por hora
    timeline = {}
    for ioc in iocs:
        if ioc.get("detected_at"):
            hour = ioc["detected_at"][:13]  # YYYY-MM-DDTHH
            if hour not in timeline:
                timeline[hour] = {"total": 0, "by_type": {}}
            timeline[hour]["total"] += 1
            ioc_type = ioc.get("ioc_type", "unknown")
            timeline[hour]["by_type"][ioc_type] = timeline[hour]["by_type"].get(ioc_type, 0) + 1
    
    return {
        "timeline": timeline,
        "data_source": "real"
    }


@router.get("/endpoints/status")
async def get_endpoints_status():
    """Get status of monitored endpoints - REAL DATA from evidence"""
    evidence_stats = dashboard_data.get_evidence_stats()
    tools = dashboard_data.get_tools_status()
    
    return {
        "cases_with_evidence": evidence_stats.get("cases", 0),
        "total_evidence_files": evidence_stats.get("files", 0),
        "storage_used_mb": evidence_stats.get("total_size_mb", 0),
        "tools_available": sum(1 for t in tools.values() if t.get("installed")),
        "tools_total": len(tools),
        "data_source": "real"
    }


# ===================== DETAIL ENDPOINTS =====================

@router.get("/cases/{case_id}")
async def get_case_detail(case_id: str):
    """Get detailed information about a specific case"""
    case = dashboard_data.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Caso {case_id} no encontrado")
    
    # Obtener IOCs del caso (primero de DB, luego extraer de evidencia)
    iocs = dashboard_data.get_iocs_by_case(case_id)
    
    # Si no hay IOCs en DB, extraer de archivos de evidencia
    if not iocs:
        iocs = dashboard_data.extract_iocs_from_evidence(case_id)
    
    # Obtener evidencia del caso
    evidence = dashboard_data.get_case_evidence(case_id)
    
    # Obtener actividad del caso
    activity = dashboard_data.get_case_activity(case_id)
    
    return {
        "case": case,
        "iocs": iocs,
        "evidence": evidence,
        "activity": activity,
        "data_source": "real"
    }


@router.get("/iocs/{ioc_id}")
async def get_ioc_detail(ioc_id: int):
    """Get detailed information about a specific IOC"""
    ioc = dashboard_data.get_ioc_by_id(ioc_id)
    if not ioc:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} no encontrado")
    
    return {
        "ioc": ioc,
        "data_source": "real"
    }


@router.put("/cases/{case_id}/status")
async def update_case_status(case_id: str, status: str):
    """Update case status"""
    result = dashboard_data.update_case_status(case_id, status)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/cases/{case_id}")
async def delete_case(case_id: str):
    """Delete a case (soft delete)"""
    result = dashboard_data.delete_case(case_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/cases/{case_id}/notes")
async def add_case_note(case_id: str, note: str):
    """Add a note to a case"""
    result = dashboard_data.add_case_note(case_id, note)
    return result
