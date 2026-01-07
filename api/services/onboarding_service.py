"""
Onboarding Service - Automated customer onboarding and setup
Handles registration, payment setup, plan selection, and tenant provisioning
"""

import logging
import sqlite3
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from api.config import settings
from api.services.stripe_service import get_stripe_service
from api.services.billing_service import get_billing_service

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "forensics.db"


class OnboardingStatus:
    """Onboarding status constants"""

    STARTED = "started"
    CUSTOMER_CREATED = "customer_created"
    PAYMENT_SETUP = "payment_setup"
    PLAN_SELECTED = "plan_selected"
    SUBSCRIPTION_CREATED = "subscription_created"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class OnboardingService:
    """Service for automated customer onboarding"""

    def __init__(self):
        self.stripe_service = get_stripe_service()
        self.billing_service = get_billing_service()
        self.db_path = DB_PATH

    def _get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Onboarding Flow
    # =========================================================================

    async def start_onboarding(
        self,
        email: str,
        name: str,
        company_name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start the onboarding process for a new customer

        Args:
            email: Customer email
            name: Customer name
            company_name: Company name (optional)
            phone: Phone number (optional)
            metadata: Additional metadata (optional)

        Returns:
            Dict with session_id and initial status
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())

            # Generate tenant ID in Jeturing format
            tenant_id = f"Jeturing_{uuid.uuid4()}"

            # Create onboarding session
            conn = self._get_db_connection()
            cursor = conn.cursor()

            expires_at = datetime.utcnow() + timedelta(hours=24)

            cursor.execute(
                """
                INSERT INTO onboarding_sessions
                (session_id, tenant_id, email, name, phone, company_name, 
                 status, current_step, started_at, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    tenant_id,
                    email,
                    name,
                    phone,
                    company_name,
                    OnboardingStatus.STARTED,
                    "welcome",
                    datetime.utcnow().isoformat(),
                    expires_at.isoformat(),
                    json.dumps(metadata or {}),
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"✅ Onboarding started: {session_id} for {email}")

            return {
                "session_id": session_id,
                "tenant_id": tenant_id,
                "status": OnboardingStatus.STARTED,
                "email": email,
                "name": name,
                "company_name": company_name,
                "expires_at": expires_at.isoformat(),
                "next_step": "create_customer",
            }

        except Exception as e:
            logger.error(f"❌ Failed to start onboarding: {e}")
            raise Exception(f"Failed to start onboarding: {str(e)}")

    async def create_customer_step(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Step 2: Create Stripe customer

        Args:
            session_id: Onboarding session ID

        Returns:
            Dict with customer details and next step
        """
        try:
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Onboarding session not found")

            if session["status"] != OnboardingStatus.STARTED:
                raise Exception(f"Invalid session status: {session['status']}")

            # Create Stripe customer
            customer = await self.stripe_service.create_customer(
                tenant_id=session["tenant_id"],
                email=session["email"],
                name=session["name"],
                phone=session.get("phone"),
                description=f"{session.get('company_name', session['name'])} - MCP Forensics",
                metadata={
                    "tenant_id": session["tenant_id"],
                    "onboarding_session_id": session_id,
                    "company_name": session.get("company_name", ""),
                },
            )

            # Save customer to database
            await self.billing_service.save_customer(customer.id, session["tenant_id"])

            # Update session
            await self._update_session(
                session_id,
                status=OnboardingStatus.CUSTOMER_CREATED,
                current_step="payment_setup",
                stripe_customer_id=customer.id,
            )

            logger.info(f"✅ Customer created in onboarding: {customer.id}")

            return {
                "session_id": session_id,
                "status": OnboardingStatus.CUSTOMER_CREATED,
                "customer_id": customer.id,
                "next_step": "setup_payment_method",
            }

        except Exception as e:
            await self._mark_session_failed(session_id, str(e))
            logger.error(f"❌ Failed to create customer in onboarding: {e}")
            raise Exception(f"Failed to create customer: {str(e)}")

    async def setup_payment_method_step(
        self,
        session_id: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """
        Step 3: Setup payment method using Stripe SetupIntent

        Args:
            session_id: Onboarding session ID
            return_url: URL to redirect after payment setup

        Returns:
            Dict with SetupIntent client_secret for frontend
        """
        try:
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Onboarding session not found")

            if session["status"] != OnboardingStatus.CUSTOMER_CREATED:
                raise Exception(f"Invalid session status: {session['status']}")

            customer_id = session.get("stripe_customer_id")
            if not customer_id:
                raise Exception("Customer ID not found in session")

            # Create SetupIntent
            setup_intent = await self.stripe_service.create_setup_intent(
                customer_id=customer_id,
                return_url=return_url,
            )

            # Update session
            await self._update_session(
                session_id,
                status=OnboardingStatus.PAYMENT_SETUP,
                current_step="plan_selection",
            )

            logger.info(
                f"✅ SetupIntent created for onboarding: {setup_intent['setup_intent_id']}"
            )

            return {
                "session_id": session_id,
                "status": OnboardingStatus.PAYMENT_SETUP,
                "client_secret": setup_intent["client_secret"],
                "setup_intent_id": setup_intent["setup_intent_id"],
                "next_step": "select_plan",
            }

        except Exception as e:
            await self._mark_session_failed(session_id, str(e))
            logger.error(f"❌ Failed to setup payment method: {e}")
            raise Exception(f"Failed to setup payment method: {str(e)}")

    async def select_plan_step(
        self,
        session_id: str,
        plan_id: str,
        price_id: str,
        discount_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Step 4: Select billing plan

        Args:
            session_id: Onboarding session ID
            plan_id: Plan identifier (e.g., "enterprise", "professional")
            price_id: Stripe price ID
            discount_code: Optional discount code

        Returns:
            Dict with plan selection details
        """
        try:
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Onboarding session not found")

            if session["status"] != OnboardingStatus.PAYMENT_SETUP:
                raise Exception(f"Invalid session status: {session['status']}")

            # Validate discount code if provided
            if discount_code:
                try:
                    await self.stripe_service.get_coupon(discount_code)
                except Exception:
                    logger.warning(f"⚠️ Invalid discount code: {discount_code}")
                    discount_code = None

            # Update session with plan selection
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE onboarding_sessions
                SET status = ?, current_step = ?, selected_plan = ?, discount_code = ?
                WHERE session_id = ?
                """,
                (
                    OnboardingStatus.PLAN_SELECTED,
                    "create_subscription",
                    json.dumps({"plan_id": plan_id, "price_id": price_id}),
                    discount_code,
                    session_id,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"✅ Plan selected in onboarding: {plan_id}")

            return {
                "session_id": session_id,
                "status": OnboardingStatus.PLAN_SELECTED,
                "plan_id": plan_id,
                "price_id": price_id,
                "discount_code": discount_code,
                "next_step": "create_subscription",
            }

        except Exception as e:
            await self._mark_session_failed(session_id, str(e))
            logger.error(f"❌ Failed to select plan: {e}")
            raise Exception(f"Failed to select plan: {str(e)}")

    async def create_subscription_step(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Step 5: Create subscription

        Args:
            session_id: Onboarding session ID

        Returns:
            Dict with subscription details
        """
        try:
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Onboarding session not found")

            if session["status"] != OnboardingStatus.PLAN_SELECTED:
                raise Exception(f"Invalid session status: {session['status']}")

            customer_id = session.get("stripe_customer_id")
            if not customer_id:
                raise Exception("Customer ID not found")

            selected_plan = json.loads(session.get("selected_plan", "{}"))
            price_id = selected_plan.get("price_id")
            if not price_id:
                raise Exception("Price ID not found")

            # Create subscription
            subscription = await self.stripe_service.create_subscription(
                customer_id=customer_id,
                price_id=price_id,
                trial_period_days=settings.BILLING_TRIAL_PERIOD_DAYS,
                coupon=session.get("discount_code"),
                metadata={
                    "tenant_id": session["tenant_id"],
                    "onboarding_session_id": session_id,
                },
            )

            # Save subscription to database
            await self.billing_service.save_subscription(
                subscription.id, session["tenant_id"]
            )

            # Update session
            await self._update_session(
                session_id,
                status=OnboardingStatus.SUBSCRIPTION_CREATED,
                current_step="complete",
                stripe_subscription_id=subscription.id,
            )

            logger.info(f"✅ Subscription created in onboarding: {subscription.id}")

            return {
                "session_id": session_id,
                "status": OnboardingStatus.SUBSCRIPTION_CREATED,
                "subscription_id": subscription.id,
                "trial_end": (
                    subscription.trial_end.isoformat()
                    if subscription.trial_end
                    else None
                ),
                "next_step": "complete_onboarding",
            }

        except Exception as e:
            await self._mark_session_failed(session_id, str(e))
            logger.error(f"❌ Failed to create subscription: {e}")
            raise Exception(f"Failed to create subscription: {str(e)}")

    async def complete_onboarding(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Step 6: Complete onboarding and provision tenant

        Args:
            session_id: Onboarding session ID

        Returns:
            Dict with completion details and tenant info
        """
        try:
            # Get session
            session = await self.get_session(session_id)
            if not session:
                raise Exception("Onboarding session not found")

            if session["status"] != OnboardingStatus.SUBSCRIPTION_CREATED:
                raise Exception(f"Invalid session status: {session['status']}")

            # Create or update tenant
            tenant_id = session["tenant_id"]
            await self._provision_tenant(session)
            
            # ================================================================
            # v4.6: Auto-assign TENANT_ADMIN role to the onboarding user
            # ================================================================
            try:
                from api.services.roles_service import auto_assign_tenant_admin
                
                # Buscar o crear el usuario asociado a este email
                user_id = await self._get_or_create_user_for_session(session)
                
                if user_id:
                    role_result = await auto_assign_tenant_admin(user_id, tenant_id)
                    if role_result.get('success'):
                        logger.info(f"✅ TENANT_ADMIN auto-asignado a {session['email']}")
                    else:
                        logger.warning(f"⚠️ No se pudo auto-asignar TENANT_ADMIN: {role_result.get('error')}")
                else:
                    logger.warning(f"⚠️ No se encontró/creó usuario para sesión {session_id}")
            except Exception as role_error:
                logger.warning(f"⚠️ Error en auto-asignación de rol: {role_error}")
                # No fallar el onboarding por esto
            # ================================================================

            # Mark onboarding complete
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE onboarding_sessions
                SET status = ?, current_step = ?, completed_at = ?
                WHERE session_id = ?
                """,
                (
                    OnboardingStatus.COMPLETED,
                    "completed",
                    datetime.utcnow().isoformat(),
                    session_id,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"✅ Onboarding completed: {session_id} - Tenant: {tenant_id}")

            return {
                "session_id": session_id,
                "status": OnboardingStatus.COMPLETED,
                "tenant_id": tenant_id,
                "customer_id": session.get("stripe_customer_id"),
                "subscription_id": session.get("stripe_subscription_id"),
                "message": "Onboarding completed successfully",
            }

        except Exception as e:
            await self._mark_session_failed(session_id, str(e))
            logger.error(f"❌ Failed to complete onboarding: {e}")
            raise Exception(f"Failed to complete onboarding: {str(e)}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get onboarding session details"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM onboarding_sessions WHERE session_id = ?
                """,
                (session_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return dict(row)

        except Exception as e:
            logger.error(f"❌ Failed to get session: {e}")
            return None

    async def _update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        current_step: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ):
        """Update onboarding session"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            updates = []
            params = []

            if status:
                updates.append("status = ?")
                params.append(status)

            if current_step:
                updates.append("current_step = ?")
                params.append(current_step)

            if stripe_customer_id:
                updates.append("stripe_customer_id = ?")
                params.append(stripe_customer_id)

            if stripe_subscription_id:
                updates.append("stripe_subscription_id = ?")
                params.append(stripe_subscription_id)

            if updates:
                params.append(session_id)
                query = f"UPDATE onboarding_sessions SET {', '.join(updates)} WHERE session_id = ?"
                cursor.execute(query, params)
                conn.commit()

            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to update session: {e}")
            raise

    async def _mark_session_failed(self, session_id: str, error_message: str):
        """Mark onboarding session as failed"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE onboarding_sessions
                SET status = ?, metadata = json_set(metadata, '$.error', ?)
                WHERE session_id = ?
                """,
                (OnboardingStatus.FAILED, error_message, session_id),
            )

            conn.commit()
            conn.close()

            logger.error(
                f"❌ Onboarding session failed: {session_id} - {error_message}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to mark session as failed: {e}")

    async def _provision_tenant(self, session: Dict[str, Any]):
        """Provision tenant in database"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # Check if tenant already exists
            cursor.execute(
                "SELECT tenant_id FROM tenants WHERE tenant_id = ?",
                (session["tenant_id"],),
            )

            if cursor.fetchone():
                # Update existing tenant
                cursor.execute(
                    """
                    UPDATE tenants
                    SET tenant_name = ?, billing_email = ?, stripe_customer_id = ?, 
                        subscription_status = 'active'
                    WHERE tenant_id = ?
                    """,
                    (
                        session.get("company_name", session["name"]),
                        session["email"],
                        session.get("stripe_customer_id"),
                        session["tenant_id"],
                    ),
                )
            else:
                # Create new tenant
                cursor.execute(
                    """
                    INSERT INTO tenants 
                    (tenant_id, tenant_name, primary_domain, client_id, billing_email, 
                     stripe_customer_id, status, onboarded_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (
                        session["tenant_id"],
                        session.get("company_name", session["name"]),
                        (
                            session["email"].split("@")[1]
                            if "@" in session["email"]
                            else None
                        ),
                        None,  # client_id - to be set later
                        session["email"],
                        session.get("stripe_customer_id"),
                        datetime.utcnow().isoformat(),
                    ),
                )

            conn.commit()
            conn.close()

            logger.info(f"✅ Tenant provisioned: {session['tenant_id']}")

        except Exception as e:
            logger.error(f"❌ Failed to provision tenant: {e}")
            raise

    async def _get_or_create_user_for_session(self, session: Dict[str, Any]) -> Optional[str]:
        """
        Get or create user associated with onboarding session.
        v4.6: Needed for auto-role assignment.
        
        Args:
            session: Onboarding session data
            
        Returns:
            user_id if found/created, None otherwise
        """
        try:
            import uuid
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            email = session.get("email")
            tenant_id = session.get("tenant_id")
            name = session.get("name", email.split("@")[0] if email else "User")
            
            # Check if user already exists
            cursor.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            )
            existing = cursor.fetchone()
            
            if existing:
                user_id = existing[0]
                # Update tenant_id if not set
                cursor.execute(
                    "UPDATE users SET tenant_id = ? WHERE id = ? AND tenant_id IS NULL",
                    (tenant_id, user_id)
                )
                conn.commit()
                conn.close()
                return user_id
            
            # Create new user
            user_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO users (id, email, full_name, tenant_id, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    user_id,
                    email,
                    name,
                    tenant_id,
                    datetime.utcnow().isoformat()
                )
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ User created for onboarding: {email}")
            return user_id
            
        except Exception as e:
            logger.error(f"❌ Failed to get/create user for session: {e}")
            return None


# Singleton instance
_onboarding_service: Optional[OnboardingService] = None


def get_onboarding_service() -> OnboardingService:
    """Get or create OnboardingService singleton"""
    global _onboarding_service
    if _onboarding_service is None:
        _onboarding_service = OnboardingService()
    return _onboarding_service
