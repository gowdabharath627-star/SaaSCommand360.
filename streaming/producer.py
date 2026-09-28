"""
SaaSCommand 360 - Live Event Telemetry Producer
Emits realistic product telemetry, subscription updates, billing events, and support tickets to the streaming bus.
Conforms to Section 6 of the assignment brief.
"""

import os
import sys
import time
import random
import uuid
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streaming.event_bus import event_bus

FEATURES = [
    "dashboard_view", "query_execution", "report_export", 
    "pipeline_run", "api_call", "alert_configuration", 
    "user_invite", "integration_sync"
]

def produce_product_event(account_id: str, user_id: str = None, feature: str = None) -> dict:
    if not feature:
        feature = random.choice(FEATURES)
    if not user_id:
        user_id = f"usr_{account_id}_01"

    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "account_id": account_id,
        "user_id": user_id,
        "feature": feature,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "session_duration_ms": random.randint(500, 15000),
            "client_ip": f"192.168.1.{random.randint(2, 254)}"
        }
    }
    event_bus.publish("product.events", event)
    return event

def produce_billing_event(account_id: str, amount: float, status: str = "paid") -> dict:
    event = {
        "event_id": f"evt_bill_{uuid.uuid4().hex[:8]}",
        "invoice_id": f"inv_live_{uuid.uuid4().hex[:6]}",
        "account_id": account_id,
        "amount": amount,
        "status": status, # paid or failed
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    event_bus.publish("billing.events", event)
    return event

def produce_support_event(account_id: str, severity: str = "medium") -> dict:
    event = {
        "event_id": f"evt_tkt_{uuid.uuid4().hex[:8]}",
        "ticket_id": f"tkt_live_{uuid.uuid4().hex[:6]}",
        "account_id": account_id,
        "severity": severity,
        "status": "open",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    event_bus.publish("support.events", event)
    return event

def simulate_burst(count: int = 25):
    print(f"[Producer] Emitting burst of {count} live telemetry events...")
    accounts = [f"acc_{i:03d}" for i in range(1, 21)]
    for i in range(count):
        acc = random.choice(accounts)
        produce_product_event(acc)
    print(f"[Producer] Burst complete. Current Bus Stats: {event_bus.get_stats()}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--burst":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        simulate_burst(n)
    else:
        # Run a 5-event sample
        simulate_burst(5)
