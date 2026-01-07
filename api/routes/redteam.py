"""Red Team integration (HexStrike AI v4.6)
Persists engagements, runs and findings while proxying to HexStrike.
"""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.middleware.auth import verify_api_key
from api.models.redteam import RedTeamEngagement, RedTeamRun, RedTeamFinding
from api.services.hexstrike_client import hexstrike_client

router = APIRouter(prefix="/redteam", tags=["Red Team"], dependencies=[Depends(verify_api_key)])


class EngagementCreate(BaseModel):
    name: str
    tenant_id: str
    scope: List[str] = Field(default_factory=list)
    rules_of_engagement: List[str] = Field(default_factory=list)
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    analysis_type: str = "comprehensive"
    targets: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    preferred_tools: List[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    engagement_id: str
    target: str
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)


class CancelRequest(BaseModel):
    reason: Optional[str] = None


def _ensure_enabled():
    if not settings.HEXSTRIKE_ENABLED:
        raise HTTPException(status_code=503, detail="HexStrike integration is disabled. Set HEXSTRIKE_ENABLED=true")


def _serialize_engagement(item: RedTeamEngagement) -> Dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "tenant_id": item.tenant_id,
        "scope": item.scope or [],
        "rules_of_engagement": item.rules_of_engagement or [],
        "owner": item.owner,
        "tags": item.tags or [],
        "status": item.status,
        "plan": item.plan or {},
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _serialize_run(item: RedTeamRun) -> Dict[str, Any]:
    return {
        "run_id": item.id,
        "engagement_id": item.engagement_id,
        "target": item.target,
        "tool": item.tool,
        "params": item.params or {},
        "status": item.status,
        "hexstrike_pid": item.hexstrike_pid,
        "result": item.result or {},
        "error": item.error,
        "started_at": item.started_at.isoformat() if item.started_at else None,
        "finished_at": item.finished_at.isoformat() if item.finished_at else None,
    }


def _serialize_finding(item: RedTeamFinding) -> Dict[str, Any]:
    return {
        "id": item.id,
        "engagement_id": item.engagement_id,
        "run_id": item.run_id,
        "title": item.title,
        "severity": item.severity,
        "description": item.description,
        "category": item.category,
        "evidence": item.evidence or {},
        "tags": item.tags or [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _persist_findings(
    db: Session,
    findings: List[Dict[str, Any]],
    engagement_id: str,
    run_id: Optional[str]
) -> List[RedTeamFinding]:
    saved: List[RedTeamFinding] = []
    for raw in findings or []:
        finding = RedTeamFinding(
            id=RedTeamFinding.generate_id(),
            engagement_id=engagement_id,
            run_id=run_id,
            title=raw.get("title") or raw.get("name") or "Finding",
            severity=raw.get("severity") or "medium",
            description=raw.get("description"),
            category=raw.get("category"),
            evidence=raw.get("evidence") or {},
            tags=raw.get("tags") or [],
        )
        db.add(finding)
        saved.append(finding)
    return saved


@router.post("/engagements")
async def create_engagement(request: EngagementCreate, db: Session = Depends(get_db)):
    _ensure_enabled()
    engagement = RedTeamEngagement(
        id=RedTeamEngagement.generate_id(),
        name=request.name,
        tenant_id=request.tenant_id,
        scope=request.scope,
        rules_of_engagement=request.rules_of_engagement,
        owner=request.owner,
        tags=request.tags,
        status="active",
    )
    db.add(engagement)
    db.commit()
    db.refresh(engagement)
    return {"success": True, "engagement": _serialize_engagement(engagement)}


@router.post("/engagements/{engagement_id}/plan")
async def plan_engagement(engagement_id: str, request: PlanRequest, db: Session = Depends(get_db)):
    _ensure_enabled()
    engagement = db.query(RedTeamEngagement).filter(RedTeamEngagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    payload = {
        "analysis_type": request.analysis_type,
        "targets": request.targets,
        "constraints": request.constraints,
        "preferred_tools": request.preferred_tools,
        "engagement_id": engagement_id,
    }
    try:
        plan = await hexstrike_client.select_tools(payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HexStrike select-tools failed: {e}")

    engagement.plan = plan
    db.commit()
    db.refresh(engagement)
    return {"success": True, "engagement_id": engagement_id, "plan": engagement.plan}


@router.post("/runs")
async def create_run(request: RunRequest, db: Session = Depends(get_db)):
    _ensure_enabled()
    engagement = db.query(RedTeamEngagement).filter(RedTeamEngagement.id == request.engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    payload = {
        "engagement_id": request.engagement_id,
        "target": request.target,
        "tool": request.tool,
        "params": request.params,
    }
    try:
        result = await hexstrike_client.run_command(payload)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HexStrike command failed: {e}")

    run_id = result.get("run_id") or f"rt-run-{uuid.uuid4()}"
    run = RedTeamRun(
        id=run_id,
        engagement_id=request.engagement_id,
        target=request.target,
        tool=request.tool,
        params=request.params,
        status=result.get("status", "running"),
        hexstrike_pid=result.get("hexstrike_pid") or result.get("pid"),
        result=result,
    )

    db.add(run)
    saved_findings = _persist_findings(db, result.get("findings") or [], request.engagement_id, run_id)
    db.commit()
    db.refresh(run)
    for f in saved_findings:
        db.refresh(f)

    response = {"success": True, "run": _serialize_run(run)}
    if saved_findings:
        response["findings"] = [_serialize_finding(f) for f in saved_findings]
    return response


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db)):
    _ensure_enabled()
    run = db.query(RedTeamRun).filter(RedTeamRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    pid = run.hexstrike_pid
    status = None
    if pid:
        try:
            status = await hexstrike_client.get_process_status(str(pid))
            run.status = status.get("status", run.status)
            db.commit()
            db.refresh(run)
        except Exception:
            db.rollback()

    return {"success": True, "run": _serialize_run(run), "process": status}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, request: CancelRequest, db: Session = Depends(get_db)):
    _ensure_enabled()
    run = db.query(RedTeamRun).filter(RedTeamRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    pid = run.hexstrike_pid
    if not pid:
        raise HTTPException(status_code=400, detail="Run has no remote pid")

    try:
        result = await hexstrike_client.terminate_process(str(pid))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HexStrike terminate failed: {e}")

    run.status = "cancelling"
    db.commit()
    db.refresh(run)
    return {"success": True, "run_id": run_id, "result": result}


@router.get("/findings")
async def list_findings(engagement_id: Optional[str] = None, db: Session = Depends(get_db)):
    _ensure_enabled()
    query = db.query(RedTeamFinding)
    if engagement_id:
        query = query.filter(RedTeamFinding.engagement_id == engagement_id)
    findings = query.order_by(RedTeamFinding.created_at.desc()).all()
    return {"success": True, "findings": [_serialize_finding(f) for f in findings]}
