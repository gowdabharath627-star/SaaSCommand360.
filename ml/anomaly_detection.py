"""
SaaSCommand 360 - Usage Telemetry Anomaly Detection

Business Objective:
- Detect abnormal customer usage behavior.
- Usage drops can indicate product blockage or churn risk.
- Usage spikes can indicate strong adoption, unusual activity, or upgrade opportunity.

Method:
- 14-day rolling historical baseline.
- Z-score comparison against the historical baseline.
- Week-over-week usage comparison.

Thresholds:
- Absolute Z-score > 2.5 triggers an anomaly.
- Usage drop > 65% week-over-week triggers a drop anomaly.

Limitations:
- Holidays, planned maintenance, seasonality, or known product incidents
  may create false positives.
"""

import os
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from warehouse.db_manager import execute_query


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

ROLLING_DAYS = 14
Z_SCORE_THRESHOLD = 2.5
WOW_DROP_THRESHOLD = 0.65


# ---------------------------------------------------------
# Main anomaly detection
# ---------------------------------------------------------

def detect_usage_anomalies() -> list:
    """
    Detects abnormal daily usage for each account.

    Returns:
        list: Detected usage anomalies.
    """

    query = """
        SELECT
            account_id,
            event_date,
            COUNT(*) AS daily_events
        FROM fact_usage
        GROUP BY account_id, event_date
        ORDER BY account_id, event_date
    """

    rows = execute_query(query)

    if not rows:
        return []

    df = pd.DataFrame(rows)

    if df.empty:
        return []

    df["event_date"] = pd.to_datetime(df["event_date"])

    df = df.sort_values(
        ["account_id", "event_date"]
    )

    anomalies = []

    # -----------------------------------------------------
    # Process each account independently
    # -----------------------------------------------------

    for account_id, group in df.groupby("account_id"):

        group = group.sort_values("event_date").copy()

        # Need enough history for a meaningful baseline
        if len(group) < ROLLING_DAYS + 1:
            continue

        group["daily_events"] = group["daily_events"].astype(float)

        # -------------------------------------------------
        # Latest observation
        # -------------------------------------------------

        latest_row = group.iloc[-1]

        latest_date = latest_row["event_date"]
        latest_events = float(latest_row["daily_events"])

        # -------------------------------------------------
        # 14-day historical baseline
        #
        # Exclude today's value from the baseline so that
        # the current observation doesn't influence its own
        # expected value.
        # -------------------------------------------------

        historical = group.iloc[-ROLLING_DAYS - 1:-1]

        historical_events = historical["daily_events"].values

        historical_mean = float(
            np.mean(historical_events)
        )

        historical_std = float(
            np.std(historical_events)
        )

        # -------------------------------------------------
        # Z-score
        # -------------------------------------------------

        if historical_std == 0:

            # If historical usage is completely constant,
            # calculate deviation using the baseline itself.
            if historical_mean == 0:
                z_score = 0.0
            else:
                z_score = (
                    (latest_events - historical_mean)
                    / historical_mean
                )

        else:

            z_score = (
                (latest_events - historical_mean)
                / historical_std
            )

        # -------------------------------------------------
        # Week-over-week comparison
        #
        # Compare latest 7 days against previous 7 days.
        # -------------------------------------------------

        wow_change = None

        if len(group) >= 14:

            previous_7 = group.iloc[-14:-7]["daily_events"].sum()
            latest_7 = group.iloc[-7:]["daily_events"].sum()

            if previous_7 > 0:

                wow_change = (
                    (latest_7 - previous_7)
                    / previous_7
                )

        # -------------------------------------------------
        # Detect anomaly
        # -------------------------------------------------

        anomaly_type = None
        severity = None
        suggested_action = None

        # ---------------------------------------------
        # Severe usage drop
        # ---------------------------------------------

        if (
            z_score < -Z_SCORE_THRESHOLD
            or (
                wow_change is not None
                and wow_change <= -WOW_DROP_THRESHOLD
            )
        ):

            anomaly_type = "Severe Usage Drop"

            severity = (
                "high"
                if z_score < -3.0
                else "medium"
            )

            suggested_action = (
                "Trigger CSM check-in on possible product blockage"
            )

        # ---------------------------------------------
        # Usage spike
        # ---------------------------------------------

        elif z_score > Z_SCORE_THRESHOLD:

            anomaly_type = "Usage Spike"

            severity = (
                "high"
                if z_score > 3.0
                else "medium"
            )

            suggested_action = (
                "Review increased product adoption for expansion opportunity"
            )

        # ---------------------------------------------
        # Store anomaly
        # ---------------------------------------------

        if anomaly_type:

            anomaly = {
                "account_id": account_id,
                "event_date": latest_date.strftime("%Y-%m-%d"),
                "latest_daily_events": int(latest_events),
                "historical_mean": round(
                    historical_mean,
                    2
                ),
                "historical_std": round(
                    historical_std,
                    2
                ),
                "z_score": round(
                    float(z_score),
                    2
                ),
                "wow_change_pct": (
                    round(float(wow_change) * 100, 2)
                    if wow_change is not None
                    else None
                ),
                "anomaly_type": anomaly_type,
                "severity": severity,
                "suggested_action": suggested_action
            }

            anomalies.append(anomaly)

    return anomalies


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    print("========== Usage Anomaly Detection ==========")

    anomalies = detect_usage_anomalies()

    print(
        f"Detected {len(anomalies)} usage anomalies across accounts."
    )

    if anomalies:

        print("\nDetected anomalies:")

        for anomaly in anomalies:

            print(
                f"[{anomaly['severity'].upper()}] "
                f"{anomaly['account_id']} | "
                f"{anomaly['anomaly_type']} | "
                f"Z={anomaly['z_score']} | "
                f"Latest={anomaly['latest_daily_events']} | "
                f"Baseline={anomaly['historical_mean']}"
            )

    else:

        print("No significant usage anomalies detected.")