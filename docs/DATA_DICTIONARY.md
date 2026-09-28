# SaaSCommand 360 — Data Dictionary

## 1. Raw / Source Entities (Bronze & Silver)

### Table: `accounts`
| Column | Type | Nullable | Primary/Foreign Key | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `account_id` | VARCHAR(64) | NO | PK | Unique identifier for customer account | `acc_enterprise_01` |
| `company_name` | VARCHAR(128) | NO | - | Customer company name | `Apex Logistics Inc` |
| `industry` | VARCHAR(64) | NO | - | Industry sector | `Fintech`, `Healthcare`, `Logistics` |
| `size` | VARCHAR(32) | NO | - | Number of employees bucket | `1-50`, `51-200`, `201-1000`, `1000+` |
| `region` | VARCHAR(32) | NO | - | Geographic operational region | `North America`, `EMEA`, `APAC` |
| `owner` | VARCHAR(64) | NO | - | Assigned Customer Success Manager (CSM) | `csm_jane_doe@saas360.com` |
| `created_at` | TIMESTAMP | NO | - | Timestamp when account was provisioned | `2025-01-15T08:30:00Z` |

### Table: `users`
| Column | Type | Nullable | Primary/Foreign Key | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `user_id` | VARCHAR(64) | NO | PK | Unique identifier for end user | `usr_9128` |
| `account_id` | VARCHAR(64) | NO | FK -> accounts | Parent account identifier | `acc_enterprise_01` |
| `email` | VARCHAR(128) | NO | - | User corporate email | `alice@apexlogistics.com` |
| `role` | VARCHAR(32) | NO | - | User permission tier | `admin`, `member`, `viewer` |
| `created_at` | TIMESTAMP | NO | - | User account creation time | `2025-01-16T09:12:00Z` |

### Table: `product_events`
| Column | Type | Nullable | Primary/Foreign Key | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | VARCHAR(64) | NO | PK | Unique telemetry event identifier | `evt_9a87f10b` |
| `user_id` | VARCHAR(64) | NO | FK -> users | User triggering event | `usr_9128` |
| `account_id` | VARCHAR(64) | NO | FK -> accounts | Account association | `acc_enterprise_01` |
| `feature` | VARCHAR(64) | NO | - | Product capability exercised | `report_export`, `pipeline_run`, `dashboard_view` |
| `timestamp` | TIMESTAMP | NO | - | Precise UTC event timestamp | `2026-03-24T14:22:10Z` |
| `metadata` | JSON | YES | - | Additional attributes/payload | `{"export_format": "csv"}` |

### Table: `subscriptions`
| Column | Type | Nullable | Primary/Foreign Key | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `subscription_id` | VARCHAR(64) | NO | PK | Unique billing subscription ID | `sub_3910` |
| `account_id` | VARCHAR(64) | NO | FK -> accounts | Account linked to subscription | `acc_enterprise_01` |
| `plan` | VARCHAR(32) | NO | - | Subscription tier | `Starter`, `Professional`, `Enterprise` |
| `start_date` | TIMESTAMP | NO | - | Subscription contract start | `2025-01-15T00:00:00Z` |
| `status` | VARCHAR(32) | NO | - | Current state | `active`, `past_due`, `cancelled`, `trial` |
| `mrr` | DECIMAL(10,2)| NO | - | Normalized Monthly Recurring Revenue ($) | `4500.00` |

### Table: `invoices`
| Column | Type | Nullable | Primary/Foreign Key | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `invoice_id` | VARCHAR(64) | NO | PK | Billing invoice invoice number | `inv_2026_0012` |
| `account_id` | VARCHAR(64) | NO | FK -> accounts | Target account | `acc_enterprise_01` |
| `amount` | DECIMAL(10,2)| NO | - | Invoiced amount in USD | `4500.00` |
| `due_date` | TIMESTAMP | NO | - | Payment deadline | `2026-03-01T00:00:00Z` |
| `status` | VARCHAR(32) | NO | - | Payment status | `paid`, `open`, `failed`, `void` |
| `paid_at` | TIMESTAMP | YES | - | Timestamp when invoice cleared | `2026-02-28T16:40:00Z` |

### Table: `support_tickets`
| Column | Type | Nullable | Primary/Foreign Key | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ticket_id` | VARCHAR(64) | NO | PK | Customer support incident ticket ID | `tkt_5041` |
| `account_id` | VARCHAR(64) | NO | FK -> accounts | Account experiencing issue | `acc_enterprise_01` |
| `severity` | VARCHAR(16) | NO | - | Urgency level | `low`, `medium`, `high`, `critical` |
| `created_at` | TIMESTAMP | NO | - | Issue report time | `2026-03-20T10:15:00Z` |
| `resolved_at` | TIMESTAMP | YES | - | Issue resolution time | `2026-03-20T12:00:00Z` |
| `status` | VARCHAR(32) | NO | - | Ticket lifecycle state | `open`, `in_progress`, `resolved`, `closed` |

---

## 2. Governed Dimensional & Mart Entities (Gold)

### Table: `mrt_customer_health`
| Column | Type | Description |
| :--- | :--- | :--- |
| `account_id` | VARCHAR(64) | Account identifier |
| `health_score` | FLOAT | Computed Composite Health Score (0 - 100) based on weighted telemetry, tickets, and payment health |
| `health_status` | VARCHAR(16) | Categorical tier: `Healthy` (>=75), `At Risk` (50-74), `Critical` (<50) |
| `churn_probability` | FLOAT | Predicted churn probability from ML classifier (0.0 to 1.0) |
| `expansion_score` | FLOAT | Upsell/expansion propensity index (0.0 to 1.0) |
| `usage_anomaly` | BOOLEAN | Indicates severe deviations from historical baseline |
| `active_users_30d` | INTEGER | Distinct users active in the trailing 30 days |
| `support_sla_rate`| FLOAT | Percentage of support tickets resolved within SLA |
| `last_updated_at` | TIMESTAMP | Pipeline refresh timestamp |

### Table: `mrt_revenue_summary`
| Column | Type | Description |
| :--- | :--- | :--- |
| `metric_date` | DATE | Daily/Monthly reporting date |
| `total_mrr` | DECIMAL(12,2) | Total current active Monthly Recurring Revenue |
| `total_arr` | DECIMAL(12,2) | Total current active Annual Recurring Revenue |
| `new_mrr` | DECIMAL(12,2) | MRR from net new accounts acquired |
| `expansion_mrr` | DECIMAL(12,2) | Revenue growth from upgrades on existing accounts |
| `contraction_mrr`| DECIMAL(12,2) | Revenue lost from plan downgrades |
| `churned_mrr` | DECIMAL(12,2) | Revenue lost from canceled subscriptions |
| `net_retention_rate` | FLOAT | Net Dollar Retention (NDR) percentage |
| `logo_churn_rate` | FLOAT | Percentage of accounts that fully churned |
