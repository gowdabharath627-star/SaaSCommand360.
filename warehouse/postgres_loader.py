"""
SaaSCommand 360 - PostgreSQL / Neon Batch Loader

Populates the Kimball Star Schema in PostgreSQL / Neon Postgres
for pgAdmin inspection and application/API use.
"""

import os
import sys
import csv
from io import StringIO

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values

# -------------------------------------------------------------------
# Project path
# -------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from warehouse.db_manager import (
    is_postgres,
    get_connection,
    init_postgres_schema,
)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def postgres_null(value):
    """
    Convert pandas / NumPy values into PostgreSQL-compatible
    native Python values.
    """
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    return value

def postgres_text(value):
    value = postgres_null(value)

    if value is None:
        return None

    return str(value)


# -------------------------------------------------------------------
# Main PostgreSQL loader
# -------------------------------------------------------------------

def load_data_to_postgres(
    df_accounts,
    df_users,
    df_plans,
    df_dates,
    df_subs,
    df_invoices,
    df_tickets,
    df_events,
    mrt_health_table,
    mrt_revenue,
    audit_row,
):
    """
    Load Silver/Gold pipeline outputs into PostgreSQL / Neon.

    Loads:

        1. dim_plan
        2. dim_account
        3. dim_user
        4. dim_date
        5. fact_subscription
        6. fact_billing
        7. fact_support
        8. fact_usage
        9. mrt_customer_health
        10. mrt_revenue_summary
        11. audit_pipeline_runs
    """

    # ---------------------------------------------------------------
    # Check database type
    # ---------------------------------------------------------------

    if not is_postgres():
        print(
            "DATABASE_URL not set to PostgreSQL. "
            "Skipping PostgreSQL load."
        )
        return False

    print("Populating PostgreSQL tables for pgAdmin / Neon...")

    # ---------------------------------------------------------------
    # Initialize PostgreSQL schema
    # ---------------------------------------------------------------

    init_postgres_schema()

    conn = get_connection()

    try:
        cur = conn.cursor()

        # ===========================================================
        # 1. dim_plan
        # ===========================================================

        plans = [
            (
                postgres_text(r["plan_name"]),
                postgres_null(r["base_mrr"]),
                postgres_null(r["seat_limit"]),
                postgres_null(r["event_quota"]),
            )
            for _, r in df_plans.iterrows()
        ]

        if plans:
            execute_values(
                cur,
                """
                INSERT INTO dim_plan (
                    plan_name,
                    base_mrr,
                    seat_limit,
                    event_quota
                )
                VALUES %s
                ON CONFLICT (plan_name)
                DO UPDATE SET
                    base_mrr = EXCLUDED.base_mrr,
                    seat_limit = EXCLUDED.seat_limit,
                    event_quota = EXCLUDED.event_quota
                """,
                plans,
            )

        # ===========================================================
        # 2. dim_account
        # ===========================================================

        accounts = [
            (
                postgres_text(r["account_id"]),
                postgres_text(r["company_name"]),
                postgres_text(r["industry"]),
                postgres_text(r["size"]),
                postgres_text(r["region"]),
                postgres_text(r["owner"]),
                postgres_null(r["created_at"]),
                postgres_text(
                    r.get("cohort", "healthy")
                ),
            )
            for _, r in df_accounts.iterrows()
        ]

        if accounts:
            execute_values(
                cur,
                """
                INSERT INTO dim_account (
                    account_id,
                    company_name,
                    industry,
                    company_size,
                    region,
                    csm_owner,
                    created_at,
                    cohort
                )
                VALUES %s
                ON CONFLICT (account_id)
                DO NOTHING
                """,
                accounts,
            )

        # ===========================================================
        # 3. dim_user
        # ===========================================================

        users = [
            (
                postgres_text(r["user_id"]),
                postgres_text(r["account_id"]),
                postgres_text(r.get("email")),
                postgres_text(r["role"]),
                postgres_null(r["created_at"]),
            )
            for _, r in df_users.iterrows()
        ]

        if users:
            execute_values(
                cur,
                """
                INSERT INTO dim_user (
                    user_id,
                    account_id,
                    email,
                    role,
                    created_at
                )
                VALUES %s
                ON CONFLICT (user_id)
                DO NOTHING
                """,
                users,
            )

        # ===========================================================
        # 4. dim_date
        # ===========================================================

        dates = [
            (
                postgres_text(r["date_key"]),
                postgres_null(r["full_date"]),
                postgres_null(r["year"]),
                postgres_null(r["quarter"]),
                postgres_null(r["month"]),
                postgres_null(r["day"]),
                postgres_text(r["day_of_week"]),
                bool(r["is_weekend"]),
            )
            for _, r in df_dates.iterrows()
        ]

        if dates:
            execute_values(
                cur,
                """
                INSERT INTO dim_date (
                    date_key,
                    full_date,
                    year,
                    quarter,
                    month,
                    day,
                    day_of_week,
                    is_weekend
                )
                VALUES %s
                ON CONFLICT (date_key)
                DO NOTHING
                """,
                dates,
            )

        # ===========================================================
        # 5. fact_subscription
        # ===========================================================

        subs = [
            (
                postgres_text(r["subscription_id"]),
                postgres_text(r["account_id"]),
                postgres_text(r["plan"]),
                postgres_null(r["start_date"]),
                postgres_text(r["status"]),
                postgres_null(r["mrr"]),
                postgres_null(r["arr"]),
            )
            for _, r in df_subs.iterrows()
        ]

        if subs:
            execute_values(
                cur,
                """
                INSERT INTO fact_subscription (
                    subscription_id,
                    account_id,
                    plan_name,
                    start_date,
                    status,
                    mrr,
                    arr
                )
                VALUES %s
                ON CONFLICT (subscription_id)
                DO NOTHING
                """,
                subs,
            )

        # ===========================================================
        # 6. fact_billing
        # ===========================================================

        invoices = [
            (
                postgres_text(r["invoice_id"]),
                postgres_text(r["account_id"]),
                postgres_null(r["amount"]),
                postgres_null(r["due_date"]),
                postgres_null(r.get("paid_at")),
                postgres_text(r["status"]),
                bool(r["is_overdue"]),
            )
            for _, r in df_invoices.iterrows()
        ]

        if invoices:
            execute_values(
                cur,
                """
                INSERT INTO fact_billing (
                    invoice_id,
                    account_id,
                    amount,
                    due_date,
                    paid_at,
                    status,
                    is_overdue
                )
                VALUES %s
                ON CONFLICT (invoice_id)
                DO NOTHING
                """,
                invoices,
            )

        # ===========================================================
        # 7. fact_support
        # ===========================================================

        tickets = [
            (
                postgres_text(r["ticket_id"]),
                postgres_text(r["account_id"]),
                postgres_text(r["severity"]),
                postgres_text(r["status"]),
                postgres_null(r["created_at"]),
                postgres_null(r.get("resolved_at")),
                postgres_null(
                    r.get("resolution_time_hours")
                ),
                bool(r["sla_breached"]),
            )
            for _, r in df_tickets.iterrows()
        ]

        if tickets:
            execute_values(
                cur,
                """
                INSERT INTO fact_support (
                    ticket_id,
                    account_id,
                    severity,
                    status,
                    created_at,
                    resolved_at,
                    resolution_time_hours,
                    sla_breached
                )
                VALUES %s
                ON CONFLICT (ticket_id)
                DO NOTHING
                """,
                tickets,
            )

        # ===========================================================
        # 8. fact_usage
        #
        # IMPORTANT:
        # Product events contain approximately 102,406 rows.
        #
        # Use PostgreSQL COPY instead of execute_values().
        # This is much more suitable for bulk loading.
        # ===========================================================

        usage_buffer = StringIO()

        usage_writer = csv.writer(
            usage_buffer,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )

        for row in df_events.itertuples(index=False):
            usage_writer.writerow(
                [
                    postgres_text(row.usage_id),
                    postgres_text(row.account_id),
                    postgres_text(row.user_id),
                    postgres_text(row.feature),
                    postgres_text(row.event_timestamp),
                    postgres_text(row.event_date),
                ]
            )

        usage_buffer.seek(0)

        if len(df_events) > 0:
            cur.copy_expert(
                """
                COPY fact_usage (
                    usage_id,
                    account_id,
                    user_id,
                    feature,
                    event_timestamp,
                    event_date
                )
                FROM STDIN
                WITH (
                    FORMAT CSV,
                    HEADER FALSE,
                    NULL ''
                )
                """,
                usage_buffer,
            )

        print(
            f"Loaded {len(df_events):,} usage events into fact_usage."
        )

        # ===========================================================
        # 9. mrt_customer_health
        # ===========================================================

        healths = [
            (
                postgres_text(r["account_id"]),
                postgres_text(r["company_name"]),
                postgres_text(r["industry"]),
                postgres_text(r["plan"]),
                postgres_null(r["mrr"]),
                postgres_text(r["csm_owner"]),
                postgres_null(r["health_score"]),
                postgres_text(r["health_tier"]),
                postgres_null(r["events_last_30d"]),
                postgres_null(r["active_users_30d"]),
                postgres_null(r["open_tickets"]),
                postgres_null(r["critical_tickets"]),
                postgres_null(r["sla_compliance_rate"]),
                postgres_text(r["payment_status"]),
                postgres_null(
                    r.get("churn_risk_score", 0.0)
                ),
                postgres_null(
                    r.get("expansion_score", 0.0)
                ),
                bool(
                    postgres_null(
                        r.get("anomaly_detected", False)
                    )
                ),
                postgres_null(r["last_updated_at"]),
            )
            for _, r in mrt_health_table.iterrows()
        ]

        if healths:
            execute_values(
                cur,
                """
                INSERT INTO mrt_customer_health (
                    account_id,
                    company_name,
                    industry,
                    plan,
                    mrr,
                    csm_owner,
                    health_score,
                    health_tier,
                    events_last_30d,
                    active_users_30d,
                    open_tickets,
                    critical_tickets,
                    sla_compliance_rate,
                    payment_status,
                    churn_risk_score,
                    expansion_score,
                    anomaly_detected,
                    last_updated_at
                )
                VALUES %s
                ON CONFLICT (account_id)
                DO UPDATE SET
                    health_score = EXCLUDED.health_score,
                    health_tier = EXCLUDED.health_tier,
                    events_last_30d = EXCLUDED.events_last_30d,
                    active_users_30d = EXCLUDED.active_users_30d,
                    churn_risk_score = EXCLUDED.churn_risk_score,
                    expansion_score = EXCLUDED.expansion_score,
                    anomaly_detected = EXCLUDED.anomaly_detected,
                    last_updated_at = EXCLUDED.last_updated_at
                """,
                healths,
            )

        # ===========================================================
        # 10. mrt_revenue_summary
        # ===========================================================

        if not mrt_revenue.empty:
            rev = mrt_revenue.iloc[0]

            cur.execute(
                """
                INSERT INTO mrt_revenue_summary (
                    total_mrr,
                    total_arr,
                    paid_invoices_amount,
                    unpaid_invoices_amount,
                    active_accounts,
                    past_due_accounts,
                    net_retention_rate,
                    logo_churn_rate,
                    revenue_churn_rate,
                    expansion_rate,
                    calculated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    postgres_null(rev["total_mrr"]),
                    postgres_null(rev["total_arr"]),
                    postgres_null(
                        rev["paid_invoices_amount"]
                    ),
                    postgres_null(
                        rev["unpaid_invoices_amount"]
                    ),
                    postgres_null(
                        rev["active_accounts"]
                    ),
                    postgres_null(
                        rev["past_due_accounts"]
                    ),
                    postgres_null(
                        rev["net_retention_rate"]
                    ),
                    postgres_null(
                        rev["logo_churn_rate"]
                    ),
                    postgres_null(
                        rev["revenue_churn_rate"]
                    ),
                    postgres_null(
                        rev["expansion_rate"]
                    ),
                    postgres_null(
                        rev["calculated_at"]
                    ),
                ),
            )

        # ===========================================================
        # 11. audit_pipeline_runs
        # ===========================================================

        if not audit_row.empty:
            aud = audit_row.iloc[0]

            cur.execute(
                """
                INSERT INTO audit_pipeline_runs (
                    run_id,
                    layer,
                    status,
                    records_processed,
                    duration_ms,
                    error_message,
                    started_at,
                    completed_at
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    postgres_text(aud["run_id"]),
                    postgres_text(aud["layer"]),
                    postgres_text(aud["status"]),
                    int(aud["records_processed"]),
                    float(aud["duration_ms"]),
                    postgres_null(aud["error_message"]),
                    postgres_null(aud["started_at"]),
                    postgres_null(aud["completed_at"]),
                ),
            )

        # ===========================================================
        # Commit
        # ===========================================================

        conn.commit()

        print(
            "Successfully loaded all facts, dimensions, "
            "and marts into PostgreSQL!"
        )

        return True

    except Exception as e:
        conn.rollback()

        print(
            f"Failed to load into PostgreSQL: {e}"
        )

        return False

    finally:
        cur.close()
        conn.close()