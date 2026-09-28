-- ========================================================
-- SaaSCommand 360: PostgreSQL Warehouse DDL (Neon / pgAdmin)
-- Star Schema & Governed Analytical Marts
-- ========================================================

-- Drop existing tables if needed for clean re-creation
DROP TABLE IF EXISTS automation_alerts CASCADE;
DROP TABLE IF EXISTS audit_pipeline_runs CASCADE;
DROP TABLE IF EXISTS mrt_revenue_summary CASCADE;
DROP TABLE IF EXISTS mrt_customer_health CASCADE;
DROP TABLE IF EXISTS fact_usage CASCADE;
DROP TABLE IF EXISTS fact_support CASCADE;
DROP TABLE IF EXISTS fact_billing CASCADE;
DROP TABLE IF EXISTS fact_subscription CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_plan CASCADE;
DROP TABLE IF EXISTS dim_user CASCADE;
DROP TABLE IF EXISTS dim_account CASCADE;

-- 1. DIMENSIONS
CREATE TABLE dim_account (
    account_id VARCHAR(64) PRIMARY KEY,
    company_name VARCHAR(128) NOT NULL,
    industry VARCHAR(64) NOT NULL,
    company_size VARCHAR(32) NOT NULL,
    region VARCHAR(32) NOT NULL,
    csm_owner VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cohort VARCHAR(32)
);

CREATE TABLE dim_user (
    user_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES dim_account(account_id) ON DELETE CASCADE,
    email VARCHAR(128),
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE dim_plan (
    plan_name VARCHAR(32) PRIMARY KEY,
    base_mrr NUMERIC(10,2) NOT NULL,
    seat_limit INTEGER NOT NULL,
    event_quota INTEGER NOT NULL
);

CREATE TABLE dim_date (
    date_key VARCHAR(10) PRIMARY KEY, -- YYYY-MM-DD
    full_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. FACTS
CREATE TABLE fact_subscription (
    subscription_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES dim_account(account_id) ON DELETE CASCADE,
    plan_name VARCHAR(32) NOT NULL REFERENCES dim_plan(plan_name),
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) NOT NULL,
    mrr NUMERIC(10,2) NOT NULL,
    arr NUMERIC(12,2) NOT NULL
);

CREATE TABLE fact_billing (
    invoice_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES dim_account(account_id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    paid_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(32) NOT NULL,
    is_overdue BOOLEAN NOT NULL
);

CREATE TABLE fact_support (
    ticket_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES dim_account(account_id) ON DELETE CASCADE,
    severity VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_time_hours DOUBLE PRECISION,
    sla_breached BOOLEAN NOT NULL
);

CREATE TABLE fact_usage (
    usage_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES dim_account(account_id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES dim_user(user_id) ON DELETE CASCADE,
    feature VARCHAR(64) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    event_date VARCHAR(10) NOT NULL REFERENCES dim_date(date_key)
);

-- 3. GOVERNED ANALYTICAL MARTS
CREATE TABLE mrt_customer_health (
    account_id VARCHAR(64) PRIMARY KEY REFERENCES dim_account(account_id) ON DELETE CASCADE,
    company_name VARCHAR(128) NOT NULL,
    industry VARCHAR(64) NOT NULL,
    plan VARCHAR(32) NOT NULL,
    mrr NUMERIC(10,2) NOT NULL,
    csm_owner VARCHAR(64) NOT NULL,
    health_score DOUBLE PRECISION NOT NULL,
    health_tier VARCHAR(16) NOT NULL, -- Healthy, At Risk, Critical
    events_last_30d INTEGER NOT NULL,
    active_users_30d INTEGER NOT NULL,
    open_tickets INTEGER NOT NULL,
    critical_tickets INTEGER NOT NULL,
    sla_compliance_rate DOUBLE PRECISION NOT NULL,
    payment_status VARCHAR(32) NOT NULL,
    churn_risk_score DOUBLE PRECISION DEFAULT 0.0,
    expansion_score DOUBLE PRECISION DEFAULT 0.0,
    anomaly_detected BOOLEAN DEFAULT FALSE,
    last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE mrt_revenue_summary (
    id SERIAL PRIMARY KEY,
    total_mrr NUMERIC(12,2) NOT NULL,
    total_arr NUMERIC(12,2) NOT NULL,
    paid_invoices_amount NUMERIC(12,2) NOT NULL,
    unpaid_invoices_amount NUMERIC(12,2) NOT NULL,
    active_accounts INTEGER NOT NULL,
    past_due_accounts INTEGER NOT NULL,
    net_retention_rate DOUBLE PRECISION NOT NULL,
    logo_churn_rate DOUBLE PRECISION NOT NULL,
    revenue_churn_rate DOUBLE PRECISION NOT NULL,
    expansion_rate DOUBLE PRECISION NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 4. DECISION ENGINE ALERTS & AUDIT LOGS
CREATE TABLE automation_alerts (
    alert_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES dim_account(account_id) ON DELETE CASCADE,
    alert_type VARCHAR(64) NOT NULL, -- CSM Alert, Payment Failure, Upsell Recommendation, Support Escalation
    severity VARCHAR(16) NOT NULL, -- critical, high, medium, low
    trigger_reason TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open', -- open, acknowledged, resolved
    owner VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    audit_history JSONB
);

CREATE TABLE audit_pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    layer VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    records_processed INTEGER NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 5. PERFORMANCE INDEXES (FOR SUB-SECOND PGADMIN & API QUERIES)
CREATE INDEX idx_usage_account_date ON fact_usage(account_id, event_date);
CREATE INDEX idx_billing_account_status ON fact_billing(account_id, status);
CREATE INDEX idx_support_account_sev ON fact_support(account_id, severity, status);
CREATE INDEX idx_health_tier ON mrt_customer_health(health_tier);
CREATE INDEX idx_alerts_account_status ON automation_alerts(account_id, status);
