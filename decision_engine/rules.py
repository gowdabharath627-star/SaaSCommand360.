"""
SaaSCommand 360 - Automation & Decision Engine

Conforms to Section 10 of the assignment brief:

1. Health drop -> CSM alert
2. Payment failure -> billing workflow
3. Adoption threshold -> upsell recommendation
4. Support deterioration -> customer-success escalation

Notification channels:
- Slack
- Microsoft Teams
- Email

Email supports multiple recipients through .env configuration.

All alerts include:
- timestamp
- severity
- owner
- trigger reason
- status
- audit history

Email is currently simulated.
Set EMAIL_ENABLED=true when a real email provider is integrated.
"""

import os
import sys
import json

from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import List, Dict, Any


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env"
    )
)


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

EMAIL_ENABLED = (
    os.getenv(
        "EMAIL_ENABLED",
        "false"
    ).lower()
    == "true"
)


def load_email_list(
    env_name: str
) -> List[str]:
    """
    Reads comma-separated email addresses from .env.

    Example:
        HEALTH_ALERT_EMAILS=csm@example.com,manager@example.com

    Returns:
        ["csm@example.com", "manager@example.com"]
    """

    value = os.getenv(
        env_name,
        ""
    )

    return [
        email.strip()
        for email in value.split(",")
        if email.strip()
    ]


EMAIL_RECIPIENTS = {

    "health_alert":
        load_email_list(
            "HEALTH_ALERT_EMAILS"
        ),

    "payment_failure":
        load_email_list(
            "PAYMENT_ALERT_EMAILS"
        ),

    "support_escalation":
        load_email_list(
            "SUPPORT_ALERT_EMAILS"
        ),

    "upsell":
        load_email_list(
            "UPSELL_ALERT_EMAILS"
        ),
}


# ============================================================
# DATABASE IMPORT
# ============================================================

from warehouse.db_manager import (
    is_postgres,
    get_connection,
    execute_query
)


# ============================================================
# SLACK NOTIFICATION
# ============================================================

def send_slack_notification(
    channel: str,
    title: str,
    message: str,
    severity: str
) -> dict:
    """
    Simulates a Slack notification.

    In production this can be replaced with
    a real Slack webhook/API integration.
    """

    payload = {
        "channel": channel,
        "username": "SaaSCommand-Decision-Bot",
        "attachments": [
            {
                "color": (
                    "#e01e5a"
                    if severity == "critical"
                    else (
                        "#ecb22e"
                        if severity == "high"
                        else "#2eb886"
                    )
                ),
                "title": (
                    f"[{severity.upper()}] "
                    f"{title}"
                ),
                "text": message,
                "ts": datetime.now(
                    timezone.utc
                ).timestamp()
            }
        ]
    }

    print(
        f"[Slack Webhook -> {channel}] "
        f"{title}: {message}"
    )

    return {
        "status": "DISPATCHED",
        "channel": channel,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# MICROSOFT TEAMS NOTIFICATION
# ============================================================

def send_teams_notification(
    webhook_url: str,
    title: str,
    text: str
) -> dict:
    """
    Simulates a Microsoft Teams notification.

    The webhook URL is intentionally not called yet.
    """

    print(
        f"[MS Teams Notification] "
        f"{title} - {text}"
    )

    return {
        "status": "DISPATCHED",
        "target": "MS_Teams",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# EMAIL NOTIFICATION
# ============================================================

def send_email_notification(
    recipients: List[str],
    subject: str,
    message: str,
    severity: str
) -> dict:
    """
    Sends/simulates an email notification
    to multiple recipients.

    EMAIL_ENABLED=false:
        Email is disabled.

    EMAIL_ENABLED=true:
        Email is currently simulated.

    A real SMTP/provider integration can be
    added later.
    """

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    if not recipients:

        print(
            f"[Email] No recipients configured "
            f"for: {subject}"
        )

        return {
            "status": "SKIPPED",
            "recipients": [],
            "timestamp": timestamp
        }

    if not EMAIL_ENABLED:

        print(
            f"[Email Disabled -> "
            f"{', '.join(recipients)}] "
            f"[{severity.upper()}] "
            f"{subject}: {message}"
        )

        return {
            "status": "DISABLED",
            "recipients": recipients,
            "timestamp": timestamp
        }

    print(
        f"[Email Simulation -> "
        f"{', '.join(recipients)}] "
        f"[{severity.upper()}] "
        f"{subject}: {message}"
    )

    return {
        "status": "SIMULATED",
        "recipients": recipients,
        "timestamp": timestamp
    }


# ============================================================
# DECISION ENGINE
# ============================================================

def evaluate_decision_rules() -> List[Dict[str, Any]]:
    """
    Evaluates the four core business rules
    against the current warehouse state.
    """

    alerts_generated = []

    now_iso = datetime.now(
        timezone.utc
    ).isoformat()


    # ========================================================
    # RULE 1
    # Health Drop -> CSM Alert
    # ========================================================

    query_health = """
        SELECT
            account_id,
            company_name,
            csm_owner,
            health_score,
            health_tier
        FROM mrt_customer_health
        WHERE health_score < 50.0
    """

    critical_health_accounts = execute_query(
        query_health
    )

    for acc in critical_health_accounts:

        alert_id = (
            f"alt_health_{acc['account_id']}"
        )

        trigger = (
            f"Account health score deteriorated "
            f"to {acc['health_score']} "
            f"(Critical tier)."
        )

        send_slack_notification(
            channel="#csm-urgent-retention",
            title=(
                f"Health Alert: "
                f"{acc['company_name']}"
            ),
            message=trigger,
            severity="critical"
        )

        send_email_notification(
            recipients=EMAIL_RECIPIENTS[
                "health_alert"
            ],
            subject=(
                f"Health Alert: "
                f"{acc['company_name']}"
            ),
            message=trigger,
            severity="critical"
        )

        alerts_generated.append(
            {
                "alert_id": alert_id,
                "account_id": acc["account_id"],
                "alert_type": "CSM Alert",
                "severity": "critical",
                "trigger_reason": trigger,
                "owner": acc["csm_owner"],
                "status": "open",
                "created_at": now_iso,
                "audit_history": json.dumps(
                    [
                        {
                            "action": "TRIGGERED",
                            "timestamp": now_iso,
                            "detail": (
                                "Automated rule evaluated: "
                                "health score < 50"
                            )
                        }
                    ]
                )
            }
        )


    # ========================================================
    # RULE 2
    # Payment Failure -> Billing Workflow
    # ========================================================

    query_billing = """
        SELECT
            b.invoice_id,
            b.account_id,
            b.amount,
            a.company_name,
            a.csm_owner
        FROM fact_billing b
        JOIN dim_account a
            ON b.account_id = a.account_id
        WHERE b.status = 'failed'
    """

    failed_invoices = execute_query(
        query_billing
    )

    for inv in failed_invoices:

        alert_id = (
            f"alt_bill_{inv['invoice_id']}"
        )

        trigger = (
            f"Invoice {inv['invoice_id']} "
            f"for ${float(inv['amount']):,.2f} "
            f"failed to clear."
        )

        send_slack_notification(
            channel="#billing-dunning-ops",
            title=(
                f"Billing Failure: "
                f"{inv['company_name']}"
            ),
            message=trigger,
            severity="high"
        )

        send_email_notification(
            recipients=EMAIL_RECIPIENTS[
                "payment_failure"
            ],
            subject=(
                f"Billing Failure: "
                f"{inv['company_name']}"
            ),
            message=trigger,
            severity="high"
        )

        alerts_generated.append(
            {
                "alert_id": alert_id,
                "account_id": inv["account_id"],
                "alert_type": "Payment Failure",
                "severity": "high",
                "trigger_reason": trigger,
                "owner": "Finance Operations",
                "status": "open",
                "created_at": now_iso,
                "audit_history": json.dumps(
                    [
                        {
                            "action": "TRIGGERED",
                            "timestamp": now_iso,
                            "detail": (
                                "Automated billing workflow "
                                "triggered for "
                                f"${inv['amount']}"
                            )
                        }
                    ]
                )
            }
        )


    # ========================================================
    # RULE 3
    # Adoption Threshold -> Upsell Recommendation
    # ========================================================

    query_adoption = """
        SELECT
            h.account_id,
            h.company_name,
            h.plan,
            h.mrr,
            h.events_last_30d,
            p.event_quota
        FROM mrt_customer_health h
        JOIN dim_plan p
            ON h.plan = p.plan_name
        WHERE h.events_last_30d * 10
              >= p.event_quota * 0.85
    """

    upsell_candidates = execute_query(
        query_adoption
    )

    for up in upsell_candidates:

        alert_id = (
            f"alt_upsell_{up['account_id']}"
        )

        trigger = (
            f"Account telemetry exceeded 85% "
            f"of plan quota ({up['plan']}). "
            f"Prime candidate for plan upgrade."
        )

        send_teams_notification(
            webhook_url=(
                "https://outlook.office.com/"
                "webhook/expansion-desk"
            ),
            title=(
                f"Upsell Opportunity: "
                f"{up['company_name']}"
            ),
            text=trigger
        )

        send_email_notification(
            recipients=EMAIL_RECIPIENTS[
                "upsell"
            ],
            subject=(
                f"Upsell Opportunity: "
                f"{up['company_name']}"
            ),
            message=trigger,
            severity="medium"
        )

        alerts_generated.append(
            {
                "alert_id": alert_id,
                "account_id": up["account_id"],
                "alert_type": "Upsell Recommendation",
                "severity": "medium",
                "trigger_reason": trigger,
                "owner": "Account Executive Team",
                "status": "open",
                "created_at": now_iso,
                "audit_history": json.dumps(
                    [
                        {
                            "action": "TRIGGERED",
                            "timestamp": now_iso,
                            "detail": (
                                "Telemetry usage threshold "
                                "breached quota limit"
                            )
                        }
                    ]
                )
            }
        )


    # ========================================================
    # RULE 4
    # Support Deterioration -> CSM Escalation
    # ========================================================

    query_support = """
        SELECT
            h.account_id,
            h.company_name,
            h.critical_tickets,
            h.csm_owner
        FROM mrt_customer_health h
        WHERE h.critical_tickets >= 2
    """

    deteriorating_accounts = execute_query(
        query_support
    )

    for sup in deteriorating_accounts:

        alert_id = (
            f"alt_sup_{sup['account_id']}"
        )

        trigger = (
            f"Account has "
            f"{sup['critical_tickets']} "
            f"unresolved critical support incidents."
        )

        send_slack_notification(
            channel="#support-escalations",
            title=(
                f"Support Deterioration: "
                f"{sup['company_name']}"
            ),
            message=trigger,
            severity="critical"
        )

        send_email_notification(
            recipients=EMAIL_RECIPIENTS[
                "support_escalation"
            ],
            subject=(
                f"Support Deterioration: "
                f"{sup['company_name']}"
            ),
            message=trigger,
            severity="critical"
        )

        alerts_generated.append(
            {
                "alert_id": alert_id,
                "account_id": sup["account_id"],
                "alert_type": "Support Deterioration",
                "severity": "critical",
                "trigger_reason": trigger,
                "owner": sup["csm_owner"],
                "status": "open",
                "created_at": now_iso,
                "audit_history": json.dumps(
                    [
                        {
                            "action": "TRIGGERED",
                            "timestamp": now_iso,
                            "detail": (
                                f"{sup['critical_tickets']} "
                                "critical unresolved tickets"
                            )
                        }
                    ]
                )
            }
        )


    # ========================================================
    # PERSIST ALERTS TO DATABASE
    # ========================================================

    conn = get_connection()

    try:

        cur = conn.cursor()

        if not is_postgres():

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_alerts (
                    alert_id VARCHAR(64) PRIMARY KEY,
                    account_id VARCHAR(64) NOT NULL,
                    alert_type VARCHAR(64) NOT NULL,
                    severity VARCHAR(16) NOT NULL,
                    trigger_reason TEXT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'open',
                    owner VARCHAR(64) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    acknowledged_at TIMESTAMP,
                    audit_history TEXT
                )
                """
            )


        for alt in alerts_generated:

            if is_postgres():

                cur.execute(
                    """
                    INSERT INTO automation_alerts
                    (
                        alert_id,
                        account_id,
                        alert_type,
                        severity,
                        trigger_reason,
                        status,
                        owner,
                        created_at,
                        audit_history
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )

                    ON CONFLICT (alert_id)
                    DO UPDATE SET
                        severity =
                            EXCLUDED.severity,
                        trigger_reason =
                            EXCLUDED.trigger_reason
                    """,
                    (
                        alt["alert_id"],
                        alt["account_id"],
                        alt["alert_type"],
                        alt["severity"],
                        alt["trigger_reason"],
                        alt["status"],
                        alt["owner"],
                        alt["created_at"],
                        alt["audit_history"]
                    )
                )

            else:

                cur.execute(
                    """
                    INSERT OR REPLACE INTO automation_alerts
                    (
                        alert_id,
                        account_id,
                        alert_type,
                        severity,
                        trigger_reason,
                        status,
                        owner,
                        created_at,
                        audit_history
                    )
                    VALUES
                    (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?
                    )
                    """,
                    (
                        alt["alert_id"],
                        alt["account_id"],
                        alt["alert_type"],
                        alt["severity"],
                        alt["trigger_reason"],
                        alt["status"],
                        alt["owner"],
                        alt["created_at"],
                        alt["audit_history"]
                    )
                )


        conn.commit()

    finally:
        conn.close()


    return alerts_generated


# ============================================================
# ACKNOWLEDGE ALERT
# ============================================================

def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = "CSM Agent",
    notes: str = ""
) -> dict:
    """
    Acknowledge an automation alert.

    Updates:
    - status
    - acknowledged_at
    - audit_history

    Works with both:
    - PostgreSQL tuple rows
    - dictionary-style rows
    """

    now_iso = datetime.now(
        timezone.utc
    ).isoformat()

    conn = get_connection()

    try:

        cur = conn.cursor()


        # ====================================================
        # POSTGRESQL
        # ====================================================

        if is_postgres():

            cur.execute(
                """
                SELECT
                    alert_id,
                    audit_history
                FROM automation_alerts
                WHERE alert_id = %s
                """,
                (alert_id,)
            )

            alt = cur.fetchone()

            if not alt:

                return {
                    "error": "Alert not found"
                }


            # ------------------------------------------------
            # IMPORTANT:
            # psycopg2 may return either:
            #
            # tuple:
            #     ("alt_health_acc_026", "[...]")
            #
            # or dictionary:
            #     {
            #         "alert_id": "...",
            #         "audit_history": "..."
            #     }
            #
            # Handle both.
            # ------------------------------------------------

            if hasattr(
                alt,
                "keys"
            ):
                existing_history = (
                    alt.get(
                        "audit_history"
                    )
                )
            else:
                existing_history = (
                    alt[1]
                    if len(alt) > 1
                    else None
                )


            # ------------------------------------------------
            # Convert audit history into list
            # ------------------------------------------------

            if not existing_history:

                audit_history = []

            elif isinstance(
                existing_history,
                str
            ):

                try:

                    audit_history = json.loads(
                        existing_history
                    )

                except (
                    json.JSONDecodeError,
                    TypeError
                ):

                    audit_history = []

            elif isinstance(
                existing_history,
                list
            ):

                audit_history = (
                    existing_history
                )

            else:

                audit_history = []


            # ------------------------------------------------
            # Add acknowledgement event
            # ------------------------------------------------

            acknowledgement_event = {
                "action": "ACKNOWLEDGED",
                "timestamp": now_iso,
                "acknowledged_by": acknowledged_by,
                "detail": (
                    "Alert acknowledged by "
                    f"{acknowledged_by}"
                )
            }

            if notes:

                acknowledgement_event[
                    "notes"
                ] = notes


            audit_history.append(
                acknowledgement_event
            )


            # ------------------------------------------------
            # Update database
            # ------------------------------------------------

            cur.execute(
                """
                UPDATE automation_alerts
                SET
                    status = 'acknowledged',
                    acknowledged_at = %s,
                    audit_history = %s
                WHERE alert_id = %s
                """,
                (
                    now_iso,
                    json.dumps(
                        audit_history
                    ),
                    alert_id
                )
            )


        # ====================================================
        # SQLITE
        # ====================================================

        else:

            cur.execute(
                """
                SELECT
                    alert_id,
                    audit_history
                FROM automation_alerts
                WHERE alert_id = ?
                """,
                (alert_id,)
            )

            alt = cur.fetchone()

            if not alt:

                return {
                    "error": "Alert not found"
                }


            # Handle tuple or dictionary
            if hasattr(
                alt,
                "keys"
            ):
                existing_history = (
                    alt.get(
                        "audit_history"
                    )
                )
            else:
                existing_history = (
                    alt[1]
                    if len(alt) > 1
                    else None
                )


            if not existing_history:

                audit_history = []

            elif isinstance(
                existing_history,
                str
            ):

                try:

                    audit_history = json.loads(
                        existing_history
                    )

                except (
                    json.JSONDecodeError,
                    TypeError
                ):

                    audit_history = []

            elif isinstance(
                existing_history,
                list
            ):

                audit_history = (
                    existing_history
                )

            else:

                audit_history = []


            acknowledgement_event = {
                "action": "ACKNOWLEDGED",
                "timestamp": now_iso,
                "acknowledged_by": acknowledged_by,
                "detail": (
                    "Alert acknowledged by "
                    f"{acknowledged_by}"
                )
            }

            if notes:

                acknowledgement_event[
                    "notes"
                ] = notes


            audit_history.append(
                acknowledgement_event
            )


            cur.execute(
                """
                UPDATE automation_alerts
                SET
                    status = ?,
                    acknowledged_at = ?,
                    audit_history = ?
                WHERE alert_id = ?
                """,
                (
                    "acknowledged",
                    now_iso,
                    json.dumps(
                        audit_history
                    ),
                    alert_id
                )
            )


        # ====================================================
        # COMMIT
        # ====================================================

        conn.commit()


        return {
            "status": "SUCCESS",
            "alert_id": alert_id,
            "acknowledged_at": now_iso,
            "acknowledged_by": acknowledged_by,
            "notes": notes
        }


    except Exception:

        conn.rollback()

        raise


    finally:

        conn.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "Evaluating automated decision rules..."
    )

    fired = evaluate_decision_rules()

    print(
        f"Decision engine evaluated. "
        f"Fired {len(fired)} automated actions."
    )

    print(
        "Notification channels: "
        "Slack + Teams + Email configuration"
    )

    if EMAIL_ENABLED:

        print(
            "Email mode: ENABLED "
            "(currently simulated)"
        )

    else:

        print(
            "Email mode: DISABLED "
            "(no emails sent)"
        )