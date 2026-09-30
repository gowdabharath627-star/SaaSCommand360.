"""
SaaSCommand 360 - Real-Time Streaming Consumer & Health Processor

Consumes events from the streaming bus, validates schemas,
writes to fact tables, and updates mrt_customer_health in real time.

Supports:
- Product telemetry
- Billing events
- Support events
- Subscription events
- Date-dimension handling for live events
- Idempotent processing
- Retry/DLQ through the event bus
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streaming.event_bus import event_bus
from warehouse.db_manager import is_postgres, get_connection


class StreamConsumer:

    def __init__(self):
        self.running = False
        self.processed_count = 0

    # ============================================================
    # DATE DIMENSION
    # ============================================================

    def ensure_date_dimension(self, cur, date_key: str):
        """
        Ensures that the date associated with a live event exists
        in dim_date before inserting into fact tables.

        Date attributes are calculated in Python instead of using
        PostgreSQL EXTRACT expressions with parameters.
        """

        date_obj = datetime.strptime(
            date_key,
            "%Y-%m-%d"
        )

        year = date_obj.year

        quarter = (
            (date_obj.month - 1) // 3
        ) + 1

        month = date_obj.month

        day = date_obj.day

        # Python:
        # Monday = 0
        # Sunday = 6
        day_of_week = date_obj.weekday()

        is_weekend = day_of_week >= 5

        if is_postgres():

            cur.execute(
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
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT (date_key) DO NOTHING
                """,
                (
                    date_key,
                    date_key,
                    year,
                    quarter,
                    month,
                    day,
                    day_of_week,
                    is_weekend
                )
            )

        else:

            cur.execute(
                """
                INSERT OR IGNORE INTO dim_date (
                    date_key,
                    full_date,
                    year,
                    quarter,
                    month,
                    day,
                    day_of_week,
                    is_weekend
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date_key,
                    date_key,
                    year,
                    quarter,
                    month,
                    day,
                    day_of_week,
                    is_weekend
                )
            )

    # ============================================================
    # PRODUCT EVENT
    # ============================================================

    def process_product_event(
        self,
        event: Dict[str, Any]
    ):
        """
        Processes product telemetry events.

        Flow:

        Live Event
             ↓
        Validate
             ↓
        Ensure Date Dimension
             ↓
        fact_usage
             ↓
        Customer Health
        """

        required_fields = [
            "event_id",
            "account_id",
            "user_id",
            "feature",
            "timestamp"
        ]

        for field in required_fields:

            if field not in event:

                raise ValueError(
                    f"Product event missing required field: {field}"
                )

        account_id = event["account_id"]

        user_id = event["user_id"]

        feature = event["feature"]

        ts = event["timestamp"]

        usage_id = event["event_id"]

        date_key = ts[:10]

        conn = get_connection()

        try:

            cur = conn.cursor()

            # ----------------------------------------------------
            # 1. Ensure live event date exists
            # ----------------------------------------------------

            self.ensure_date_dimension(
                cur,
                date_key
            )

            # ----------------------------------------------------
            # 2. Insert usage event
            # ----------------------------------------------------

            if is_postgres():

                cur.execute(
                    """
                    INSERT INTO fact_usage (
                        usage_id,
                        account_id,
                        user_id,
                        feature,
                        event_timestamp,
                        event_date
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (usage_id) DO NOTHING
                    """,
                    (
                        usage_id,
                        account_id,
                        user_id,
                        feature,
                        ts,
                        date_key
                    )
                )

                inserted = cur.rowcount

                # ------------------------------------------------
                # 3. Update customer health
                # ------------------------------------------------

                if inserted > 0:

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            events_last_30d =
                                events_last_30d + 1,

                            health_score =
                                LEAST(
                                    100.0,
                                    health_score + 0.1
                                ),

                            health_tier =
                                CASE
                                    WHEN LEAST(
                                        100.0,
                                        health_score + 0.1
                                    ) >= 75.0
                                        THEN 'Healthy'

                                    WHEN LEAST(
                                        100.0,
                                        health_score + 0.1
                                    ) >= 50.0
                                        THEN 'At Risk'

                                    ELSE 'Critical'
                                END,

                            last_updated_at = %s

                        WHERE account_id = %s
                        """,
                        (
                            ts,
                            account_id
                        )
                    )

            else:

                cur.execute(
                    """
                    INSERT OR IGNORE INTO fact_usage (
                        usage_id,
                        account_id,
                        user_id,
                        feature,
                        event_timestamp,
                        event_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        usage_id,
                        account_id,
                        user_id,
                        feature,
                        ts,
                        date_key
                    )
                )

                inserted = cur.rowcount

                if inserted > 0:

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            events_last_30d =
                                events_last_30d + 1,

                            health_score =
                                MIN(
                                    100.0,
                                    health_score + 0.1
                                ),

                            health_tier =
                                CASE
                                    WHEN MIN(
                                        100.0,
                                        health_score + 0.1
                                    ) >= 75.0
                                        THEN 'Healthy'

                                    WHEN MIN(
                                        100.0,
                                        health_score + 0.1
                                    ) >= 50.0
                                        THEN 'At Risk'

                                    ELSE 'Critical'
                                END,

                            last_updated_at = ?

                        WHERE account_id = ?
                        """,
                        (
                            ts,
                            account_id
                        )
                    )

            conn.commit()

            if inserted > 0:

                self.processed_count += 1

                print(
                    f"[Consumer] ✅ Processed telemetry "
                    f"{usage_id} for {account_id}. "
                    f"Health updated."
                )

            else:

                print(
                    f"[Consumer] ⚠️ Duplicate telemetry "
                    f"{usage_id} ignored."
                )

        except Exception:

            conn.rollback()

            raise

        finally:

            conn.close()

    # ============================================================
    # BILLING EVENT
    # ============================================================

    def process_billing_event(
        self,
        event: Dict[str, Any]
    ):
        """
        Processes live billing updates.

        Failed payment:
            ↓
        Customer health penalty
            ↓
        Payment status = Failed / Overdue
        """

        required_fields = [
            "event_id",
            "account_id",
            "invoice_id",
            "amount",
            "status",
            "timestamp"
        ]

        for field in required_fields:

            if field not in event:

                raise ValueError(
                    f"Billing event missing required field: {field}"
                )

        account_id = event["account_id"]

        status = event["status"]

        amount = event["amount"]

        invoice_id = event["invoice_id"]

        ts = event["timestamp"]

        conn = get_connection()

        try:

            cur = conn.cursor()

            # Ensure live event date exists
            date_key = ts[:10]

            self.ensure_date_dimension(
                cur,
                date_key
            )

            if status == "failed":

                if is_postgres():

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            payment_status =
                                'Failed / Overdue',

                            health_score =
                                GREATEST(
                                    0.0,
                                    health_score - 25.0
                                ),

                            health_tier =
                                CASE
                                    WHEN GREATEST(
                                        0.0,
                                        health_score - 25.0
                                    ) >= 75.0
                                        THEN 'Healthy'

                                    WHEN GREATEST(
                                        0.0,
                                        health_score - 25.0
                                    ) >= 50.0
                                        THEN 'At Risk'

                                    ELSE 'Critical'
                                END,

                            last_updated_at = %s

                        WHERE account_id = %s
                        """,
                        (
                            ts,
                            account_id
                        )
                    )

                else:

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            payment_status =
                                'Failed / Overdue',

                            health_score =
                                MAX(
                                    0.0,
                                    health_score - 25.0
                                ),

                            health_tier =
                                CASE
                                    WHEN MAX(
                                        0.0,
                                        health_score - 25.0
                                    ) >= 75.0
                                        THEN 'Healthy'

                                    WHEN MAX(
                                        0.0,
                                        health_score - 25.0
                                    ) >= 50.0
                                        THEN 'At Risk'

                                    ELSE 'Critical'
                                END,

                            last_updated_at = ?

                        WHERE account_id = ?
                        """,
                        (
                            ts,
                            account_id
                        )
                    )

                print(
                    f"[Consumer] 🚨 Payment failure "
                    f"for {account_id}! "
                    f"Health penalized."
                )

            conn.commit()

            self.processed_count += 1

        except Exception:

            conn.rollback()

            raise

        finally:

            conn.close()

    # ============================================================
    # SUPPORT EVENT
    # ============================================================

    def process_support_event(
        self,
        event: Dict[str, Any]
    ):
        """
        Processes live support tickets.

        High severity support issues reduce customer health.
        """

        required_fields = [
            "event_id",
            "ticket_id",
            "account_id",
            "severity",
            "status",
            "timestamp"
        ]

        for field in required_fields:

            if field not in event:

                raise ValueError(
                    f"Support event missing required field: {field}"
                )

        account_id = event["account_id"]

        severity = event["severity"]

        status = event["status"]

        ts = event["timestamp"]

        conn = get_connection()

        try:

            cur = conn.cursor()

            date_key = ts[:10]

            self.ensure_date_dimension(
                cur,
                date_key
            )

            # ----------------------------------------------------
            # Determine health penalty
            # ----------------------------------------------------

            if severity == "high":

                penalty = 15.0

            elif severity == "medium":

                penalty = 5.0

            else:

                penalty = 0.0

            # ----------------------------------------------------
            # Update customer health
            # ----------------------------------------------------

            if penalty > 0:

                if is_postgres():

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            health_score =
                                GREATEST(
                                    0.0,
                                    health_score - %s
                                ),

                            health_tier =
                                CASE
                                    WHEN GREATEST(
                                        0.0,
                                        health_score - %s
                                    ) >= 75.0
                                        THEN 'Healthy'

                                    WHEN GREATEST(
                                        0.0,
                                        health_score - %s
                                    ) >= 50.0
                                        THEN 'At Risk'

                                    ELSE 'Critical'
                                END,

                            last_updated_at = %s

                        WHERE account_id = %s
                        """,
                        (
                            penalty,
                            penalty,
                            penalty,
                            ts,
                            account_id
                        )
                    )

                else:

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            health_score =
                                MAX(
                                    0.0,
                                    health_score - ?
                                ),

                            health_tier =
                                CASE
                                    WHEN MAX(
                                        0.0,
                                        health_score - ?
                                    ) >= 75.0
                                        THEN 'Healthy'

                                    WHEN MAX(
                                        0.0,
                                        health_score - ?
                                    ) >= 50.0
                                        THEN 'At Risk'

                                    ELSE 'Critical'
                                END,

                            last_updated_at = ?

                        WHERE account_id = ?
                        """,
                        (
                            penalty,
                            penalty,
                            penalty,
                            ts,
                            account_id
                        )
                    )

            conn.commit()

            self.processed_count += 1

            print(
                f"[Consumer] 🎫 Support event processed "
                f"for {account_id}. "
                f"Severity={severity}, "
                f"Status={status}"
            )

        except Exception:

            conn.rollback()

            raise

        finally:

            conn.close()

    # ============================================================
    # SUBSCRIPTION EVENT
    # ============================================================

    def process_subscription_event(
        self,
        event: Dict[str, Any]
    ):
        """
        Processes live subscription updates.

        The current producer does not yet emit subscription
        events, but the consumer is prepared to process them.
        """

        required_fields = [
            "event_id",
            "account_id",
            "status",
            "timestamp"
        ]

        for field in required_fields:

            if field not in event:

                raise ValueError(
                    f"Subscription event missing required field: {field}"
                )

        account_id = event["account_id"]

        status = event["status"]

        ts = event["timestamp"]

        conn = get_connection()

        try:

            cur = conn.cursor()

            date_key = ts[:10]

            self.ensure_date_dimension(
                cur,
                date_key
            )

            # ----------------------------------------------------
            # Handle cancelled/churned subscription
            # ----------------------------------------------------

            if status in [
                "cancelled",
                "churned"
            ]:

                if is_postgres():

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            health_score =
                                GREATEST(
                                    0.0,
                                    health_score - 30.0
                                ),

                            health_tier =
                                'Critical',

                            last_updated_at = %s

                        WHERE account_id = %s
                        """,
                        (
                            ts,
                            account_id
                        )
                    )

                else:

                    cur.execute(
                        """
                        UPDATE mrt_customer_health
                        SET
                            health_score =
                                MAX(
                                    0.0,
                                    health_score - 30.0
                                ),

                            health_tier =
                                'Critical',

                            last_updated_at = ?

                        WHERE account_id = ?

                        """,
                        (
                            ts,
                            account_id
                        )
                    )

            conn.commit()

            self.processed_count += 1

            print(
                f"[Consumer] 🔄 Subscription event "
                f"processed for {account_id}. "
                f"Status={status}"
            )

        except Exception:

            conn.rollback()

            raise

        finally:

            conn.close()

    # ============================================================
    # POLL ALL TOPICS
    # ============================================================

    def poll_and_process_all(self):
        """
        Drains all waiting events from all streaming topics.
        """

        topics = [
            "product.events",
            "subscription.events",
            "billing.events",
            "support.events"
        ]

        for topic in topics:

            while True:

                evt = event_bus.consume(topic)

                if not evt:

                    break

                try:

                    if topic == "product.events":

                        self.process_product_event(evt)

                    elif topic == "billing.events":

                        self.process_billing_event(evt)

                    elif topic == "support.events":

                        self.process_support_event(evt)

                    elif topic == "subscription.events":

                        self.process_subscription_event(evt)

                except Exception as e:

                    print(
                        f"[Consumer] ❌ Failed processing "
                        f"{evt.get('event_id', 'unknown')}: {e}"
                    )

                    # Send failed event through retry/DLQ
                    # mechanism.
                    event_bus.handle_failure(
                        evt,
                        str(e)
                    )


# ================================================================
# GLOBAL CONSUMER
# ================================================================

consumer = StreamConsumer()


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":

    print(
        "[Consumer] Running stream consumer poll..."
    )

    consumer.poll_and_process_all()

    print(
        f"[Consumer] Completed. "
        f"Processed {consumer.processed_count} events."
    )