"""
Tests for endpoint forensic tools (YARA, Loki, OSQuery, Volatility).
Covers execution, output parsing, and threat detection.
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
    settings.YARA_RULES_PATH = Path("/opt/forensics-tools/yara-rules")
    return settings


@pytest.fixture
def sample_yara_output():
    """Sample YARA scan output."""
    return """Trojan_Emotet /tmp/suspicious/malware.exe
0x1a5:$s1: "cmd.exe /c"
0x2b0:$s2: "powershell -enc"

Webshell_Generic /var/www/uploads/shell.php
0x50:$php1: "<?php eval("
0x120:$php2: "$_REQUEST["
"""


@pytest.fixture
def sample_loki_output():
    """Sample Loki scanner output."""
    return """
[INFO] Starting LOKI scan
[INFO] Scanning /tmp/target

[ALERT] 
REASON: Webshell found
FILE: /var/www/html/uploads/c99.php
SCORE: 100
RULE: webshell_c99
HASH: a3b2c1d4e5f6...

[WARNING]
REASON: Suspicious process name
FILE: /tmp/svchost.exe
SCORE: 60
RULE: SUSP_svchost_wrong_location

[INFO] Scan finished
ALERTS: 1
WARNINGS: 1
"""


@pytest.fixture
def sample_osquery_output():
    """Sample OSQuery JSON output."""
    return [
        {"pid": "1234", "name": "suspicious.exe", "path": "/tmp/suspicious.exe", "cmdline": "suspicious.exe -hidden"},
        {"pid": "5678", "name": "powershell.exe", "path": "/usr/bin/pwsh", "cmdline": "pwsh -enc SGVsbG8="},
        {"pid": "9999", "name": "bash", "path": "/bin/bash", "cmdline": "bash"}
    ]


@pytest.fixture
def sample_volatility_output():
    """Sample Volatility 3 pslist output."""
    return """PID	PPID	ImageFileName	Offset(V)	Threads	Handles	SessionId	Wow64	CreateTime	ExitTime
4	0	System	0xfa8000c52040	108	-	-	False	2025-01-01 00:00:00.000000	N/A
348	4	smss.exe	0xfa8001c52040	2	29	-	False	2025-01-01 00:00:01.000000	N/A
1234	1200	malware.exe	0xfa8002c52040	5	150	1	False	2025-01-10 10:30:00.000000	N/A
"""


# ============================================================
# YARA Tests
# ============================================================

class TestYARAService:
    """Tests for YARA malware scanning service."""

    @pytest.mark.asyncio
    async def test_yara_scan_success(self, mock_settings, sample_yara_output, tmp_path):
        """Test successful YARA scan execution."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_yara_scan
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                sample_yara_output.encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_yara_scan(
                    case_id="IR-TEST-001",
                    target_path="/tmp/suspicious",
                    rules_path="/opt/yara-rules/malware.yar"
                )
                
                assert result is not None
                assert "matches" in result or "status" in result

    @pytest.mark.asyncio
    async def test_yara_rules_not_found(self, mock_settings):
        """Test error when YARA rules file doesn't exist."""
        mock_settings.YARA_RULES_PATH = Path("/nonexistent")
        
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_yara_scan
            
            with pytest.raises(Exception) as exc_info:
                await run_yara_scan(
                    case_id="IR-TEST-002",
                    target_path="/tmp/target",
                    rules_path="/nonexistent/rules.yar"
                )
            
            assert "not found" in str(exc_info.value).lower() or "rule" in str(exc_info.value).lower()

    def test_parse_yara_output(self, sample_yara_output):
        """Test YARA output parsing."""
        from api.services.endpoint import parse_yara_output
        
        matches = parse_yara_output(sample_yara_output)
        
        assert len(matches) == 2
        assert matches[0]["rule"] == "Trojan_Emotet"
        assert matches[0]["file"] == "/tmp/suspicious/malware.exe"
        assert matches[1]["rule"] == "Webshell_Generic"

    def test_parse_yara_strings(self, sample_yara_output):
        """Test YARA matched strings extraction."""
        from api.services.endpoint import parse_yara_output
        
        matches = parse_yara_output(sample_yara_output)
        
        # First match should have 2 string matches
        assert len(matches[0].get("strings", [])) >= 1

    @pytest.mark.asyncio
    async def test_yara_recursive_scan(self, mock_settings):
        """Test recursive directory scanning with YARA."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_yara_scan
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                await run_yara_scan(
                    case_id="IR-TEST-003",
                    target_path="/home/user",
                    recursive=True
                )
                
                # Verify -r flag was used
                call_args = mock_exec.call_args
                assert "-r" in call_args[0] or any("-r" in str(arg) for arg in call_args[0])


# ============================================================
# Loki Tests
# ============================================================

class TestLokiService:
    """Tests for Loki IOC scanner service."""

    @pytest.mark.asyncio
    async def test_loki_scan_success(self, mock_settings, sample_loki_output, tmp_path):
        """Test successful Loki scan execution."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_loki_scan
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                sample_loki_output.encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_loki_scan(
                    case_id="IR-TEST-010",
                    target_paths=["/tmp", "/home"]
                )
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_loki_not_installed(self, mock_settings):
        """Test error when Loki is not installed."""
        mock_settings.TOOLS_DIR = Path("/nonexistent")
        
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_loki_scan
            
            with pytest.raises(Exception):
                await run_loki_scan(
                    case_id="IR-TEST-011",
                    target_paths=["/tmp"]
                )

    def test_parse_loki_alerts(self, sample_loki_output):
        """Test Loki alert parsing."""
        from api.services.endpoint import parse_loki_output
        
        result = parse_loki_output(sample_loki_output)
        
        assert result["alerts_count"] == 1
        assert result["warnings_count"] == 1
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["file"] == "/var/www/html/uploads/c99.php"
        assert result["alerts"][0]["rule"] == "webshell_c99"

    def test_parse_loki_warnings(self, sample_loki_output):
        """Test Loki warning parsing."""
        from api.services.endpoint import parse_loki_output
        
        result = parse_loki_output(sample_loki_output)
        
        assert len(result["warnings"]) == 1
        assert "svchost" in result["warnings"][0]["file"]

    def test_loki_score_filtering(self, sample_loki_output):
        """Test filtering by Loki score threshold."""
        from api.services.endpoint import parse_loki_output
        
        result = parse_loki_output(sample_loki_output, min_score=70)
        
        # Only alerts with score >= 70 should be included
        assert all(a["score"] >= 70 for a in result["alerts"])


# ============================================================
# OSQuery Tests
# ============================================================

class TestOSQueryService:
    """Tests for OSQuery system artifact collection."""

    @pytest.mark.asyncio
    async def test_osquery_execution_success(self, mock_settings, sample_osquery_output):
        """Test successful OSQuery execution."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_osquery
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                json.dumps(sample_osquery_output).encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_osquery(
                    case_id="IR-TEST-020",
                    query="SELECT pid, name, path, cmdline FROM processes"
                )
                
                assert result is not None
                assert len(result) == 3

    @pytest.mark.asyncio
    async def test_osquery_invalid_query(self, mock_settings):
        """Test error handling for invalid OSQuery."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_osquery
            
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(
                b"",
                b"Error: near 'SELEC': syntax error"
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with pytest.raises(Exception):
                    await run_osquery(
                        case_id="IR-TEST-021",
                        query="SELEC * FROM processes"  # Invalid SQL
                    )

    def test_osquery_process_analysis(self, sample_osquery_output):
        """Test suspicious process detection from OSQuery results."""
        from api.services.endpoint import analyze_processes
        
        suspicious = analyze_processes(sample_osquery_output)
        
        # Should flag processes with suspicious characteristics
        assert len(suspicious) >= 1
        assert any("suspicious" in p["name"].lower() for p in suspicious)

    @pytest.mark.asyncio
    async def test_osquery_predefined_queries(self, mock_settings):
        """Test predefined forensic queries."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import FORENSIC_QUERIES
            
            assert "processes" in FORENSIC_QUERIES
            assert "network_connections" in FORENSIC_QUERIES
            assert "users" in FORENSIC_QUERIES
            assert "startup_items" in FORENSIC_QUERIES


# ============================================================
# Volatility Tests
# ============================================================

class TestVolatilityService:
    """Tests for Volatility 3 memory forensics."""

    @pytest.mark.asyncio
    async def test_volatility_pslist_success(self, mock_settings, sample_volatility_output):
        """Test successful Volatility pslist execution."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_volatility
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                sample_volatility_output.encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_volatility(
                    case_id="IR-TEST-030",
                    memory_dump="/evidence/memory.dmp",
                    plugin="windows.pslist"
                )
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_volatility_invalid_dump(self, mock_settings):
        """Test error handling for invalid memory dump."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_volatility
            
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(
                b"",
                b"Unsupported file format"
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with pytest.raises(Exception):
                    await run_volatility(
                        case_id="IR-TEST-031",
                        memory_dump="/evidence/invalid.bin",
                        plugin="windows.pslist"
                    )

    def test_parse_volatility_pslist(self, sample_volatility_output):
        """Test Volatility pslist parsing."""
        from api.services.endpoint import parse_volatility_output
        
        processes = parse_volatility_output(sample_volatility_output, "windows.pslist")
        
        assert len(processes) == 3
        assert processes[2]["ImageFileName"] == "malware.exe"
        assert processes[2]["PID"] == "1234"

    def test_detect_suspicious_processes(self, sample_volatility_output):
        """Test detection of suspicious processes in memory."""
        from api.services.endpoint import parse_volatility_output, analyze_memory_processes
        
        processes = parse_volatility_output(sample_volatility_output, "windows.pslist")
        suspicious = analyze_memory_processes(processes)
        
        # Should flag malware.exe as suspicious
        assert len(suspicious) >= 1
        assert any("malware" in p["name"].lower() for p in suspicious)

    @pytest.mark.asyncio
    async def test_volatility_netscan(self, mock_settings):
        """Test Volatility network scan plugin."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_volatility
            
            netscan_output = """Offset	Proto	LocalAddr	LocalPort	ForeignAddr	ForeignPort	State	PID	Owner
0xfa8001a52040	TCPv4	192.168.1.100	445	45.33.22.11	4444	ESTABLISHED	1234	malware.exe
"""
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(
                netscan_output.encode(),
                b""
            ))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_volatility(
                    case_id="IR-TEST-032",
                    memory_dump="/evidence/memory.dmp",
                    plugin="windows.netscan"
                )
                
                assert result is not None


# ============================================================
# Integration Tests
# ============================================================

class TestEndpointIntegration:
    """Integration tests for endpoint forensic workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_endpoint_scan_workflow(self, mock_settings, tmp_path):
        """Test complete endpoint scanning workflow."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_endpoint_scan
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Scan complete", b""))
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("api.services.endpoint.EVIDENCE_DIR", tmp_path):
                    result = await run_endpoint_scan(
                        case_id="IR-TEST-100",
                        hostname="PC-INFECTED",
                        actions=["yara", "loki", "osquery"]
                    )
                    
                    assert "status" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_memory_forensics_workflow(self, mock_settings, tmp_path):
        """Test memory forensics workflow with multiple plugins."""
        with patch("api.services.endpoint.settings", mock_settings):
            from api.services.endpoint import run_memory_analysis
            
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Analysis complete", b""))
            
            # Create fake memory dump
            memory_dump = tmp_path / "memory.dmp"
            memory_dump.write_bytes(b"\x00" * 1024)
            
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await run_memory_analysis(
                    case_id="IR-TEST-101",
                    memory_dump=str(memory_dump),
                    plugins=["windows.pslist", "windows.netscan", "windows.malfind"]
                )
                
                assert result is not None
