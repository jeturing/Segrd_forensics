"""
Subscription Models - SQLAlchemy models for billing and subscriptions
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, 
    ForeignKey, Text, Numeric, JSON
)
from sqlalchemy.orm import relationship
import uuid

from api.database import Base, GUID


class SubscriptionPlan(Base):
    """Available subscription plans"""
    
    __tablename__ = "subscription_plans"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    plan_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Pricing
    price_monthly = Column(Numeric(10, 2), default=0)
    price_yearly = Column(Numeric(10, 2), default=0)
    stripe_price_id_monthly = Column(String(100))
    stripe_price_id_yearly = Column(String(100))
    currency = Column(String(3), default="USD")
    
    # Limits
    max_users = Column(Integer, default=1)
    max_cases = Column(Integer, default=10)
    max_storage_gb = Column(Integer, default=5)
    max_analyses_per_month = Column(Integer, default=50)
    max_agents = Column(Integer, default=0)
    
    # Features
    features = Column(JSON, default=list)
    
    # Trial
    trial_days = Column(Integer, default=0)
    is_free = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "price_monthly": float(self.price_monthly) if self.price_monthly else 0,
            "price_yearly": float(self.price_yearly) if self.price_yearly else 0,
            "currency": self.currency,
            "max_users": self.max_users,
            "max_cases": self.max_cases,
            "max_storage_gb": self.max_storage_gb,
            "max_analyses_per_month": self.max_analyses_per_month,
            "max_agents": self.max_agents,
            "features": self.features or [],
            "trial_days": self.trial_days,
            "is_free": self.is_free,
            "stripe_price_id_monthly": self.stripe_price_id_monthly,
            "stripe_price_id_yearly": self.stripe_price_id_yearly,
        }


class Subscription(Base):
    """Tenant subscriptions"""
    
    __tablename__ = "subscriptions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id = Column(GUID(), ForeignKey("subscription_plans.id"), nullable=False)
    
    # Stripe
    stripe_subscription_id = Column(String(100), unique=True)
    stripe_customer_id = Column(String(100))
    
    # Status: trialing, active, past_due, canceled, expired
    status = Column(String(30), default="trialing", index=True)
    
    # Billing
    billing_period = Column(String(20), default="monthly")
    
    # Trial
    trial_start = Column(DateTime)
    trial_end = Column(DateTime, index=True)
    is_trial = Column(Boolean, default=False)
    trial_expired_notified = Column(Boolean, default=False)
    
    # Period
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    canceled_at = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Access Control
    is_read_only = Column(Boolean, default=False)
    grace_period_end = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    invoices = relationship("BillingInvoice", back_populates="subscription")
    
    @property
    def is_active_subscription(self) -> bool:
        """Check if subscription allows full access"""
        if self.status in ["active", "trialing"]:
            if self.is_trial and self.trial_end:
                return datetime.utcnow() < self.trial_end
            return True
        return False
    
    @property
    def trial_days_remaining(self) -> int:
        """Get remaining trial days"""
        if not self.is_trial or not self.trial_end:
            return 0
        delta = self.trial_end - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def should_be_read_only(self) -> bool:
        """Check if account should be read-only"""
        if self.status in ["canceled", "expired", "past_due"]:
            return True
        if self.is_trial and self.trial_end and datetime.utcnow() > self.trial_end:
            return True
        return False
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "plan_id": str(self.plan_id),
            "status": self.status,
            "billing_period": self.billing_period,
            "is_trial": self.is_trial,
            "trial_days_remaining": self.trial_days_remaining,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "is_read_only": self.is_read_only or self.should_be_read_only,
            "is_active": self.is_active_subscription,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "stripe_subscription_id": self.stripe_subscription_id,
        }


class BillingInvoice(Base):
    """Invoice history"""
    
    __tablename__ = "billing_invoices"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id", ondelete="SET NULL"))
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Stripe
    stripe_invoice_id = Column(String(100), unique=True)
    stripe_payment_intent_id = Column(String(100))
    
    # Details
    invoice_number = Column(String(50))
    status = Column(String(30), default="draft", index=True)
    
    # Amounts (cents)
    subtotal = Column(Integer, default=0)
    tax = Column(Integer, default=0)
    total = Column(Integer, default=0)
    amount_paid = Column(Integer, default=0)
    amount_due = Column(Integer, default=0)
    currency = Column(String(3), default="USD")
    
    # Dates
    invoice_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    
    # URLs
    invoice_pdf_url = Column(Text)
    hosted_invoice_url = Column(Text)
    
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")


class PaymentMethod(Base):
    """Stored payment methods"""
    
    __tablename__ = "payment_methods"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Stripe
    stripe_payment_method_id = Column(String(100), unique=True, nullable=False)
    stripe_customer_id = Column(String(100))
    
    # Card details (masked)
    type = Column(String(30), default="card")
    card_brand = Column(String(30))
    card_last4 = Column(String(4))
    card_exp_month = Column(Integer)
    card_exp_year = Column(Integer)
    
    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "type": self.type,
            "card_brand": self.card_brand,
            "card_last4": self.card_last4,
            "card_exp_month": self.card_exp_month,
            "card_exp_year": self.card_exp_year,
            "is_default": self.is_default,
        }


class RegistrationSession(Base):
    """Self-service registration sessions"""
    
    __tablename__ = "registration_sessions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(100), unique=True, nullable=False, index=True)
    
    # User Info
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(50))
    full_name = Column(String(255))
    company_name = Column(String(255))
    phone = Column(String(50))
    
    # Plan
    selected_plan_id = Column(GUID(), ForeignKey("subscription_plans.id"))
    billing_period = Column(String(20), default="monthly")
    
    # Stripe
    stripe_checkout_session_id = Column(String(100))
    stripe_customer_id = Column(String(100))
    
    # Status: pending, payment_pending, completed, expired, failed
    status = Column(String(30), default="pending")
    # Steps: info, plan, payment, setup, complete
    current_step = Column(String(30), default="info")
    
    # After completion
    user_id = Column(GUID(), ForeignKey("users.id"))
    tenant_id = Column(GUID(), ForeignKey("tenants.id"))
    
    # Tracking
    ip_address = Column(String(45))
    user_agent = Column(Text)
    referral_source = Column(String(100))
    
    # Dates
    expires_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    selected_plan = relationship("SubscriptionPlan")
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def to_dict(self):
        return {
            "session_token": self.session_token,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "company_name": self.company_name,
            "status": self.status,
            "current_step": self.current_step,
            "selected_plan_id": str(self.selected_plan_id) if self.selected_plan_id else None,
            "billing_period": self.billing_period,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
        }
