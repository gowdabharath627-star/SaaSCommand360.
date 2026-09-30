"""
SaaSCommand 360 - REST API Route Handlers

Implements all 12 Mandatory Endpoints defined in Section 12
of the Capstone Brief:

1.  GET  /api/customers/{id}/health
2.  GET  /api/revenue
3.  GET  /api/product/usage
4.  GET  /api/churn-risk
5.  POST /api/customer-action
6.  GET  /api/dashboard
7.  GET  /api/events/live
8.  GET  /api/alerts
9.  GET  /api/forecasts
10. GET  /api/risk
11. POST /api/alerts/{id}/acknowledge
12. GET  /api/data-quality
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Path


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# PROJECT IMPORTS
# ============================================================

from warehouse.db_manager import execute_query

from backend.app.core.security import get_current_user

from backend.app.models.schemas import (
    HealthResponse,
    RevenueSummaryResponse,
    CustomerActionRequest,
    CustomerActionResponse,
    AlertAcknowledgeRequest,
)

from streaming.event_bus import event_bus
from streaming.producer import produce_product_event
from streaming.consumer import consumer

from ml.churn_model import churn_service
from ml.expansion_model import expansion_service
from ml.anomaly_detection import detect_usage_anomalies
from ml.revenue_forecast import generate_revenue_forecast

from decision_engine.rules import acknowledge_alert

from warehouse.data_quality import run_data_quality_suite


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api",
    tags=["SaaS Analytics & Command Center"]
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def serialize_datetime(value):
    """
    Convert datetime values into ISO-8601 strings.

    This prevents FastAPI response validation errors when
    response schemas define datetime fields as strings.
    """
    if isinstance(value, datetime):
        return value.isoformat()

    return value


def serialize_row(row):
    """
    Convert database row values into JSON/API-safe values.

    Handles dictionary-like database rows and converts
    datetime values to ISO strings.
    """
    if not row:
        return row

    if hasattr(row, "items"):
        return {
            key: serialize_datetime(value)
            for key, value in row.items()
        }

    return row


def serialize_rows(rows):
    """
    Serialize a list of database rows.
    """
    return [serialize_row(row) for row in rows]


# ============================================================
# 1. GET /api/customers/{account_id}/health
# ============================================================

@router.get(
    "/customers/{account_id}/health",
    response_model=HealthResponse
)
def get_customer_health(
    account_id: str = Path(
        ...,
        description="Target Account ID (e.g. acc_001)"
    ),
    user: dict = Depends(get_current_user)
):
    """
    Return customer health information for a specific account.
    """

    query = """
        SELECT *
        FROM mrt_customer_health
        WHERE account_id = %s
    """

    row = execute_query(
        query,
        (account_id,),
        fetch="one"
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Customer account '{account_id}' not found."
        )

    return serialize_row(row)


# ============================================================
# 2. GET /api/revenue
# ============================================================

@router.get(
    "/revenue",
    response_model=RevenueSummaryResponse
)
def get_revenue_metrics(
    user: dict = Depends(get_current_user)
):
    """
    Return the latest revenue summary.

    Important:
    The database returns calculated_at as a datetime object.
    The API response schema expects a string, so the value is
    converted to ISO-8601 format before returning.
    """

    row = execute_query(
        """
        SELECT *
        FROM mrt_revenue_summary
        ORDER BY id DESC
        LIMIT 1
        """,
        fetch="one"
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Revenue metrics not computed yet."
        )

    return serialize_row(row)


# ============================================================
# 3. GET /api/product/usage
# ============================================================

@router.get("/product/usage")
def get_product_usage(
    user: dict = Depends(get_current_user)
):
    """
    Return product usage metrics.
    """

    total_events_row = execute_query(
        """
        SELECT COUNT(*) AS count
        FROM fact_usage
        """,
        fetch="one"
    )

    total_events = (
        total_events_row["count"]
        if total_events_row
        else 0
    )

    active_users_row = execute_query(
        """
        SELECT COUNT(DISTINCT user_id) AS count
        FROM fact_usage
        """,
        fetch="one"
    )

    active_users = (
        active_users_row["count"]
        if active_users_row
        else 0
    )

    top_features = execute_query(
        """
        SELECT
            feature,
            COUNT(*) AS event_count
        FROM fact_usage
        GROUP BY feature
        ORDER BY event_count DESC
        LIMIT 10
        """
    )

    daily_trends = execute_query(
        """
        SELECT
            event_date,
            COUNT(*) AS daily_events
        FROM fact_usage
        GROUP BY event_date
        ORDER BY event_date DESC
        LIMIT 30
        """
    )

    daily_trends.reverse()

    return {
        "total_events": total_events,
        "active_users": active_users,
        "top_features": serialize_rows(top_features),
        "daily_usage_trends": serialize_rows(daily_trends),
    }


# ============================================================
# 4. GET /api/churn-risk
# ============================================================

@router.get("/churn-risk")
def get_churn_risk(
    user: dict = Depends(get_current_user)
):
    """
    Return customer churn-risk segmentation.
    """

    rows = execute_query(
        """
        SELECT
            account_id,
            company_name,
            industry,
            plan,
            mrr,
            csm_owner,
            health_score,
            health_tier,
            churn_risk_score,
            open_tickets,
            critical_tickets,
            payment_status
        FROM mrt_customer_health
        ORDER BY churn_risk_score DESC
        """
    )

    rows = serialize_rows(rows)

    high = [
        r for r in rows
        if r["churn_risk_score"] >= 0.60
    ]

    moderate = [
        r for r in rows
        if 0.30 <= r["churn_risk_score"] < 0.60
    ]

    low = [
        r for r in rows
        if r["churn_risk_score"] < 0.30
    ]

    return {
        "high_risk_count": len(high),
        "moderate_risk_count": len(moderate),
        "low_risk_count": len(low),
        "total_evaluated": len(rows),
        "accounts": rows,
    }


# ============================================================
# 5. POST /api/customer-action
# ============================================================

@router.post(
    "/customer-action",
    response_model=CustomerActionResponse
)
def execute_customer_action(
    payload: CustomerActionRequest,
    user: dict = Depends(get_current_user)
):
    """
    Schedule a customer action.
    """

    action_id = f"act_{uuid.uuid4().hex[:8]}"

    now_iso = datetime.now(
        timezone.utc
    ).isoformat()

    return {
        "action_id": action_id,
        "account_id": payload.account_id,
        "action_type": payload.action_type,
        "status": "SCHEDULED",
        "assigned_to": (
            payload.assigned_to
            or user.get("user", "CSM")
        ),
        "timestamp": now_iso,
    }


# ============================================================
# 6. GET /api/dashboard
# ============================================================

@router.get("/dashboard")
def get_dashboard_summary(
    user: dict = Depends(get_current_user)
):
    """
    Return the main SaaS Command Center dashboard data.
    """

    revenue = execute_query(
        """
        SELECT *
        FROM mrt_revenue_summary
        ORDER BY id DESC
        LIMIT 1
        """,
        fetch="one"
    )

    health_counts = execute_query(
        """
        SELECT
            health_tier,
            COUNT(*) AS count
        FROM mrt_customer_health
        GROUP BY health_tier
        """
    )

    top_risks = execute_query(
        """
        SELECT
            account_id,
            company_name,
            mrr,
            health_score,
            churn_risk_score,
            csm_owner
        FROM mrt_customer_health
        WHERE health_tier = 'Critical'
        ORDER BY churn_risk_score DESC
        LIMIT 5
        """
    )

    active_alerts = execute_query(
        """
        SELECT
            alert_id,
            account_id,
            alert_type,
            severity,
            trigger_reason,
            status,
            created_at
        FROM automation_alerts
        WHERE status = 'open'
        ORDER BY created_at DESC
        LIMIT 5
        """
    )

    return {
        "revenue": serialize_row(revenue),

        "health_distribution": {
            r["health_tier"]: r["count"]
            for r in health_counts
        },

        "top_risk_accounts": serialize_rows(top_risks),

        "recent_alerts": serialize_rows(active_alerts),

        "streaming_stats": event_bus.get_stats(),
    }


# ============================================================
# 7. GET /api/events/live
# ============================================================

@router.get("/events/live")
def get_live_events(
    limit: int = Query(
        25,
        ge=1,
        le=100
    ),
    user: dict = Depends(get_current_user)
):
    """
    Return recent product usage events.

    The limit parameter is now actually used by the SQL query.
    """

    events = execute_query(
        f"""
        SELECT
            usage_id AS event_id,
            account_id,
            user_id,
            feature,
            event_timestamp
        FROM fact_usage
        ORDER BY event_timestamp DESC
        LIMIT {limit}
        """
    )

    return {
        "bus_metrics": event_bus.get_stats(),
        "recent_events": serialize_rows(events),
    }


# ============================================================
# 8. GET /api/alerts
# ============================================================

@router.get("/alerts")
def get_alerts(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Return automation alerts.
    """

    if status:
        alerts = execute_query(
            """
            SELECT *
            FROM automation_alerts
            WHERE status = ?
            ORDER BY created_at DESC
            """,
            (status,)
        )
    else:
        alerts = execute_query(
            """
            SELECT *
            FROM automation_alerts
            ORDER BY created_at DESC
            """
        )

    alerts = serialize_rows(alerts)

    return {
        "count": len(alerts),
        "alerts": alerts,
    }


# ============================================================
# 9. GET /api/forecasts
# ============================================================

@router.get("/forecasts")
def get_forecasts(
    months: int = Query(
        12,
        ge=1,
        le=24
    ),
    user: dict = Depends(get_current_user)
):
    """
    Generate revenue forecast.
    """

    return generate_revenue_forecast(
        horizon_months=months
    )


# ============================================================
# 10. GET /api/risk
# ============================================================

@router.get("/risk")
def get_risk_center(
    user: dict = Depends(get_current_user)
):
    """
    Return high-risk accounts and usage anomalies.
    """

    churn_accounts = execute_query(
        """
        SELECT
            account_id,
            company_name,
            mrr,
            health_score,
            churn_risk_score,
            open_tickets,
            payment_status
        FROM mrt_customer_health
        WHERE churn_risk_score >= 0.50
        ORDER BY churn_risk_score DESC
        """
    )

    anomalies = detect_usage_anomalies()

    return {
        "high_risk_accounts": serialize_rows(
            churn_accounts
        ),

        "usage_anomalies": anomalies,

        "evaluated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# ============================================================
# 11. POST /api/alerts/{alert_id}/acknowledge
# ============================================================

@router.post(
    "/alerts/{alert_id}/acknowledge"
)
def acknowledge_alert_endpoint(
    alert_id: str = Path(...),

    payload: AlertAcknowledgeRequest = (
        AlertAcknowledgeRequest()
    ),

    user: dict = Depends(get_current_user)
):
    """
    Acknowledge an automation alert.
    """

    res = acknowledge_alert(
        alert_id,
        acknowledged_by=(
            payload.acknowledged_by
            or user.get("user")
        )
    )

    if "error" in res:
        raise HTTPException(
            status_code=404,
            detail=res["error"]
        )

    return serialize_row(res)


# ============================================================
# 12. GET /api/data-quality
# ============================================================

@router.get("/data-quality")
def get_data_quality_report(
    user: dict = Depends(get_current_user)
):
    """
    Run and return the data-quality report.
    """

    return run_data_quality_suite()


# ============================================================
# BONUS ENDPOINT
# POST /api/events/simulate
# ============================================================

@router.post("/events/simulate")
def simulate_telemetry_burst(
    count: int = Query(
        10,
        ge=1,
        le=50
    ),
    user: dict = Depends(get_current_user)
):
    """
    Generate simulated product telemetry events
    for frontend/live dashboard testing.
    """

    import random

    accounts = [
        f"acc_{i:03d}"
        for i in range(1, 21)
    ]

    emitted = []

    for _ in range(count):

        account_id = random.choice(accounts)

        event = produce_product_event(
            account_id
        )

        emitted.append(event)

    consumer.poll_and_process_all()

    return {
        "status": "SUCCESS",
        "events_emitted": len(emitted),
        "bus_stats": event_bus.get_stats(),
    }