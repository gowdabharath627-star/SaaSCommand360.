# SaaSCommand 360 — Entity-Relationship Diagram (ERD) & Star Schema

## 1. Entity-Relationship Conceptual Model

The transactional and telemetry models capture user activity, subscription states, invoices, and customer support.

```mermaid
erDiagram
    ACCOUNTS ||--o{ USERS : "employs"
    ACCOUNTS ||--o{ SUBSCRIPTIONS : "contracts"
    ACCOUNTS ||--o{ INVOICES : "billed"
    ACCOUNTS ||--o{ SUPPORT_TICKETS : "raises"
    USERS ||--o{ PRODUCT_EVENTS : "triggers"

    ACCOUNTS {
        string account_id PK
        string industry
        string size
        string region
        string owner
        timestamp created_at
    }

    USERS {
        string user_id PK
        string account_id FK
        string role
        timestamp created_at
    }

    PRODUCT_EVENTS {
        string event_id PK
        string user_id FK
        string feature
        timestamp timestamp
        string session_id
        json payload
    }

    SUBSCRIPTIONS {
        string subscription_id PK
        string account_id FK
        string plan
        timestamp start_date
        timestamp end_date
        string status
        float mrr_amount
    }

    INVOICES {
        string invoice_id PK
        string account_id FK
        float amount
        timestamp due_date
        timestamp paid_at
        string status
    }

    SUPPORT_TICKETS {
        string ticket_id PK
        string account_id FK
        string severity
        timestamp created_at
        timestamp resolved_at
        string status
    }
```

---

## 2. Kimball Dimensional Star Schema (Gold Warehouse Marts)

For analytical queries, BI, and ML feature stores, data is modeled into dimension and fact tables:

```mermaid
erDiagram
    DIM_ACCOUNT ||--o{ FACT_USAGE : "has"
    DIM_USER ||--o{ FACT_USAGE : "performs"
    DIM_DATE ||--o{ FACT_USAGE : "occurred_on"
    
    DIM_ACCOUNT ||--o{ FACT_BILLING : "incurred"
    DIM_DATE ||--o{ FACT_BILLING : "due_on"

    DIM_ACCOUNT ||--o{ FACT_SUBSCRIPTION : "owns"
    DIM_PLAN ||--o{ FACT_SUBSCRIPTION : "tier"
    DIM_DATE ||--o{ FACT_SUBSCRIPTION : "started_on"

    DIM_ACCOUNT ||--o{ FACT_SUPPORT : "logged"
    DIM_DATE ||--o{ FACT_SUPPORT : "created_on"

    FACT_USAGE {
        bigint usage_key PK
        string account_id FK
        string user_id FK
        string date_key FK
        string feature_name
        int event_count
        int active_duration_seconds
    }

    FACT_BILLING {
        bigint billing_key PK
        string account_id FK
        string date_key FK
        string invoice_id
        decimal invoice_amount
        string payment_status
        int days_overdue
    }

    FACT_SUBSCRIPTION {
        bigint subscription_key PK
        string account_id FK
        string plan_key FK
        string date_key FK
        decimal mrr
        decimal arr
        string status
        string change_type
    }

    FACT_SUPPORT {
        bigint support_key PK
        string account_id FK
        string date_key FK
        string ticket_id
        string severity
        int time_to_resolution_hours
        boolean sla_breached
    }

    DIM_ACCOUNT {
        string account_id PK
        string company_name
        string industry
        string company_size
        string region
        string account_tier
        string csm_owner
        timestamp first_active_date
    }

    DIM_USER {
        string user_id PK
        string account_id FK
        string role
        string email_domain
        timestamp created_at
    }

    DIM_PLAN {
        string plan_id PK
        string plan_name
        string billing_interval
        decimal base_price
        int seat_limit
        json included_features
    }

    DIM_DATE {
        string date_key PK
        date full_date
        int year
        int quarter
        int month
        int week
        int day_of_week
        boolean is_weekend
    }
```

---

## 3. Pre-Aggregated Analytical Data Marts

### `mrt_customer_health_daily`
- Grain: `account_id` + `date_key`
- Metrics:
  - `health_score` (0-100 calculated index)
  - `churn_risk_score` (ML output probability)
  - `active_users_7d`, `active_users_30d`
  - `total_events_7d`, `event_growth_wow`
  - `open_tickets_count`, `unresolved_p1_tickets`
  - `payment_status` (`current`, `overdue`, `grace_period`)

### `mrt_mrr_movements`
- Grain: `date_key` + `account_id`
- Metrics:
  - `beginning_mrr`, `new_mrr`, `expansion_mrr`, `contraction_mrr`, `churn_mrr`, `ending_mrr`
  - Net New MRR = $(New + Expansion) - (Contraction + Churn)$
