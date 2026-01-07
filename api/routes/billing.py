"""
Billing Routes - API endpoints for Stripe billing operations
Handles customers, subscriptions, invoices, usage tracking, and webhooks
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.models.billing import (
    CreateCustomerRequest,
    CreateSubscriptionRequest,
    RecordUsageRequest,
    CreatePaymentMethodRequest,
    CreateDiscountRequest,
    CustomerResponse,
    SubscriptionResponse,
    InvoiceResponse,
    UsageRecordResponse,
    UsageSummary,
    BillingStatus,
    DiscountResponse,
)
from api.database import get_db
from api.middleware.usage_tracking import usage_metrics_service, ApiUsage
from api.services.stripe_service import get_stripe_service
from api.services.billing_service import get_billing_service
from api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

stripe_service = get_stripe_service()
billing_service = get_billing_service()


# ============================================================================
# Customer Endpoints
# ============================================================================


@router.post(
    "/customers",
    response_model=CustomerResponse,
    dependencies=[Depends(verify_api_key)],
)
async def create_customer(request: CreateCustomerRequest):
    """
    Create a new Stripe customer

    - **tenant_id**: Internal tenant ID (Jeturing_GUID format)
    - **email**: Customer email address
    - **name**: Customer name
    - **phone**: Customer phone (optional)
    - **description**: Customer description (optional)
    - **metadata**: Additional metadata (optional)
    """
    try:
        customer = await stripe_service.create_customer(
            tenant_id=request.tenant_id,
            email=request.email,
            name=request.name,
            phone=request.phone,
            description=request.description,
            metadata=request.metadata,
        )

        # Save to local database
        await billing_service.save_customer(customer.id, request.tenant_id)

        return customer

    except Exception as e:
        logger.error(f"❌ Error creating customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_customer(customer_id: str):
    """Get customer details from Stripe"""
    try:
        customer = await stripe_service.get_customer(customer_id)
        return customer

    except Exception as e:
        logger.error(f"❌ Error retrieving customer: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Subscription Endpoints
# ============================================================================


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    dependencies=[Depends(verify_api_key)],
)
async def create_subscription(request: CreateSubscriptionRequest):
    """
    Create a subscription for a customer

    - **tenant_id**: Internal tenant ID
    - **customer_id**: Stripe customer ID
    - **price_id**: Stripe price ID for the plan
    - **trial_period_days**: Trial period in days (optional)
    - **discount_code**: Coupon code for discount (optional)
    - **metadata**: Additional metadata (optional)
    """
    try:
        subscription = await stripe_service.create_subscription(
            customer_id=request.customer_id,
            price_id=request.price_id,
            trial_period_days=request.trial_period_days,
            coupon=request.discount_code,
            metadata=request.metadata,
        )

        # Save to local database
        await billing_service.save_subscription(subscription.id, request.tenant_id)

        return subscription

    except Exception as e:
        logger.error(f"❌ Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_subscription(subscription_id: str):
    """Get subscription details"""
    try:
        subscription = await stripe_service.get_subscription(subscription_id)
        return subscription

    except Exception as e:
        logger.error(f"❌ Error retrieving subscription: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    dependencies=[Depends(verify_api_key)],
)
async def cancel_subscription(subscription_id: str, at_period_end: bool = True):
    """
    Cancel a subscription

    - **subscription_id**: Stripe subscription ID
    - **at_period_end**: If true, cancel at end of billing period; if false, cancel immediately
    """
    try:
        subscription = await stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=at_period_end,
        )
        return subscription

    except Exception as e:
        logger.error(f"❌ Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subscriptions/customer/{customer_id}",
    response_model=List[SubscriptionResponse],
    dependencies=[Depends(verify_api_key)],
)
async def list_customer_subscriptions(customer_id: str):
    """List all subscriptions for a customer"""
    try:
        subscriptions = await stripe_service.list_customer_subscriptions(customer_id)
        return subscriptions

    except Exception as e:
        logger.error(f"❌ Error listing subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Invoice Endpoints
# ============================================================================


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_invoice(invoice_id: str):
    """Get invoice details"""
    try:
        invoice = await stripe_service.get_invoice(invoice_id)
        return invoice

    except Exception as e:
        logger.error(f"❌ Error retrieving invoice: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/invoices/customer/{customer_id}",
    response_model=List[InvoiceResponse],
    dependencies=[Depends(verify_api_key)],
)
async def list_customer_invoices(customer_id: str, limit: int = 10):
    """List invoices for a customer"""
    try:
        invoices = await stripe_service.list_customer_invoices(customer_id, limit)
        return invoices

    except Exception as e:
        logger.error(f"❌ Error listing invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/invoices/customer/{customer_id}/upcoming",
    response_model=Optional[InvoiceResponse],
    dependencies=[Depends(verify_api_key)],
)
async def get_upcoming_invoice(customer_id: str):
    """Get upcoming invoice for a customer"""
    try:
        invoice = await stripe_service.get_upcoming_invoice(customer_id)
        return invoice

    except Exception as e:
        logger.error(f"❌ Error retrieving upcoming invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Usage Tracking Endpoints
# ============================================================================


@router.post(
    "/usage", response_model=UsageRecordResponse, dependencies=[Depends(verify_api_key)]
)
async def record_usage(request: RecordUsageRequest):
    """
    Record usage for billing

    - **tenant_id**: Tenant ID
    - **usage_type**: Type of usage (agent, user, case, event_ingestion, api_call, platform_base)
    - **quantity**: Quantity of usage (default: 1)
    - **timestamp**: Usage timestamp (optional, default: now)
    - **metadata**: Additional context (optional)
    """
    try:
        usage_record = await billing_service.record_usage(
            tenant_id=request.tenant_id,
            usage_type=request.usage_type,
            quantity=request.quantity,
            metadata=request.metadata,
        )

        return usage_record

    except Exception as e:
        logger.error(f"❌ Error recording usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/usage/tenant/{tenant_id}/summary",
    response_model=UsageSummary,
    dependencies=[Depends(verify_api_key)],
)
async def get_usage_summary(
    tenant_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
):
    """
    Get usage summary for a billing period

    - **tenant_id**: Tenant ID
    - **period_start**: Start of period (ISO 8601 format, default: beginning of current month)
    - **period_end**: End of period (ISO 8601 format, default: now)
    """
    try:
        from datetime import datetime

        ps = datetime.fromisoformat(period_start) if period_start else None
        pe = datetime.fromisoformat(period_end) if period_end else None

        summary = await billing_service.get_usage_summary(
            tenant_id=tenant_id,
            period_start=ps,
            period_end=pe,
        )

        return summary

    except Exception as e:
        logger.error(f"❌ Error getting usage summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/usage/tenant/{tenant_id}/unbilled",
    response_model=List[UsageRecordResponse],
    dependencies=[Depends(verify_api_key)],
)
async def get_unbilled_usage(
    tenant_id: str,
    limit: int = 100,
):
    """Get unbilled usage records for a tenant"""
    try:
        records = await billing_service.get_unbilled_usage(tenant_id, limit)
        return records

    except Exception as e:
        logger.error(f"❌ Error getting unbilled usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Billing Status Endpoints
# ============================================================================


@router.get(
    "/status/tenant/{tenant_id}",
    response_model=BillingStatus,
    dependencies=[Depends(verify_api_key)],
)
async def get_billing_status(tenant_id: str):
    """
    Get comprehensive billing status for a tenant

    Includes:
    - Customer information
    - Active subscription status
    - Trial period information
    - Payment method status
    - Outstanding balance
    - Upcoming invoice details
    """
    try:
        status = await billing_service.get_billing_status(tenant_id)
        return status

    except Exception as e:
        logger.error(f"❌ Error getting billing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Payment Method Endpoints
# ============================================================================


@router.post("/payment-methods/setup-intent", dependencies=[Depends(verify_api_key)])
async def create_setup_intent(request: CreatePaymentMethodRequest):
    """
    Create a SetupIntent for collecting payment method

    Returns client_secret for Stripe.js on the frontend
    """
    try:
        setup_intent = await stripe_service.create_setup_intent(
            customer_id=request.customer_id,
            return_url=request.return_url,
        )

        return setup_intent

    except Exception as e:
        logger.error(f"❌ Error creating SetupIntent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment-methods/attach", dependencies=[Depends(verify_api_key)])
async def attach_payment_method(
    customer_id: str,
    payment_method_id: str,
):
    """Attach a payment method to a customer and set as default"""
    try:
        result = await stripe_service.attach_payment_method(
            payment_method_id=payment_method_id,
            customer_id=customer_id,
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error attaching payment method: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Discount/Coupon Endpoints
# ============================================================================


@router.post(
    "/discounts",
    response_model=DiscountResponse,
    dependencies=[Depends(verify_api_key)],
)
async def create_discount(request: CreateDiscountRequest):
    """
    Create a discount coupon

    - **code**: Coupon code
    - **percent_off**: Percentage discount (0-100) OR
    - **amount_off**: Fixed amount discount in cents
    - **duration**: Duration type (once, repeating, forever)
    - **duration_in_months**: Months if duration is repeating
    - **max_redemptions**: Maximum number of redemptions (optional)
    """
    try:
        discount = await stripe_service.create_coupon(
            code=request.code,
            percent_off=request.percent_off,
            amount_off=request.amount_off,
            duration=request.duration,
            duration_in_months=request.duration_in_months,
            max_redemptions=request.max_redemptions,
        )

        return discount

    except Exception as e:
        logger.error(f"❌ Error creating discount: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/discounts/{code}",
    response_model=DiscountResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_discount(code: str):
    """Get discount coupon details"""
    try:
        discount = await stripe_service.get_coupon(code)
        return discount

    except Exception as e:
        logger.error(f"❌ Error retrieving discount: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Webhook Endpoint
# ============================================================================


@router.post("/webhooks")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Stripe webhook handler for processing events

    Handles events like:
    - customer.created
    - customer.updated
    - invoice.created
    - invoice.paid
    - invoice.payment_failed
    - subscription.created
    - subscription.updated
    - subscription.deleted
    - payment_method.attached
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        # Get raw body
        payload = await request.body()

        # Verify webhook signature
        event = await stripe_service.verify_webhook_signature(
            payload=payload,
            signature=stripe_signature,
        )

        # Process event in background
        background_tasks.add_task(process_webhook_event, event)

        return {"status": "received"}

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def process_webhook_event(event: dict):
    """Process Stripe webhook event"""
    try:
        event_type = event["type"]
        event_data = event["data"]["object"]

        logger.info(f"🔔 Processing webhook: {event_type}")

        # Handle different event types
        if event_type == "invoice.paid":
            # Mark usage as billed
            invoice_id = event_data["id"]
            customer_id = event_data["customer"]

            # Get tenant_id from customer metadata
            customer = await stripe_service.get_customer(customer_id)
            tenant_id = customer.metadata.get("tenant_id")

            if tenant_id:
                await billing_service.mark_usage_billed(tenant_id, invoice_id)
                await billing_service.save_invoice(invoice_id, tenant_id)

        elif event_type == "invoice.payment_failed":
            # Handle failed payment
            invoice_id = event_data["id"]
            logger.error(f"❌ Payment failed for invoice: {invoice_id}")

        elif event_type == "customer.subscription.created":
            # Save subscription
            subscription_id = event_data["id"]
            tenant_id = event_data["metadata"].get("tenant_id")
            if tenant_id:
                await billing_service.save_subscription(subscription_id, tenant_id)

        elif event_type == "customer.subscription.updated":
            # Update subscription
            subscription_id = event_data["id"]
            tenant_id = event_data["metadata"].get("tenant_id")
            if tenant_id:
                await billing_service.save_subscription(subscription_id, tenant_id)

        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription_id = event_data["id"]
            logger.info(f"📌 Subscription canceled: {subscription_id}")

        logger.info(f"✅ Webhook processed: {event_type}")

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)


# ============================================================================
# Usage Analytics Endpoints (v4.6)
# ============================================================================


class UsageSummaryResponse(BaseModel):
    """Usage summary response for billing analytics."""

    total_api_calls: int
    total_billable_units: float
    usage_by_category: list
    top_endpoints: list
    period: dict


class BillingExportResponse(BaseModel):
    """Billing export response."""

    tenant_id: str
    billing_period: str
    usage_summary: dict
    invoice_ready: bool
    generated_at: str


@router.get("/usage/summary")
async def get_usage_summary_v2(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
    db: Session = Depends(get_db),
):
    """
    Get usage summary for billing analytics.

    Returns aggregated usage statistics including:
    - Total API calls
    - Total billable units
    - Usage by category (compute, storage, api_call)
    - Top endpoints by usage
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    summary = usage_metrics_service.get_usage_summary(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )

    return summary


@router.get("/usage/tenant/{tenant_id}")
async def get_tenant_usage(
    tenant_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get detailed usage for a specific tenant."""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)

    if not end_date:
        end_date = datetime.utcnow()

    summary = usage_metrics_service.get_usage_summary(
        db=db, tenant_id=tenant_id, start_date=start_date, end_date=end_date
    )

    return {"tenant_id": tenant_id, "summary": summary}


@router.get("/usage/export/{tenant_id}/{year}/{month}")
async def export_tenant_usage_for_billing(
    tenant_id: str, year: int, month: int, db: Session = Depends(get_db)
):
    """
    Export usage data for billing system integration.

    Generates a billing-ready report for the specified month.
    Can be consumed by external billing platforms (Stripe, Chargebee, etc.)
    """
    # Validate year and month
    if year < 2020 or year > 2100:
        raise HTTPException(
            status_code=400, detail="Year must be between 2020 and 2100"
        )

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    billing_data = usage_metrics_service.export_usage_for_billing(
        db=db, tenant_id=tenant_id, month=month, year=year
    )

    return billing_data


@router.get("/usage/details")
async def get_usage_details(
    tenant_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    endpoint: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get detailed usage records with filters.

    Useful for:
    - Debugging usage patterns
    - Identifying high-usage endpoints
    - Auditing API access
    """
    query = db.query(ApiUsage)

    if tenant_id:
        query = query.filter(ApiUsage.tenant_id == tenant_id)

    if user_id:
        query = query.filter(ApiUsage.user_id == user_id)

    if endpoint:
        query = query.filter(ApiUsage.endpoint == endpoint)

    if start_date:
        query = query.filter(ApiUsage.timestamp >= start_date)

    if end_date:
        query = query.filter(ApiUsage.timestamp <= end_date)

    total = query.count()
    records = (
        query.order_by(ApiUsage.timestamp.desc()).limit(limit).offset(offset).all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": [r.to_dict() for r in records],
    }


@router.get("/usage/statistics")
async def get_usage_statistics(db: Session = Depends(get_db)):
    """
    Get overall usage statistics.

    Provides system-wide metrics for monitoring and capacity planning.
    """
    from sqlalchemy import func

    # Total usage
    total_calls = db.query(func.count(ApiUsage.id)).scalar()
    total_billable = db.query(func.sum(ApiUsage.billable_units)).scalar() or 0

    # Average response time
    avg_response_time = db.query(func.avg(ApiUsage.response_time_ms)).scalar() or 0

    # Today's usage
    today = datetime.utcnow().date()
    today_calls = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.timestamp >= datetime.combine(today, datetime.min.time()))
        .scalar()
    )

    # Current month usage
    first_day_month = datetime(datetime.utcnow().year, datetime.utcnow().month, 1)
    month_calls = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.timestamp >= first_day_month)
        .scalar()
    )

    # Top tenants by usage
    top_tenants = (
        db.query(
            ApiUsage.tenant_id,
            func.count(ApiUsage.id),
            func.sum(ApiUsage.billable_units),
        )
        .group_by(ApiUsage.tenant_id)
        .order_by(func.count(ApiUsage.id).desc())
        .limit(10)
        .all()
    )

    return {
        "total_api_calls": total_calls,
        "total_billable_units": float(total_billable),
        "average_response_time_ms": float(avg_response_time),
        "today_calls": today_calls,
        "month_calls": month_calls,
        "top_tenants": [
            {"tenant_id": t[0], "calls": t[1], "billable_units": float(t[2] or 0)}
            for t in top_tenants
        ],
    }


@router.get("/usage/rate-limits/{tenant_id}")
async def get_rate_limit_status(
    tenant_id: str, db: Session = Depends(get_db)
):
    """
    Get current rate limit status for a tenant.

    Useful for:
    - Displaying remaining quota in UI
    - Implementing soft/hard limits
    - Sending alerts when approaching limits
    """
    from sqlalchemy import func

    # Get usage for current hour
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    hourly_calls = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.tenant_id == tenant_id, ApiUsage.timestamp >= hour_ago)
        .scalar()
    )

    # Get usage for current day
    day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_calls = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.tenant_id == tenant_id, ApiUsage.timestamp >= day_start)
        .scalar()
    )

    # Get usage for current month
    month_start = datetime(datetime.utcnow().year, datetime.utcnow().month, 1)
    monthly_calls = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.tenant_id == tenant_id, ApiUsage.timestamp >= month_start)
        .scalar()
    )

    # Define limits (could be fetched from tenant configuration)
    HOURLY_LIMIT = 1000
    DAILY_LIMIT = 10000
    MONTHLY_LIMIT = 100000

    return {
        "tenant_id": tenant_id,
        "hourly": {
            "used": hourly_calls,
            "limit": HOURLY_LIMIT,
            "remaining": max(0, HOURLY_LIMIT - hourly_calls),
            "percentage": min(100, (hourly_calls / HOURLY_LIMIT) * 100),
        },
        "daily": {
            "used": daily_calls,
            "limit": DAILY_LIMIT,
            "remaining": max(0, DAILY_LIMIT - daily_calls),
            "percentage": min(100, (daily_calls / DAILY_LIMIT) * 100),
        },
        "monthly": {
            "used": monthly_calls,
            "limit": MONTHLY_LIMIT,
            "remaining": max(0, MONTHLY_LIMIT - monthly_calls),
            "percentage": min(100, (monthly_calls / MONTHLY_LIMIT) * 100),
        },
    }
