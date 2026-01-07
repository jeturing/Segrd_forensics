"""
MCP Kali Forensics - MinIO Storage Service
Multi-tenant evidence storage with S3-compatible API

Estructura de almacenamiento:
    forensics-evidence/
    ├── {tenant_id}/
    │   ├── cases/{case_id}/
    │   │   ├── evidence/
    │   │   ├── reports/
    │   │   └── artifacts/
    │   ├── scans/{scan_type}/
    │   ├── m365_graph/
    │   ├── threat_intel/
    │   ├── pentest/
    │   └── exports/
    └── _system/
        ├── templates/
        └── shared-iocs/
"""

import io
import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, BinaryIO, Union

# Import minio with graceful fallback
try:
    from minio import Minio
    from minio.error import S3Error
    from minio.commonconfig import ENABLED
    from minio.versioningconfig import VersioningConfig
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    Minio = None
    S3Error = Exception
    ENABLED = None
    VersioningConfig = None
    logging.getLogger(__name__).warning("minio package not installed - MinIO storage disabled")

from api.config import settings

logger = logging.getLogger(__name__)


class MinIOStorageService:
    """
    Servicio de almacenamiento MinIO para evidencias forenses multi-tenant.
    Implementa S3-compatible API con estructura jerárquica por tenant.
    """

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        secure: bool = False,
    ):
        """Inicializa el cliente MinIO."""
        if not MINIO_AVAILABLE:
            logger.warning("⚠️ MinIO package not available - storage service disabled")
            self.client = None
            self.enabled = False
            return
            
        self.enabled = True
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or settings.MINIO_BUCKET
        self.secure = secure if secure is not None else settings.MINIO_SECURE
        
        # Remover protocolo si está presente
        if self.endpoint.startswith("http://"):
            self.endpoint = self.endpoint.replace("http://", "")
        elif self.endpoint.startswith("https://"):
            self.endpoint = self.endpoint.replace("https://", "")
            self.secure = True
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        
        logger.info(f"🗄️ MinIO client initialized: {self.endpoint}, bucket: {self.bucket_name}")

    # =========================================================================
    # BUCKET MANAGEMENT
    # =========================================================================

    def ensure_bucket_exists(self) -> bool:
        """Verifica y crea el bucket principal si no existe."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"✅ Bucket '{self.bucket_name}' created")
                
                # Habilitar versionado para integridad de evidencias
                self.client.set_bucket_versioning(
                    self.bucket_name,
                    VersioningConfig(ENABLED)
                )
                logger.info(f"📚 Versioning enabled for '{self.bucket_name}'")
            else:
                logger.info(f"✅ Bucket '{self.bucket_name}' already exists")
            
            return True
            
        except S3Error as e:
            logger.error(f"❌ MinIO bucket error: {e}")
            return False

    def create_tenant_structure(self, tenant_id: str) -> Dict[str, bool]:
        """Crea la estructura de carpetas para un nuevo tenant."""
        folders = [
            f"{tenant_id}/cases/",
            f"{tenant_id}/scans/",
            f"{tenant_id}/exports/",
            f"{tenant_id}/m365_graph/",
            f"{tenant_id}/threat_intel/",
            f"{tenant_id}/pentest/",
        ]
        
        results = {}
        
        for folder in folders:
            try:
                self.client.put_object(
                    self.bucket_name,
                    f"{folder}.keep",
                    io.BytesIO(b""),
                    0,
                    content_type="application/x-empty"
                )
                results[folder] = True
                logger.info(f"📁 Created folder structure: {folder}")
            except S3Error as e:
                results[folder] = False
                logger.error(f"❌ Failed to create {folder}: {e}")
        
        return results

    def list_tenants(self) -> List[str]:
        """Lista todos los tenants registrados en el bucket."""
        try:
            tenants = set()
            objects = self.client.list_objects(self.bucket_name, prefix="", recursive=False)
            
            for obj in objects:
                if obj.is_dir:
                    tenant_id = obj.object_name.rstrip("/")
                    if not tenant_id.startswith("_"):
                        tenants.add(tenant_id)
            
            return sorted(list(tenants))
            
        except S3Error as e:
            logger.error(f"❌ Error listing tenants: {e}")
            return []

    # =========================================================================
    # EVIDENCE UPLOAD & MANAGEMENT
    # =========================================================================

    def upload_evidence(
        self,
        tenant_id: str,
        case_id: str,
        file_data: Union[bytes, BinaryIO],
        file_name: str,
        evidence_type: str = "evidence",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Sube un archivo de evidencia al storage."""
        object_path = f"{tenant_id}/cases/{case_id}/{evidence_type}/{file_name}"
        
        try:
            if isinstance(file_data, bytes):
                content = file_data
                file_stream = io.BytesIO(file_data)
                size = len(file_data)
            else:
                content = file_data.read()
                file_stream = io.BytesIO(content)
                size = len(content)
            
            sha256_hash = hashlib.sha256(content).hexdigest()
            
            upload_metadata = {
                "x-amz-meta-tenant": tenant_id,
                "x-amz-meta-case": case_id,
                "x-amz-meta-type": evidence_type,
                "x-amz-meta-sha256": sha256_hash,
                "x-amz-meta-uploaded": datetime.utcnow().isoformat(),
            }
            
            if metadata:
                for key, value in metadata.items():
                    upload_metadata[f"x-amz-meta-{key}"] = str(value)
            
            result = self.client.put_object(
                self.bucket_name,
                object_path,
                file_stream,
                size,
                metadata=upload_metadata,
            )
            
            logger.info(f"📤 Evidence uploaded: {object_path} ({size} bytes)")
            
            return {
                "success": True,
                "object_name": object_path,
                "etag": result.etag,
                "version_id": result.version_id,
                "size": size,
                "sha256": sha256_hash,
                "bucket": self.bucket_name,
                "url": f"s3://{self.bucket_name}/{object_path}",
            }
            
        except S3Error as e:
            logger.error(f"❌ Upload failed: {e}")
            return {"success": False, "error": str(e), "object_name": object_path}

    def download_evidence(
        self,
        tenant_id: str,
        case_id: str,
        file_name: str,
        evidence_type: str = "evidence",
    ) -> Optional[bytes]:
        """Descarga un archivo de evidencia."""
        object_path = f"{tenant_id}/cases/{case_id}/{evidence_type}/{file_name}"
        
        try:
            response = self.client.get_object(self.bucket_name, object_path)
            content = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"📥 Evidence downloaded: {object_path}")
            return content
            
        except S3Error as e:
            logger.error(f"❌ Download failed: {e}")
            return None

    def list_case_evidence(
        self,
        tenant_id: str,
        case_id: str,
        evidence_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista todos los archivos de evidencia de un caso."""
        if evidence_type:
            prefix = f"{tenant_id}/cases/{case_id}/{evidence_type}/"
        else:
            prefix = f"{tenant_id}/cases/{case_id}/"
        
        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True
            )
            
            evidence_list = []
            for obj in objects:
                if not obj.object_name.endswith(".keep"):
                    evidence_list.append({
                        "name": os.path.basename(obj.object_name),
                        "path": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                        "etag": obj.etag,
                    })
            
            return evidence_list
            
        except S3Error as e:
            logger.error(f"❌ List failed: {e}")
            return []

    def delete_evidence(
        self,
        tenant_id: str,
        case_id: str,
        file_name: str,
        evidence_type: str = "evidence",
    ) -> bool:
        """Elimina un archivo de evidencia."""
        object_path = f"{tenant_id}/cases/{case_id}/{evidence_type}/{file_name}"
        
        try:
            self.client.remove_object(self.bucket_name, object_path)
            logger.info(f"🗑️ Evidence deleted: {object_path}")
            return True
            
        except S3Error as e:
            logger.error(f"❌ Delete failed: {e}")
            return False

    # =========================================================================
    # SCAN RESULTS STORAGE
    # =========================================================================

    def save_scan_results(
        self,
        tenant_id: str,
        scan_type: str,
        results: Dict[str, Any],
        scan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Guarda los resultados de un escaneo."""
        if not scan_id:
            scan_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        file_name = f"{scan_type}_{scan_id}.json"
        object_path = f"{tenant_id}/scans/{scan_type}/{file_name}"
        
        try:
            json_content = json.dumps(results, indent=2, default=str)
            content_bytes = json_content.encode("utf-8")
            
            result = self.client.put_object(
                self.bucket_name,
                object_path,
                io.BytesIO(content_bytes),
                len(content_bytes),
                content_type="application/json",
                metadata={
                    "x-amz-meta-tenant": tenant_id,
                    "x-amz-meta-scan-type": scan_type,
                    "x-amz-meta-scan-id": scan_id,
                    "x-amz-meta-timestamp": datetime.utcnow().isoformat(),
                }
            )
            
            logger.info(f"📊 Scan results saved: {object_path}")
            
            return {
                "success": True,
                "object_name": object_path,
                "scan_id": scan_id,
                "etag": result.etag,
            }
            
        except S3Error as e:
            logger.error(f"❌ Save scan results failed: {e}")
            return {"success": False, "error": str(e)}

    def get_scan_results(
        self,
        tenant_id: str,
        scan_type: str,
        scan_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Obtiene los resultados de un escaneo."""
        file_name = f"{scan_type}_{scan_id}.json"
        object_path = f"{tenant_id}/scans/{scan_type}/{file_name}"
        
        try:
            response = self.client.get_object(self.bucket_name, object_path)
            content = response.read().decode("utf-8")
            response.close()
            response.release_conn()
            
            return json.loads(content)
            
        except S3Error as e:
            logger.error(f"❌ Get scan results failed: {e}")
            return None

    def list_scans(
        self,
        tenant_id: str,
        scan_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista todos los escaneos de un tenant."""
        if scan_type:
            prefix = f"{tenant_id}/scans/{scan_type}/"
        else:
            prefix = f"{tenant_id}/scans/"
        
        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True
            )
            
            scans = []
            for obj in objects:
                if obj.object_name.endswith(".json"):
                    name = os.path.basename(obj.object_name)
                    parts = name.replace(".json", "").split("_", 1)
                    
                    scans.append({
                        "scan_type": parts[0] if len(parts) > 0 else "unknown",
                        "scan_id": parts[1] if len(parts) > 1 else name,
                        "path": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    })
            
            return sorted(scans, key=lambda x: x.get("last_modified", ""), reverse=True)
            
        except S3Error as e:
            logger.error(f"❌ List scans failed: {e}")
            return []

    # =========================================================================
    # M365 GRAPH DATA STORAGE
    # =========================================================================

    def save_m365_data(
        self,
        tenant_id: str,
        data_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Guarda datos de Microsoft 365 Graph API."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{data_type}_{timestamp}.json"
        object_path = f"{tenant_id}/m365_graph/{data_type}/{file_name}"
        
        try:
            json_content = json.dumps(data, indent=2, default=str)
            content_bytes = json_content.encode("utf-8")
            
            result = self.client.put_object(
                self.bucket_name,
                object_path,
                io.BytesIO(content_bytes),
                len(content_bytes),
                content_type="application/json",
            )
            
            logger.info(f"📊 M365 data saved: {object_path}")
            
            return {"success": True, "object_name": object_path, "etag": result.etag}
            
        except S3Error as e:
            logger.error(f"❌ Save M365 data failed: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_presigned_url(
        self,
        object_path: str,
        expires_hours: int = 1,
    ) -> Optional[str]:
        """Genera una URL pre-firmada para descarga temporal."""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_path,
                expires=timedelta(hours=expires_hours),
            )
            return url
            
        except S3Error as e:
            logger.error(f"❌ Presigned URL failed: {e}")
            return None

    def get_storage_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene estadísticas de almacenamiento."""
        prefix = f"{tenant_id}/" if tenant_id else ""
        
        try:
            total_size = 0
            total_objects = 0
            by_type = {}
            
            objects = self.client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True
            )
            
            for obj in objects:
                if not obj.object_name.endswith(".keep"):
                    total_size += obj.size or 0
                    total_objects += 1
                    
                    parts = obj.object_name.split("/")
                    if len(parts) >= 3:
                        obj_type = parts[2] if tenant_id else parts[1]
                        by_type[obj_type] = by_type.get(obj_type, 0) + 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_objects": total_objects,
                "by_type": by_type,
                "tenant_id": tenant_id,
            }
            
        except S3Error as e:
            logger.error(f"❌ Stats failed: {e}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de conexión con MinIO."""
        try:
            bucket_exists = self.client.bucket_exists(self.bucket_name)
            
            return {
                "status": "healthy" if bucket_exists else "bucket_missing",
                "endpoint": self.endpoint,
                "bucket": self.bucket_name,
                "bucket_exists": bucket_exists,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "endpoint": self.endpoint,
                "bucket": self.bucket_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# =========================================================================
# SINGLETON INSTANCE
# =========================================================================

_minio_service: Optional[MinIOStorageService] = None


def get_minio_service() -> MinIOStorageService:
    """Obtiene la instancia singleton del servicio MinIO."""
    global _minio_service
    
    if _minio_service is None:
        _minio_service = MinIOStorageService()
        if _minio_service.enabled:
            _minio_service.ensure_bucket_exists()
    
    return _minio_service


def init_minio_storage() -> bool:
    """Inicializa el almacenamiento MinIO con la estructura base."""
    if not MINIO_AVAILABLE:
        logger.warning("⚠️ MinIO not available - skipping initialization")
        return False
        
    try:
        service = get_minio_service()
        if not service.enabled:
            return False
        
        system_folders = [
            "_system/templates/",
            "_system/shared-iocs/",
            "_system/backups/",
        ]
        
        for folder in system_folders:
            service.client.put_object(
                service.bucket_name,
                f"{folder}.keep",
                io.BytesIO(b""),
                0,
            )
        
        logger.info("✅ MinIO storage initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ MinIO initialization failed: {e}")
        return False
