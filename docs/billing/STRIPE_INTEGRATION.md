# Stripe Billing Integration Guide

## Overview

MCP Kali Forensics integrates with Stripe for automated billing and payment processing. The system supports:

- **Subscription-based billing**: Monthly/yearly plans with automatic renewals
- **Usage-based billing**: Per-agent, per-user, per-case, per-event, and API usage metering
- **Automated onboarding**: 6-step wizard from registration to full provisioning
- **Discount management**: Coupon codes and promotional discounts
- **Multi-tenant isolation**: Each tenant (Jeturing_{GUID}) has independent billing

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Stripe Configuration
STRIPE_ENABLED=true
STRIPE_SECRET_KEY=sk_test_your_test_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_ENVIRONMENT=test

# Billing Rates (in USD cents)
BILLING_RATE_PER_AGENT_MONTHLY=5000      # $50.00/month per agent
BILLING_RATE_PER_USER_MONTHLY=2500       # $25.00/month per user
BILLING_RATE_PER_CASE=1000               # $10.00 per case
BILLING_RATE_PER_EVENT_INGESTION=1       # $0.01 per event
BILLING_RATE_API_CALL=10                 # $0.10 per 1000 API calls
BILLING_RATE_PLATFORM_BASE=10000         # $100.00/month base platform fee

# Billing Configuration
BILLING_CURRENCY=usd
BILLING_TRIAL_PERIOD_DAYS=14
```

### Database Migration

Run the billing tables migration:

```bash
sqlite3 forensics.db < migrations/add_billing_tables.sql
```

This creates:
- `billing_customers` - Stripe customer records
- `billing_subscriptions` - Active subscriptions
- `billing_invoices` - Invoice history
- `billing_usage_records` - Usage tracking
- `billing_payment_methods` - Payment method details
- `billing_discounts` - Coupon codes
- `onboarding_sessions` - Onboarding wizard state

## Stripe Setup

### 1. Create Stripe Account

1. Sign up at https://stripe.com
2. Get your API keys from the Dashboard
3. Use test keys for development (`sk_test_...` and `pk_test_...`)

### 2. Create Products and Prices

In Stripe Dashboard:

1. Go to **Products** → **Add Product**
2. Create products for each plan (Enterprise, Professional, Basic)
3. Add monthly/yearly prices for each product
4. Copy the Price IDs (e.g., `price_1ABC123...`)

### 3. Configure Webhook

1. Go to **Developers** → **Webhooks** → **Add endpoint**
2. Set URL: `https://your-domain.com/api/v1/billing/webhooks`
3. Select events:
   - `customer.created`
   - `customer.updated`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `subscription.created`
   - `subscription.updated`
   - `subscription.deleted`
4. Copy the webhook signing secret (`whsec_...`)

## Usage

### Automated Onboarding Flow

The onboarding flow guides new customers through 6 steps:

#### Step 1: Start Onboarding

```bash
POST /api/v1/onboarding/start
Content-Type: application/json
X-API-Key: your-api-key

{
  "email": "customer@example.com",
  "name": "John Doe",
  "company_name": "ACME Corp",
  "phone": "+1234567890"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "session_id": "uuid-here",
    "tenant_id": "Jeturing_guid-here",
    "status": "started",
    "next_step": "create_customer"
  }
}
```

#### Step 2: Create Stripe Customer

```bash
POST /api/v1/onboarding/step/create-customer
{
  "session_id": "uuid-from-step-1"
}
```

#### Step 3: Setup Payment Method

```bash
POST /api/v1/onboarding/step/setup-payment
{
  "session_id": "uuid-from-step-1",
  "return_url": "https://your-app.com/onboarding/complete"
}
```

Response includes `client_secret` for Stripe.js:
```json
{
  "success": true,
  "data": {
    "client_secret": "seti_1ABC123...",
    "setup_intent_id": "seti_1ABC123",
    "next_step": "select_plan"
  }
}
```

Use this client_secret with Stripe Elements on your frontend:

```javascript
const stripe = Stripe('pk_test_your_publishable_key');
const { error } = await stripe.confirmSetup({
  elements,
  clientSecret,
  confirmParams: {
    return_url: 'https://your-app.com/onboarding/complete',
  },
});
```

#### Step 4: Select Plan

```bash
POST /api/v1/onboarding/step/select-plan
{
  "session_id": "uuid-from-step-1",
  "plan_id": "enterprise",
  "price_id": "price_1ABC123...",
  "discount_code": "LAUNCH50"
}
```

#### Step 5: Create Subscription

```bash
POST /api/v1/onboarding/step/create-subscription
{
  "session_id": "uuid-from-step-1"
}
```

#### Step 6: Complete Onboarding

```bash
POST /api/v1/onboarding/complete
{
  "session_id": "uuid-from-step-1"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "tenant_id": "Jeturing_guid-here",
    "customer_id": "cus_ABC123",
    "subscription_id": "sub_ABC123",
    "status": "completed",
    "message": "Onboarding completed! Your account is ready."
  }
}
```

### Manual Billing Operations

#### Create Customer

```bash
POST /api/v1/billing/customers
{
  "tenant_id": "Jeturing_123",
  "email": "customer@example.com",
  "name": "John Doe"
}
```

#### Create Subscription

```bash
POST /api/v1/billing/subscriptions
{
  "tenant_id": "Jeturing_123",
  "customer_id": "cus_ABC123",
  "price_id": "price_1ABC123...",
  "trial_period_days": 14,
  "discount_code": "LAUNCH50"
}
```

#### Record Usage

```bash
POST /api/v1/billing/usage
{
  "tenant_id": "Jeturing_123",
  "usage_type": "case",
  "quantity": 1,
  "metadata": {
    "case_id": "IR-2024-001"
  }
}
```

Usage types:
- `agent` - Per agent ($50/month each)
- `user` - Per user ($25/month each)
- `case` - Per case ($10 each)
- `event_ingestion` - Per event ($0.01 each)
- `api_call` - Per 1000 API calls ($0.10)
- `platform_base` - Platform base fee ($100/month)

#### Get Usage Summary

```bash
GET /api/v1/billing/usage/tenant/Jeturing_123/summary
    ?period_start=2024-01-01T00:00:00Z
    &period_end=2024-01-31T23:59:59Z
```

#### Get Billing Status

```bash
GET /api/v1/billing/status/tenant/Jeturing_123
```

Response:
```json
{
  "tenant_id": "Jeturing_123",
  "customer_id": "cus_ABC123",
  "has_active_subscription": true,
  "subscription_status": "active",
  "trial_ends_at": "2024-02-01T00:00:00Z",
  "current_period_end": "2024-02-01T00:00:00Z",
  "is_delinquent": false,
  "outstanding_balance_cents": 0,
  "next_invoice_amount_cents": 10000,
  "payment_method_configured": true
}
```

## Automatic API Usage Tracking

The `UsageTrackingMiddleware` automatically tracks API calls:

- Batches API calls (records every 100 calls to reduce DB writes)
- Extracts tenant_id from query params, headers, or path
- Excludes health check and docs endpoints
- Non-blocking (doesn't slow down requests)

Configuration in `main.py`:
```python
if settings.STRIPE_ENABLED:
    app.add_middleware(
        UsageTrackingMiddleware,
        enabled=True,
        batch_size=100,
    )
```

## Webhook Event Handling

The webhook endpoint (`/api/v1/billing/webhooks`) handles Stripe events:

- **invoice.paid**: Marks usage records as billed
- **invoice.payment_failed**: Logs payment failure
- **subscription.created**: Saves subscription to database
- **subscription.updated**: Updates subscription status
- **subscription.deleted**: Logs cancellation

Events are verified using the webhook secret to prevent tampering.

## Discount Management

### Create Coupon

```bash
POST /api/v1/billing/discounts
{
  "code": "SUMMER2024",
  "percent_off": 25.0,
  "duration": "repeating",
  "duration_in_months": 3,
  "max_redemptions": 100
}
```

### Get Coupon

```bash
GET /api/v1/billing/discounts/SUMMER2024
```

## Testing

### Run Tests

```bash
pytest tests/test_billing.py -v
```

### Test with Stripe CLI

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. Login: `stripe login`
3. Forward webhooks:
```bash
stripe listen --forward-to http://localhost:8080/api/v1/billing/webhooks
```
4. Trigger test events:
```bash
stripe trigger invoice.paid
stripe trigger invoice.payment_failed
```

### Test Cards

Use these test card numbers with Stripe:

- **Success**: 4242 4242 4242 4242
- **Decline**: 4000 0000 0000 0002
- **Requires authentication**: 4000 0025 0000 3155

Any future expiry date and any 3-digit CVC.

## Troubleshooting

### Webhook Signature Verification Fails

- Ensure `STRIPE_WEBHOOK_SECRET` is set correctly
- Use the webhook secret from Stripe Dashboard
- Check that raw request body is passed (not parsed JSON)

### Customer Creation Fails

- Verify `STRIPE_SECRET_KEY` is valid
- Check API key has necessary permissions
- Ensure email is valid format

### Subscription Not Created

- Verify price_id exists in your Stripe account
- Check customer has valid payment method
- Review Stripe Dashboard logs

### Usage Not Recording

- Check database migration ran successfully
- Verify tenant_id is being passed correctly
- Check `UsageTrackingMiddleware` is enabled

## Production Checklist

Before going to production:

- [ ] Switch to live Stripe API keys (`sk_live_...`, `pk_live_...`)
- [ ] Update `STRIPE_ENVIRONMENT=live` in `.env`
- [ ] Configure production webhook URL in Stripe Dashboard
- [ ] Test webhook signature verification with live keys
- [ ] Set up monitoring for failed payments
- [ ] Configure Stripe radar rules for fraud prevention
- [ ] Set up Stripe tax calculation (if needed)
- [ ] Review and adjust billing rates
- [ ] Test complete onboarding flow
- [ ] Verify invoices are generated correctly
- [ ] Set up automated dunning for failed payments

## Support

For issues with:
- **Stripe integration**: Contact Stripe support or check docs.stripe.com
- **MCP billing module**: Create issue in GitHub repository
- **Configuration**: Review this guide and `.env.example`
