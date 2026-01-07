"""
MCP Kali Forensics - Evidence Management Service
Handles external evidence upload, import, and management
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import mimetypes

from sqlalchemy.orm import Session
from fastapi import UploadFile

from api.models.evidence_management import (
    EvidenceSource,
    ExternalEvidence,
    EvidenceAssociation,
)
from api.config import settings

logger = logging.getLogger(__name__)

# Evidence storage directory
EVIDENCE_STORAGE = settings.EVIDENCE_DIR / "external"
EVIDENCE_STORAGE.mkdir(parents=True, exist_ok=True)


class EvidenceService:
    """Service for managing external evidence"""

    @staticmethod
    def calculate_file_hashes(file_path: Path) -> Dict[str, str]:
        """
        Calculate MD5, SHA1, and SHA256 hashes for a file.
        Uses chunked reading for large files.
        """
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)

        return {
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "sha256": sha256.hexdigest(),
        }

    @staticmethod
    async def upload_evidence(
        db: Session,
        file: UploadFile,
        name: str,
        evidence_type: str,
        description: Optional[str] = None,
        source_tool_name: Optional[str] = None,
        collected_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExternalEvidence:
        """
        Upload and store evidence file with integrity verification.

        Args:
            db: Database session
            file: Uploaded file
            name: Evidence name
            evidence_type: Type of evidence
            description: Optional description
            source_tool_name: Name of the tool that generated this evidence
            collected_by: Person who collected the evidence
            tags: Optional tags
            metadata: Additional metadata

        Returns:
            ExternalEvidence object
        """
        try:
            # Generate storage path
            evidence_id = f"EVD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex().upper()}"
            storage_dir = EVIDENCE_STORAGE / evidence_id
            storage_dir.mkdir(parents=True, exist_ok=True)

            # Save file
            file_path = storage_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            logger.info(f"📦 Evidence file saved: {file_path}")

            # Calculate hashes
            hashes = EvidenceService.calculate_file_hashes(file_path)
            logger.info(f"🔐 Hashes calculated - SHA256: {hashes['sha256'][:16]}...")

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)

            # Get or create evidence source
            source_tool_id = None
            if source_tool_name:
                source = (
                    db.query(EvidenceSource)
                    .filter(EvidenceSource.tool_name == source_tool_name)
                    .first()
                )

                if not source:
                    source = EvidenceSource(
                        tool_name=source_tool_name,
                        tool_type="external",
                        created_at=datetime.utcnow(),
                    )
                    db.add(source)
                    db.flush()
                    logger.info(f"📝 Created new evidence source: {source_tool_name}")

                source_tool_id = source.id

            # Create evidence record
            evidence = ExternalEvidence(
                id=evidence_id,
                name=name,
                description=description,
                evidence_type=evidence_type,
                source_tool_id=source_tool_id,
                file_path=str(file_path),
                file_name=file.filename,
                file_size=os.path.getsize(file_path),
                file_hash_md5=hashes["md5"],
                file_hash_sha1=hashes["sha1"],
                file_hash_sha256=hashes["sha256"],
                mime_type=mime_type,
                collected_by=collected_by,
                integrity_verified=True,
                verification_method="sha256",
                verification_timestamp=datetime.utcnow(),
                tags=tags or [],
                import_metadata=metadata or {},
                uploaded_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )

            # Add chain of custody entry
            evidence.custody_chain = [
                {
                    "action": "uploaded",
                    "by": collected_by or "unknown",
                    "at": datetime.utcnow().isoformat(),
                    "notes": "Evidence uploaded via API",
                }
            ]

            db.add(evidence)
            db.commit()
            db.refresh(evidence)

            logger.info(f"✅ Evidence created: {evidence_id}")

            return evidence

        except Exception as e:
            logger.error(f"❌ Error uploading evidence: {e}", exc_info=True)
            db.rollback()
            # Clean up file if database transaction failed
            if "storage_dir" in locals() and storage_dir.exists():
                shutil.rmtree(storage_dir)
            raise

    @staticmethod
    def get_evidence(db: Session, evidence_id: str) -> Optional[ExternalEvidence]:
        """Get evidence by ID"""
        return (
            db.query(ExternalEvidence)
            .filter(ExternalEvidence.id == evidence_id)
            .first()
        )

    @staticmethod
    def list_evidence(
        db: Session,
        evidence_type: Optional[str] = None,
        source_tool_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ExternalEvidence]:
        """List evidence with filters"""
        query = db.query(ExternalEvidence)

        if evidence_type:
            query = query.filter(ExternalEvidence.evidence_type == evidence_type)

        if source_tool_name:
            query = query.join(EvidenceSource).filter(
                EvidenceSource.tool_name == source_tool_name
            )

        if tags:
            # Filter by any matching tag
            for tag in tags:
                query = query.filter(ExternalEvidence.tags.contains([tag]))

        return (
            query.order_by(ExternalEvidence.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def associate_evidence(
        db: Session,
        evidence_id: str,
        entity_type: str,
        entity_id: str,
        association_type: Optional[str] = None,
        relevance: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> EvidenceAssociation:
        """
        Create association between evidence and an entity (case, agent, user, event).

        Args:
            db: Database session
            evidence_id: Evidence ID
            entity_type: Type of entity (case, agent, user, event, investigation)
            entity_id: ID of the entity
            association_type: Type of association (primary, secondary, reference)
            relevance: Relevance level (critical, high, medium, low)
            notes: Optional notes
            created_by: User who created the association

        Returns:
            EvidenceAssociation object
        """
        # Check if evidence exists
        evidence = (
            db.query(ExternalEvidence)
            .filter(ExternalEvidence.id == evidence_id)
            .first()
        )

        if not evidence:
            raise ValueError(f"Evidence {evidence_id} not found")

        # Create association
        association = EvidenceAssociation(
            evidence_id=evidence_id,
            entity_type=entity_type,
            entity_id=entity_id,
            association_type=association_type,
            relevance=relevance,
            notes=notes,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )

        db.add(association)
        db.commit()
        db.refresh(association)

        logger.info(
            f"🔗 Evidence {evidence_id} associated with {entity_type}:{entity_id}"
        )

        return association

    @staticmethod
    def get_evidence_associations(
        db: Session,
        evidence_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> List[EvidenceAssociation]:
        """Get evidence associations with filters"""
        query = db.query(EvidenceAssociation)

        if evidence_id:
            query = query.filter(EvidenceAssociation.evidence_id == evidence_id)

        if entity_type:
            query = query.filter(EvidenceAssociation.entity_type == entity_type)

        if entity_id:
            query = query.filter(EvidenceAssociation.entity_id == entity_id)

        return query.all()

    @staticmethod
    def verify_evidence_integrity(db: Session, evidence_id: str) -> bool:
        """
        Verify evidence integrity by recalculating hash.

        Returns:
            True if integrity is verified, False otherwise
        """
        evidence = (
            db.query(ExternalEvidence)
            .filter(ExternalEvidence.id == evidence_id)
            .first()
        )

        if not evidence or not evidence.file_path:
            logger.error(f"❌ Evidence {evidence_id} not found or no file path")
            return False

        file_path = Path(evidence.file_path)
        if not file_path.exists():
            logger.error(f"❌ Evidence file not found: {file_path}")
            return False

        # Recalculate hash
        hashes = EvidenceService.calculate_file_hashes(file_path)

        # Verify against stored hash
        verified = hashes["sha256"] == evidence.file_hash_sha256

        if verified:
            logger.info(f"✅ Evidence {evidence_id} integrity verified")
        else:
            logger.warning(f"⚠️ Evidence {evidence_id} integrity check FAILED!")

        return verified

    @staticmethod
    def delete_evidence(db: Session, evidence_id: str, permanent: bool = False) -> bool:
        """
        Delete evidence record and optionally the file.

        Args:
            db: Database session
            evidence_id: Evidence ID
            permanent: If True, also delete the file from storage

        Returns:
            True if deleted successfully
        """
        evidence = (
            db.query(ExternalEvidence)
            .filter(ExternalEvidence.id == evidence_id)
            .first()
        )

        if not evidence:
            return False

        # Delete file if requested
        if permanent and evidence.file_path:
            file_path = Path(evidence.file_path)
            if file_path.exists():
                # Delete the entire evidence directory
                storage_dir = file_path.parent
                shutil.rmtree(storage_dir, ignore_errors=True)
                logger.info(f"🗑️ Deleted evidence file: {storage_dir}")

        # Delete database record (associations will cascade)
        db.delete(evidence)
        db.commit()

        logger.info(f"✅ Evidence {evidence_id} deleted from database")

        return True

    @staticmethod
    def import_from_axion(
        db: Session,
        file_path: Path,
        case_id: Optional[str] = None,
        collected_by: Optional[str] = None,
    ) -> ExternalEvidence:
        """
        Import evidence from Axion Forensic format.

        Axion typically exports as:
        - .axz (Axion compressed archive)
        - CSV/JSON reports
        - Timeline exports
        """
        # TODO: Implement Axion-specific parsing
        # For now, treat as generic import
        logger.info(f"📦 Importing from Axion Forensic: {file_path}")

        raise NotImplementedError("Axion import not yet implemented")

    @staticmethod
    def import_from_autopsy(
        db: Session,
        file_path: Path,
        case_id: Optional[str] = None,
        collected_by: Optional[str] = None,
    ) -> ExternalEvidence:
        """
        Import evidence from Autopsy format.

        Autopsy typically exports as:
        - CSV reports
        - Tagged files
        - Timeline data
        """
        # TODO: Implement Autopsy-specific parsing
        logger.info(f"📦 Importing from Autopsy: {file_path}")

        raise NotImplementedError("Autopsy import not yet implemented")


# Singleton instance
evidence_service = EvidenceService()
