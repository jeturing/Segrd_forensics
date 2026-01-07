"""
Registration Routes - Public endpoints for self-service registration
Handles signup flow with Stripe integration and trial activation
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
import bcrypt
import uuid

from api.database import get_db
from api.models.subscription import (
    SubscriptionPlan, Subscription, RegistrationSession
)
from api.models.user import User, user_tenants
from api.models.tenant import Tenant
from api.services.stripe_service import get_stripe_service
from api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/register", tags=["Registration"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartRegistrationRequest(BaseModel):
    """Start registration request"""
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    referral_source: Optional[str] = Field(None, description="How did you hear about us?")


class SelectPlanRequest(BaseModel):
    """Select plan request"""
    session_token: str = Field(..., description="Registration session token")
    plan_id: str = Field(..., description="Selected plan ID (e.g., 'free_trial', 'professional')")
    billing_period: str = Field("monthly", description="Billing period: monthly or yearly")


class CreateAccountRequest(BaseModel):
    """Create account request (after plan selection)"""
    session_token: str = Field(..., description="Registration session token")
    username: str = Field(..., min_length=3, max_length=50, description="Desired username")
    password: str = Field(..., min_length=8, description="Password")


class CompletePaymentRequest(BaseModel):
    """Complete payment request (for paid plans)"""
    session_token: str = Field(..., description="Registration session token")
    payment_method_id: Optional[str] = Field(None, description="Stripe payment method ID")


class RegistrationResponse(BaseModel):
    """Registration response"""
    success: bool
    session_token: Optional[str] = None
    current_step: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None


# ============================================================================
# Helper Functions
# ============================================================================

def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


def generate_tenant_id(company_name: str) -> str:
    """Generate tenant slug from company name"""
    import re
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', company_name.lower()).strip('_')
    return f"{slug}_{secrets.token_hex(4)}"


# ============================================================================
# Public Registration Endpoints
# ============================================================================

@router.get("/plans")
async def get_available_plans(db: Session = Depends(get_db)):
    """
    Get all available subscription plans (public endpoint)
    
    Returns list of plans with pricing and features
    """
    try:
        plans = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.is_active == True
        ).order_by(SubscriptionPlan.sort_order).all()
        
        return {
            "success": True,
            "plans": [plan.to_dict() for plan in plans]
        }
    except Exception as e:
        logger.error(f"❌ Failed to get plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plans")


@router.post("/start", response_model=RegistrationResponse)
async def start_registration(
    request: StartRegistrationRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Step 1: Start registration process
    
    Creates a registration session and validates email
    """
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="An account with this email already exists. Please login instead."
            )
        
        # Check for existing pending registration
        existing_session = db.query(RegistrationSession).filter(
            RegistrationSession.email == request.email,
            RegistrationSession.status == "pending",
            RegistrationSession.expires_at > datetime.utcnow()
        ).first()
        
        if existing_session:
            # Return existing session
            return RegistrationResponse(
                success=True,
                session_token=existing_session.session_token,
                current_step=existing_session.current_step,
                message="Continuing existing registration",
                data=existing_session.to_dict()
            )
        
        # Create new registration session
        session_token = generate_session_token()
        
        registration = RegistrationSession(
            session_token=session_token,
            email=request.email,
            full_name=request.full_name,
            company_name=request.company_name,
            phone=request.phone,
            referral_source=request.referral_source,
            status="pending",
            current_step="plan",  # Next step: select plan
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent"),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        
        db.add(registration)
        db.commit()
        db.refresh(registration)
        
        logger.info(f"✅ Registration started: {request.email}")
        
        return RegistrationResponse(
            success=True,
            session_token=session_token,
            current_step="plan",
            message="Registration started. Please select a plan.",
            data={
                "email": request.email,
                "full_name": request.full_name,
                "company_name": request.company_name,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to start registration: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select-plan", response_model=RegistrationResponse)
async def select_plan(
    request: SelectPlanRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2: Select subscription plan
    
    For free trial: proceeds to account creation
    For paid plans: proceeds to payment
    """
    try:
        # Get registration session
        session = db.query(RegistrationSession).filter(
            RegistrationSession.session_token == request.session_token,
            RegistrationSession.status == "pending"
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Registration session not found or expired")
        
        if session.is_expired:
            raise HTTPException(status_code=400, detail="Registration session expired. Please start again.")
        
        # Get selected plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_id == request.plan_id,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Update session
        session.selected_plan_id = plan.id
        session.billing_period = request.billing_period
        
        if plan.is_free or plan.trial_days > 0:
            # Free trial - go to account creation
            session.current_step = "account"
            next_step = "account"
            message = f"Plan selected: {plan.name}. Please create your account."
        else:
            # Paid plan - go to payment
            session.current_step = "payment"
            next_step = "payment"
            message = f"Plan selected: {plan.name}. Please complete payment."
        
        session.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Plan selected: {plan.plan_id} for {session.email}")
        
        return RegistrationResponse(
            success=True,
            session_token=request.session_token,
            current_step=next_step,
            message=message,
            data={
                "plan": plan.to_dict(),
                "billing_period": request.billing_period,
                "requires_payment": not (plan.is_free or plan.trial_days > 0),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to select plan: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-account", response_model=RegistrationResponse)
async def create_account(
    request: CreateAccountRequest,
    db: Session = Depends(get_db)
):
    """
    Step 3: Create user account and activate subscription
    
    For free trial: creates account and activates 15-day trial
    For paid plans: should have completed payment first
    """
    try:
        # Get registration session
        session = db.query(RegistrationSession).filter(
            RegistrationSession.session_token == request.session_token,
            RegistrationSession.status == "pending"
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Registration session not found or expired")
        
        if session.is_expired:
            raise HTTPException(status_code=400, detail="Registration session expired. Please start again.")
        
        if not session.selected_plan_id:
            raise HTTPException(status_code=400, detail="Please select a plan first")
        
        # Check username availability
        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Get plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == session.selected_plan_id
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Selected plan not found")
        
        # For paid plans without payment, redirect to payment
        if not plan.is_free and plan.trial_days == 0:
            if session.current_step != "payment_completed":
                raise HTTPException(
                    status_code=400, 
                    detail="Please complete payment before creating account"
                )
        
        # Create tenant
        tenant_slug = generate_tenant_id(session.company_name or session.full_name)
        subdomain = tenant_slug.lower().replace('_', '-')[:63]  # Max 63 chars for subdomain
        schema_name = f"tenant_{subdomain.replace('-', '_')}"
        
        tenant = Tenant(
            tenant_id=tenant_slug,
            name=session.company_name or f"{session.full_name}'s Organization",
            subdomain=subdomain,
            schema_name=schema_name,
            contact_email=session.email,
            contact_phone=session.phone,
            is_active=True,
            max_users=plan.max_users,
            max_cases=plan.max_cases,
            max_storage_gb=plan.max_storage_gb,
            plan=plan.plan_id,  # Store plan ID
        )
        
        db.add(tenant)
        db.flush()  # Get tenant ID
        
        # Create user
        password_hash = bcrypt.hashpw(
            request.password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        user = User(
            username=request.username,
            email=session.email,
            password_hash=password_hash,
            full_name=session.full_name,
            phone=session.phone,
            is_active=True,
            is_verified=True,  # Auto-verify for self-registration
            is_global_admin=False,
        )
        
        db.add(user)
        db.flush()  # Get user ID
        
        # Associate user with tenant
        db.execute(
            user_tenants.insert().values(
                user_id=user.id,
                tenant_id=tenant.id,
                created_at=datetime.utcnow()
            )
        )
        
        # Create subscription
        trial_end = None
        if plan.trial_days > 0:
            trial_end = datetime.utcnow() + timedelta(days=plan.trial_days)
        
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="trialing" if plan.trial_days > 0 else "active",
            billing_period=session.billing_period,
            is_trial=plan.trial_days > 0,
            trial_start=datetime.utcnow() if plan.trial_days > 0 else None,
            trial_end=trial_end,
            current_period_start=datetime.utcnow(),
            current_period_end=trial_end or (datetime.utcnow() + timedelta(days=30)),
            stripe_customer_id=session.stripe_customer_id,
        )
        
        db.add(subscription)
        
        # Update registration session
        session.status = "completed"
        session.current_step = "complete"
        session.user_id = user.id
        session.tenant_id = tenant.id
        session.completed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ Account created: {request.username} ({session.email}) - {plan.name}")
        
        return RegistrationResponse(
            success=True,
            session_token=request.session_token,
            current_step="complete",
            message="Account created successfully! You can now login.",
            data={
                "username": request.username,
                "email": session.email,
                "tenant_id": tenant.tenant_id,
                "plan": plan.name,
                "is_trial": plan.trial_days > 0,
                "trial_days": plan.trial_days,
                "trial_ends": trial_end.isoformat() if trial_end else None,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create account: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CompletePaymentRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Create Stripe Checkout session for paid plans
    
    Returns URL to redirect user to Stripe Checkout
    """
    try:
        stripe_service = get_stripe_service()
        if not stripe_service.enabled:
            raise HTTPException(status_code=503, detail="Payment processing not available")
        
        # Get registration session
        session = db.query(RegistrationSession).filter(
            RegistrationSession.session_token == request.session_token,
            RegistrationSession.status == "pending"
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Registration session not found")
        
        if not session.selected_plan_id:
            raise HTTPException(status_code=400, detail="Please select a plan first")
        
        # Get plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == session.selected_plan_id
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Selected plan not found")
        
        # Get price ID based on billing period
        price_id = (
            plan.stripe_price_id_yearly 
            if session.billing_period == "yearly" 
            else plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise HTTPException(
                status_code=400, 
                detail="This plan is not available for online payment"
            )
        
        # Determine URLs
        base_url = str(req.base_url).rstrip('/')
        success_url = f"{base_url}/register/payment-success?session_token={session.session_token}"
        cancel_url = f"{base_url}/register/payment-cancel?session_token={session.session_token}"
        
        # Create Stripe checkout session
        import stripe
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            customer_email=session.email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "registration_session_token": session.session_token,
                "plan_id": plan.plan_id,
            },
            subscription_data={
                "metadata": {
                    "registration_session_token": session.session_token,
                }
            }
        )
        
        # Update session
        session.stripe_checkout_session_id = checkout_session.id
        session.status = "payment_pending"
        session.current_step = "payment"
        session.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Checkout session created for {session.email}")
        
        return {
            "success": True,
            "checkout_url": checkout_session.url,
            "checkout_session_id": checkout_session.id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create checkout session: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_token}")
async def get_registration_status(
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Get current registration session status
    """
    session = db.query(RegistrationSession).filter(
        RegistrationSession.session_token == session_token
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Include plan details if selected
    plan_data = None
    if session.selected_plan_id:
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == session.selected_plan_id
        ).first()
        if plan:
            plan_data = plan.to_dict()
    
    return {
        "success": True,
        "session": session.to_dict(),
        "selected_plan": plan_data,
    }


@router.post("/payment-success")
async def handle_payment_success(
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    Handle successful payment callback
    
    Called by Stripe webhook or redirect
    """
    try:
        session = db.query(RegistrationSession).filter(
            RegistrationSession.session_token == session_token
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session status
        session.status = "pending"  # Ready for account creation
        session.current_step = "account"
        session.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Payment successful! Please complete your account setup.",
            "current_step": "account",
        }
        
    except Exception as e:
        logger.error(f"❌ Payment success handler failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
