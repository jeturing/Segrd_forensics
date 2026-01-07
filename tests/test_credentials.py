"""
Tests for credential checking services (HIBP, Dehashed, stealer logs).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.HIBP_API_KEY = "test-hibp-key"
    settings.DEHASHED_API_KEY = "test-dehashed-key"
    settings.DEHASHED_EMAIL = "test@example.com"
    return settings


@pytest.fixture
def sample_hibp_response():
    """Sample HIBP API response."""
    return [
        {
            "Name": "LinkedIn",
            "Title": "LinkedIn",
            "Domain": "linkedin.com",
            "BreachDate": "2012-05-05",
            "PwnCount": 164611595,
            "DataClasses": ["Email addresses", "Passwords"]
        },
        {
            "Name": "Adobe",
            "Title": "Adobe",
            "Domain": "adobe.com",
            "BreachDate": "2013-10-04",
            "PwnCount": 152445165,
            "DataClasses": ["Email addresses", "Password hints", "Passwords", "Usernames"]
        }
    ]


@pytest.fixture
def sample_dehashed_response():
    """Sample Dehashed API response."""
    return {
        "entries": [
            {
                "email": "user@example.com",
                "password": "***redacted***",
                "database_name": "Collection1",
                "username": "user123"
            },
            {
                "email": "user@example.com",
                "hashed_password": "5f4dcc3b5aa765d61d8327deb882cf99",
                "database_name": "LinkedIn2016"
            }
        ],
        "total": 2
    }


# ============================================================
# HIBP Tests
# ============================================================

class TestHIBPService:
    """Tests for Have I Been Pwned integration."""

    @pytest.mark.asyncio
    async def test_hibp_check_success(self, mock_settings, sample_hibp_response):
        """Test successful HIBP breach check."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import check_hibp_breaches
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_hibp_response)
            
            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await check_hibp_breaches("user@example.com")
                
                assert result["breached"] == True
                assert len(result["breaches"]) == 2
                assert "LinkedIn" in [b["name"] for b in result["breaches"]]

    @pytest.mark.asyncio
    async def test_hibp_no_breaches(self, mock_settings):
        """Test HIBP check with no breaches found."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import check_hibp_breaches
            
            mock_response = AsyncMock()
            mock_response.status = 404  # No breaches found
            
            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await check_hibp_breaches("clean@example.com")
                
                assert result["breached"] == False
                assert len(result["breaches"]) == 0

    @pytest.mark.asyncio
    async def test_hibp_rate_limiting(self, mock_settings):
        """Test HIBP rate limiting compliance."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import check_hibp_breaches, _last_hibp_request
            
            # Should wait between requests
            start_time = asyncio.get_event_loop().time()
            
            mock_response = AsyncMock()
            mock_response.status = 404
            
            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                await check_hibp_breaches("test1@example.com")
                await check_hibp_breaches("test2@example.com")
                
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # Should take at least 1.5 seconds between calls
                assert elapsed >= 1.5

    @pytest.mark.asyncio
    async def test_hibp_api_key_required(self, mock_settings):
        """Test that HIBP requires API key."""
        mock_settings.HIBP_API_KEY = None
        
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import check_hibp_breaches
            
            with pytest.raises((ValueError, Exception)) as exc_info:
                await check_hibp_breaches("user@example.com")
            
            assert "api key" in str(exc_info.value).lower()

    def test_parse_hibp_response(self, sample_hibp_response):
        """Test HIBP response parsing."""
        from api.services.credentials import parse_hibp_breaches
        
        breaches = parse_hibp_breaches(sample_hibp_response)
        
        assert len(breaches) == 2
        assert breaches[0]["name"] == "LinkedIn"
        assert breaches[0]["date"] == "2012-05-05"
        assert "Passwords" in breaches[0]["data_classes"]


# ============================================================
# Dehashed Tests
# ============================================================

class TestDehashedService:
    """Tests for Dehashed credential search."""

    @pytest.mark.asyncio
    async def test_dehashed_search_success(self, mock_settings, sample_dehashed_response):
        """Test successful Dehashed search."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import search_dehashed
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_dehashed_response)
            
            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await search_dehashed("user@example.com")
                
                assert result["found"] == True
                assert result["total"] == 2
                assert len(result["entries"]) == 2

    @pytest.mark.asyncio
    async def test_dehashed_no_results(self, mock_settings):
        """Test Dehashed search with no results."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import search_dehashed
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"entries": [], "total": 0})
            
            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await search_dehashed("unknown@example.com")
                
                assert result["found"] == False
                assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_dehashed_domain_search(self, mock_settings):
        """Test Dehashed domain-wide search."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import search_dehashed
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "entries": [
                    {"email": "user1@company.com"},
                    {"email": "user2@company.com"},
                    {"email": "admin@company.com"}
                ],
                "total": 3
            })
            
            with patch("aiohttp.ClientSession.get", return_value=mock_response):
                result = await search_dehashed("@company.com", search_type="domain")
                
                assert result["total"] == 3

    def test_dehashed_password_redaction(self, sample_dehashed_response):
        """Test that passwords are properly redacted."""
        from api.services.credentials import process_dehashed_results
        
        processed = process_dehashed_results(sample_dehashed_response["entries"])
        
        # Plain passwords should be redacted in output
        for entry in processed:
            if "password" in entry:
                assert "***" in entry["password"] or entry["password"] == "[REDACTED]"


# ============================================================
# Stealer Logs Tests
# ============================================================

class TestStealerLogsService:
    """Tests for stealer log analysis."""

    @pytest.fixture
    def sample_stealer_log(self, tmp_path):
        """Create sample stealer log file."""
        log_content = """
URL: https://mail.company.com/owa
Username: admin@company.com
Password: SuperSecret123!

URL: https://vpn.company.com
Username: admin
Password: VPNPassword456

URL: https://banking.example.com
Username: john.doe
Password: BankPass789
"""
        log_file = tmp_path / "stealer_log.txt"
        log_file.write_text(log_content)
        return log_file

    @pytest.mark.asyncio
    async def test_parse_stealer_log(self, sample_stealer_log):
        """Test stealer log parsing."""
        from api.services.credentials import parse_stealer_log
        
        credentials = parse_stealer_log(str(sample_stealer_log))
        
        assert len(credentials) == 3
        assert credentials[0]["url"] == "https://mail.company.com/owa"
        assert credentials[0]["username"] == "admin@company.com"

    @pytest.mark.asyncio
    async def test_stealer_log_domain_filter(self, sample_stealer_log):
        """Test filtering stealer logs by domain."""
        from api.services.credentials import parse_stealer_log
        
        credentials = parse_stealer_log(
            str(sample_stealer_log),
            domain_filter="company.com"
        )
        
        # Should only return company.com entries
        assert len(credentials) == 2
        assert all("company.com" in c["url"] for c in credentials)

    @pytest.mark.asyncio
    async def test_stealer_log_categorization(self, sample_stealer_log):
        """Test credential categorization by service type."""
        from api.services.credentials import categorize_credentials
        
        credentials = [
            {"url": "https://mail.company.com/owa", "type": "webmail"},
            {"url": "https://vpn.company.com", "type": "vpn"},
            {"url": "https://banking.example.com", "type": "financial"}
        ]
        
        categorized = categorize_credentials(credentials)
        
        assert "webmail" in categorized
        assert "vpn" in categorized
        assert "financial" in categorized


# ============================================================
# Credential Analysis Tests
# ============================================================

class TestCredentialAnalysis:
    """Tests for credential analysis and risk assessment."""

    def test_password_strength_analysis(self):
        """Test password strength scoring."""
        from api.services.credentials import analyze_password_strength
        
        weak = analyze_password_strength("password123")
        strong = analyze_password_strength("Kj8#mP@9xQ!2nL$5")
        
        assert weak["score"] < strong["score"]
        assert weak["strength"] in ["weak", "very_weak"]
        assert strong["strength"] in ["strong", "very_strong"]

    def test_credential_reuse_detection(self):
        """Test detection of password reuse across services."""
        from api.services.credentials import detect_credential_reuse
        
        credentials = [
            {"url": "site1.com", "password_hash": "abc123"},
            {"url": "site2.com", "password_hash": "abc123"},  # Reused
            {"url": "site3.com", "password_hash": "def456"}
        ]
        
        reused = detect_credential_reuse(credentials)
        
        assert len(reused) >= 1
        assert "abc123" in [r["hash"] for r in reused]

    def test_corporate_credential_identification(self):
        """Test identification of corporate credentials."""
        from api.services.credentials import identify_corporate_credentials
        
        credentials = [
            {"email": "user@company.com", "url": "personal.site.com"},
            {"email": "personal@gmail.com", "url": "company.com"},
            {"email": "admin@company.com", "url": "company.sharepoint.com"}
        ]
        
        corporate = identify_corporate_credentials(credentials, "company.com")
        
        assert len(corporate) >= 2


# ============================================================
# Integration Tests
# ============================================================

class TestCredentialsIntegration:
    """Integration tests for credential checking workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_credential_check_workflow(self, mock_settings):
        """Test complete credential check workflow."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import run_credential_check
            
            # Mock all external API calls
            mock_hibp = AsyncMock(return_value={"breached": False, "breaches": []})
            mock_dehashed = AsyncMock(return_value={"found": False, "entries": []})
            
            with patch("api.services.credentials.check_hibp_breaches", mock_hibp):
                with patch("api.services.credentials.search_dehashed", mock_dehashed):
                    result = await run_credential_check(
                        case_id="IR-TEST-100",
                        emails=["user@company.com"],
                        check_hibp=True,
                        check_dehashed=True
                    )
                    
                    assert "status" in result
                    assert "results" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulk_email_check(self, mock_settings):
        """Test bulk email credential checking."""
        with patch("api.services.credentials.settings", mock_settings):
            from api.services.credentials import run_credential_check
            
            emails = [f"user{i}@company.com" for i in range(10)]
            
            mock_hibp = AsyncMock(return_value={"breached": False, "breaches": []})
            
            with patch("api.services.credentials.check_hibp_breaches", mock_hibp):
                result = await run_credential_check(
                    case_id="IR-TEST-101",
                    emails=emails,
                    check_hibp=True,
                    check_dehashed=False
                )
                
                # Should process all emails with rate limiting
                assert mock_hibp.call_count == 10
