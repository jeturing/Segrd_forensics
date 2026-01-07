"""
MCP Kali Forensics - Evidence Management Models
Models for external evidence upload, command traceability, and flexible associations
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Boolean,
    BigInteger,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from api.database import Base


def generate_evidence_id():
    """Generate unique ID for evidence: EVD-YYYY-XXXXX"""
    today = datetime.utcnow()
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"EVD-{today.year}-{short_uuid}"


def generate_command_id():
    """Generate unique ID for command log: CMD-YYYY-XXXXX"""
    today = datetime.utcnow()
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"CMD-{today.year}-{short_uuid}"


class EvidenceSource(Base):
    """
    External forensic tool source metadata.
    Tracks which tools generated evidence and their versions.
    """

    __tablename__ = "evidence_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tool identification
    tool_name = Column(
        String(100), nullable=False, index=True
    )  # axion, autopsy, volatility, etc.
    tool_version = Column(String(50), nullable=True)
    tool_vendor = Column(
        String(100), nullable=True
    )  # "Magnet Forensics", "Basis Technology", etc.

    # Tool categorization
    tool_category = Column(
        String(50), nullable=True
    )  # disk_forensics, memory_forensics, network_forensics
    tool_type = Column(String(50), nullable=True)  # commercial, open_source, custom

    # Format support
    supported_formats = Column(JSON, nullable=True)  # [".e01", ".raw", ".mem", ".pcap"]
    import_format = Column(String(50), nullable=True)  # Format used for this import

    # Metadata
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evidences = relationship("ExternalEvidence", back_populates="source")

    def __repr__(self):
        return f"<EvidenceSource(tool={self.tool_name}, version={self.tool_version})>"

    def to_dict(self):
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "tool_vendor": self.tool_vendor,
            "tool_category": self.tool_category,
            "tool_type": self.tool_type,
            "supported_formats": self.supported_formats,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExternalEvidence(Base):
    """
    Evidence imported from external forensic tools.
    Extends CaseEvidence with external tool metadata and flexible associations.
    """

    __tablename__ = "external_evidences"

    id = Column(String(50), primary_key=True, default=generate_evidence_id)

    # Basic info
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    evidence_type = Column(
        String(50), nullable=False
    )  # disk_image, memory_dump, timeline, report, etc.

    # External tool metadata
    source_tool_id = Column(
        Integer, ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True
    )
    import_metadata = Column(JSON, nullable=True)  # Tool-specific metadata

    # File information
    file_path = Column(String(1024), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(
        BigInteger, nullable=True
    )  # Bytes (BigInteger for large disk images)
    file_hash_md5 = Column(String(32), nullable=True, index=True)
    file_hash_sha1 = Column(String(40), nullable=True)
    file_hash_sha256 = Column(String(64), nullable=True, index=True)
    mime_type = Column(String(100), nullable=True)

    # Original source
    original_location = Column(
        String(1024), nullable=True
    )  # Original path before import
    original_filename = Column(String(255), nullable=True)
    acquisition_date = Column(DateTime, nullable=True)

    # Chain of custody
    collected_by = Column(String(100), nullable=True)
    collected_from = Column(String(255), nullable=True)  # System, device, or person
    collection_method = Column(
        String(100), nullable=True
    )  # dd, FTK Imager, manual, etc.
    custody_chain = Column(JSON, nullable=True)  # [{action, by, at, notes}]

    # Integrity verification
    integrity_verified = Column(Boolean, default=False)
    verification_method = Column(String(100), nullable=True)  # hash, signature, etc.
    verification_timestamp = Column(DateTime, nullable=True)

    # Analysis status
    processed = Column(Boolean, default=False)
    analysis_notes = Column(Text, nullable=True)

    # Tags and classification
    tags = Column(JSON, nullable=True)  # ["malware", "exfiltration", "persistence"]
    classification = Column(
        String(50), nullable=True
    )  # public, internal, confidential, restricted

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source = relationship("EvidenceSource", back_populates="evidences")
    associations = relationship(
        "EvidenceAssociation", back_populates="evidence", cascade="all, delete-orphan"
    )
    command_logs = relationship(
        "CommandLog", back_populates="evidence", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ExternalEvidence(id={self.id}, name={self.name[:30]})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "evidence_type": self.evidence_type,
            "source_tool_id": self.source_tool_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_hash_sha256": self.file_hash_sha256,
            "collected_by": self.collected_by,
            "integrity_verified": self.integrity_verified,
            "processed": self.processed,
            "tags": self.tags,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EvidenceAssociation(Base):
    """
    Flexible associations between evidence and entities (cases, agents, users, events).
    Enables evidence to be linked to multiple contexts.
    """

    __tablename__ = "evidence_associations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Evidence reference
    evidence_id = Column(
        String(50),
        ForeignKey("external_evidences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Association target
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # case, agent, user, event, investigation
    entity_id = Column(String(100), nullable=False, index=True)  # ID of the entity

    # Association metadata
    association_type = Column(
        String(50), nullable=True
    )  # primary, secondary, reference
    relevance = Column(String(20), nullable=True)  # critical, high, medium, low
    notes = Column(Text, nullable=True)

    # Who created the association
    created_by = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    evidence = relationship("ExternalEvidence", back_populates="associations")

    def __repr__(self):
        return f"<EvidenceAssociation(evidence={self.evidence_id}, entity={self.entity_type}:{self.entity_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "evidence_id": self.evidence_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "association_type": self.association_type,
            "relevance": self.relevance,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CommandLog(Base):
    """
    Comprehensive logging of all commands executed by forensic tools.
    Ensures complete traceability and auditability.
    """

    __tablename__ = "command_logs"

    id = Column(String(50), primary_key=True, default=generate_command_id)

    # Command identification
    command = Column(Text, nullable=False)  # Full command with arguments
    tool_name = Column(String(100), nullable=False, index=True)
    tool_version = Column(String(50), nullable=True)

    # Context
    case_id = Column(String(50), nullable=True, index=True)  # Associated case
    evidence_id = Column(
        String(50),
        ForeignKey("external_evidences.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    analysis_id = Column(
        String(50), nullable=True, index=True
    )  # Associated ForensicAnalysis

    # Execution details
    executed_by = Column(String(100), nullable=True)  # User who ran the command
    execution_host = Column(String(255), nullable=True)  # Hostname where executed
    working_directory = Column(String(1024), nullable=True)
    environment_vars = Column(JSON, nullable=True)  # Relevant env vars

    # Parameters
    parameters = Column(JSON, nullable=True)  # Parsed parameters as dict
    input_files = Column(JSON, nullable=True)  # List of input files
    output_files = Column(JSON, nullable=True)  # List of generated files

    # Results
    exit_code = Column(Integer, nullable=True)
    status = Column(
        String(30), default="pending", index=True
    )  # pending, running, completed, failed
    stdout = Column(Text, nullable=True)  # Standard output (truncated if needed)
    stderr = Column(Text, nullable=True)  # Standard error (truncated if needed)
    output_summary = Column(Text, nullable=True)  # Parsed summary of results

    # Performance
    duration_seconds = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    cpu_usage_percent = Column(Integer, nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    evidence = relationship("ExternalEvidence", back_populates="command_logs")

    def __repr__(self):
        return (
            f"<CommandLog(id={self.id}, tool={self.tool_name}, status={self.status})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "command": (
                self.command[:100] + "..." if len(self.command) > 100 else self.command
            ),
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "case_id": self.case_id,
            "evidence_id": self.evidence_id,
            "executed_by": self.executed_by,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

    def to_detailed_dict(self):
        """Return complete command log with full output"""
        return {
            **self.to_dict(),
            "full_command": self.command,
            "parameters": self.parameters,
            "input_files": self.input_files,
            "output_files": self.output_files,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output_summary": self.output_summary,
            "execution_host": self.execution_host,
            "working_directory": self.working_directory,
        }
