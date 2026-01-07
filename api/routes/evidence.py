"""
Evidence Routes - API endpoints para acceder a evidencias forenses
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json
import os
from api.config import settings

router = APIRouter(prefix="/forensics/evidence", tags=["Evidence"])

EVIDENCE_DIR = settings.EVIDENCE_DIR


@router.get("/{case_id}/summary")
async def get_evidence_summary(case_id: str):
    """
    Obtener resumen de evidencias de un caso
    """
    case_path = EVIDENCE_DIR / case_id
    
    if not case_path.exists():
        raise HTTPException(status_code=404, detail=f"No evidence found for case {case_id}")
    
    # Look for investigation summary
    summary_path = case_path / "m365_graph" / "investigation_summary.json"
    
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            return json.load(f)
    
    # Return basic info if no summary
    files = []
    for root, dirs, filenames in os.walk(case_path):
        for filename in filenames:
            filepath = Path(root) / filename
            files.append({
                "name": filename,
                "path": str(filepath.relative_to(case_path)),
                "size_kb": round(filepath.stat().st_size / 1024, 2)
            })
    
    return {
        "case_id": case_id,
        "files_count": len(files),
        "files": files
    }


@router.get("/{case_id}/m365")
async def get_m365_evidence(case_id: str):
    """
    Obtener evidencia de investigación M365 Graph
    """
    m365_path = EVIDENCE_DIR / case_id / "m365_graph"
    
    if not m365_path.exists():
        raise HTTPException(status_code=404, detail="No M365 evidence found")
    
    # Load investigation summary if exists
    summary_path = m365_path / "investigation_summary.json"
    summary = None
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            summary = json.load(f)
    
    # List all evidence files
    files = []
    for f in m365_path.glob("*.json"):
        files.append({
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 2)
        })
    
    return {
        "case_id": case_id,
        "evidence_type": "m365_graph",
        "summary": summary.get("summary") if summary else None,
        "files": files
    }


@router.get("/{case_id}/signins")
async def get_signins_evidence(case_id: str):
    """
    Obtener evidencia de sign-ins
    """
    # Try different possible file locations
    possible_paths = [
        EVIDENCE_DIR / case_id / "m365_graph" / "risky_signins.json",
        EVIDENCE_DIR / case_id / "m365_graph" / "signin_logs.json",
        EVIDENCE_DIR / case_id / "sparrow" / "signins.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("value", [])
    
    raise HTTPException(status_code=404, detail="No sign-ins evidence found")


@router.get("/{case_id}/users")
async def get_users_evidence(case_id: str):
    """
    Obtener evidencia de usuarios analizados
    """
    possible_paths = [
        EVIDENCE_DIR / case_id / "m365_graph" / "risky_users.json",
        EVIDENCE_DIR / case_id / "m365_graph" / "users_analysis.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("value", [])
    
    raise HTTPException(status_code=404, detail="No users evidence found")


@router.get("/{case_id}/oauth")
async def get_oauth_evidence(case_id: str):
    """
    Obtener evidencia de apps OAuth
    """
    possible_paths = [
        EVIDENCE_DIR / case_id / "m365_graph" / "oauth_consents.json",
        EVIDENCE_DIR / case_id / "sparrow" / "oauth_apps.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("value", [])
    
    raise HTTPException(status_code=404, detail="No OAuth evidence found")


@router.get("/{case_id}/rules")
async def get_rules_evidence(case_id: str):
    """
    Obtener evidencia de reglas de buzón
    """
    possible_paths = [
        EVIDENCE_DIR / case_id / "m365_graph" / "inbox_rules.json",
        EVIDENCE_DIR / case_id / "hawk" / "mailbox_rules.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("value", [])
    
    raise HTTPException(status_code=404, detail="No inbox rules evidence found")


@router.get("/{case_id}/raw")
async def get_raw_files(case_id: str):
    """
    Listar todos los archivos de evidencia raw
    """
    case_path = EVIDENCE_DIR / case_id
    
    if not case_path.exists():
        raise HTTPException(status_code=404, detail="No evidence found")
    
    files = []
    for root, dirs, filenames in os.walk(case_path):
        for filename in filenames:
            filepath = Path(root) / filename
            files.append({
                "name": filename,
                "path": str(filepath.relative_to(case_path)),
                "size_kb": round(filepath.stat().st_size / 1024, 2),
                "type": filepath.suffix.replace('.', '')
            })
    
    return files


@router.get("/{case_id}/file/{filename}")
async def get_evidence_file(case_id: str, filename: str):
    """
    Obtener contenido de un archivo de evidencia específico
    """
    case_path = EVIDENCE_DIR / case_id
    
    if not case_path.exists():
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Search for file in all subdirectories
    for path in case_path.rglob(filename):
        if path.is_file():
            # Return JSON content
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    return json.load(f)
            # Return text content
            elif path.suffix in ['.txt', '.csv', '.log']:
                with open(path, 'r') as f:
                    return {"content": f.read(), "type": path.suffix}
            else:
                return {"message": "Binary file - use download endpoint"}
    
    raise HTTPException(status_code=404, detail=f"File {filename} not found")


@router.get("/{case_id}/download/{filename}")
async def download_evidence_file(case_id: str, filename: str):
    """
    Descargar un archivo de evidencia
    """
    case_path = EVIDENCE_DIR / case_id
    
    if not case_path.exists():
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Search for file
    for path in case_path.rglob(filename):
        if path.is_file():
            return FileResponse(
                path=str(path),
                filename=filename,
                media_type='application/octet-stream'
            )
    
    raise HTTPException(status_code=404, detail=f"File {filename} not found")


@router.get("/{case_id}/timeline")
async def get_evidence_timeline(case_id: str):
    """
    Generar timeline de eventos basado en las evidencias
    """
    events = []
    
    # Load sign-ins
    signins_path = EVIDENCE_DIR / case_id / "m365_graph" / "risky_signins.json"
    if signins_path.exists():
        with open(signins_path, 'r') as f:
            signins = json.load(f)
            for s in signins[:50]:
                events.append({
                    "timestamp": s.get("createdDateTime"),
                    "type": "signin",
                    "severity": "high" if s.get("riskLevelDuringSignIn") == "high" else "medium",
                    "title": f"Sign-in from {s.get('ipAddress', 'unknown')}",
                    "description": f"User: {s.get('userPrincipalName', 'N/A')} | Location: {s.get('location', {}).get('city', 'Unknown')}"
                })
    
    # Load audit logs
    audit_path = EVIDENCE_DIR / case_id / "m365_graph" / "audit_logs.json"
    if audit_path.exists():
        with open(audit_path, 'r') as f:
            audits = json.load(f)
            for a in audits[:50]:
                events.append({
                    "timestamp": a.get("activityDateTime"),
                    "type": "audit",
                    "severity": "low",
                    "title": a.get("operationType", "Activity"),
                    "description": a.get("activityDisplayName", "")
                })
    
    # Sort by timestamp
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "case_id": case_id,
        "events_count": len(events),
        "events": events
    }
