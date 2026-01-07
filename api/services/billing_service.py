"""
Billing Service - Business logic for billing operations
Handles usage tracking, invoice generation, and billing calculations
"""

import logging
import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from api.config import settings
from api.models.billing import (
    UsageType,
    UsageRecordResponse,
    UsageSummary,
    BillingStatus,
    SubscriptionStatus,
)
from api.services.stripe_service import get_stripe_service

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "forensics.db"


class BillingService:
    """Service for billing business logic and usage tracking"""

    def __init__(self):
        self.stripe_service = get_stripe_service()
        self.db_path = DB_PATH
        self._ensure_tables()

    def _get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        """Ensure billing tables exist"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Check if billing tables exist
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='billing_usage_records'"
            )
            if not cursor.fetchone():
                logger.warning(
                    "⚠️ Billing tables not found - run migration: migrations/add_billing_tables.sql"
                )

            conn.close()
        except Exception as e:
            logger.error(f"❌ Error checking billing tables: {e}")

    # =========================================================================
    # Usage Tracking
    # =========================================================================

    async def record_usage(
        self,
        tenant_id: str,
        usage_type: UsageType,
        quantity: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecordResponse:
        """
        Record usage for billing

        Args:
            tenant_id: Tenant ID
            usage_type: Type of usage (agent, user, case, etc.)
            quantity: Quantity of usage
            metadata: Additional context

        Returns:
            UsageRecordResponse
        """
        try:
            # Calculate cost based on usage type and quantity
            amount_cents = self._calculate_cost(usage_type, quantity)

            # Store usage record in database
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO billing_usage_records 
                (tenant_id, usage_type, quantity, amount_cents, timestamp, billed, metadata)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    tenant_id,
                    usage_type.value,
                    quantity,
                    amount_cents,
                    datetime.utcnow().isoformat(),
                    json.dumps(metadata or {}),
                ),
            )

            usage_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(
                f"✅ Usage recorded: {tenant_id} - {usage_type.value} x{quantity} = ${amount_cents/100:.2f}"
            )

            return UsageRecordResponse(
                id=str(usage_id),
                tenant_id=tenant_id,
                usage_type=usage_type,
                quantity=quantity,
                timestamp=datetime.utcnow(),
                billed=False,
                invoice_id=None,
                amount_cents=amount_cents,
                metadata=metadata or {},
            )

        except Exception as e:
            logger.error(f"❌ Failed to record usage: {e}")
            raise Exception(f"Failed to record usage: {str(e)}")

    def _calculate_cost(self, usage_type: UsageType, quantity: int) -> int:
        """
        Calculate cost in cents for usage

        Args:
            usage_type: Type of usage
            quantity: Quantity used

        Returns:
            Cost in cents
        """
        rates = {
            UsageType.AGENT: settings.BILLING_RATE_PER_AGENT_MONTHLY,
            UsageType.USER: settings.BILLING_RATE_PER_USER_MONTHLY,
            UsageType.CASE: settings.BILLING_RATE_PER_CASE,
            UsageType.EVENT_INGESTION: settings.BILLING_RATE_PER_EVENT_INGESTION,
            UsageType.API_CALL: settings.BILLING_RATE_API_CALL,
            UsageType.PLATFORM_BASE: settings.BILLING_RATE_PLATFORM_BASE,
        }

        rate = rates.get(usage_type, 0)

        # API calls are billed per 1000 calls
        if usage_type == UsageType.API_CALL:
            return int((quantity / 1000) * rate)

        return rate * quantity

    async def get_usage_summary(
        self,
        tenant_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> UsageSummary:
        """
        Get usage summary for a billing period

        Args:
            tenant_id: Tenant ID
            period_start: Start of period (default: beginning of current month)
            period_end: End of period (default: now)

        Returns:
            UsageSummary with aggregated usage
        """
        try:
            # Default to current month if not specified
            if period_start is None:
                now = datetime.utcnow()
                period_start = datetime(now.year, now.month, 1)

            if period_end is None:
                period_end = datetime.utcnow()

            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Query usage records for period
            cursor.execute(
                """
                SELECT usage_type, SUM(quantity) as total_quantity, SUM(amount_cents) as total_cost
                FROM billing_usage_records
                WHERE tenant_id = ? AND timestamp >= ? AND timestamp <= ?
                GROUP BY usage_type
                """,
                (tenant_id, period_start.isoformat(), period_end.isoformat()),
            )

            rows = cursor.fetchall()
            conn.close()

            usage_by_type = {}
            costs_by_type = {}
            total_cost_cents = 0

            for row in rows:
                usage_type = UsageType(row["usage_type"])
                quantity = row["total_quantity"]
                cost = row["total_cost"]

                usage_by_type[usage_type] = quantity
                costs_by_type[usage_type] = cost
                total_cost_cents += cost

            return UsageSummary(
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                usage_by_type=usage_by_type,
                costs_by_type=costs_by_type,
                total_cost_cents=total_cost_cents,
                total_cost_usd=total_cost_cents / 100,
            )

        except Exception as e:
            logger.error(f"❌ Failed to get usage summary: {e}")
            raise Exception(f"Failed to get usage summary: {str(e)}")

    async def get_unbilled_usage(
        self,
        tenant_id: str,
        limit: int = 100,
    ) -> List[UsageRecordResponse]:
        """Get unbilled usage records for a tenant"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, tenant_id, usage_type, quantity, amount_cents, 
                       timestamp, billed, stripe_invoice_id, metadata
                FROM billing_usage_records
                WHERE tenant_id = ? AND billed = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            )

            rows = cursor.fetchall()
            conn.close()

            records = []
            for row in rows:
                records.append(
                    UsageRecordResponse(
                        id=str(row["id"]),
                        tenant_id=row["tenant_id"],
                        usage_type=UsageType(row["usage_type"]),
                        quantity=row["quantity"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        billed=bool(row["billed"]),
                        invoice_id=row["stripe_invoice_id"],
                        amount_cents=row["amount_cents"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    )
                )

            return records

        except Exception as e:
            logger.error(f"❌ Failed to get unbilled usage: {e}")
            raise Exception(f"Failed to get unbilled usage: {str(e)}")

    async def mark_usage_billed(
        self,
        tenant_id: str,
        invoice_id: str,
        usage_ids: Optional[List[str]] = None,
    ):
        """Mark usage records as billed"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            if usage_ids:
                # Mark specific usage records
                placeholders = ",".join("?" * len(usage_ids))
                cursor.execute(
                    f"""
                    UPDATE billing_usage_records
                    SET billed = 1, stripe_invoice_id = ?
                    WHERE id IN ({placeholders})
                    """,
                    [invoice_id] + usage_ids,
                )
            else:
                # Mark all unbilled usage for tenant
                cursor.execute(
                    """
                    UPDATE billing_usage_records
                    SET billed = 1, stripe_invoice_id = ?
                    WHERE tenant_id = ? AND billed = 0
                    """,
                    (invoice_id, tenant_id),
                )

            conn.commit()
            conn.close()

            logger.info(f"✅ Usage marked as billed for invoice {invoice_id}")

        except Exception as e:
            logger.error(f"❌ Failed to mark usage as billed: {e}")
            raise Exception(f"Failed to mark usage as billed: {str(e)}")

    # =========================================================================
    # Billing Status
    # =========================================================================

    async def get_billing_status(self, tenant_id: str) -> BillingStatus:
        """
        Get comprehensive billing status for a tenant

        Args:
            tenant_id: Tenant ID

        Returns:
            BillingStatus with current billing information
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Get customer info
            cursor.execute(
                """
                SELECT stripe_customer_id, delinquent, balance
                FROM billing_customers
                WHERE tenant_id = ?
                """,
                (tenant_id,),
            )
            customer_row = cursor.fetchone()

            if not customer_row:
                # No billing setup yet
                conn.close()
                return BillingStatus(
                    tenant_id=tenant_id,
                    has_active_subscription=False,
                    payment_method_configured=False,
                )

            customer_id = customer_row["stripe_customer_id"]
            is_delinquent = bool(customer_row["delinquent"])
            balance = customer_row["balance"]

            # Get active subscription
            cursor.execute(
                """
                SELECT stripe_subscription_id, status, current_period_end, trial_end
                FROM billing_subscriptions
                WHERE stripe_customer_id = ? AND status IN ('active', 'trialing')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (customer_id,),
            )
            subscription_row = cursor.fetchone()

            has_active_subscription = subscription_row is not None
            subscription_status = None
            current_period_end = None
            trial_ends_at = None

            if subscription_row:
                subscription_status = SubscriptionStatus(subscription_row["status"])
                current_period_end = datetime.fromisoformat(
                    subscription_row["current_period_end"]
                )
                if subscription_row["trial_end"]:
                    trial_ends_at = datetime.fromisoformat(
                        subscription_row["trial_end"]
                    )

            # Check for payment method
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM billing_payment_methods
                WHERE stripe_customer_id = ?
                """,
                (customer_id,),
            )
            payment_method_row = cursor.fetchone()
            payment_method_configured = payment_method_row["count"] > 0

            # Get upcoming invoice estimate
            next_invoice_amount = None
            next_invoice_date = None
            try:
                upcoming = await self.stripe_service.get_upcoming_invoice(customer_id)
                if upcoming:
                    next_invoice_amount = upcoming.amount_due
                    next_invoice_date = upcoming.period_end
            except Exception:
                pass

            conn.close()

            return BillingStatus(
                tenant_id=tenant_id,
                customer_id=customer_id,
                has_active_subscription=has_active_subscription,
                subscription_status=subscription_status,
                trial_ends_at=trial_ends_at,
                current_period_end=current_period_end,
                is_delinquent=is_delinquent,
                outstanding_balance_cents=balance,
                next_invoice_amount_cents=next_invoice_amount,
                next_invoice_date=next_invoice_date,
                payment_method_configured=payment_method_configured,
            )

        except Exception as e:
            logger.error(f"❌ Failed to get billing status: {e}")
            raise Exception(f"Failed to get billing status: {str(e)}")

    # =========================================================================
    # Database Persistence
    # =========================================================================

    async def save_customer(self, customer_id: str, tenant_id: str):
        """Save Stripe customer to database"""
        try:
            customer = await self.stripe_service.get_customer(customer_id)

            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO billing_customers
                (tenant_id, stripe_customer_id, email, name, phone, currency, balance, delinquent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    customer.id,
                    customer.email,
                    customer.name,
                    None,  # phone
                    customer.currency,
                    customer.balance,
                    1 if customer.delinquent else 0,
                    json.dumps(customer.metadata),
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"✅ Customer {customer_id} saved to database")

        except Exception as e:
            logger.error(f"❌ Failed to save customer: {e}")
            raise

    async def save_subscription(self, subscription_id: str, tenant_id: str):
        """Save Stripe subscription to database"""
        try:
            subscription = await self.stripe_service.get_subscription(subscription_id)

            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO billing_subscriptions
                (tenant_id, stripe_subscription_id, stripe_customer_id, status,
                 current_period_start, current_period_end, trial_start, trial_end,
                 cancel_at_period_end, canceled_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    subscription.id,
                    subscription.customer_id,
                    subscription.status.value,
                    subscription.current_period_start.isoformat(),
                    subscription.current_period_end.isoformat(),
                    (
                        subscription.trial_start.isoformat()
                        if subscription.trial_start
                        else None
                    ),
                    (
                        subscription.trial_end.isoformat()
                        if subscription.trial_end
                        else None
                    ),
                    1 if subscription.cancel_at_period_end else 0,
                    (
                        subscription.canceled_at.isoformat()
                        if subscription.canceled_at
                        else None
                    ),
                    json.dumps(subscription.metadata),
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"✅ Subscription {subscription_id} saved to database")

        except Exception as e:
            logger.error(f"❌ Failed to save subscription: {e}")
            raise

    async def save_invoice(self, invoice_id: str, tenant_id: str):
        """Save Stripe invoice to database"""
        try:
            invoice = await self.stripe_service.get_invoice(invoice_id)

            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO billing_invoices
                (tenant_id, stripe_invoice_id, stripe_customer_id, status,
                 amount_due, amount_paid, amount_remaining, currency,
                 period_start, period_end, invoice_pdf, hosted_invoice_url, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    invoice.id,
                    invoice.customer_id,
                    invoice.status.value,
                    invoice.amount_due,
                    invoice.amount_paid,
                    invoice.amount_remaining,
                    invoice.currency,
                    invoice.period_start.isoformat(),
                    invoice.period_end.isoformat(),
                    invoice.invoice_pdf,
                    invoice.hosted_invoice_url,
                    invoice.due_date.isoformat() if invoice.due_date else None,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"✅ Invoice {invoice_id} saved to database")

        except Exception as e:
            logger.error(f"❌ Failed to save invoice: {e}")
            raise


# Singleton instance
_billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    """Get or create BillingService singleton"""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
