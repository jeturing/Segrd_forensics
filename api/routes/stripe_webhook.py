"""
Stripe Webhook Handlers - Process Stripe events for subscription management
"""

import logging
import stripe
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.config import settings
from api.models.subscription import (
    Subscription, SubscriptionPlan, BillingInvoice, 
    PaymentMethod, RegistrationSession
)
from api.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing Webhooks"])


# ============================================================================
# Stripe Webhook Endpoint
# ============================================================================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events
    
    Events handled:
    - checkout.session.completed: Payment completed, activate subscription
    - customer.subscription.created: New subscription created
    - customer.subscription.updated: Subscription status changed
    - customer.subscription.deleted: Subscription canceled
    - invoice.paid: Invoice paid
    - invoice.payment_failed: Payment failed
    - payment_method.attached: New payment method added
    """
    try:
        # Get raw body for signature verification
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        # Verify webhook signature if configured
        event = None
        if settings.STRIPE_WEBHOOK_SECRET:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
                )
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"❌ Stripe signature verification failed: {e}")
                raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            # Development mode - parse without verification
            import json
            event = stripe.Event.construct_from(
                json.loads(payload), stripe.api_key
            )
        
        event_type = event["type"]
        data = event["data"]["object"]
        
        logger.info(f"📨 Stripe webhook received: {event_type}")
        
        # Route to appropriate handler
        handlers = {
            "checkout.session.completed": handle_checkout_completed,
            "customer.subscription.created": handle_subscription_created,
            "customer.subscription.updated": handle_subscription_updated,
            "customer.subscription.deleted": handle_subscription_deleted,
            "invoice.paid": handle_invoice_paid,
            "invoice.payment_failed": handle_payment_failed,
            "payment_method.attached": handle_payment_method_attached,
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(data, db)
        else:
            logger.debug(f"Unhandled event type: {event_type}")
        
        return {"status": "success", "event_type": event_type}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Event Handlers
# ============================================================================

async def handle_checkout_completed(data: dict, db: Session):
    """
    Handle successful Stripe Checkout session
    
    This activates the subscription after payment
    """
    try:
        checkout_session_id = data.get("id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        
        # Get registration session token from metadata
        session_token = data.get("metadata", {}).get("registration_session_token")
        
        if session_token:
            # Find registration session
            registration = db.query(RegistrationSession).filter(
                RegistrationSession.stripe_checkout_session_id == checkout_session_id
            ).first()
            
            if registration:
                # Update registration to allow account creation
                registration.stripe_customer_id = customer_id
                registration.status = "pending"  # Ready for account creation
                registration.current_step = "account"
                registration.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"✅ Checkout completed for registration: {session_token}")
        
        # If subscription already exists (upgrade flow), update it
        if subscription_id:
            existing_sub = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if existing_sub:
                existing_sub.status = "active"
                existing_sub.stripe_customer_id = customer_id
                existing_sub.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"✅ Subscription activated: {subscription_id}")
        
    except Exception as e:
        logger.error(f"❌ Error handling checkout completed: {e}")
        db.rollback()
        raise


async def handle_subscription_created(data: dict, db: Session):
    """Handle new subscription creation from Stripe"""
    try:
        stripe_sub_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")
        
        # Find tenant by customer ID
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            subscription.stripe_subscription_id = stripe_sub_id
            subscription.status = status
            subscription.current_period_start = datetime.fromtimestamp(
                data.get("current_period_start", 0)
            )
            subscription.current_period_end = datetime.fromtimestamp(
                data.get("current_period_end", 0)
            )
            subscription.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✅ Subscription created: {stripe_sub_id}")
        
    except Exception as e:
        logger.error(f"❌ Error handling subscription created: {e}")
        db.rollback()


async def handle_subscription_updated(data: dict, db: Session):
    """Handle subscription status changes"""
    try:
        stripe_sub_id = data.get("id")
        status = data.get("status")
        cancel_at_period_end = data.get("cancel_at_period_end", False)
        
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if subscription:
            old_status = subscription.status
            subscription.status = status
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.current_period_start = datetime.fromtimestamp(
                data.get("current_period_start", 0)
            )
            subscription.current_period_end = datetime.fromtimestamp(
                data.get("current_period_end", 0)
            )
            
            # Handle status transitions
            if status == "past_due" and old_status != "past_due":
                # Payment failed - set grace period
                subscription.grace_period_end = datetime.utcnow() + timedelta(days=7)
                logger.warning(f"⚠️ Subscription past due: {stripe_sub_id}")
            
            if status == "active" and old_status in ["past_due", "trialing"]:
                # Payment succeeded or trial converted
                subscription.is_trial = False
                subscription.is_read_only = False
                logger.info(f"✅ Subscription activated: {stripe_sub_id}")
            
            # Update tenant status
            if subscription.tenant_id:
                tenant = db.query(Tenant).filter(
                    Tenant.id == subscription.tenant_id
                ).first()
                if tenant:
                    tenant.subscription_status = status
                    tenant.is_read_only = status in ["past_due", "canceled", "expired"]
            
            subscription.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"📝 Subscription updated: {stripe_sub_id} -> {status}")
        
    except Exception as e:
        logger.error(f"❌ Error handling subscription updated: {e}")
        db.rollback()


async def handle_subscription_deleted(data: dict, db: Session):
    """Handle subscription cancellation"""
    try:
        stripe_sub_id = data.get("id")
        
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if subscription:
            subscription.status = "canceled"
            subscription.canceled_at = datetime.utcnow()
            subscription.is_read_only = True
            subscription.updated_at = datetime.utcnow()
            
            # Update tenant
            if subscription.tenant_id:
                tenant = db.query(Tenant).filter(
                    Tenant.id == subscription.tenant_id
                ).first()
                if tenant:
                    tenant.subscription_status = "canceled"
                    tenant.is_read_only = True
            
            db.commit()
            logger.info(f"❌ Subscription canceled: {stripe_sub_id}")
        
    except Exception as e:
        logger.error(f"❌ Error handling subscription deleted: {e}")
        db.rollback()


async def handle_invoice_paid(data: dict, db: Session):
    """Handle successful invoice payment"""
    try:
        stripe_invoice_id = data.get("id")
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")
        
        # Find subscription
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            # Create invoice record
            invoice = BillingInvoice(
                subscription_id=subscription.id,
                tenant_id=subscription.tenant_id,
                stripe_invoice_id=stripe_invoice_id,
                stripe_payment_intent_id=data.get("payment_intent"),
                invoice_number=data.get("number"),
                status="paid",
                subtotal=data.get("subtotal", 0),
                tax=data.get("tax", 0),
                total=data.get("total", 0),
                amount_paid=data.get("amount_paid", 0),
                amount_due=0,
                currency=data.get("currency", "usd").upper(),
                invoice_date=datetime.fromtimestamp(data.get("created", 0)),
                paid_at=datetime.utcnow(),
                invoice_pdf_url=data.get("invoice_pdf"),
                hosted_invoice_url=data.get("hosted_invoice_url"),
            )
            db.add(invoice)
            
            # Ensure subscription is active
            subscription.status = "active"
            subscription.is_read_only = False
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"💰 Invoice paid: {stripe_invoice_id}")
        
    except Exception as e:
        logger.error(f"❌ Error handling invoice paid: {e}")
        db.rollback()


async def handle_payment_failed(data: dict, db: Session):
    """Handle failed payment"""
    try:
        stripe_invoice_id = data.get("id")
        subscription_id = data.get("subscription")
        
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            # Create failed invoice record
            invoice = BillingInvoice(
                subscription_id=subscription.id,
                tenant_id=subscription.tenant_id,
                stripe_invoice_id=stripe_invoice_id,
                invoice_number=data.get("number"),
                status="open",  # Still open/unpaid
                subtotal=data.get("subtotal", 0),
                total=data.get("total", 0),
                amount_due=data.get("amount_due", 0),
                currency=data.get("currency", "usd").upper(),
                invoice_date=datetime.fromtimestamp(data.get("created", 0)),
                due_date=datetime.fromtimestamp(data.get("due_date", 0)) if data.get("due_date") else None,
            )
            db.add(invoice)
            
            # Set grace period if not already set
            if not subscription.grace_period_end:
                subscription.grace_period_end = datetime.utcnow() + timedelta(days=7)
            
            db.commit()
            logger.warning(f"⚠️ Payment failed for invoice: {stripe_invoice_id}")
        
    except Exception as e:
        logger.error(f"❌ Error handling payment failed: {e}")
        db.rollback()


async def handle_payment_method_attached(data: dict, db: Session):
    """Handle new payment method attachment"""
    try:
        payment_method_id = data.get("id")
        customer_id = data.get("customer")
        card = data.get("card", {})
        
        # Find subscription by customer
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()
        
        if subscription:
            # Create or update payment method
            existing = db.query(PaymentMethod).filter(
                PaymentMethod.stripe_payment_method_id == payment_method_id
            ).first()
            
            if not existing:
                payment_method = PaymentMethod(
                    tenant_id=subscription.tenant_id,
                    stripe_payment_method_id=payment_method_id,
                    stripe_customer_id=customer_id,
                    type=data.get("type", "card"),
                    card_brand=card.get("brand"),
                    card_last4=card.get("last4"),
                    card_exp_month=card.get("exp_month"),
                    card_exp_year=card.get("exp_year"),
                    is_default=True,  # First card is default
                )
                
                # Unset other defaults
                db.query(PaymentMethod).filter(
                    PaymentMethod.tenant_id == subscription.tenant_id,
                    PaymentMethod.is_default == True
                ).update({"is_default": False})
                
                db.add(payment_method)
                db.commit()
                
                logger.info(f"💳 Payment method added: ****{card.get('last4')}")
        
    except Exception as e:
        logger.error(f"❌ Error handling payment method: {e}")
        db.rollback()


# ============================================================================
# Trial Expiration Background Task
# ============================================================================

async def check_expired_trials(db: Session):
    """
    Background task to check and expire trials
    
    Should be run periodically (e.g., every hour)
    """
    try:
        now = datetime.utcnow()
        
        # Find expired trials
        expired = db.query(Subscription).filter(
            Subscription.is_trial == True,
            Subscription.trial_end < now,
            Subscription.status == "trialing"
        ).all()
        
        for sub in expired:
            sub.status = "expired"
            sub.is_read_only = True
            sub.trial_expired_notified = True
            
            # Update tenant
            if sub.tenant_id:
                tenant = db.query(Tenant).filter(Tenant.id == sub.tenant_id).first()
                if tenant:
                    tenant.subscription_status = "expired"
                    tenant.is_read_only = True
            
            logger.info(f"⏰ Trial expired for tenant: {sub.tenant_id}")
        
        if expired:
            db.commit()
            logger.info(f"✅ Processed {len(expired)} expired trials")
        
    except Exception as e:
        logger.error(f"❌ Error checking expired trials: {e}")
        db.rollback()
