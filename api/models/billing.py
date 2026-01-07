"""
Billing Models for Stripe Integration
Includes customers, subscriptions, invoices, usage records, and discounts
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# Enums
# ============================================================================


class BillingPeriod(str, Enum):
    """Billing period types"""

    MONTHLY = "monthly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class UsageType(str, Enum):
    """Types of usage that can be billed"""

    AGENT = "agent"
    USER = "user"
    CASE = "case"
    EVENT_INGESTION = "event_ingestion"
    API_CALL = "api_call"
    PLATFORM_BASE = "platform_base"


class SubscriptionStatus(str, Enum):
    """Stripe subscription statuses"""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"


class InvoiceStatus(str, Enum):
    """Stripe invoice statuses"""

    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


# ============================================================================
# Request Models
# ============================================================================


class CreateCustomerRequest(BaseModel):
    """Request to create a Stripe customer"""

    tenant_id: str = Field(..., description="Tenant ID (Jeturing_GUID format)")
    email: str = Field(..., description="Customer email address")
    name: str = Field(..., description="Customer name")
    phone: Optional[str] = Field(None, description="Customer phone number")
    description: Optional[str] = Field(None, description="Customer description")
    metadata: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription"""

    tenant_id: str = Field(..., description="Tenant ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    price_id: str = Field(..., description="Stripe price ID")
    trial_period_days: Optional[int] = Field(None, description="Trial period in days")
    discount_code: Optional[str] = Field(None, description="Coupon code for discount")
    metadata: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class RecordUsageRequest(BaseModel):
    """Request to record usage for billing"""

    tenant_id: str = Field(..., description="Tenant ID")
    usage_type: UsageType = Field(..., description="Type of usage")
    quantity: int = Field(..., ge=1, description="Quantity of usage")
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.utcnow, description="Usage timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional context"
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CreatePaymentMethodRequest(BaseModel):
    """Request to create or attach payment method"""

    tenant_id: str = Field(..., description="Tenant ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    payment_method_id: Optional[str] = Field(
        None, description="Existing payment method ID"
    )
    return_url: str = Field(..., description="URL to return after setup")


class CreateDiscountRequest(BaseModel):
    """Request to create a discount coupon"""

    code: str = Field(..., description="Coupon code")
    percent_off: Optional[float] = Field(
        None, ge=0, le=100, description="Percentage discount (0-100)"
    )
    amount_off: Optional[int] = Field(
        None, ge=0, description="Fixed amount discount in cents"
    )
    duration: str = Field("once", description="Duration: once, repeating, forever")
    duration_in_months: Optional[int] = Field(
        None, description="Months if duration is repeating"
    )
    max_redemptions: Optional[int] = Field(
        None, description="Maximum number of redemptions"
    )

    @field_validator("percent_off", "amount_off")
    @classmethod
    def validate_discount(cls, v, info):
        # Ensure at least one discount type is provided
        if info.field_name == "amount_off" and v is None:
            if info.data.get("percent_off") is None:
                raise ValueError("Either percent_off or amount_off must be provided")
        return v


# ============================================================================
# Response Models
# ============================================================================


class CustomerResponse(BaseModel):
    """Stripe customer response"""

    id: str = Field(..., description="Stripe customer ID")
    tenant_id: str = Field(..., description="Associated tenant ID")
    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Customer name")
    created: datetime = Field(..., description="Creation timestamp")
    currency: str = Field(..., description="Default currency")
    balance: int = Field(0, description="Account balance in cents")
    delinquent: bool = Field(False, description="Whether account is delinquent")
    metadata: Dict[str, str] = Field(default_factory=dict)


class SubscriptionResponse(BaseModel):
    """Stripe subscription response"""

    id: str = Field(..., description="Stripe subscription ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    tenant_id: str = Field(..., description="Associated tenant ID")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    current_period_start: datetime = Field(
        ..., description="Current billing period start"
    )
    current_period_end: datetime = Field(..., description="Current billing period end")
    trial_start: Optional[datetime] = Field(None, description="Trial period start")
    trial_end: Optional[datetime] = Field(None, description="Trial period end")
    cancel_at_period_end: bool = Field(
        False, description="Whether to cancel at period end"
    )
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    metadata: Dict[str, str] = Field(default_factory=dict)


class InvoiceResponse(BaseModel):
    """Stripe invoice response"""

    id: str = Field(..., description="Stripe invoice ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    tenant_id: str = Field(..., description="Associated tenant ID")
    status: InvoiceStatus = Field(..., description="Invoice status")
    amount_due: int = Field(..., description="Amount due in cents")
    amount_paid: int = Field(..., description="Amount paid in cents")
    amount_remaining: int = Field(..., description="Amount remaining in cents")
    currency: str = Field(..., description="Currency code")
    period_start: datetime = Field(..., description="Billing period start")
    period_end: datetime = Field(..., description="Billing period end")
    invoice_pdf: Optional[str] = Field(None, description="URL to invoice PDF")
    hosted_invoice_url: Optional[str] = Field(None, description="URL to hosted invoice")
    created: datetime = Field(..., description="Creation timestamp")
    due_date: Optional[datetime] = Field(None, description="Payment due date")


class UsageRecordResponse(BaseModel):
    """Usage record response"""

    id: str = Field(..., description="Usage record ID")
    tenant_id: str = Field(..., description="Associated tenant ID")
    usage_type: UsageType = Field(..., description="Type of usage")
    quantity: int = Field(..., description="Quantity used")
    timestamp: datetime = Field(..., description="When usage occurred")
    billed: bool = Field(False, description="Whether usage has been billed")
    invoice_id: Optional[str] = Field(None, description="Associated invoice ID")
    amount_cents: int = Field(..., description="Calculated cost in cents")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiscountResponse(BaseModel):
    """Discount coupon response"""

    id: str = Field(..., description="Stripe coupon ID")
    code: str = Field(..., description="Coupon code")
    percent_off: Optional[float] = Field(None, description="Percentage discount")
    amount_off: Optional[int] = Field(
        None, description="Fixed amount discount in cents"
    )
    currency: Optional[str] = Field(None, description="Currency for amount_off")
    duration: str = Field(..., description="Duration type")
    duration_in_months: Optional[int] = Field(None, description="Duration in months")
    max_redemptions: Optional[int] = Field(None, description="Maximum redemptions")
    times_redeemed: int = Field(0, description="Times already redeemed")
    valid: bool = Field(True, description="Whether coupon is valid")


# ============================================================================
# Webhook Event Models
# ============================================================================


class StripeWebhookEvent(BaseModel):
    """Stripe webhook event"""

    id: str = Field(..., description="Event ID")
    type: str = Field(..., description="Event type (e.g., invoice.paid)")
    data: Dict[str, Any] = Field(..., description="Event data object")
    created: int = Field(..., description="Unix timestamp")


# ============================================================================
# Billing Summary Models
# ============================================================================


class UsageSummary(BaseModel):
    """Summary of usage for billing period"""

    tenant_id: str
    period_start: datetime
    period_end: datetime
    usage_by_type: Dict[UsageType, int] = Field(
        default_factory=dict, description="Quantity by usage type"
    )
    costs_by_type: Dict[UsageType, int] = Field(
        default_factory=dict, description="Cost in cents by type"
    )
    total_cost_cents: int = Field(0, description="Total cost in cents")
    total_cost_usd: float = Field(0.0, description="Total cost in USD")


class BillingStatus(BaseModel):
    """Overall billing status for a tenant"""

    tenant_id: str
    customer_id: Optional[str] = None
    has_active_subscription: bool = False
    subscription_status: Optional[SubscriptionStatus] = None
    trial_ends_at: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    is_delinquent: bool = False
    outstanding_balance_cents: int = 0
    next_invoice_amount_cents: Optional[int] = None
    next_invoice_date: Optional[datetime] = None
    payment_method_configured: bool = False
