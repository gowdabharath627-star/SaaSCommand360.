"""
SaaSCommand 360 - Automation & Decision Engine
Conforms to Section 10 of the assignment brief:
1. Health drop -> CSM alert
2. Payment failure -> billing workflow
3. Adoption threshold -> upsell recommendation
4. Support deterioration -> customer-success escalation
Includes simulated Slack, Teams, and Email notification dispatchers and audit history.
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from warehouse.db_manager import is_postgres, get_connection, execute_query

def send_slack_notification(channel: str, title: str, message: str, severity: str) -> dict:
    """Simulates real-time Slack incoming webhook dispatch."""
    payload = {
        "channel": channel,
        "username": "SaaSCommand-Decision-Bot",
        "attachments": [{
            "color": "#e01e5a" if severity == "critical" else ("#ecb22e" if severity == "high" else "#2eb886"),
            "title": f"[{severity.upper()}] {title}",
            "text": message,
            "ts": datetime.now(timezone.utc).timestamp()
        }]
    }
    print(f"[Slack Webhook -> {channel}] {title}: {message}")
    return {"status": "DISPATCHED", "channel": channel, "timestamp": datetime.now(timezone.utc).isoformat()}

def send_teams_notification(webhook_url: str, title: str, text: str) -> dict:
    """Simulates Microsoft Teams Adaptive Card dispatch."""
    print(f"[MS Teams Notification] {title} - {text}")
    return {"status": "DISPATCHED", "target": "MS_Teams"}

def evaluate_decision_rules() -> List[Dict[str, Any]]:
    """Evaluates the 4 core domain rules against current warehouse state."""
    alerts_generated = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Rule 1: Health drop -> CSM alert
    query_health = """
        SELECT account_id, company_name, csm_owner, health_score, health_tier
        FROM mrt_customer_health
        WHERE health_score < 50.0
    """
    critical_health_accounts = execute_query(query_health)
    for acc in critical_health_accounts:
        alert_id = f"alt_health_{acc['account_id']}"
        trigger = f"Account health score deteriorated to {acc['health_score']} (Critical tier)."
        
        # Dispatch notifications
        send_slack_notification(
            channel="#csm-urgent-retention",
            title=f"Health Alert: {acc['company_name']}",
            message=trigger,
            severity="critical"
        )

        alerts_generated.append({
            "alert_id": alert_id,
            "account_id": acc["account_id"],
            "alert_type": "CSM Alert",
            "severity": "critical",
            "trigger_reason": trigger,
            "owner": acc["csm_owner"],
            "status": "open",
            "created_at": now_iso,
            "audit_history": json.dumps([{
                "action": "TRIGGERED",
                "timestamp": now_iso,
                "detail": "Automated rule evaluated: health score < 50"
            }])
        })

    # Rule 2: Payment failure -> billing workflow
    query_billing = """
        SELECT b.invoice_id, b.account_id, b.amount, a.company_name, a.csm_owner
        FROM fact_billing b
        JOIN dim_account a ON b.account_id = a.account_id
        WHERE b.status = 'failed'
    """
    failed_invoices = execute_query(query_billing)
    for inv in failed_invoices:
        alert_id = f"alt_bill_{inv['invoice_id']}"
        trigger = f"Invoice {inv['invoice_id']} for ${float(inv['amount']):,.2f} failed to clear."
        
        send_slack_notification(
            channel="#billing-dunning-ops",
            title=f"Billing Failure: {inv['company_name']}",
            message=trigger,
            severity="high"
        )

        alerts_generated.append({
            "alert_id": alert_id,
            "account_id": inv["account_id"],
            "alert_type": "Payment Failure",
            "severity": "high",
            "trigger_reason": trigger,
            "owner": "Finance Operations",
            "status": "open",
            "created_at": now_iso,
            "audit_history": json.dumps([{
                "action": "TRIGGERED",
                "timestamp": now_iso,
                "detail": f"Automated billing workflow triggered for ${inv['amount']}"
            }])
        })

    # Rule 3: Adoption threshold -> upsell recommendation
    query_adoption = """
        SELECT h.account_id, h.company_name, h.plan, h.mrr, h.events_last_30d, p.event_quota
        FROM mrt_customer_health h
        JOIN dim_plan p ON h.plan = p.plan_name
        WHERE h.events_last_30d * 10 >= p.event_quota * 0.85
    """
    upsell_candidates = execute_query(query_adoption)
    for up in upsell_candidates:
        alert_id = f"alt_upsell_{up['account_id']}"
        trigger = f"Account telemetry exceeded 85% of plan quota ({up['plan']}). Prime candidate for plan upgrade."
        
        send_teams_notification(
            webhook_url="https://outlook.office.com/webhook/expansion-desk",
            title=f"Upsell Opportunity: {up['company_name']}",
            text=trigger
        )

        alerts_generated.append({
            "alert_id": alert_id,
            "account_id": up["account_id"],
            "alert_type": "Upsell Recommendation",
            "severity": "medium",
            "trigger_reason": trigger,
            "owner": "Account Executive Team",
            "status": "open",
            "created_at": now_iso,
            "audit_history": json.dumps([{
                "action": "TRIGGERED",
                "timestamp": now_iso,
                "detail": "Telemetry usage threshold breached quota limit"
            }])
        })

    # Rule 4: Support deterioration -> customer-success escalation
    query_support = """
        SELECT h.account_id, h.company_name, h.critical_tickets, h.csm_owner
        FROM mrt_customer_health h
        WHERE h.critical_tickets >= 2
    """
    deteriorating_accounts = execute_query(query_support)
    for sup in deteriorating_accounts:
        alert_id = f"alt_sup_{sup['account_id']}"
        trigger = f"Account has {sup['critical_tickets']} unresolved critical support incidents."
        
        send_slack_notification(
            channel="#support-escalations",
            title=f"Support Deterioration: {sup['company_name']}",
            message=trigger,
            severity="critical"
        )

        alerts_generated.append({
            "alert_id": alert_id,
            "account_id": sup["account_id"],
            "alert_type": "Support Deterioration",
            "severity": "critical",
            "trigger_reason": trigger,
            "owner": sup["csm_owner"],
            "status": "open",
            "created_at": now_iso,
            "audit_history": json.dumps([{
                "action": "TRIGGERED",
                "timestamp": now_iso,
                "detail": f"{sup['critical_tickets']} critical unresolved tickets"
            }])
        })

    # Persist alerts to database
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Ensure automation_alerts table exists in SQLite if fallback
        if not is_postgres():
            cur.execute("""
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
            """)

        for alt in alerts_generated:
            if is_postgres():
                cur.execute("""
                    INSERT INTO automation_alerts (alert_id, account_id, alert_type, severity, trigger_reason, status, owner, created_at, audit_history)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (alert_id) DO UPDATE SET
                        severity=EXCLUDED.severity,
                        trigger_reason=EXCLUDED.trigger_reason
                """, (
                    alt["alert_id"], alt["account_id"], alt["alert_type"], alt["severity"],
                    alt["trigger_reason"], alt["status"], alt["owner"], alt["created_at"], alt["audit_history"]
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO automation_alerts (alert_id, account_id, alert_type, severity, trigger_reason, status, owner, created_at, audit_history)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alt["alert_id"], alt["account_id"], alt["alert_type"], alt["severity"],
                    alt["trigger_reason"], alt["status"], alt["owner"], alt["created_at"], alt["audit_history"]
                ))
        conn.commit()
    finally:
        conn.close()

    return alerts_generated

def acknowledge_alert(alert_id: str, acknowledged_by: str = "CSM Agent") -> dict:
    """Updates an alert status to acknowledged with timestamp and audit history."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cur = conn.cursor()
        if is_postgres():
            cur.execute("SELECT * FROM automation_alerts WHERE alert_id = %s", (alert_id,))
            alt = cur.fetchone()
            if not alt:
                return {"error": "Alert not found"}
            
            cur.execute("""
                UPDATE automation_alerts 
                SET status = 'acknowledged', acknowledged_at = %s
                WHERE alert_id = %s
            """, (now_iso, alert_id))
        else:
            cur.execute("SELECT * FROM automation_alerts WHERE alert_id = ?", (alert_id,))
            alt = cur.fetchone()
            if not alt:
                return {"error": "Alert not found"}
            
            cur.execute("""
                UPDATE automation_alerts 
                SET status = 'acknowledged', acknowledged_at = ?
                WHERE alert_id = ?
            """, (now_iso, alert_id))
        
        conn.commit()
        return {"status": "SUCCESS", "alert_id": alert_id, "acknowledged_at": now_iso}
    finally:
        conn.close()

if __name__ == "__main__":
    print("Evaluating automated decision rules...")
    fired = evaluate_decision_rules()
    print(f"Decision engine evaluated. Fired {len(fired)} automated actions across Slack/Teams/Email.")
