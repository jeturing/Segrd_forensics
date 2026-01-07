"""
MCP Kali Forensics - Evidence Management Routes
API endpoints for uploading, importing, and managing external evidence
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging
from pathlib import Path

from api.database import get_db
from api.services.evidence_service import evidence_service
from api.services.command_logger import command_logger
from api.models.evidence_management import ExternalEvidence, CommandLog

router = APIRouter(prefix="/evidence-management", tags=["Evidence Management"])
logger = logging.getLogger(__name__)


# ==================== REQUEST MODELS ====================


class EvidenceUploadMetadata(BaseModel):
    """Metadata for evidence upload"""

    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    evidence_type: str = Field(
        ..., description="Type: disk_image, memory_dump, timeline, report, etc."
    )
    source_tool_name: Optional[str] = Field(
        None, description="Tool that generated this evidence"
    )
    collected_by: Optional[str] = None
    collected_from: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AssociateEvidenceRequest(BaseModel):
    """Request to associate evidence with entity"""

    entity_type: str = Field(
        ..., description="Entity type: case, agent, user, event, investigation"
    )
    entity_id: str = Field(..., description="Entity ID")
    association_type: Optional[str] = Field(
        None, description="primary, secondary, reference"
    )
    relevance: Optional[str] = Field(None, description="critical, high, medium, low")
    notes: Optional[str] = None
    created_by: Optional[str] = None


class BulkImportRequest(BaseModel):
    """Request for bulk evidence import"""

    tool_name: str = Field(..., description="axion, autopsy, or generic")
    file_paths: List[str] = Field(..., min_items=1)
    case_id: Optional[str] = None
    collected_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ==================== UPLOAD ENDPOINTS ====================


@router.post("/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    name: str = Form(...),
    evidence_type: str = Form(...),
    description: Optional[str] = Form(None),
    source_tool_name: Optional[str] = Form(None),
    collected_by: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string of tags
    metadata: Optional[str] = Form(None),  # JSON string of metadata
    db: Session = Depends(get_db),
):
    """
    Upload external evidence file.

    Supports:
    - Disk images (.e01, .raw, .dd, .img)
    - Memory dumps (.mem, .dmp, .vmem)
    - Reports (PDF, HTML, CSV, JSON)
    - Timelines (CSV, JSON)
    - Any forensic artifact

    The file will be:
    1. Stored securely with unique ID
    2. Hashed (MD5, SHA1, SHA256) for integrity
    3. Added to chain of custody
    4. Made available for association with cases/agents/users
    """
    try:
        # Parse tags and metadata if provided
        import json

        tags_list = json.loads(tags) if tags else None
        metadata_dict = json.loads(metadata) if metadata else None

        evidence = await evidence_service.upload_evidence(
            db=db,
            file=file,
            name=name,
            evidence_type=evidence_type,
            description=description,
            source_tool_name=source_tool_name,
            collected_by=collected_by,
            tags=tags_list,
            metadata=metadata_dict,
        )

        logger.info(f"✅ Evidence uploaded: {evidence.id}")

        return {
            "success": True,
            "evidence_id": evidence.id,
            "file_name": evidence.file_name,
            "file_size": evidence.file_size,
            "sha256": evidence.file_hash_sha256,
            "message": "Evidence uploaded successfully",
        }

    except Exception as e:
        logger.error(f"❌ Error uploading evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-upload")
async def bulk_upload_evidence(
    files: List[UploadFile] = File(...),
    case_id: Optional[str] = Form(None),
    evidence_type: str = Form("generic"),
    source_tool_name: Optional[str] = Form(None),
    collected_by: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload multiple evidence files at once.
    Useful for importing entire case directories.
    """
    results = []

    for file in files:
        try:
            evidence = await evidence_service.upload_evidence(
                db=db,
                file=file,
                name=file.filename,
                evidence_type=evidence_type,
                source_tool_name=source_tool_name,
                collected_by=collected_by,
            )

            # Associate with case if provided
            if case_id:
                evidence_service.associate_evidence(
                    db=db,
                    evidence_id=evidence.id,
                    entity_type="case",
                    entity_id=case_id,
                    association_type="primary",
                    created_by=collected_by,
                )

            results.append(
                {
                    "success": True,
                    "file_name": file.filename,
                    "evidence_id": evidence.id,
                }
            )

        except Exception as e:
            logger.error(f"❌ Error uploading {file.filename}: {e}")
            results.append(
                {"success": False, "file_name": file.filename, "error": str(e)}
            )

    success_count = sum(1 for r in results if r["success"])

    return {
        "total_files": len(files),
        "successful": success_count,
        "failed": len(files) - success_count,
        "results": results,
    }


# ==================== RETRIEVAL ENDPOINTS ====================


@router.get("/")
async def list_evidence(
    evidence_type: Optional[str] = Query(None),
    source_tool_name: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),  # Comma-separated tags
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all evidence with optional filters"""
    tags_list = tags.split(",") if tags else None

    evidences = evidence_service.list_evidence(
        db=db,
        evidence_type=evidence_type,
        source_tool_name=source_tool_name,
        tags=tags_list,
        limit=limit,
        offset=offset,
    )

    return {
        "total": len(evidences),
        "limit": limit,
        "offset": offset,
        "evidences": [e.to_dict() for e in evidences],
    }


@router.get("/{evidence_id}")
async def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """Get detailed information about specific evidence"""
    evidence = evidence_service.get_evidence(db, evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Get associations
    associations = evidence_service.get_evidence_associations(
        db=db, evidence_id=evidence_id
    )

    # Get command logs
    commands = command_logger.get_evidence_commands(db, evidence_id)

    return {
        "evidence": evidence.to_dict(),
        "associations": [a.to_dict() for a in associations],
        "commands_executed": len(commands),
        "custody_chain": evidence.custody_chain or [],
    }


@router.get("/{evidence_id}/download")
async def download_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """Download evidence file"""
    evidence = evidence_service.get_evidence(db, evidence_id)

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if not evidence.file_path or not Path(evidence.file_path).exists():
        raise HTTPException(status_code=404, detail="Evidence file not found")

    return FileResponse(
        path=evidence.file_path,
        filename=evidence.file_name,
        media_type="application/octet-stream",
    )


@router.get("/{evidence_id}/verify")
async def verify_evidence_integrity(evidence_id: str, db: Session = Depends(get_db)):
    """Verify evidence integrity by recalculating hash"""
    verified = evidence_service.verify_evidence_integrity(db, evidence_id)

    if verified:
        return {"verified": True, "message": "Evidence integrity verified successfully"}
    else:
        return {
            "verified": False,
            "message": "Evidence integrity check FAILED - hash mismatch",
        }


# ==================== ASSOCIATION ENDPOINTS ====================


@router.post("/{evidence_id}/associate")
async def associate_evidence(
    evidence_id: str, request: AssociateEvidenceRequest, db: Session = Depends(get_db)
):
    """
    Associate evidence with a case, agent, user, or event.
    Allows flexible linking for different investigation contexts.
    """
    try:
        association = evidence_service.associate_evidence(
            db=db,
            evidence_id=evidence_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            association_type=request.association_type,
            relevance=request.relevance,
            notes=request.notes,
            created_by=request.created_by,
        )

        return {
            "success": True,
            "association_id": association.id,
            "message": f"Evidence associated with {request.entity_type}:{request.entity_id}",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error associating evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{evidence_id}/associations")
async def get_evidence_associations_endpoint(
    evidence_id: str, db: Session = Depends(get_db)
):
    """Get all associations for specific evidence"""
    associations = evidence_service.get_evidence_associations(
        db=db, evidence_id=evidence_id
    )

    return {
        "evidence_id": evidence_id,
        "total_associations": len(associations),
        "associations": [a.to_dict() for a in associations],
    }


@router.get("/associations/{entity_type}/{entity_id}")
async def get_entity_evidence(
    entity_type: str, entity_id: str, db: Session = Depends(get_db)
):
    """
    Get all evidence associated with a specific entity.

    Examples:
    - GET /evidence-management/associations/case/CASE-2024-ABC
    - GET /evidence-management/associations/agent/AGT-001
    - GET /evidence-management/associations/user/analyst@company.com
    """
    associations = evidence_service.get_evidence_associations(
        db=db, entity_type=entity_type, entity_id=entity_id
    )

    # Get full evidence details
    evidence_ids = [a.evidence_id for a in associations]
    evidences = []
    for eid in evidence_ids:
        ev = evidence_service.get_evidence(db, eid)
        if ev:
            evidences.append(ev.to_dict())

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "total_evidence": len(evidences),
        "evidences": evidences,
    }


# ==================== COMMAND LOG ENDPOINTS ====================


@router.get("/{evidence_id}/commands")
async def get_evidence_commands(
    evidence_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get all commands executed on this evidence"""
    commands = command_logger.get_evidence_commands(db, evidence_id, limit=limit)

    return {
        "evidence_id": evidence_id,
        "total_commands": len(commands),
        "commands": [c.to_dict() for c in commands],
    }


@router.get("/commands/{command_id}")
async def get_command_details(command_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a command execution"""
    command = command_logger.get_command_log(db, command_id)

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    return command.to_detailed_dict()


@router.get("/case/{case_id}/commands")
async def get_case_commands(
    case_id: str,
    tool_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Get all commands executed for a case.
    Essential for traceability and report generation.
    """
    commands = command_logger.get_case_commands(
        db=db, case_id=case_id, tool_name=tool_name, status=status, limit=limit
    )

    return {
        "case_id": case_id,
        "total_commands": len(commands),
        "commands": [c.to_dict() for c in commands],
    }


# ==================== DELETION ENDPOINTS ====================


@router.delete("/{evidence_id}")
async def delete_evidence(
    evidence_id: str,
    permanent: bool = Query(False, description="Also delete file from storage"),
    db: Session = Depends(get_db),
):
    """
    Delete evidence record and optionally the file.

    WARNING: This action may be irreversible if permanent=True
    """
    deleted = evidence_service.delete_evidence(
        db=db, evidence_id=evidence_id, permanent=permanent
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Evidence not found")

    return {
        "success": True,
        "evidence_id": evidence_id,
        "permanent": permanent,
        "message": "Evidence deleted successfully",
    }


# ==================== STATISTICS ====================


@router.get("/stats/overview")
async def get_evidence_statistics(db: Session = Depends(get_db)):
    """Get overview statistics about evidence storage"""
    from sqlalchemy import func
    from api.models.evidence_management import EvidenceSource

    total_evidence = db.query(func.count(ExternalEvidence.id)).scalar()
    total_size = db.query(func.sum(ExternalEvidence.file_size)).scalar() or 0
    total_commands = db.query(func.count(CommandLog.id)).scalar()
    total_sources = db.query(func.count(EvidenceSource.id)).scalar()

    # Evidence by type
    by_type = (
        db.query(ExternalEvidence.evidence_type, func.count(ExternalEvidence.id))
        .group_by(ExternalEvidence.evidence_type)
        .all()
    )

    # Top tools
    top_tools = (
        db.query(EvidenceSource.tool_name, func.count(ExternalEvidence.id))
        .join(ExternalEvidence, EvidenceSource.id == ExternalEvidence.source_tool_id)
        .group_by(EvidenceSource.tool_name)
        .limit(10)
        .all()
    )

    return {
        "total_evidence": total_evidence,
        "total_size_bytes": total_size,
        "total_size_gb": round(total_size / (1024**3), 2),
        "total_commands": total_commands,
        "total_sources": total_sources,
        "evidence_by_type": [{"type": t[0], "count": t[1]} for t in by_type],
        "top_tools": [{"tool": t[0], "count": t[1]} for t in top_tools],
    }
