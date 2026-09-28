"""
SaaSCommand 360 - Real-Time Streaming Event Bus
Kafka-compatible event bus with topics, idempotency deduplication, retry policy, and Dead-Letter Queue (DLQ).
Implements Section 6 of the assignment brief.
"""

import os
import sys
import time
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Callable
from collections import deque
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TOPICS = [
    "product.events",
    "subscription.events",
    "billing.events",
    "support.events"
]

class EventBus:
    """High-throughput In-Memory & Kafka-compatible streaming bus."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._init_bus()
        return cls._instance

    def _init_bus(self):
        self.queues: Dict[str, deque] = {topic: deque() for topic in TOPICS}
        self.dead_letter_queue: deque = deque()
        self.processed_event_hashes: set = set()
        self.subscribers: Dict[str, List[Callable]] = {topic: [] for topic in TOPICS}
        self.metrics = {
            "published": 0,
            "consumed": 0,
            "duplicates_dropped": 0,
            "retried": 0,
            "dlq_count": 0
        }

    def _generate_event_hash(self, event: Dict[str, Any]) -> str:
        """Generates deterministic idempotency hash to prevent duplicate processing."""
        key_fields = f"{event.get('event_id', '')}:{event.get('account_id', '')}:{event.get('feature', '')}:{event.get('timestamp', '')}"
        return hashlib.sha256(key_fields.encode('utf-8')).hexdigest()

    def publish(self, topic: str, event: Dict[str, Any], max_retries: int = 3) -> bool:
        if topic not in self.queues:
            raise ValueError(f"Unknown topic: {topic}. Available topics: {TOPICS}")

        # Ensure required metadata
        if "event_id" not in event:
            event["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        event["_topic"] = topic
        event["_published_at"] = datetime.now(timezone.utc).isoformat()
        event["_retry_count"] = 0
        event["_max_retries"] = max_retries

        # Idempotency deduplication check
        evt_hash = self._generate_event_hash(event)
        if evt_hash in self.processed_event_hashes:
            self.metrics["duplicates_dropped"] += 1
            print(f"[Streaming Bus] ⚠️ Duplicate event dropped: {event['event_id']}")
            return False

        self.processed_event_hashes.add(evt_hash)
        self.queues[topic].append(event)
        self.metrics["published"] += 1
        
        # Trigger real-time subscribers if any
        for callback in self.subscribers.get(topic, []):
            try:
                callback(event)
            except Exception as e:
                self.handle_failure(event, error=str(e))

        return True

    def consume(self, topic: str) -> Optional[Dict[str, Any]]:
        """Pulls next event from topic queue."""
        if topic in self.queues and len(self.queues[topic]) > 0:
            evt = self.queues[topic].popleft()
            self.metrics["consumed"] += 1
            return evt
        return None

    def handle_failure(self, event: Dict[str, Any], error: str):
        """Retries failed event with exponential backoff or routes to Dead Letter Queue (DLQ)."""
        retries = event.get("_retry_count", 0)
        max_retries = event.get("_max_retries", 3)

        if retries < max_retries:
            event["_retry_count"] = retries + 1
            event["_last_error"] = error
            self.metrics["retried"] += 1
            backoff_seconds = (2 ** retries) * 0.1
            time.sleep(backoff_seconds)
            self.queues[event["_topic"]].append(event)
            print(f"[Streaming Bus] 🔄 Retrying event {event['event_id']} (Attempt {retries+1}/{max_retries})")
        else:
            event["_dead_lettered_at"] = datetime.now(timezone.utc).isoformat()
            event["_fatal_error"] = error
            self.dead_letter_queue.append(event)
            self.metrics["dlq_count"] += 1
            print(f"[Streaming Bus] ❌ Event {event['event_id']} routed to Dead Letter Queue (DLQ): {error}")

    def subscribe(self, topic: str, callback: Callable):
        """Registers a push-based subscriber for live stream processing."""
        if topic in self.subscribers:
            self.subscribers[topic].append(callback)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics,
            "queue_depths": {t: len(q) for t, q in self.queues.items()},
            "dlq_depth": len(self.dead_letter_queue)
        }

# Global singleton event bus instance
event_bus = EventBus()
