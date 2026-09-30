"""
SaaSCommand 360 - Expansion Opportunity Scoring Engine

Business Objective:
- Identify customer accounts primed for plan upgrades,
  tier expansions, or add-ons.

Features:
- Event usage ratio vs plan quota
- Active user count vs seat limit
- Customer health score

Scoring:
- Seat utilization: 40%
- Event utilization: 35%
- Health score: 25%

Thresholds:
- Score >= 0.75: High expansion propensity
- Score >= 0.45 and < 0.75: Moderate expansion propensity
- Score < 0.45: Low expansion propensity

Limitations:
- Does not account for external customer budgetary approval cycles.
- Potential MRR expansion is an estimated business opportunity,
  not a guaranteed revenue outcome.
"""

import os
import sys


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from warehouse.db_manager import execute_query

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

HIGH_THRESHOLD = 0.75
MODERATE_THRESHOLD = 0.45


class ExpansionModel:

    def score_all_accounts(self) -> list:
        """
        Calculates expansion opportunity scores for all accounts.
        """

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
            JOIN dim_plan p
                ON h.plan = p.plan_name
        """

        rows = execute_query(query)

        if not rows:
            return []

        scored = []

        for r in rows:

            # -------------------------------------------------
            # Seat utilization
            # -------------------------------------------------

            seat_utilization = min(
                1.0,
                float(r["active_users_30d"])
                / max(1, float(r["seat_limit"]))
            )

            # -------------------------------------------------
            # Event utilization
            #
            # events_last_30d is scaled because the event
            # quota represents a larger usage capacity.
            # -------------------------------------------------

            event_utilization = min(
                1.0,
                (
                    float(r["events_last_30d"]) * 10
                )
                / max(1, float(r["event_quota"]))
            )

            # -------------------------------------------------
            # Customer health factor
            # -------------------------------------------------

            health_factor = min(
                1.0,
                max(
                    0.0,
                    float(r["health_score"]) / 100.0
                )
            )

            # -------------------------------------------------
            # Weighted expansion score
            #
            # Seat utilization  = 40%
            # Event utilization = 35%
            # Health score       = 25%
            # -------------------------------------------------

            score = (
                (seat_utilization * 0.40)
                + (event_utilization * 0.35)
                + (health_factor * 0.25)
            )

            score = round(
                min(0.99, max(0.01, score)),
                3
            )

            # -------------------------------------------------
            # Opportunity tier
            # -------------------------------------------------

            if score >= HIGH_THRESHOLD:

                tier = "High"

            elif score >= MODERATE_THRESHOLD:

                tier = "Moderate"

            else:

                tier = "Low"

            # -------------------------------------------------
            # Recommended upgrade
            # -------------------------------------------------

            recommended_upgrade = {
                "Starter": "Professional",
                "Professional": "Enterprise",
                "Enterprise": "Enterprise Plus",
                "Enterprise Plus": "Custom Dedicated Cluster"
            }.get(
                r["plan"],
                "Enterprise"
            )

            # -------------------------------------------------
            # Potential MRR
            #
            # This is an estimated opportunity value.
            # -------------------------------------------------

            potential_mrr = (
                float(r["mrr"]) * 0.80
            )

            scored.append({

                "account_id":
                    r["account_id"],

                "company_name":
                    r["company_name"],

                "current_plan":
                    r["plan"],

                "current_mrr":
                    float(r["mrr"]),

                "seat_utilization":
                    round(
                        seat_utilization * 100,
                        1
                    ),

                "event_utilization":
                    round(
                        event_utilization * 100,
                        1
                    ),

                "health_score":
                    round(
                        float(r["health_score"]),
                        1
                    ),

                "expansion_score":
                    score,

                "opportunity_tier":
                    tier,

                "recommended_plan":
                    recommended_upgrade,

                "potential_mrr_expansion":
                    round(
                        potential_mrr,
                        2
                    )
            })

        # Highest opportunity first
        scored.sort(
            key=lambda x: x["expansion_score"],
            reverse=True
        )

        return scored


# ---------------------------------------------------------
# Service instance
# ---------------------------------------------------------

expansion_service = ExpansionModel()


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    print(
        "========== Expansion Opportunity Scoring =========="
    )

    opportunities = (
        expansion_service.score_all_accounts()
    )

    print(
        f"Computed {len(opportunities)} expansion scores."
    )

    if opportunities:

        print("\nTop 10 opportunities:")

        for opportunity in opportunities[:10]:

            print(
                f"{opportunity['account_id']} | "
                f"{opportunity['company_name']} | "
                f"Score={opportunity['expansion_score']} | "
                f"Tier={opportunity['opportunity_tier']} | "
                f"{opportunity['current_plan']} -> "
                f"{opportunity['recommended_plan']} | "
                f"Potential MRR="
                f"${opportunity['potential_mrr_expansion']:,.2f}"
            )

    else:

        print(
            "No expansion opportunities found."
        )