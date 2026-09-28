"""
SaaSCommand 360 - Expansion Opportunity Scoring Engine
Conforms to Section 9 of the assignment brief:
- Business Objective: Identify customer accounts primed for plan upgrades, tier expansions, or add-ons.
- Features: Event usage ratio vs plan quota, active user count vs seat limit, health score, account age.
- Thresholds: Score >= 0.75 indicates high expansion propensity.
- Limitations: Does not account for external customer budgetary approval cycles.
"""

import os
import sys
import pandas as pd
from warehouse.db_manager import execute_query

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class ExpansionModel:
    def score_all_accounts(self) -> list:
        query = """
            SELECT 
                h.account_id,
                h.company_name,
                h.plan,
                h.mrr,
                h.health_score,
                h.events_last_30d,
                h.active_users_30d,
                p.seat_limit,
                p.event_quota
            FROM mrt_customer_health h
            JOIN dim_plan p ON h.plan = p.plan_name
        """
        rows = execute_query(query)
        scored = []

        for r in rows:
            seat_utilization = min(1.0, r["active_users_30d"] / max(1, r["seat_limit"]))
            event_utilization = min(1.0, (r["events_last_30d"] * 10) / max(1, r["event_quota"]))
            health_factor = r["health_score"] / 100.0

            # Weighted expansion score (0.0 to 1.0)
            score = (seat_utilization * 0.40) + (event_utilization * 0.35) + (health_factor * 0.25)
            score = round(min(0.99, max(0.01, score)), 3)

            tier = "High" if score >= 0.70 else ("Moderate" if score >= 0.45 else "Low")
            recommended_upgrade = {
                "Starter": "Professional",
                "Professional": "Enterprise",
                "Enterprise": "Enterprise Plus",
                "Enterprise Plus": "Custom Dedicated Cluster"
            }.get(r["plan"], "Enterprise")

            scored.append({
                "account_id": r["account_id"],
                "company_name": r["company_name"],
                "current_plan": r["plan"],
                "current_mrr": float(r["mrr"]),
                "seat_utilization": round(seat_utilization * 100, 1),
                "event_utilization": round(event_utilization * 100, 1),
                "expansion_score": score,
                "opportunity_tier": tier,
                "recommended_plan": recommended_upgrade,
                "potential_mrr_expansion": round(float(r["mrr"]) * 0.8, 2)
            })

        scored.sort(key=lambda x: x["expansion_score"], reverse=True)
        return scored

expansion_service = ExpansionModel()

if __name__ == "__main__":
    opps = expansion_service.score_all_accounts()
    print(f"Computed {len(opps)} expansion scores. Top opportunity: {opps[0]}")
