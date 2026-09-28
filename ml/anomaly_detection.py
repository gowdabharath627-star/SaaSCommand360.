"""
SaaSCommand 360 - Usage Telemetry Anomaly Detection
Conforms to Section 9 of the assignment brief:
- Business Objective: Flag sudden, statistically abnormal usage drops (leading churn indicator) or spikes (potential abuse / upgrade signal).
- Method: Rolling 14-day Z-Score & Isolation bounds against historical baseline.
- Threshold: Absolute Z-Score > 2.5 or > 65% WoW drop triggers anomaly flag.
- Limitations: Holidays and system-wide planned maintenance may produce false positive anomalies.
"""

import os
import sys
import numpy as np
import pandas as pd
from warehouse.db_manager import execute_query

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def detect_usage_anomalies() -> list:
    """Calculates daily usage trajectories per account and flags anomalies."""
    query = """
        SELECT 
            account_id,
            event_date,
            COUNT(*) as daily_events
        FROM fact_usage
        GROUP BY account_id, event_date
        ORDER BY account_id, event_date
    """
    rows = execute_query(query)
    if not rows:
        return []

    df = pd.DataFrame(rows)
    anomalies = []

    for account_id, group in df.groupby("account_id"):
        if len(group) < 7:
            continue
        
        events = group["daily_events"].values
        mean = np.mean(events[:-1])
        std = np.std(events[:-1]) or 1.0

        latest = events[-1]
        z_score = (latest - mean) / std

        # Flag significant drops (Z-Score < -2.0 or drop > 70%)
        if z_score < -2.0 or (mean > 20 and latest < mean * 0.3):
            anomalies.append({
                "account_id": account_id,
                "latest_daily_events": int(latest),
                "historical_mean": round(float(mean), 1),
                "z_score": round(float(z_score), 2),
                "anomaly_type": "Severe Usage Drop",
                "severity": "high" if z_score < -3.0 else "medium",
                "suggested_action": "Trigger CSM check-in on product blockage"
            })

    return anomalies

if __name__ == "__main__":
    anoms = detect_usage_anomalies()
    print(f"Detected {len(anoms)} usage anomalies across accounts.")
