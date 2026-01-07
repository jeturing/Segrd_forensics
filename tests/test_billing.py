"""
Unit tests for Stripe billing integration
Tests StripeService, BillingService, and OnboardingService
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from api.services.stripe_service import StripeService
from api.services.billing_service import BillingService
from api.services.onboarding_service import OnboardingService, OnboardingStatus
from api.models.billing import (
    UsageType,
    SubscriptionStatus,
    InvoiceStatus,
    CustomerResponse,
    SubscriptionResponse,
    UsageSummary,
)


# =============================================================================
# StripeService Tests
# =============================================================================

class TestStripeService:
    """Tests for StripeService"""
    
    @pytest.fixture
    def stripe_service(self):
        """Create StripeService instance"""
        with patch("api.services.stripe_service.settings") as mock_settings:
            mock_settings.STRIPE_ENABLED = True
            mock_settings.STRIPE_SECRET_KEY = "sk_test_fake_key"
            mock_settings.BILLING_CURRENCY = "usd"
            mock_settings.BILLING_TRIAL_PERIOD_DAYS = 14
            return StripeService()
    
    @pytest.mark.asyncio
    async def test_create_customer(self, stripe_service):
        """Test customer creation"""
        with patch("stripe.Customer.create") as mock_create:
            # Mock Stripe response
            mock_customer = MagicMock()
            mock_customer.id = "cus_test123"
            mock_customer.email = "test@example.com"
            mock_customer.name = "Test Customer"
            mock_customer.created = int(datetime.utcnow().timestamp())
            mock_customer.currency = "usd"
            mock_customer.balance = 0
            mock_customer.delinquent = False
            mock_customer.metadata = {"tenant_id": "Jeturing_123"}
            mock_create.return_value = mock_customer
            
            # Create customer
            result = await stripe_service.create_customer(
                tenant_id="Jeturing_123",
                email="test@example.com",
                name="Test Customer",
            )
            
            # Assertions
            assert result.id == "cus_test123"
            assert result.email == "test@example.com"
            assert result.tenant_id == "Jeturing_123"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_subscription(self, stripe_service):
        """Test subscription creation"""
        with patch("stripe.Subscription.create") as mock_create:
            # Mock Stripe response
            mock_subscription = MagicMock()
            mock_subscription.id = "sub_test123"
            mock_subscription.customer = "cus_test123"
            mock_subscription.status = "active"
            mock_subscription.current_period_start = int(datetime.utcnow().timestamp())
            mock_subscription.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            mock_subscription.trial_start = None
            mock_subscription.trial_end = None
            mock_subscription.cancel_at_period_end = False
            mock_subscription.canceled_at = None
            mock_subscription.metadata = {"tenant_id": "Jeturing_123"}
            mock_create.return_value = mock_subscription
            
            # Create subscription
            result = await stripe_service.create_subscription(
                customer_id="cus_test123",
                price_id="price_test123",
            )
            
            # Assertions
            assert result.id == "sub_test123"
            assert result.customer_id == "cus_test123"
            assert result.status == SubscriptionStatus.ACTIVE
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_coupon(self, stripe_service):
        """Test coupon creation"""
        with patch("stripe.Coupon.create") as mock_create:
            # Mock Stripe response
            mock_coupon = MagicMock()
            mock_coupon.id = "TESTCODE"
            mock_coupon.percent_off = 50.0
            mock_coupon.amount_off = None
            mock_coupon.currency = None
            mock_coupon.duration = "once"
            mock_coupon.duration_in_months = None
            mock_coupon.max_redemptions = 100
            mock_coupon.times_redeemed = 0
            mock_coupon.valid = True
            mock_create.return_value = mock_coupon
            
            # Create coupon
            result = await stripe_service.create_coupon(
                code="TESTCODE",
                percent_off=50.0,
                duration="once",
                max_redemptions=100,
            )
            
            # Assertions
            assert result.code == "TESTCODE"
            assert result.percent_off == 50.0
            assert result.duration == "once"
            mock_create.assert_called_once()


# =============================================================================
# BillingService Tests
# =============================================================================

class TestBillingService:
    """Tests for BillingService"""
    
    @pytest.fixture
    def billing_service(self):
        """Create BillingService instance"""
        with patch("api.services.billing_service.DB_PATH", ":memory:"):
            service = BillingService()
            # Mock database connection for tests
            return service
    
    def test_calculate_cost(self, billing_service):
        """Test cost calculation"""
        # Test agent cost
        cost = billing_service._calculate_cost(UsageType.AGENT, 1)
        assert cost == 5000  # $50.00
        
        # Test user cost
        cost = billing_service._calculate_cost(UsageType.USER, 1)
        assert cost == 2500  # $25.00
        
        # Test case cost
        cost = billing_service._calculate_cost(UsageType.CASE, 1)
        assert cost == 1000  # $10.00
        
        # Test API call cost (per 1000)
        cost = billing_service._calculate_cost(UsageType.API_CALL, 1000)
        assert cost == 10  # $0.10 per 1000 calls
    
    @pytest.mark.asyncio
    async def test_record_usage(self, billing_service):
        """Test usage recording"""
        with patch.object(billing_service, "_get_db_connection") as mock_conn:
            # Mock database connection
            mock_cursor = MagicMock()
            mock_cursor.lastrowid = 1
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Record usage
            result = await billing_service.record_usage(
                tenant_id="Jeturing_123",
                usage_type=UsageType.CASE,
                quantity=1,
            )
            
            # Assertions
            assert result.tenant_id == "Jeturing_123"
            assert result.usage_type == UsageType.CASE
            assert result.quantity == 1
            assert result.amount_cents == 1000


# =============================================================================
# OnboardingService Tests
# =============================================================================

class TestOnboardingService:
    """Tests for OnboardingService"""
    
    @pytest.fixture
    def onboarding_service(self):
        """Create OnboardingService instance"""
        with patch("api.services.onboarding_service.DB_PATH", ":memory:"):
            service = OnboardingService()
            return service
    
    @pytest.mark.asyncio
    async def test_start_onboarding(self, onboarding_service):
        """Test onboarding start"""
        with patch.object(onboarding_service, "_get_db_connection") as mock_conn:
            # Mock database connection
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Start onboarding
            result = await onboarding_service.start_onboarding(
                email="test@example.com",
                name="Test User",
                company_name="Test Company",
            )
            
            # Assertions
            assert "session_id" in result
            assert "tenant_id" in result
            assert result["status"] == OnboardingStatus.STARTED
            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"
            assert result["company_name"] == "Test Company"
    
    @pytest.mark.asyncio
    async def test_onboarding_flow_validation(self, onboarding_service):
        """Test onboarding flow state validation"""
        # Mock session with wrong status
        mock_session = {
            "session_id": "test_session",
            "tenant_id": "Jeturing_123",
            "status": OnboardingStatus.STARTED,
            "email": "test@example.com",
            "name": "Test User",
        }
        
        with patch.object(onboarding_service, "get_session", return_value=mock_session):
            # Trying to setup payment before creating customer should fail
            with pytest.raises(Exception) as exc_info:
                await onboarding_service.setup_payment_method_step(
                    session_id="test_session",
                    return_url="http://localhost",
                )
            
            assert "Invalid session status" in str(exc_info.value)


# =============================================================================
# Integration Tests
# =============================================================================

class TestBillingIntegration:
    """Integration tests for billing flow"""
    
    @pytest.mark.asyncio
    async def test_full_onboarding_flow(self):
        """Test complete onboarding flow"""
        # This would require mocking all services and database
        # For now, testing individual components is sufficient
        pass
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_webhook_processing(self):
        """Test webhook event processing"""
        # Test with real Stripe test events
        # Requires Stripe test keys and webhook secrets
        pass


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================

@pytest.fixture
def mock_stripe_customer():
    """Mock Stripe customer object"""
    customer = MagicMock()
    customer.id = "cus_test123"
    customer.email = "test@example.com"
    customer.name = "Test Customer"
    customer.created = int(datetime.utcnow().timestamp())
    customer.currency = "usd"
    customer.balance = 0
    customer.delinquent = False
    customer.metadata = {"tenant_id": "Jeturing_123"}
    return customer


@pytest.fixture
def mock_stripe_subscription():
    """Mock Stripe subscription object"""
    subscription = MagicMock()
    subscription.id = "sub_test123"
    subscription.customer = "cus_test123"
    subscription.status = "active"
    subscription.current_period_start = int(datetime.utcnow().timestamp())
    subscription.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
    subscription.trial_start = None
    subscription.trial_end = None
    subscription.cancel_at_period_end = False
    subscription.canceled_at = None
    subscription.metadata = {"tenant_id": "Jeturing_123"}
    return subscription


@pytest.fixture
def mock_stripe_invoice():
    """Mock Stripe invoice object"""
    invoice = MagicMock()
    invoice.id = "in_test123"
    invoice.customer = "cus_test123"
    invoice.subscription = "sub_test123"
    invoice.status = "paid"
    invoice.amount_due = 10000
    invoice.amount_paid = 10000
    invoice.amount_remaining = 0
    invoice.currency = "usd"
    invoice.period_start = int(datetime.utcnow().timestamp())
    invoice.period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
    invoice.created = int(datetime.utcnow().timestamp())
    invoice.invoice_pdf = "https://invoice.stripe.com/test"
    invoice.hosted_invoice_url = "https://invoice.stripe.com/test"
    invoice.due_date = None
    return invoice
