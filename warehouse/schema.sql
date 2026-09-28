-- SaaSCommand 360: Kimball Star Schema DDL (Gold Analytical Marts)

-- ========================================================
-- 1. DIMENSION TABLES
-- ========================================================

CREATE TABLE IF NOT EXISTS dim_account (
    account_id VARCHAR(64) PRIMARY KEY,
    company_name VARCHAR(128) NOT NULL,
    industry VARCHAR(64) NOT NULL,
    company_size VARCHAR(32) NOT NULL,
    region VARCHAR(32) NOT NULL,
    csm_owner VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    cohort VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS dim_user (
    user_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    email VARCHAR(128),
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dim_account(account_id)
);

CREATE TABLE IF NOT EXISTS dim_plan (
    plan_name VARCHAR(32) PRIMARY KEY,
    base_mrr DECIMAL(10,2) NOT NULL,
    seat_limit INTEGER NOT NULL,
    event_quota INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key VARCHAR(10) PRIMARY KEY, -- YYYY-MM-DD
    full_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- ========================================================
-- 2. FACT TABLES
-- ========================================================

CREATE TABLE IF NOT EXISTS fact_subscription (
    subscription_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    plan_name VARCHAR(32) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    status VARCHAR(32) NOT NULL,
    mrr DECIMAL(10,2) NOT NULL,
    arr DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dim_account(account_id),
    FOREIGN KEY (plan_name) REFERENCES dim_plan(plan_name)
);

CREATE TABLE IF NOT EXISTS fact_billing (
    invoice_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    due_date TIMESTAMP NOT NULL,
    paid_at TIMESTAMP,
    status VARCHAR(32) NOT NULL,
    is_overdue BOOLEAN NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dim_account(account_id)
);

CREATE TABLE IF NOT EXISTS fact_support (
    ticket_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    resolution_time_hours FLOAT,
    sla_breached BOOLEAN NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dim_account(account_id)
);

CREATE TABLE IF NOT EXISTS fact_usage (
    usage_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    feature VARCHAR(64) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    event_date VARCHAR(10) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dim_account(account_id),
    FOREIGN KEY (user_id) REFERENCES dim_user(user_id)
);

-- ========================================================
-- 3. GOVERNED ANALYTICAL MARTS
-- ========================================================

CREATE TABLE IF NOT EXISTS mrt_customer_health (
    account_id VARCHAR(64) PRIMARY KEY,
    company_name VARCHAR(128) NOT NULL,
    industry VARCHAR(64) NOT NULL,
    plan VARCHAR(32) NOT NULL,
    mrr DECIMAL(10,2) NOT NULL,
    csm_owner VARCHAR(64) NOT NULL,
    health_score FLOAT NOT NULL,
    health_tier VARCHAR(16) NOT NULL, -- Healthy, At Risk, Critical
    events_last_30d INTEGER NOT NULL,
    active_users_30d INTEGER NOT NULL,
    open_tickets INTEGER NOT NULL,
    critical_tickets INTEGER NOT NULL,
    sla_compliance_rate FLOAT NOT NULL,
    payment_status VARCHAR(32) NOT NULL,
    churn_risk_score FLOAT DEFAULT 0.0,
    expansion_score FLOAT DEFAULT 0.0,
    anomaly_detected BOOLEAN DEFAULT FALSE,
    last_updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS mrt_revenue_summary (
    id INTEGER PRIMARY KEY,
    total_mrr DECIMAL(12,2) NOT NULL,
    total_arr DECIMAL(12,2) NOT NULL,
    paid_invoices_amount DECIMAL(12,2) NOT NULL,
    unpaid_invoices_amount DECIMAL(12,2) NOT NULL,
    active_accounts INTEGER NOT NULL,
    past_due_accounts INTEGER NOT NULL,
    net_retention_rate FLOAT NOT NULL,
    logo_churn_rate FLOAT NOT NULL,
    revenue_churn_rate FLOAT NOT NULL,
    expansion_rate FLOAT NOT NULL,
    calculated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    layer VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    records_processed INTEGER NOT NULL,
    duration_ms FLOAT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);
