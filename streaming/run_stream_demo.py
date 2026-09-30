"""
SaaSCommand 360 - Streaming Demo Runner
Runs producer and consumer in the same process so the
in-memory event bus can be demonstrated end-to-end.
"""

import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streaming.producer import (
    produce_product_event,
    produce_billing_event,
    produce_support_event
)

from streaming.consumer import consumer
from streaming.event_bus import event_bus


def run_demo():
    print("\n========== SaaSCommand 360 Streaming Demo ==========\n")

    # -------------------------------------------------
    # 1. PRODUCE LIVE EVENTS
    # -------------------------------------------------
    print("[1] Producing live events...")

    for _ in range(5):
        produce_product_event(
            account_id="acc_001",
            user_id="usr_acc_001_01"
        )

    produce_billing_event(
        account_id="acc_002",
        amount=1500.00,
        status="failed"
    )

    produce_support_event(
        account_id="acc_003",
        severity="high"
    )

    print("\n[Producer] Bus stats:")
    print(event_bus.get_stats())

    # -------------------------------------------------
    # 2. CONSUME EVENTS
    # -------------------------------------------------
    print("\n[2] Consuming events...")

    consumer.poll_and_process_all()

    # -------------------------------------------------
    # 3. FINAL STREAMING METRICS
    # -------------------------------------------------
    print("\n[3] Final streaming metrics:")

    print(event_bus.get_stats())

    print(f"\n[Consumer] Processed events: {consumer.processed_count}")

    print("\n========== Streaming Demo Complete ==========\n")


if __name__ == "__main__":
    run_demo()