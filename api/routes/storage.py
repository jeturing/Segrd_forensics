"""
MCP Kali Forensics - Storage API Routes
Endpoints para gestión de almacenamiento MinIO multi-tenant
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from pydantic import BaseModel

from api.services.minio_storage import get_minio_service, MinIOStorageService, MINIO_AVAILABLE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])


# =========================================================================
# SCHEMAS
# =========================================================================

class TenantCreate(BaseModel):
    tenant_id: str
    description: Optional[str] = None


class TenantInfo(BaseModel):
    tenant_id: str
    created: bool
    folders: dict


class EvidenceUploadResponse(BaseModel):
    success: bool
    object_name: Optional[str] = None
    etag: Optional[str] = None
    size: Optional[int] = None
    sha256: Optional[str] = None
    error: Optional[str] = None


class EvidenceInfo(BaseModel):
    name: str
    path: str
    size: int
    last_modified: Optional[str] = None


class StorageStats(BaseModel):
    total_size_bytes: int
    total_size_mb: float
    total_objects: int
    by_type: dict
    tenant_id: Optional[str] = None


class HealthStatus(BaseModel):
    status: str
    endpoint: str
    bucket: str
    bucket_exists: bool
    timestamp: str


# =========================================================================
# DEPENDENCY
# =========================================================================

def get_storage() -> MinIOStorageService:
    """Dependency para obtener servicio MinIO."""
    return get_minio_service()


# =========================================================================
# ENDPOINTS - HEALTH & STATS
# =========================================================================

@router.get("/health", response_model=HealthStatus)
async def storage_health(storage: MinIOStorageService = Depends(get_storage)):
    """Verifica el estado del almacenamiento MinIO."""
    return storage.health_check()


@router.get("/stats", response_model=StorageStats)
async def storage_stats(
    tenant_id: Optional[str] = Query(None, description="Filtrar por tenant"),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Obtiene estadísticas de almacenamiento."""
    return storage.get_storage_stats(tenant_id)


# =========================================================================
# ENDPOINTS - TENANT MANAGEMENT
# =========================================================================

@router.get("/tenants", response_model=List[str])
async def list_tenants(storage: MinIOStorageService = Depends(get_storage)):
    """Lista todos los tenants registrados."""
    return storage.list_tenants()


@router.post("/tenants", response_model=TenantInfo)
async def create_tenant(
    tenant: TenantCreate,
    storage: MinIOStorageService = Depends(get_storage)
):
    """Crea la estructura de carpetas para un nuevo tenant."""
    results = storage.create_tenant_structure(tenant.tenant_id)
    
    return TenantInfo(
        tenant_id=tenant.tenant_id,
        created=all(results.values()),
        folders=results
    )


# =========================================================================
# ENDPOINTS - EVIDENCE MANAGEMENT
# =========================================================================

@router.post("/tenants/{tenant_id}/cases/{case_id}/evidence", response_model=EvidenceUploadResponse)
async def upload_evidence(
    tenant_id: str,
    case_id: str,
    file: UploadFile = File(...),
    evidence_type: str = Query("evidence", description="Tipo: evidence, reports, artifacts, timeline"),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Sube un archivo de evidencia para un caso."""
    try:
        content = await file.read()
        result = storage.upload_evidence(
            tenant_id=tenant_id,
            case_id=case_id,
            file_data=content,
            file_name=file.filename,
            evidence_type=evidence_type,
        )
        
        return EvidenceUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}/cases/{case_id}/evidence", response_model=List[EvidenceInfo])
async def list_case_evidence(
    tenant_id: str,
    case_id: str,
    evidence_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Lista todos los archivos de evidencia de un caso."""
    evidence_list = storage.list_case_evidence(
        tenant_id=tenant_id,
        case_id=case_id,
        evidence_type=evidence_type,
    )
    
    return [EvidenceInfo(**e) for e in evidence_list]


@router.get("/tenants/{tenant_id}/cases/{case_id}/evidence/{file_name}")
async def download_evidence(
    tenant_id: str,
    case_id: str,
    file_name: str,
    evidence_type: str = Query("evidence"),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Descarga un archivo de evidencia."""
    from fastapi.responses import Response
    
    content = storage.download_evidence(
        tenant_id=tenant_id,
        case_id=case_id,
        file_name=file_name,
        evidence_type=evidence_type,
    )
    
    if content is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Determinar content-type
    import mimetypes
    content_type, _ = mimetypes.guess_type(file_name)
    
    return Response(
        content=content,
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_name}"}
    )


@router.delete("/tenants/{tenant_id}/cases/{case_id}/evidence/{file_name}")
async def delete_evidence(
    tenant_id: str,
    case_id: str,
    file_name: str,
    evidence_type: str = Query("evidence"),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Elimina un archivo de evidencia."""
    success = storage.delete_evidence(
        tenant_id=tenant_id,
        case_id=case_id,
        file_name=file_name,
        evidence_type=evidence_type,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Evidence not found or delete failed")
    
    return {"success": True, "message": f"Evidence '{file_name}' deleted"}


@router.get("/tenants/{tenant_id}/cases/{case_id}/evidence/{file_name}/url")
async def get_evidence_url(
    tenant_id: str,
    case_id: str,
    file_name: str,
    evidence_type: str = Query("evidence"),
    expires_hours: int = Query(1, ge=1, le=24),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Genera URL temporal pre-firmada para descarga."""
    object_path = f"{tenant_id}/cases/{case_id}/{evidence_type}/{file_name}"
    
    url = storage.get_presigned_url(object_path, expires_hours)
    
    if url is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return {
        "url": url,
        "expires_in_hours": expires_hours,
        "file_name": file_name,
    }


# =========================================================================
# ENDPOINTS - SCAN RESULTS
# =========================================================================

@router.get("/tenants/{tenant_id}/scans")
async def list_scans(
    tenant_id: str,
    scan_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    storage: MinIOStorageService = Depends(get_storage)
):
    """Lista todos los escaneos de un tenant."""
    return storage.list_scans(tenant_id, scan_type)


@router.get("/tenants/{tenant_id}/scans/{scan_type}/{scan_id}")
async def get_scan_results(
    tenant_id: str,
    scan_type: str,
    scan_id: str,
    storage: MinIOStorageService = Depends(get_storage)
):
    """Obtiene los resultados de un escaneo específico."""
    results = storage.get_scan_results(tenant_id, scan_type, scan_id)
    
    if results is None:
        raise HTTPException(status_code=404, detail="Scan results not found")
    
    return results
