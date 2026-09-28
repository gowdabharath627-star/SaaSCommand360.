"""
SaaSCommand 360 - PostgreSQL / Neon Batch Loader
Populates Kimball Star Schema in PostgreSQL / Neon Postgres for pgAdmin inspection.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import psycopg2
from psycopg2.extras import execute_values
from warehouse.db_manager import is_postgres, get_connection, init_postgres_schema

def load_data_to_postgres(
    df_accounts, df_users, df_plans, df_dates,
    df_subs, df_invoices, df_tickets, df_events,
    mrt_health_table, mrt_revenue, audit_row
):
    if not is_postgres():
        print("DATABASE_URL not set to PostgreSQL. Skipping PostgreSQL load.")
        return False

    print("Populating PostgreSQL tables for pgAdmin / Neon...")
    init_postgres_schema()
    conn = get_connection()
    try:
        cur = conn.cursor()

        # 1. dim_plan
        plans = [
            (r["plan_name"], r["base_mrr"], r["seat_limit"], r["event_quota"])
            for _, r in df_plans.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO dim_plan (plan_name, base_mrr, seat_limit, event_quota)
            VALUES %s ON CONFLICT (plan_name) DO UPDATE SET base_mrr=EXCLUDED.base_mrr
        """, plans)

        # 2. dim_account
        accounts = [
            (r["account_id"], r["company_name"], r["industry"], r["company_size"], r["region"], r["csm_owner"], r["created_at"], r.get("cohort", "healthy"))
            for _, r in df_accounts.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO dim_account (account_id, company_name, industry, company_size, region, csm_owner, created_at, cohort)
            VALUES %s ON CONFLICT (account_id) DO NOTHING
        """, accounts)

        # 3. dim_user
        users = [
            (r["user_id"], r["account_id"], r.get("email"), r["role"], r["created_at"])
            for _, r in df_users.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO dim_user (user_id, account_id, email, role, created_at)
            VALUES %s ON CONFLICT (user_id) DO NOTHING
        """, users)

        # 4. dim_date
        dates = [
            (r["date_key"], r["full_date"], r["year"], r["quarter"], r["month"], r["day"], r["day_of_week"], bool(r["is_weekend"]))
            for _, r in df_dates.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO dim_date (date_key, full_date, year, quarter, month, day, day_of_week, is_weekend)
            VALUES %s ON CONFLICT (date_key) DO NOTHING
        """, dates)

        # 5. fact_subscription
        subs = [
            (r["subscription_id"], r["account_id"], r["plan_name"], r["start_date"], r["status"], r["mrr"], r["arr"])
            for _, r in df_subs.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO fact_subscription (subscription_id, account_id, plan_name, start_date, status, mrr, arr)
            VALUES %s ON CONFLICT (subscription_id) DO NOTHING
        """, subs)

        # 6. fact_billing
        invoices = [
            (r["invoice_id"], r["account_id"], r["amount"], r["due_date"], r.get("paid_at"), r["status"], bool(r["is_overdue"]))
            for _, r in df_invoices.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO fact_billing (invoice_id, account_id, amount, due_date, paid_at, status, is_overdue)
            VALUES %s ON CONFLICT (invoice_id) DO NOTHING
        """, invoices)

        # 7. fact_support
        tickets = [
            (r["ticket_id"], r["account_id"], r["severity"], r["status"], r["created_at"], r.get("resolved_at"), r.get("resolution_time_hours"), bool(r["sla_breached"]))
            for _, r in df_tickets.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO fact_support (ticket_id, account_id, severity, status, created_at, resolved_at, resolution_time_hours, sla_breached)
            VALUES %s ON CONFLICT (ticket_id) DO NOTHING
        """, tickets)

        # 8. fact_usage (in chunks of 10,000)
        events = [
            (r["usage_id"], r["account_id"], r["user_id"], r["feature"], r["event_timestamp"], r["event_date"])
            for _, r in df_events.iterrows()
        ]
        chunk_size = 10000
        for i in range(0, len(events), chunk_size):
            chunk = events[i:i + chunk_size]
            execute_values(cur, """
                INSERT INTO fact_usage (usage_id, account_id, user_id, feature, event_timestamp, event_date)
                VALUES %s ON CONFLICT (usage_id) DO NOTHING
            """, chunk)

        # 9. mrt_customer_health
        healths = [
            (
                r["account_id"], r["company_name"], r["industry"], r["plan"], r["mrr"], r["csm_owner"],
                r["health_score"], r["health_tier"], r["events_last_30d"], r["active_users_30d"],
                r["open_tickets"], r["critical_tickets"], r["sla_compliance_rate"], r["payment_status"],
                r.get("churn_risk_score", 0.0), r.get("expansion_score", 0.0), bool(r.get("anomaly_detected", False)),
                r["last_updated_at"]
            )
            for _, r in mrt_health_table.iterrows()
        ]
        execute_values(cur, """
            INSERT INTO mrt_customer_health (
                account_id, company_name, industry, plan, mrr, csm_owner,
                health_score, health_tier, events_last_30d, active_users_30d,
                open_tickets, critical_tickets, sla_compliance_rate, payment_status,
                churn_risk_score, expansion_score, anomaly_detected, last_updated_at
            ) VALUES %s ON CONFLICT (account_id) DO UPDATE SET
                health_score=EXCLUDED.health_score,
                health_tier=EXCLUDED.health_tier,
                events_last_30d=EXCLUDED.events_last_30d,
                active_users_30d=EXCLUDED.active_users_30d,
                churn_risk_score=EXCLUDED.churn_risk_score,
                expansion_score=EXCLUDED.expansion_score,
                last_updated_at=EXCLUDED.last_updated_at
        """, healths)

        # 10. mrt_revenue_summary
        rev = mrt_revenue.iloc[0]
        cur.execute("""
            INSERT INTO mrt_revenue_summary (
                total_mrr, total_arr, paid_invoices_amount, unpaid_invoices_amount,
                active_accounts, past_due_accounts, net_retention_rate, logo_churn_rate,
                revenue_churn_rate, expansion_rate, calculated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            rev["total_mrr"], rev["total_arr"], rev["paid_invoices_amount"], rev["unpaid_invoices_amount"],
            rev["active_accounts"], rev["past_due_accounts"], rev["net_retention_rate"], rev["logo_churn_rate"],
            rev["revenue_churn_rate"], rev["expansion_rate"], rev["calculated_at"]
        ))

        # 11. audit_pipeline_runs
        aud = audit_row.iloc[0]
        cur.execute("""
            INSERT INTO audit_pipeline_runs (run_id, layer, status, records_processed, duration_ms, error_message, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            aud["run_id"], aud["layer"], aud["status"], int(aud["records_processed"]),
            float(aud["duration_ms"]), aud["error_message"], aud["started_at"], aud["completed_at"]
        ))

        conn.commit()
        print("Successfully loaded all facts, dimensions, and marts into PostgreSQL!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Failed to load into PostgreSQL: {e}")
        return False
    finally:
        conn.close()
