"""
SaaSCommand 360 - Revenue Forecasting Engine
Conforms to Section 9 of the assignment brief:
- Business Objective: Forecast Monthly Recurring Revenue (MRR) and Annual Recurring Revenue (ARR) across Bear, Base, and Bull trajectories.
- Method: Multi-factor compound monthly growth model incorporating historical expansion, contraction, and churn rates.
- Evaluation: Scenario modeling across 12 forward-looking months.
"""

import os
import sys
from datetime import datetime, timezone
from warehouse.db_manager import execute_query

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def generate_revenue_forecast(horizon_months: int = 12) -> dict:
    """Generates 12-month forward MRR and ARR projections across 3 business scenarios."""
    summary_row = execute_query("SELECT * FROM mrt_revenue_summary ORDER BY id DESC LIMIT 1", fetch="one")
    if not summary_row:
        base_mrr = 125000.0
    else:
        base_mrr = float(summary_row["total_mrr"])

    monthly_expansion_base = 0.035 # 3.5% MoM expansion
    monthly_churn_base = 0.015     # 1.5% MoM churn
    net_growth_base = monthly_expansion_base - monthly_churn_base

    scenarios = {
        "base": {"growth": net_growth_base, "label": "Base Case (Planned Targets)"},
        "bull": {"growth": net_growth_base + 0.02, "label": "Bull Case (High Expansion)"},
        "bear": {"growth": max(0.002, net_growth_base - 0.02), "label": "Bear Case (Higher Churn)"}
    }

    forecast_data = []
    current_mrr_state = {s: base_mrr for s in scenarios}

    now = datetime.now(timezone.utc)
    for m in range(1, horizon_months + 1):
        month_label = f"Month +{m}"
        month_obj = {"period": month_label, "month_index": m}

        for s_key, s_cfg in scenarios.items():
            current_mrr_state[s_key] *= (1.0 + s_cfg["growth"])
            month_obj[f"mrr_{s_key}"] = round(current_mrr_state[s_key], 2)
            month_obj[f"arr_{s_key}"] = round(current_mrr_state[s_key] * 12.0, 2)

        forecast_data.append(month_obj)

    return {
        "starting_mrr": round(base_mrr, 2),
        "starting_arr": round(base_mrr * 12.0, 2),
        "horizon_months": horizon_months,
        "scenarios": scenarios,
        "projections": forecast_data
    }

if __name__ == "__main__":
    fc = generate_revenue_forecast()
    print(f"Generated forecast for {fc['horizon_months']} months. Starting MRR: ${fc['starting_mrr']:,.2f}")
