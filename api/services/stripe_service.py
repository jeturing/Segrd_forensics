"""
Stripe Service - Direct integration with Stripe API
Handles customers, subscriptions, invoices, payment methods, and webhooks
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import stripe

from api.config import settings
from api.models.billing import (
    CustomerResponse,
    SubscriptionResponse,
    InvoiceResponse,
    DiscountResponse,
    SubscriptionStatus,
    InvoiceStatus,
)

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
if settings.STRIPE_ENABLED and settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    logger.info(f"🔵 Stripe initialized in {settings.STRIPE_ENVIRONMENT} mode")
else:
    logger.warning("⚠️ Stripe not configured - billing features disabled")


class StripeService:
    """Service for interacting with Stripe API"""

    def __init__(self):
        self.enabled = (
            settings.STRIPE_ENABLED and settings.STRIPE_SECRET_KEY is not None
        )
        if not self.enabled:
            logger.warning("⚠️ StripeService initialized but disabled (no API key)")

    # =========================================================================
    # Customer Management
    # =========================================================================

    async def create_customer(
        self,
        tenant_id: str,
        email: str,
        name: str,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> CustomerResponse:
        """
        Create a new Stripe customer

        Args:
            tenant_id: Internal tenant ID
            email: Customer email
            name: Customer name
            phone: Customer phone (optional)
            description: Customer description (optional)
            metadata: Additional metadata (optional)

        Returns:
            CustomerResponse with Stripe customer details
        """
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            # Merge tenant_id into metadata
            customer_metadata = metadata or {}
            customer_metadata["tenant_id"] = tenant_id

            # Create customer in Stripe
            customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone,
                description=description or f"MCP Forensics - {tenant_id}",
                metadata=customer_metadata,
            )

            logger.info(
                f"✅ Stripe customer created: {customer.id} for tenant {tenant_id}"
            )

            return CustomerResponse(
                id=customer.id,
                tenant_id=tenant_id,
                email=customer.email,
                name=customer.name,
                created=datetime.fromtimestamp(customer.created),
                currency=customer.currency or settings.BILLING_CURRENCY,
                balance=customer.balance,
                delinquent=customer.delinquent,
                metadata=customer.metadata,
            )

        except stripe.error.StripeError as e:
            logger.error(f"❌ Stripe customer creation failed: {e}")
            raise Exception(f"Failed to create Stripe customer: {str(e)}")

    async def get_customer(self, customer_id: str) -> CustomerResponse:
        """Get customer details from Stripe"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            customer = stripe.Customer.retrieve(customer_id)

            return CustomerResponse(
                id=customer.id,
                tenant_id=customer.metadata.get("tenant_id", ""),
                email=customer.email,
                name=customer.name or "",
                created=datetime.fromtimestamp(customer.created),
                currency=customer.currency or settings.BILLING_CURRENCY,
                balance=customer.balance,
                delinquent=customer.delinquent,
                metadata=customer.metadata,
            )

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to retrieve Stripe customer: {e}")
            raise Exception(f"Failed to retrieve customer: {str(e)}")

    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> CustomerResponse:
        """Update customer information"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            update_data = {}
            if email:
                update_data["email"] = email
            if name:
                update_data["name"] = name
            if phone:
                update_data["phone"] = phone
            if metadata:
                update_data["metadata"] = metadata

            stripe.Customer.modify(customer_id, **update_data)

            logger.info(f"✅ Customer {customer_id} updated")

            return await self.get_customer(customer_id)

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to update customer: {e}")
            raise Exception(f"Failed to update customer: {str(e)}")

    # =========================================================================
    # Subscription Management
    # =========================================================================

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None,
        coupon: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> SubscriptionResponse:
        """
        Create a subscription for a customer

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID for the plan
            trial_period_days: Trial period in days (optional)
            coupon: Coupon code to apply (optional)
            metadata: Additional metadata (optional)

        Returns:
            SubscriptionResponse with subscription details
        """
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
            }

            # Add trial period if specified
            if trial_period_days:
                subscription_data["trial_period_days"] = trial_period_days
            elif settings.BILLING_TRIAL_PERIOD_DAYS > 0:
                subscription_data["trial_period_days"] = (
                    settings.BILLING_TRIAL_PERIOD_DAYS
                )

            # Add coupon if specified
            if coupon:
                subscription_data["coupon"] = coupon

            # Create subscription
            subscription = stripe.Subscription.create(**subscription_data)

            logger.info(
                f"✅ Subscription created: {subscription.id} for customer {customer_id}"
            )

            return self._subscription_to_response(subscription)

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to create subscription: {e}")
            raise Exception(f"Failed to create subscription: {str(e)}")

    async def get_subscription(self, subscription_id: str) -> SubscriptionResponse:
        """Get subscription details"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return self._subscription_to_response(subscription)

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to retrieve subscription: {e}")
            raise Exception(f"Failed to retrieve subscription: {str(e)}")

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> SubscriptionResponse:
        """
        Cancel a subscription

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period; if False, cancel immediately

        Returns:
            Updated SubscriptionResponse
        """
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id, cancel_at_period_end=True
                )
                logger.info(
                    f"✅ Subscription {subscription_id} will cancel at period end"
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
                logger.info(f"✅ Subscription {subscription_id} canceled immediately")

            return self._subscription_to_response(subscription)

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to cancel subscription: {e}")
            raise Exception(f"Failed to cancel subscription: {str(e)}")

    async def list_customer_subscriptions(
        self, customer_id: str
    ) -> List[SubscriptionResponse]:
        """List all subscriptions for a customer"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            subscriptions = stripe.Subscription.list(customer=customer_id)
            return [self._subscription_to_response(sub) for sub in subscriptions.data]

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to list subscriptions: {e}")
            raise Exception(f"Failed to list subscriptions: {str(e)}")

    # =========================================================================
    # Invoice Management
    # =========================================================================

    async def get_invoice(self, invoice_id: str) -> InvoiceResponse:
        """Get invoice details"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return self._invoice_to_response(invoice)

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to retrieve invoice: {e}")
            raise Exception(f"Failed to retrieve invoice: {str(e)}")

    async def list_customer_invoices(
        self, customer_id: str, limit: int = 10
    ) -> List[InvoiceResponse]:
        """List invoices for a customer"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            return [self._invoice_to_response(inv) for inv in invoices.data]

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to list invoices: {e}")
            raise Exception(f"Failed to list invoices: {str(e)}")

    async def get_upcoming_invoice(self, customer_id: str) -> Optional[InvoiceResponse]:
        """Get upcoming invoice for a customer"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            invoice = stripe.Invoice.upcoming(customer=customer_id)
            return self._invoice_to_response(invoice)

        except stripe.error.InvalidRequestError:
            # No upcoming invoice
            return None
        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to get upcoming invoice: {e}")
            raise Exception(f"Failed to get upcoming invoice: {str(e)}")

    # =========================================================================
    # Payment Method Management
    # =========================================================================

    async def create_setup_intent(
        self, customer_id: str, return_url: str
    ) -> Dict[str, Any]:
        """
        Create a SetupIntent for collecting payment method

        Args:
            customer_id: Stripe customer ID
            return_url: URL to redirect after setup

        Returns:
            Dict with client_secret and setup_intent_id
        """
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=["card"],
                metadata={"return_url": return_url},
            )

            logger.info(f"✅ SetupIntent created for customer {customer_id}")

            return {
                "client_secret": setup_intent.client_secret,
                "setup_intent_id": setup_intent.id,
            }

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to create SetupIntent: {e}")
            raise Exception(f"Failed to create SetupIntent: {str(e)}")

    async def attach_payment_method(
        self, payment_method_id: str, customer_id: str
    ) -> Dict[str, Any]:
        """Attach a payment method to a customer"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )

            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )

            logger.info(
                f"✅ Payment method {payment_method_id} attached to customer {customer_id}"
            )

            return {
                "id": payment_method.id,
                "type": payment_method.type,
                "card": (
                    payment_method.card if hasattr(payment_method, "card") else None
                ),
            }

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to attach payment method: {e}")
            raise Exception(f"Failed to attach payment method: {str(e)}")

    # =========================================================================
    # Coupon/Discount Management
    # =========================================================================

    async def create_coupon(
        self,
        code: str,
        percent_off: Optional[float] = None,
        amount_off: Optional[int] = None,
        duration: str = "once",
        duration_in_months: Optional[int] = None,
        max_redemptions: Optional[int] = None,
    ) -> DiscountResponse:
        """Create a discount coupon"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            coupon_data: Dict[str, Any] = {
                "id": code,
                "duration": duration,
            }

            if percent_off:
                coupon_data["percent_off"] = percent_off
            elif amount_off:
                coupon_data["amount_off"] = amount_off
                coupon_data["currency"] = settings.BILLING_CURRENCY

            if duration_in_months:
                coupon_data["duration_in_months"] = duration_in_months

            if max_redemptions:
                coupon_data["max_redemptions"] = max_redemptions

            coupon = stripe.Coupon.create(**coupon_data)

            logger.info(f"✅ Coupon created: {code}")

            return DiscountResponse(
                id=coupon.id,
                code=code,
                percent_off=coupon.percent_off,
                amount_off=coupon.amount_off,
                currency=coupon.currency,
                duration=coupon.duration,
                duration_in_months=coupon.duration_in_months,
                max_redemptions=coupon.max_redemptions,
                times_redeemed=coupon.times_redeemed,
                valid=coupon.valid,
            )

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to create coupon: {e}")
            raise Exception(f"Failed to create coupon: {str(e)}")

    async def get_coupon(self, code: str) -> DiscountResponse:
        """Get coupon details"""
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        try:
            coupon = stripe.Coupon.retrieve(code)

            return DiscountResponse(
                id=coupon.id,
                code=code,
                percent_off=coupon.percent_off,
                amount_off=coupon.amount_off,
                currency=coupon.currency,
                duration=coupon.duration,
                duration_in_months=coupon.duration_in_months,
                max_redemptions=coupon.max_redemptions,
                times_redeemed=coupon.times_redeemed,
                valid=coupon.valid,
            )

        except stripe.error.StripeError as e:
            logger.error(f"❌ Failed to retrieve coupon: {e}")
            raise Exception(f"Failed to retrieve coupon: {str(e)}")

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    async def verify_webhook_signature(
        self, payload: bytes, signature: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature and parse event

        Args:
            payload: Raw webhook payload
            signature: Stripe-Signature header value

        Returns:
            Parsed webhook event
        """
        if not self.enabled:
            raise Exception("Stripe is not enabled")

        if not settings.STRIPE_WEBHOOK_SECRET:
            raise Exception("Stripe webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )

            logger.info(f"✅ Webhook verified: {event['type']}")
            return event

        except ValueError as e:
            logger.error(f"❌ Invalid webhook payload: {e}")
            raise Exception("Invalid webhook payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"❌ Invalid webhook signature: {e}")
            raise Exception("Invalid webhook signature")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _subscription_to_response(self, subscription: Any) -> SubscriptionResponse:
        """Convert Stripe Subscription to SubscriptionResponse"""
        return SubscriptionResponse(
            id=subscription.id,
            customer_id=subscription.customer,
            tenant_id=subscription.metadata.get("tenant_id", ""),
            status=SubscriptionStatus(subscription.status),
            current_period_start=datetime.fromtimestamp(
                subscription.current_period_start
            ),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end),
            trial_start=(
                datetime.fromtimestamp(subscription.trial_start)
                if subscription.trial_start
                else None
            ),
            trial_end=(
                datetime.fromtimestamp(subscription.trial_end)
                if subscription.trial_end
                else None
            ),
            cancel_at_period_end=subscription.cancel_at_period_end,
            canceled_at=(
                datetime.fromtimestamp(subscription.canceled_at)
                if subscription.canceled_at
                else None
            ),
            metadata=subscription.metadata,
        )

    def _invoice_to_response(self, invoice: Any) -> InvoiceResponse:
        """Convert Stripe Invoice to InvoiceResponse"""
        tenant_id = ""
        if invoice.subscription:
            # Try to get tenant_id from subscription metadata
            try:
                sub = stripe.Subscription.retrieve(invoice.subscription)
                tenant_id = sub.metadata.get("tenant_id", "")
            except Exception:
                pass

        return InvoiceResponse(
            id=invoice.id,
            customer_id=invoice.customer,
            tenant_id=tenant_id,
            status=InvoiceStatus(invoice.status or "draft"),
            amount_due=invoice.amount_due,
            amount_paid=invoice.amount_paid,
            amount_remaining=invoice.amount_remaining,
            currency=invoice.currency,
            period_start=datetime.fromtimestamp(invoice.period_start),
            period_end=datetime.fromtimestamp(invoice.period_end),
            invoice_pdf=invoice.invoice_pdf,
            hosted_invoice_url=invoice.hosted_invoice_url,
            created=datetime.fromtimestamp(invoice.created),
            due_date=(
                datetime.fromtimestamp(invoice.due_date) if invoice.due_date else None
            ),
        )


# Singleton instance
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get or create StripeService singleton"""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
