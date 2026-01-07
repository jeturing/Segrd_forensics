"""
Test Evidence Management Functionality
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

from api.database import Base
from api.models.evidence_management import EvidenceSource, ExternalEvidence, EvidenceAssociation, CommandLog
from api.services.evidence_service import EvidenceService
from api.services.command_logger import CommandLogger


@pytest.fixture
def test_db():
    """Create in-memory test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_file():
    """Create a sample file for testing"""
    content = b"This is test evidence content for forensic analysis"
    return BytesIO(content), "test_evidence.txt", len(content)


class TestEvidenceModels:
    """Test evidence management models"""
    
    def test_evidence_source_creation(self, test_db):
        """Test creating an evidence source"""
        source = EvidenceSource(
            tool_name="Autopsy",
            tool_version="4.19.0",
            tool_vendor="Basis Technology",
            tool_category="disk_forensics",
            tool_type="open_source"
        )
        test_db.add(source)
        test_db.commit()
        
        assert source.id is not None
        assert source.tool_name == "Autopsy"
    
    def test_external_evidence_creation(self, test_db):
        """Test creating external evidence record"""
        evidence = ExternalEvidence(
            name="Test Disk Image",
            evidence_type="disk_image",
            file_name="disk.e01",
            file_size=1024 * 1024 * 100,  # 100 MB
            file_hash_sha256="abc123def456"
        )
        test_db.add(evidence)
        test_db.commit()
        
        assert evidence.id is not None
        assert evidence.id.startswith("EVD-")
        assert evidence.name == "Test Disk Image"
    
    def test_evidence_association(self, test_db):
        """Test evidence association with case"""
        # Create evidence
        evidence = ExternalEvidence(
            name="Test Evidence",
            evidence_type="report",
            file_name="report.pdf"
        )
        test_db.add(evidence)
        test_db.commit()
        
        # Create association
        assoc = EvidenceAssociation(
            evidence_id=evidence.id,
            entity_type="case",
            entity_id="CASE-2024-001",
            association_type="primary",
            relevance="high"
        )
        test_db.add(assoc)
        test_db.commit()
        
        assert assoc.id is not None
        assert assoc.evidence_id == evidence.id
        assert assoc.entity_type == "case"
    
    def test_command_log_creation(self, test_db):
        """Test creating a command log entry"""
        cmd_log = CommandLog(
            command="volatility -f memory.dmp windows.pslist",
            tool_name="volatility",
            tool_version="3.0",
            case_id="CASE-2024-001",
            executed_by="analyst@company.com",
            status="completed"
        )
        test_db.add(cmd_log)
        test_db.commit()
        
        assert cmd_log.id is not None
        assert cmd_log.id.startswith("CMD-")
        assert cmd_log.tool_name == "volatility"


class TestEvidenceService:
    """Test evidence service operations"""
    
    def test_calculate_file_hashes(self):
        """Test hash calculation"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"Test content for hashing")
            temp_path = Path(f.name)
        
        try:
            hashes = EvidenceService.calculate_file_hashes(temp_path)
            
            assert "md5" in hashes
            assert "sha1" in hashes
            assert "sha256" in hashes
            assert len(hashes["md5"]) == 32
            assert len(hashes["sha1"]) == 40
            assert len(hashes["sha256"]) == 64
        finally:
            temp_path.unlink()
    
    def test_get_evidence(self, test_db):
        """Test retrieving evidence"""
        # Create evidence
        evidence = ExternalEvidence(
            name="Test Evidence",
            evidence_type="report",
            file_name="report.pdf"
        )
        test_db.add(evidence)
        test_db.commit()
        
        # Retrieve evidence
        retrieved = EvidenceService.get_evidence(test_db, evidence.id)
        
        assert retrieved is not None
        assert retrieved.id == evidence.id
        assert retrieved.name == "Test Evidence"
    
    def test_list_evidence_with_filters(self, test_db):
        """Test listing evidence with filters"""
        # Create multiple evidence items
        for i in range(5):
            evidence = ExternalEvidence(
                name=f"Evidence {i}",
                evidence_type="disk_image" if i % 2 == 0 else "report",
                file_name=f"file{i}.bin"
            )
            test_db.add(evidence)
        test_db.commit()
        
        # List all
        all_evidence = EvidenceService.list_evidence(test_db, limit=10)
        assert len(all_evidence) == 5
        
        # Filter by type
        disk_images = EvidenceService.list_evidence(
            test_db,
            evidence_type="disk_image",
            limit=10
        )
        assert len(disk_images) == 3


class TestCommandLogger:
    """Test command logging service"""
    
    def test_log_command(self, test_db):
        """Test logging a command"""
        cmd_log = CommandLogger.log_command(
            db=test_db,
            command="loki.py --noprocscan --path /tmp",
            tool_name="loki",
            case_id="CASE-2024-001",
            executed_by="analyst@company.com"
        )
        
        assert cmd_log.id is not None
        assert cmd_log.status == "pending"
        assert cmd_log.tool_name == "loki"
    
    def test_update_command_status(self, test_db):
        """Test updating command status"""
        # Create command log
        cmd_log = CommandLogger.log_command(
            db=test_db,
            command="test command",
            tool_name="test_tool",
            case_id="CASE-2024-001"
        )
        
        # Update status
        updated = CommandLogger.update_command_status(
            db=test_db,
            command_id=cmd_log.id,
            status="completed",
            exit_code=0,
            stdout="Command completed successfully",
            duration_seconds=45
        )
        
        assert updated.status == "completed"
        assert updated.exit_code == 0
        assert updated.duration_seconds == 45
        assert updated.completed_at is not None
    
    def test_get_case_commands(self, test_db):
        """Test retrieving commands for a case"""
        case_id = "CASE-2024-TEST"
        
        # Create multiple commands
        for i in range(3):
            CommandLogger.log_command(
                db=test_db,
                command=f"command {i}",
                tool_name=f"tool{i}",
                case_id=case_id
            )
        
        # Retrieve case commands
        commands = CommandLogger.get_case_commands(test_db, case_id)
        
        assert len(commands) == 3
        assert all(cmd.case_id == case_id for cmd in commands)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
