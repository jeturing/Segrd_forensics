"""
Subscription Middleware - Verifies active subscription and handles read-only mode
"""

import logging
from datetime import datetime
from typing import Optional, Tuple
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.subscription import Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)

# Routes that are always allowed (even without subscription)
ALWAYS_ALLOWED_ROUTES = [
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/refresh",
    "/api/register",
    "/api/onboarding",
    "/api/billing/plans",
    "/api/billing/webhook",
    "/docs",
    "/openapi.json",
]

# Routes that are read-only safe (GET requests allowed even in read-only mode)
READ_ONLY_SAFE_PREFIXES = [
    "/api/cases",
    "/api/evidence",
    "/api/reports",
    "/api/dashboard",
    "/api/investigations",
]


class SubscriptionStatus:
    """Subscription status constants"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    NONE = "none"


def get_subscription_for_tenant(
    db: Session, 
    tenant_id: str
) -> Tuple[Optional[Subscription], Optional[SubscriptionPlan]]:
    """
    Get subscription and plan for a tenant
    
    Returns:
        Tuple of (subscription, plan) or (None, None)
    """
    try:
        subscription = db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()
        
        if subscription:
            plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.id == subscription.plan_id
            ).first()
            return subscription, plan
        
        return None, None
    except Exception as e:
        logger.error(f"❌ Error getting subscription: {e}")
        return None, None


def check_subscription_access(
    tenant_id: str,
    route_path: str,
    method: str
) -> Tuple[bool, bool, str]:
    """
    Check if tenant has valid subscription access
    
    Args:
        tenant_id: Tenant UUID
        route_path: Request path
        method: HTTP method
        
    Returns:
        Tuple of (allowed, is_read_only, message)
    """
    db = SessionLocal()
    try:
        subscription, plan = get_subscription_for_tenant(db, tenant_id)
        
        if not subscription:
            # No subscription - only allow registration/billing routes
            return False, True, "No active subscription. Please subscribe to continue."
        
        now = datetime.utcnow()
        
        # Check trial expiration
        if subscription.is_trial and subscription.trial_end:
            if now > subscription.trial_end:
                # Trial expired
                if not subscription.trial_expired_notified:
                    subscription.trial_expired_notified = True
                    subscription.status = SubscriptionStatus.EXPIRED
                    subscription.is_read_only = True
                    db.commit()
                
                if method == "GET":
                    return True, True, "Trial expired. Read-only mode. Please upgrade."
                return False, True, "Trial expired. Please upgrade to continue."
        
        # Check subscription status
        if subscription.status == SubscriptionStatus.EXPIRED:
            if method == "GET":
                return True, True, "Subscription expired. Read-only mode."
            return False, True, "Subscription expired. Please renew."
        
        if subscription.status == SubscriptionStatus.PAST_DUE:
            # Grace period - allow read access
            if method == "GET":
                return True, True, "Payment overdue. Read-only mode."
            return False, True, "Payment overdue. Please update payment method."
        
        if subscription.status == SubscriptionStatus.CANCELED:
            # Check if still in paid period
            if subscription.current_period_end and now < subscription.current_period_end:
                return True, False, "Subscription active until period end."
            if method == "GET":
                return True, True, "Subscription canceled. Read-only mode."
            return False, True, "Subscription canceled."
        
        if subscription.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
            return True, False, "OK"
        
        return False, True, "Invalid subscription status."
        
    except Exception as e:
        logger.error(f"❌ Subscription check error: {e}")
        # Fail open for now - don't block on errors
        return True, False, "OK"
    finally:
        db.close()


def is_route_allowed_without_subscription(path: str) -> bool:
    """Check if route is allowed without subscription"""
    for allowed in ALWAYS_ALLOWED_ROUTES:
        if path.startswith(allowed):
            return True
    return False


def is_read_only_safe_route(path: str, method: str) -> bool:
    """Check if route is safe in read-only mode"""
    if method != "GET":
        return False
    for prefix in READ_ONLY_SAFE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class SubscriptionMiddleware:
    """
    Middleware to verify subscription status and enforce read-only mode
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        path = request.url.path
        method = request.method
        
        # Allow routes that don't need subscription
        if is_route_allowed_without_subscription(path):
            await self.app(scope, receive, send)
            return
        
        # Get tenant from request (requires auth middleware to run first)
        tenant_id = scope.get("state", {}).get("tenant_id")
        
        if not tenant_id:
            # No tenant in context - let auth middleware handle
            await self.app(scope, receive, send)
            return
        
        # Check subscription
        allowed, is_read_only, message = check_subscription_access(
            tenant_id, path, method
        )
        
        if not allowed:
            # Block request
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=403,
                content={
                    "detail": message,
                    "subscription_required": True,
                    "is_read_only": is_read_only,
                }
            )
            await response(scope, receive, send)
            return
        
        # Add subscription info to request state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["is_read_only"] = is_read_only
        scope["state"]["subscription_message"] = message
        
        # Add warning header for read-only mode
        if is_read_only:
            # Will be handled by response middleware
            scope["state"]["add_read_only_warning"] = True
        
        await self.app(scope, receive, send)


def get_subscription_info(tenant_id: str) -> dict:
    """
    Get subscription info for a tenant
    
    Returns dict with subscription status, plan, and limits
    """
    db = SessionLocal()
    try:
        subscription, plan = get_subscription_for_tenant(db, tenant_id)
        
        if not subscription:
            return {
                "has_subscription": False,
                "status": SubscriptionStatus.NONE,
                "is_read_only": True,
                "message": "No subscription",
            }
        
        trial_days_remaining = 0
        if subscription.is_trial and subscription.trial_end:
            delta = subscription.trial_end - datetime.utcnow()
            trial_days_remaining = max(0, delta.days)
        
        return {
            "has_subscription": True,
            "status": subscription.status,
            "is_trial": subscription.is_trial,
            "trial_days_remaining": trial_days_remaining,
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "is_read_only": subscription.is_read_only or subscription.should_be_read_only,
            "plan": plan.to_dict() if plan else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting subscription info: {e}")
        return {
            "has_subscription": False,
            "status": "error",
            "is_read_only": True,
            "message": str(e),
        }
    finally:
        db.close()


async def verify_subscription_active(request: Request):
    """
    FastAPI dependency to verify active subscription
    
    Use in routes that require active subscription:
    @router.post("/...", dependencies=[Depends(verify_subscription_active)])
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    allowed, is_read_only, message = check_subscription_access(
        tenant_id,
        request.url.path,
        request.method
    )
    
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "message": message,
                "subscription_required": True,
                "is_read_only": is_read_only,
            }
        )
    
    if is_read_only and request.method != "GET":
        raise HTTPException(
            status_code=403,
            detail={
                "message": message,
                "is_read_only": True,
            }
        )
    
    return True


async def verify_not_read_only(request: Request):
    """
    FastAPI dependency to verify account is not in read-only mode
    
    Use for write operations that should be blocked in read-only mode
    """
    is_read_only = getattr(request.state, "is_read_only", False)
    
    if is_read_only:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Account is in read-only mode. Please upgrade your subscription.",
                "is_read_only": True,
            }
        )
    
    return True
