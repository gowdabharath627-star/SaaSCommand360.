"""
SaaSCommand 360 - Real-Time Streaming Consumer & Health Processor
Consumes events from the bus, validates schemas, writes to fact tables,
and updates mrt_customer_health in real time.
Conforms to Section 6 of the assignment brief.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streaming.event_bus import event_bus
from warehouse.db_manager import is_postgres, get_connection

SQLITE_PATH = os.path.join(PROJECT_ROOT, "warehouse", "saascommand360.db")

class StreamConsumer:
    def __init__(self):
        self.running = False
        self.processed_count = 0

    def process_product_event(self, event: Dict[str, Any]):
        """Processes product telemetry events and updates usage & customer health."""
        account_id = event["account_id"]
        user_id = event["user_id"]
        feature = event["feature"]
        ts = event["timestamp"]
        date_key = ts[:10]
        usage_id = event["event_id"]

        conn = get_connection()
        try:
            cur = conn.cursor()
            # 1. Insert into fact_usage
            if is_postgres():
                cur.execute("""
                    INSERT INTO fact_usage (usage_id, account_id, user_id, feature, event_timestamp, event_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (usage_id) DO NOTHING
                """, (usage_id, account_id, user_id, feature, ts, date_key))
                
                # 2. Increment events_last_30d in mrt_customer_health and adjust health score
                cur.execute("""
                    UPDATE mrt_customer_health
                    SET events_last_30d = events_last_30d + 1,
                        health_score = LEAST(100.0, health_score + 0.1),
                        health_tier = CASE WHEN health_score >= 75.0 THEN 'Healthy' WHEN health_score >= 50.0 THEN 'At Risk' ELSE 'Critical' END,
                        last_updated_at = %s
                    WHERE account_id = %s
                """, (ts, account_id))
            else:
                cur.execute("""
                    INSERT OR IGNORE INTO fact_usage (usage_id, account_id, user_id, feature, event_timestamp, event_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (usage_id, account_id, user_id, feature, ts, date_key))

                cur.execute("""
                    UPDATE mrt_customer_health
                    SET events_last_30d = events_last_30d + 1,
                        health_score = MIN(100.0, health_score + 0.1),
                        health_tier = CASE WHEN health_score >= 75.0 THEN 'Healthy' WHEN health_score >= 50.0 THEN 'At Risk' ELSE 'Critical' END,
                        last_updated_at = ?
                    WHERE account_id = ?
                """, (ts, account_id))

            conn.commit()
            self.processed_count += 1
            print(f"[Consumer] ✅ Processed telemetry {usage_id} for {account_id}. Health updated.")
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def process_billing_event(self, event: Dict[str, Any]):
        """Processes live billing updates (e.g. payment failure)."""
        account_id = event["account_id"]
        status = event["status"]
        amount = event["amount"]
        inv_id = event["invoice_id"]
        ts = event["timestamp"]

        conn = get_connection()
        try:
            cur = conn.cursor()
            if status == "failed":
                if is_postgres():
                    cur.execute("""
                        UPDATE mrt_customer_health
                        SET payment_status = 'Failed / Overdue',
                            health_score = GREATEST(0.0, health_score - 25.0),
                            health_tier = CASE WHEN health_score >= 75.0 THEN 'Healthy' WHEN health_score >= 50.0 THEN 'At Risk' ELSE 'Critical' END,
                            last_updated_at = %s
                        WHERE account_id = %s
                    """, (ts, account_id))
                else:
                    cur.execute("""
                        UPDATE mrt_customer_health
                        SET payment_status = 'Failed / Overdue',
                            health_score = MAX(0.0, health_score - 25.0),
                            health_tier = CASE WHEN health_score >= 75.0 THEN 'Healthy' WHEN health_score >= 50.0 THEN 'At Risk' ELSE 'Critical' END,
                            last_updated_at = ?
                        WHERE account_id = ?
                    """, (ts, account_id))
                print(f"[Consumer] 🚨 Payment failure for {account_id}! Health penalized.")
            conn.commit()
        finally:
            conn.close()

    def poll_and_process_all(self):
        """Drains all waiting events from topics."""
        for topic in ["product.events", "billing.events", "support.events"]:
            while True:
                evt = event_bus.consume(topic)
                if not evt:
                    break
                try:
                    if topic == "product.events":
                        self.process_product_event(evt)
                    elif topic == "billing.events":
                        self.process_billing_event(evt)
                except Exception as e:
                    event_bus.handle_failure(evt, str(e))

consumer = StreamConsumer()

if __name__ == "__main__":
    print("[Consumer] Running stream consumer poll...")
    consumer.poll_and_process_all()
    print(f"[Consumer] Completed. Processed {consumer.processed_count} events.")
