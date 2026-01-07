-- Migration: Add Billing Tables for Stripe Integration
-- Version: v4.6.0
-- Date: 2024-12-16
-- Description: Creates tables for billing, subscriptions, usage tracking, and discounts

-- ============================================================================
-- Stripe Customers Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    stripe_customer_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    description TEXT,
    currency TEXT DEFAULT 'usd',
    balance INTEGER DEFAULT 0,
    delinquent INTEGER DEFAULT 0,  -- SQLite: 0=False, 1=True
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_billing_customers_tenant ON billing_customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_customers_stripe ON billing_customers(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_billing_customers_email ON billing_customers(email);

-- ============================================================================
-- Subscriptions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    stripe_subscription_id TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- active, past_due, canceled, etc.
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    cancel_at_period_end INTEGER DEFAULT 0,
    canceled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_customer_id) REFERENCES billing_customers(stripe_customer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_tenant ON billing_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_stripe ON billing_subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_customer ON billing_subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_status ON billing_subscriptions(status);

-- ============================================================================
-- Invoices Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    stripe_invoice_id TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL,  -- draft, open, paid, void, uncollectible
    amount_due INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0,
    amount_remaining INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    invoice_pdf TEXT,  -- URL to PDF
    hosted_invoice_url TEXT,  -- URL to hosted invoice
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_customer_id) REFERENCES billing_customers(stripe_customer_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_subscription_id) REFERENCES billing_subscriptions(stripe_subscription_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_invoices_tenant ON billing_invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_stripe ON billing_invoices(stripe_invoice_id);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_customer ON billing_invoices(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_status ON billing_invoices(status);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_period ON billing_invoices(period_start, period_end);

-- ============================================================================
-- Usage Records Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    usage_type TEXT NOT NULL,  -- agent, user, case, event_ingestion, api_call, platform_base
    quantity INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    billed INTEGER DEFAULT 0,  -- 0=not billed, 1=billed
    stripe_invoice_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_invoice_id) REFERENCES billing_invoices(stripe_invoice_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_usage_tenant ON billing_usage_records(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_usage_type ON billing_usage_records(usage_type);
CREATE INDEX IF NOT EXISTS idx_billing_usage_billed ON billing_usage_records(billed);
CREATE INDEX IF NOT EXISTS idx_billing_usage_timestamp ON billing_usage_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_billing_usage_invoice ON billing_usage_records(stripe_invoice_id);

-- ============================================================================
-- Discount Coupons Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_discounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_coupon_id TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE NOT NULL,
    percent_off REAL,  -- 0-100
    amount_off INTEGER,  -- in cents
    currency TEXT,
    duration TEXT NOT NULL,  -- once, repeating, forever
    duration_in_months INTEGER,
    max_redemptions INTEGER,
    times_redeemed INTEGER DEFAULT 0,
    valid INTEGER DEFAULT 1,  -- 0=invalid, 1=valid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON stored as TEXT
);

CREATE INDEX IF NOT EXISTS idx_billing_discounts_code ON billing_discounts(code);
CREATE INDEX IF NOT EXISTS idx_billing_discounts_stripe ON billing_discounts(stripe_coupon_id);
CREATE INDEX IF NOT EXISTS idx_billing_discounts_valid ON billing_discounts(valid);

-- ============================================================================
-- Applied Discounts Table (junction table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_applied_discounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    stripe_coupon_id TEXT NOT NULL,
    stripe_subscription_id TEXT,
    stripe_invoice_id TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_coupon_id) REFERENCES billing_discounts(stripe_coupon_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_subscription_id) REFERENCES billing_subscriptions(stripe_subscription_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_invoice_id) REFERENCES billing_invoices(stripe_invoice_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_applied_discounts_tenant ON billing_applied_discounts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_applied_discounts_coupon ON billing_applied_discounts(stripe_coupon_id);
CREATE INDEX IF NOT EXISTS idx_applied_discounts_subscription ON billing_applied_discounts(stripe_subscription_id);

-- ============================================================================
-- Onboarding Sessions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS onboarding_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    company_name TEXT,
    status TEXT NOT NULL DEFAULT 'started',  -- started, payment_setup, plan_selected, completed, failed
    current_step TEXT,  -- Step identifier in the wizard
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    selected_plan TEXT,
    discount_code TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata TEXT,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_customer_id) REFERENCES billing_customers(stripe_customer_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_onboarding_session_id ON onboarding_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_tenant ON onboarding_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_status ON onboarding_sessions(status);
CREATE INDEX IF NOT EXISTS idx_onboarding_email ON onboarding_sessions(email);

-- ============================================================================
-- Payment Methods Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    stripe_payment_method_id TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,  -- card, bank_account, etc.
    is_default INTEGER DEFAULT 0,  -- 0=False, 1=True
    last4 TEXT,  -- Last 4 digits of card/account
    brand TEXT,  -- visa, mastercard, etc.
    exp_month INTEGER,
    exp_year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (stripe_customer_id) REFERENCES billing_customers(stripe_customer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_tenant ON billing_payment_methods(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payment_methods_customer ON billing_payment_methods(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_payment_methods_stripe ON billing_payment_methods(stripe_payment_method_id);

-- ============================================================================
-- Webhook Events Log Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    tenant_id TEXT,
    processed INTEGER DEFAULT 0,  -- 0=not processed, 1=processed
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    event_data TEXT NOT NULL,  -- JSON stored as TEXT
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_stripe ON billing_webhook_events(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON billing_webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON billing_webhook_events(processed);
CREATE INDEX IF NOT EXISTS idx_webhook_events_tenant ON billing_webhook_events(tenant_id);

-- ============================================================================
-- Update tenants table to add billing-related columns
-- ============================================================================
-- Check if column exists before adding (SQLite doesn't have IF NOT EXISTS for ALTER TABLE)
-- These will be executed conditionally in the migration script

-- Add stripe_customer_id to tenants table
-- ALTER TABLE tenants ADD COLUMN stripe_customer_id TEXT;

-- Add billing_plan to tenants table
-- ALTER TABLE tenants ADD COLUMN billing_plan TEXT DEFAULT 'enterprise';

-- Add subscription_status to tenants table
-- ALTER TABLE tenants ADD COLUMN subscription_status TEXT DEFAULT 'active';

-- Add trial_ends_at to tenants table
-- ALTER TABLE tenants ADD COLUMN trial_ends_at TIMESTAMP;

-- ============================================================================
-- Views for Reporting
-- ============================================================================

-- View: Current billing status by tenant
CREATE VIEW IF NOT EXISTS v_tenant_billing_status AS
SELECT 
    t.tenant_id,
    t.tenant_name,
    bc.stripe_customer_id,
    bc.email,
    bc.delinquent,
    bs.stripe_subscription_id,
    bs.status AS subscription_status,
    bs.current_period_end,
    bs.trial_end,
    COUNT(DISTINCT bu.id) AS unbilled_usage_count,
    SUM(CASE WHEN bu.billed = 0 THEN bu.amount_cents ELSE 0 END) AS unbilled_amount_cents
FROM tenants t
LEFT JOIN billing_customers bc ON t.tenant_id = bc.tenant_id
LEFT JOIN billing_subscriptions bs ON bc.stripe_customer_id = bs.stripe_customer_id AND bs.status = 'active'
LEFT JOIN billing_usage_records bu ON t.tenant_id = bu.tenant_id AND bu.billed = 0
GROUP BY t.tenant_id, t.tenant_name, bc.stripe_customer_id, bc.email, bc.delinquent, 
         bs.stripe_subscription_id, bs.status, bs.current_period_end, bs.trial_end;

-- View: Usage summary by tenant and type
CREATE VIEW IF NOT EXISTS v_usage_summary_by_type AS
SELECT 
    tenant_id,
    usage_type,
    COUNT(*) AS usage_count,
    SUM(quantity) AS total_quantity,
    SUM(amount_cents) AS total_amount_cents,
    MIN(timestamp) AS first_usage,
    MAX(timestamp) AS last_usage,
    SUM(CASE WHEN billed = 1 THEN 1 ELSE 0 END) AS billed_count,
    SUM(CASE WHEN billed = 0 THEN 1 ELSE 0 END) AS unbilled_count
FROM billing_usage_records
GROUP BY tenant_id, usage_type;

-- View: Monthly invoice summary
CREATE VIEW IF NOT EXISTS v_monthly_invoice_summary AS
SELECT 
    tenant_id,
    strftime('%Y-%m', period_start) AS month,
    COUNT(*) AS invoice_count,
    SUM(amount_due) AS total_due,
    SUM(amount_paid) AS total_paid,
    SUM(amount_remaining) AS total_remaining,
    SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_invoices,
    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_invoices
FROM billing_invoices
GROUP BY tenant_id, strftime('%Y-%m', period_start);

-- ============================================================================
-- Triggers for updating timestamps
-- ============================================================================

-- Trigger: Update billing_customers.updated_at on update
CREATE TRIGGER IF NOT EXISTS trigger_update_billing_customers_timestamp 
AFTER UPDATE ON billing_customers
BEGIN
    UPDATE billing_customers 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Trigger: Update billing_subscriptions.updated_at on update
CREATE TRIGGER IF NOT EXISTS trigger_update_billing_subscriptions_timestamp 
AFTER UPDATE ON billing_subscriptions
BEGIN
    UPDATE billing_subscriptions 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Trigger: Update billing_invoices.updated_at on update
CREATE TRIGGER IF NOT EXISTS trigger_update_billing_invoices_timestamp 
AFTER UPDATE ON billing_invoices
BEGIN
    UPDATE billing_invoices 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Trigger: Update billing_payment_methods.updated_at on update
CREATE TRIGGER IF NOT EXISTS trigger_update_payment_methods_timestamp 
AFTER UPDATE ON billing_payment_methods
BEGIN
    UPDATE billing_payment_methods 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Trigger: Increment times_redeemed when discount is applied
CREATE TRIGGER IF NOT EXISTS trigger_increment_discount_redemptions 
AFTER INSERT ON billing_applied_discounts
BEGIN
    UPDATE billing_discounts 
    SET times_redeemed = times_redeemed + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE stripe_coupon_id = NEW.stripe_coupon_id;
END;

-- ============================================================================
-- Sample Data (for testing - can be removed in production)
-- ============================================================================

-- Insert sample discount codes
INSERT OR IGNORE INTO billing_discounts (stripe_coupon_id, code, percent_off, duration, valid, metadata)
VALUES 
    ('STRIPE_TEST_LAUNCH50', 'LAUNCH50', 50.0, 'once', 1, '{"description":"Launch promotion - 50% off first month"}'),
    ('STRIPE_TEST_TRIAL30', 'TRIAL30', 30.0, 'repeating', 1, '{"description":"30% off for 3 months", "duration_in_months":3}');
