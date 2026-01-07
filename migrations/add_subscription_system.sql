-- ============================================================================
-- Migration: Subscription System for MCP Forensics
-- Version: 4.5.0
-- Date: 2025-12-29
-- Description: Adds subscription, billing, and trial management tables
-- ============================================================================

-- Plans table (defines available subscription plans)
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id VARCHAR(50) UNIQUE NOT NULL,  -- 'free_trial', 'professional', 'enterprise'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Pricing
    price_monthly DECIMAL(10, 2) DEFAULT 0,
    price_yearly DECIMAL(10, 2) DEFAULT 0,
    stripe_price_id_monthly VARCHAR(100),
    stripe_price_id_yearly VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Limits
    max_users INTEGER DEFAULT 1,
    max_cases INTEGER DEFAULT 10,
    max_storage_gb INTEGER DEFAULT 5,
    max_analyses_per_month INTEGER DEFAULT 50,
    max_agents INTEGER DEFAULT 0,
    
    -- Features (JSON array)
    features JSONB DEFAULT '[]',
    
    -- Trial settings
    trial_days INTEGER DEFAULT 0,
    is_free BOOLEAN DEFAULT FALSE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    
    -- Stripe Integration
    stripe_subscription_id VARCHAR(100) UNIQUE,
    stripe_customer_id VARCHAR(100),
    
    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'trialing',  -- trialing, active, past_due, canceled, expired
    
    -- Billing Period
    billing_period VARCHAR(20) DEFAULT 'monthly',  -- monthly, yearly
    
    -- Trial Management
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    is_trial BOOLEAN DEFAULT FALSE,
    trial_expired_notified BOOLEAN DEFAULT FALSE,
    
    -- Subscription Dates
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    canceled_at TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    
    -- Access Control
    is_read_only BOOLEAN DEFAULT FALSE,  -- True when trial expired or payment failed
    grace_period_end TIMESTAMP,  -- Grace period before full lockout
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id)
);

-- Billing history / Invoices
CREATE TABLE IF NOT EXISTS billing_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Stripe
    stripe_invoice_id VARCHAR(100) UNIQUE,
    stripe_payment_intent_id VARCHAR(100),
    
    -- Invoice Details
    invoice_number VARCHAR(50),
    status VARCHAR(30) NOT NULL DEFAULT 'draft',  -- draft, open, paid, void, uncollectible
    
    -- Amounts (in cents)
    subtotal INTEGER DEFAULT 0,
    tax INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    amount_paid INTEGER DEFAULT 0,
    amount_due INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Dates
    invoice_date TIMESTAMP DEFAULT NOW(),
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    
    -- PDF
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Payment Methods
CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Stripe
    stripe_payment_method_id VARCHAR(100) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(100),
    
    -- Card Details (masked)
    type VARCHAR(30) DEFAULT 'card',  -- card, bank_account, etc
    card_brand VARCHAR(30),  -- visa, mastercard, amex
    card_last4 VARCHAR(4),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    
    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Usage tracking for metered billing
CREATE TABLE IF NOT EXISTS usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Usage Type
    usage_type VARCHAR(50) NOT NULL,  -- 'case', 'analysis', 'user', 'agent', 'storage_gb'
    
    -- Quantity
    quantity INTEGER DEFAULT 1,
    
    -- Period
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Stripe
    stripe_usage_record_id VARCHAR(100),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Registration/Onboarding sessions (enhanced)
CREATE TABLE IF NOT EXISTS registration_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_token VARCHAR(100) UNIQUE NOT NULL,
    
    -- User Info
    email VARCHAR(255) NOT NULL,
    username VARCHAR(50),
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    phone VARCHAR(50),
    
    -- Plan Selection
    selected_plan_id UUID REFERENCES subscription_plans(id),
    billing_period VARCHAR(20) DEFAULT 'monthly',
    
    -- Stripe
    stripe_checkout_session_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    
    -- Status
    status VARCHAR(30) DEFAULT 'pending',  -- pending, payment_pending, completed, expired, failed
    current_step VARCHAR(30) DEFAULT 'info',  -- info, plan, payment, setup, complete
    
    -- After completion
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    
    -- Tracking
    ip_address VARCHAR(45),
    user_agent TEXT,
    referral_source VARCHAR(100),
    
    -- Dates
    expires_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- Insert Default Plans
-- ============================================================================

INSERT INTO subscription_plans (plan_id, name, description, price_monthly, price_yearly, trial_days, is_free, max_users, max_cases, max_storage_gb, max_analyses_per_month, max_agents, features, sort_order)
VALUES 
(
    'free_trial',
    'Free Trial',
    '15-day free trial with full access to all features',
    0, 0, 15, TRUE, 2, 10, 5, 50, 1,
    '["Full forensic analysis", "M365 integration", "Endpoint scanning", "Basic reports", "Email support"]'::jsonb,
    1
),
(
    'professional',
    'Professional',
    'For security teams and small organizations',
    99, 990, 0, FALSE, 5, 100, 50, 500, 3,
    '["Everything in Free Trial", "Unlimited analyses", "Priority support", "Advanced reports", "API access", "Custom YARA rules"]'::jsonb,
    2
),
(
    'enterprise',
    'Enterprise',
    'For large organizations with advanced needs',
    299, 2990, 0, FALSE, 25, 1000, 500, -1, 10,
    '["Everything in Professional", "Unlimited cases", "Unlimited storage", "SSO/SAML", "Dedicated support", "Custom integrations", "SLA guarantee", "On-premise option"]'::jsonb,
    3
)
ON CONFLICT (plan_id) DO NOTHING;

-- ============================================================================
-- Indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant ON subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_trial_end ON subscriptions(trial_end);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_tenant ON billing_invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_status ON billing_invoices(status);
CREATE INDEX IF NOT EXISTS idx_usage_records_tenant ON usage_records(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_period ON usage_records(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_email ON registration_sessions(email);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_token ON registration_sessions(session_token);

-- ============================================================================
-- Add subscription_id to tenants for easy lookup
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'tenants' AND column_name = 'subscription_status') THEN
        ALTER TABLE tenants ADD COLUMN subscription_status VARCHAR(30) DEFAULT 'none';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'tenants' AND column_name = 'is_read_only') THEN
        ALTER TABLE tenants ADD COLUMN is_read_only BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE subscription_plans IS 'Available subscription plans with pricing and limits';
COMMENT ON TABLE subscriptions IS 'Tenant subscriptions with trial and billing info';
COMMENT ON TABLE billing_invoices IS 'Invoice history from Stripe';
COMMENT ON TABLE payment_methods IS 'Stored payment methods for recurring billing';
COMMENT ON TABLE usage_records IS 'Usage tracking for metered billing';
COMMENT ON TABLE registration_sessions IS 'Self-service registration sessions';
