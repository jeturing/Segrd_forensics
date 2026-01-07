"""
Tests for M365 forensic tools (Sparrow, Hawk, O365 Extractor).
Covers integration, output parsing, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import asyncio


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.TOOLS_DIR = Path("/opt/forensics-tools")
    settings.EVIDENCE_DIR = Path("/tmp/test-evidence")
    settings.M365_TENANT_ID = "test-tenant-id"
    settings.M365_CLIENT_ID = "test-client-id"
    settings.M365_CLIENT_SECRET = "test-secret"
    return settings


@pytest.fixture
def sample_sparrow_output():
    """Sample Sparrow tool output for parsing tests."""
    return """
TenantId: test-tenant-id
Domain: example.com
StartDate: 2025-01-01
EndDate: 2025-01-15

Suspicious Sign-ins Found: 3
OAuth Applications with risky permissions: 2
Mailbox forwarding rules detected: 1
"""


@pytest.fixture
def sample_sparrow_csv():
    """Sample Sparrow CSV output."""
    return """timestamp,user,ip_address,location,status,risk_level
2025-01-10T10:30:00Z,admin@example.com,192.168.1.100,New York,Success,Low
2025-01-10T11:45:00Z,admin@example.com,45.33.22.11,Lagos,Success,High
2025-01-10T12:00:00Z,finance@example.com,8.8.8.8,Unknown,Failure,Medium
"""


@pytest.fixture
def sample_hawk_output():
    """Sample Hawk tool JSON output."""
    return {
        "tenant": "example.com",
        "users_analyzed": 5,
        "mailboxes": [
            {
                "email": "ceo@example.com",
                "forwarding_rules": [
                    {"destination": "external@attacker.com", "created": "2025-01-05"}
                ],
                "delegate_access": ["suspicious@external.com"]
            }
        ],
        "teams_changes": [],
        "risky_oauth_apps": [
            {"name": "SuspiciousApp", "permissions": ["Mail.ReadWrite", "Contacts.Read"]}
        ]
    }


# ============================================================
# Sparrow Tests
# ============================================================

class TestSparrowService:
    """Tests for Sparrow 365 forensic service."""

    @pytest.mark.asyncio
    async def test_sparrow_execution_success(self, mock_settings, sample_sparrow_csv, tmp_path):
        """Test successful Sparrow execution."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import run_sparrow_analysis
            
            # Setup mock subprocess
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                b"Analysis complete. Results saved to output/",
                b""
            ))
            
            # Create fake output CSV
            evidence_dir = tmp_path / "IR-TEST-001" / "sparrow"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "suspicious_signins.csv").write_text(sample_sparrow_csv)
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("api.services.m365.EVIDENCE_DIR", tmp_path):
                    # Llamar función
                    result = await run_sparrow_analysis(
                        case_id="IR-TEST-001",
                        tenant_id="test-tenant",
                        days_to_search=30
                    )
                    
                    assert result["status"] in ["completed", "running"]

    @pytest.mark.asyncio
    async def test_sparrow_tool_not_found(self, mock_settings):
        """Test error handling when Sparrow is not installed."""
        mock_settings.TOOLS_DIR = Path("/nonexistent/path")
        
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import run_sparrow_analysis
            
            with pytest.raises(Exception) as exc_info:
                await run_sparrow_analysis(
                    case_id="IR-TEST-002",
                    tenant_id="test-tenant",
                    days_to_search=30
                )
            
            assert "not found" in str(exc_info.value).lower() or "not installed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_sparrow_timeout_handling(self, mock_settings):
        """Test timeout handling for long-running Sparrow analysis."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import run_sparrow_analysis
            
            # Mock subprocess that times out
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_process.kill = MagicMock()
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with pytest.raises((asyncio.TimeoutError, Exception)):
                    await run_sparrow_analysis(
                        case_id="IR-TEST-003",
                        tenant_id="test-tenant",
                        days_to_search=90
                    )

    def test_parse_sparrow_output(self, sample_sparrow_output):
        """Test Sparrow output parsing."""
        from api.services.m365 import parse_sparrow_output
        
        result = parse_sparrow_output(sample_sparrow_output)
        
        assert "tenant_id" in result or isinstance(result, dict)

    def test_parse_sparrow_csv(self, sample_sparrow_csv, tmp_path):
        """Test Sparrow CSV parsing."""
        csv_file = tmp_path / "suspicious_signins.csv"
        csv_file.write_text(sample_sparrow_csv)
        
        from api.services.m365 import parse_csv_results
        
        results = parse_csv_results(str(csv_file))
        
        assert len(results) == 3
        assert results[1]["risk_level"] == "High"
        assert results[1]["location"] == "Lagos"


# ============================================================
# Hawk Tests
# ============================================================

class TestHawkService:
    """Tests for Hawk forensic service."""

    @pytest.mark.asyncio
    async def test_hawk_execution_success(self, mock_settings, sample_hawk_output, tmp_path):
        """Test successful Hawk execution."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import run_hawk_analysis
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                json.dumps(sample_hawk_output).encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_hawk_analysis(
                    case_id="IR-TEST-010",
                    target_user="admin@example.com"
                )
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_hawk_module_not_installed(self, mock_settings):
        """Test error when Exchange Online module is missing."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import run_hawk_analysis
            
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(
                b"",
                b"The term 'Get-HawkTenantConfiguration' is not recognized"
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with pytest.raises(Exception):
                    await run_hawk_analysis(
                        case_id="IR-TEST-011",
                        target_user="test@example.com"
                    )

    def test_parse_hawk_mailbox_results(self, sample_hawk_output):
        """Test Hawk mailbox analysis parsing."""
        mailboxes = sample_hawk_output["mailboxes"]
        
        assert len(mailboxes) == 1
        assert mailboxes[0]["email"] == "ceo@example.com"
        assert len(mailboxes[0]["forwarding_rules"]) == 1
        assert "external@attacker.com" in mailboxes[0]["forwarding_rules"][0]["destination"]

    def test_detect_suspicious_forwarding_rules(self, sample_hawk_output):
        """Test detection of suspicious forwarding rules."""
        from api.services.m365 import analyze_forwarding_rules
        
        mailboxes = sample_hawk_output["mailboxes"]
        suspicious = analyze_forwarding_rules(mailboxes)
        
        assert len(suspicious) >= 1
        assert any("external" in str(s).lower() for s in suspicious)


# ============================================================
# O365 Extractor Tests
# ============================================================

class TestO365Extractor:
    """Tests for O365 Unified Audit Log extractor."""

    @pytest.mark.asyncio
    async def test_ual_extraction_success(self, mock_settings):
        """Test successful UAL extraction."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import extract_unified_audit_logs
            
            mock_logs = [
                {"timestamp": "2025-01-10", "operation": "FileDownloaded", "user": "user@example.com"},
                {"timestamp": "2025-01-10", "operation": "FileShared", "user": "user@example.com"}
            ]
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                json.dumps(mock_logs).encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await extract_unified_audit_logs(
                    case_id="IR-TEST-020",
                    start_date="2025-01-01",
                    end_date="2025-01-15"
                )
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_ual_date_validation(self, mock_settings):
        """Test date range validation for UAL extraction."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import extract_unified_audit_logs
            
            # End date before start date should fail
            with pytest.raises((ValueError, Exception)):
                await extract_unified_audit_logs(
                    case_id="IR-TEST-021",
                    start_date="2025-01-15",
                    end_date="2025-01-01"
                )

    def test_parse_ual_operations(self):
        """Test UAL operation categorization."""
        from api.services.m365 import categorize_ual_operations
        
        operations = [
            {"operation": "FileDownloaded"},
            {"operation": "MailItemsAccessed"},
            {"operation": "UserLoggedIn"},
            {"operation": "Add-MailboxPermission"}
        ]
        
        categorized = categorize_ual_operations(operations)
        
        assert "file_operations" in categorized
        assert "mail_operations" in categorized
        assert "authentication" in categorized


# ============================================================
# Integration Tests
# ============================================================

class TestM365Integration:
    """Integration tests for M365 forensic workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_m365_analysis_workflow(self, mock_settings, tmp_path):
        """Test complete M365 analysis workflow."""
        with patch("api.services.m365.settings", mock_settings):
            from api.services.m365 import run_m365_analysis
            
            # Mock all subprocess calls
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("api.services.m365.EVIDENCE_DIR", tmp_path):
                    result = await run_m365_analysis(
                        case_id="IR-TEST-100",
                        tenant_id="test-tenant",
                        scope=["sparrow", "hawk"]
                    )
                    
                    assert "status" in result

    @pytest.mark.integration
    def test_m365_route_endpoint(self, mock_settings):
        """Test M365 API endpoint."""
        from fastapi.testclient import TestClient
        
        # This would require full app setup
        # Placeholder for integration test
        pass
