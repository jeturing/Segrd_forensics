"""
Onboarding Routes - API endpoints for automated customer onboarding
Handles registration, payment setup, plan selection, and provisioning
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel, Field

from api.services.onboarding_service import get_onboarding_service, OnboardingStatus
from api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

onboarding_service = get_onboarding_service()


# ============================================================================
# Request/Response Models
# ============================================================================


class StartOnboardingRequest(BaseModel):
    """Request to start onboarding"""

    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Customer name")
    company_name: Optional[str] = Field(None, description="Company name")
    phone: Optional[str] = Field(None, description="Phone number")


class CreateCustomerStepRequest(BaseModel):
    """Request to create customer step"""

    session_id: str = Field(..., description="Onboarding session ID")


class SetupPaymentMethodRequest(BaseModel):
    """Request to setup payment method"""

    session_id: str = Field(..., description="Onboarding session ID")
    return_url: str = Field(..., description="URL to return after payment setup")


class SelectPlanRequest(BaseModel):
    """Request to select a plan"""

    session_id: str = Field(..., description="Onboarding session ID")
    plan_id: str = Field(
        ..., description="Plan identifier (e.g., enterprise, professional)"
    )
    price_id: str = Field(..., description="Stripe price ID")
    discount_code: Optional[str] = Field(None, description="Optional discount code")


class CreateSubscriptionStepRequest(BaseModel):
    """Request to create subscription"""

    session_id: str = Field(..., description="Onboarding session ID")


class CompleteOnboardingRequest(BaseModel):
    """Request to complete onboarding"""

    session_id: str = Field(..., description="Onboarding session ID")


# ============================================================================
# Onboarding Flow Endpoints
# ============================================================================


@router.post("/start", dependencies=[Depends(verify_api_key)])
async def start_onboarding(request: StartOnboardingRequest):
    """
    Step 1: Start the onboarding process

    Creates an onboarding session and generates a tenant ID.

    - **email**: Customer email address (required)
    - **name**: Customer name (required)
    - **company_name**: Company name (optional)
    - **phone**: Phone number (optional)

    Returns session_id, tenant_id, and next_step information
    """
    try:
        result = await onboarding_service.start_onboarding(
            email=request.email,
            name=request.name,
            company_name=request.company_name,
            phone=request.phone,
        )

        logger.info(f"✅ Onboarding started: {result['session_id']}")

        return {
            "success": True,
            "data": result,
            "message": "Onboarding session created successfully",
        }

    except Exception as e:
        logger.error(f"❌ Error starting onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step/create-customer", dependencies=[Depends(verify_api_key)])
async def create_customer_step(request: CreateCustomerStepRequest):
    """
    Step 2: Create Stripe customer

    Creates a Stripe customer record and links it to the tenant.

    - **session_id**: Onboarding session ID from Step 1

    Returns customer_id and next_step information
    """
    try:
        result = await onboarding_service.create_customer_step(
            session_id=request.session_id,
        )

        logger.info(f"✅ Customer created: {result['customer_id']}")

        return {
            "success": True,
            "data": result,
            "message": "Stripe customer created successfully",
        }

    except Exception as e:
        logger.error(f"❌ Error creating customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step/setup-payment", dependencies=[Depends(verify_api_key)])
async def setup_payment_method_step(request: SetupPaymentMethodRequest):
    """
    Step 3: Setup payment method

    Creates a Stripe SetupIntent for collecting payment information.
    The frontend should use the client_secret with Stripe.js to collect payment details.

    - **session_id**: Onboarding session ID
    - **return_url**: URL to redirect after payment setup

    Returns client_secret for Stripe.js and setup_intent_id
    """
    try:
        result = await onboarding_service.setup_payment_method_step(
            session_id=request.session_id,
            return_url=request.return_url,
        )

        logger.info(f"✅ Payment setup initiated: {result['setup_intent_id']}")

        return {
            "success": True,
            "data": result,
            "message": "Payment setup initiated. Use client_secret with Stripe.js",
        }

    except Exception as e:
        logger.error(f"❌ Error setting up payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step/select-plan", dependencies=[Depends(verify_api_key)])
async def select_plan_step(request: SelectPlanRequest):
    """
    Step 4: Select billing plan

    Records the customer's plan selection and optional discount code.

    - **session_id**: Onboarding session ID
    - **plan_id**: Plan identifier (e.g., "enterprise", "professional", "basic")
    - **price_id**: Stripe price ID for the selected plan
    - **discount_code**: Optional coupon code for discount

    Returns plan details and next_step information
    """
    try:
        result = await onboarding_service.select_plan_step(
            session_id=request.session_id,
            plan_id=request.plan_id,
            price_id=request.price_id,
            discount_code=request.discount_code,
        )

        logger.info(f"✅ Plan selected: {result['plan_id']}")

        return {
            "success": True,
            "data": result,
            "message": "Plan selected successfully",
        }

    except Exception as e:
        logger.error(f"❌ Error selecting plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step/create-subscription", dependencies=[Depends(verify_api_key)])
async def create_subscription_step(request: CreateSubscriptionStepRequest):
    """
    Step 5: Create subscription

    Creates a Stripe subscription based on the selected plan and payment method.
    Applies trial period and discount code if applicable.

    - **session_id**: Onboarding session ID

    Returns subscription_id, trial_end, and next_step information
    """
    try:
        result = await onboarding_service.create_subscription_step(
            session_id=request.session_id,
        )

        logger.info(f"✅ Subscription created: {result['subscription_id']}")

        return {
            "success": True,
            "data": result,
            "message": "Subscription created successfully",
        }

    except Exception as e:
        logger.error(f"❌ Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete", dependencies=[Depends(verify_api_key)])
async def complete_onboarding(request: CompleteOnboardingRequest):
    """
    Step 6: Complete onboarding

    Finalizes the onboarding process and provisions the tenant.
    After this step, the customer can access the platform.

    - **session_id**: Onboarding session ID

    Returns tenant_id, customer_id, subscription_id, and completion message
    """
    try:
        result = await onboarding_service.complete_onboarding(
            session_id=request.session_id,
        )

        logger.info(f"✅ Onboarding completed: {result['tenant_id']}")

        return {
            "success": True,
            "data": result,
            "message": "Onboarding completed! Your account is ready.",
        }

    except Exception as e:
        logger.error(f"❌ Error completing onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Status and Retrieval Endpoints
# ============================================================================


@router.get("/status/{session_id}", dependencies=[Depends(verify_api_key)])
async def get_onboarding_status(session_id: str):
    """
    Get current onboarding session status

    Returns the current state of the onboarding process including:
    - Current status (started, customer_created, payment_setup, etc.)
    - Current step
    - Associated IDs (customer_id, subscription_id)
    - Next action required

    - **session_id**: Onboarding session ID
    """
    try:
        session = await onboarding_service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Onboarding session not found")

        # Determine next step based on status
        next_step_map = {
            OnboardingStatus.STARTED: "create_customer",
            OnboardingStatus.CUSTOMER_CREATED: "setup_payment_method",
            OnboardingStatus.PAYMENT_SETUP: "select_plan",
            OnboardingStatus.PLAN_SELECTED: "create_subscription",
            OnboardingStatus.SUBSCRIPTION_CREATED: "complete_onboarding",
            OnboardingStatus.COMPLETED: None,
            OnboardingStatus.FAILED: None,
            OnboardingStatus.EXPIRED: None,
        }

        return {
            "success": True,
            "data": {
                "session_id": session["session_id"],
                "tenant_id": session["tenant_id"],
                "status": session["status"],
                "current_step": session["current_step"],
                "email": session["email"],
                "name": session["name"],
                "company_name": session.get("company_name"),
                "stripe_customer_id": session.get("stripe_customer_id"),
                "stripe_subscription_id": session.get("stripe_subscription_id"),
                "selected_plan": session.get("selected_plan"),
                "discount_code": session.get("discount_code"),
                "started_at": session["started_at"],
                "completed_at": session.get("completed_at"),
                "expires_at": session["expires_at"],
                "next_step": next_step_map.get(session["status"]),
            },
            "message": f"Onboarding status: {session['status']}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting onboarding status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Available Plans Endpoint
# ============================================================================


@router.get("/plans")
async def get_available_plans():
    """
    Get available billing plans

    Returns list of available plans with pricing information.
    Frontend can use this to display plan options during onboarding.

    Note: In production, these should be fetched from Stripe Products/Prices API
    """
    # TODO: Fetch from Stripe API in production
    # For now, return predefined plans

    plans = [
        {
            "plan_id": "enterprise",
            "name": "Enterprise",
            "description": "Full platform access with unlimited agents and users",
            "features": [
                "Unlimited forensic agents",
                "Unlimited users",
                "Unlimited cases",
                "Priority support",
                "Advanced analytics",
                "Custom integrations",
            ],
            "price_monthly": 10000,  # $100.00
            "price_yearly": 100000,  # $1000.00 (2 months free)
            "currency": "usd",
            "stripe_price_id_monthly": "price_enterprise_monthly",  # Replace with real Stripe price ID
            "stripe_price_id_yearly": "price_enterprise_yearly",  # Replace with real Stripe price ID
            "trial_days": 14,
            "recommended": True,
        },
        {
            "plan_id": "professional",
            "name": "Professional",
            "description": "For growing teams with moderate usage",
            "features": [
                "Up to 10 forensic agents",
                "Up to 50 users",
                "Unlimited cases",
                "Email support",
                "Standard analytics",
            ],
            "price_monthly": 5000,  # $50.00
            "price_yearly": 50000,  # $500.00 (2 months free)
            "currency": "usd",
            "stripe_price_id_monthly": "price_professional_monthly",
            "stripe_price_id_yearly": "price_professional_yearly",
            "trial_days": 14,
            "recommended": False,
        },
        {
            "plan_id": "basic",
            "name": "Basic",
            "description": "For small teams getting started",
            "features": [
                "Up to 3 forensic agents",
                "Up to 10 users",
                "Up to 100 cases/month",
                "Community support",
            ],
            "price_monthly": 2500,  # $25.00
            "price_yearly": 25000,  # $250.00 (2 months free)
            "currency": "usd",
            "stripe_price_id_monthly": "price_basic_monthly",
            "stripe_price_id_yearly": "price_basic_yearly",
            "trial_days": 7,
            "recommended": False,
        },
    ]

    return {
        "success": True,
        "data": {
            "plans": plans,
            "currency": "usd",
            "trial_available": True,
        },
        "message": "Available billing plans",
    }
