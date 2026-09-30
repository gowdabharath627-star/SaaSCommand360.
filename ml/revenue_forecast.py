"""
SaaSCommand 360 - Revenue Forecasting Engine

Business Objective:
- Forecast Monthly Recurring Revenue (MRR) and Annual Recurring Revenue (ARR).
- Provide Base, Bull, and Bear business scenarios.

Data Source:
- Current MRR, revenue churn, and expansion metrics are read
  from the warehouse revenue mart.

Method:
- Warehouse KPI-informed scenario forecasting.
- Expansion and revenue churn are combined to calculate
  annual net revenue growth.
- Annual growth is converted to an equivalent monthly
  compounded growth rate.
- MRR is projected month by month for the selected horizon.

Scenarios:
- Base: Current warehouse-derived trend.
- Bull: Base annual growth + 2 percentage points.
- Bear: Base annual growth - 2 percentage points.

Limitations:
- The current synthetic dataset does not contain a long historical
  MRR time series, so this is a scenario forecast rather than a
  trained time-series forecasting model.
- Future pricing changes, new customer acquisition, contract
  renewals, and unexpected market conditions are not modeled.
"""

import os
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from warehouse.db_manager import execute_query


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SCENARIO_ADJUSTMENT = 0.02


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def annual_to_monthly_rate(annual_rate: float) -> float:
    """
    Converts an annual growth rate into an equivalent
    monthly compounded growth rate.

    Example:
        12% annual growth
        -> approximately 0.95% monthly growth
    """

    if annual_rate <= -1:
        return -1.0

    return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0


# ---------------------------------------------------------
# Forecast
# ---------------------------------------------------------

def generate_revenue_forecast(horizon_months: int = 12) -> dict:
    """
    Generates forward MRR and ARR projections.

    The starting MRR and revenue metrics come from the
    warehouse revenue mart.
    """

    if horizon_months <= 0:
        raise ValueError("horizon_months must be greater than 0")

    # -----------------------------------------------------
    # Read current warehouse revenue KPIs
    # -----------------------------------------------------

    query = """
        SELECT
            total_mrr,
            revenue_churn_rate,
            expansion_rate
        FROM mrt_revenue_summary
        ORDER BY id DESC
        LIMIT 1
    """

    summary_row = execute_query(
        query,
        fetch="one"
    )

    if not summary_row:
        raise RuntimeError(
            "No revenue summary found in mrt_revenue_summary."
        )

    # -----------------------------------------------------
    # Current warehouse values
    # -----------------------------------------------------

    base_mrr = float(
        summary_row["total_mrr"] or 0
    )

    revenue_churn_rate = float(
        summary_row["revenue_churn_rate"] or 0
    )

    expansion_rate = float(
        summary_row["expansion_rate"] or 0
    )

    # -----------------------------------------------------
    # Convert percentage values to decimal
    #
    # Example:
    # 3.07% -> 0.0307
    # -----------------------------------------------------

    expansion_annual = expansion_rate / 100.0
    churn_annual = revenue_churn_rate / 100.0

    # -----------------------------------------------------
    # Base net revenue growth
    #
    # Net growth = expansion - churn
    # -----------------------------------------------------

    base_net_annual_growth = (
        expansion_annual - churn_annual
    )

    # -----------------------------------------------------
    # Build scenarios
    # -----------------------------------------------------

    scenarios = {

        "base": {
            "annual_growth": base_net_annual_growth,
            "label": "Base Case (Current Warehouse Trend)"
        },

        "bull": {
            "annual_growth": (
                base_net_annual_growth
                + SCENARIO_ADJUSTMENT
            ),
            "label": "Bull Case (Improved Growth)"
        },

        "bear": {
            "annual_growth": (
                base_net_annual_growth
                - SCENARIO_ADJUSTMENT
            ),
            "label": "Bear Case (Higher Pressure)"
        }
    }

    # -----------------------------------------------------
    # Convert annual growth to monthly growth
    # -----------------------------------------------------

    for scenario in scenarios.values():

        scenario["monthly_growth"] = annual_to_monthly_rate(
            scenario["annual_growth"]
        )

    # -----------------------------------------------------
    # Generate monthly projections
    # -----------------------------------------------------

    forecast_data = []

    current_mrr_state = {
        scenario: base_mrr
        for scenario in scenarios
    }

    now = datetime.now(timezone.utc)

    for month_index in range(
        1,
        horizon_months + 1
    ):

        month_obj = {
            "period": f"Month +{month_index}",
            "month_index": month_index
        }

        for scenario_key, scenario_config in scenarios.items():

            monthly_growth = scenario_config[
                "monthly_growth"
            ]

            current_mrr_state[
                scenario_key
            ] *= (1.0 + monthly_growth)

            projected_mrr = current_mrr_state[
                scenario_key
            ]

            projected_arr = projected_mrr * 12.0

            month_obj[
                f"mrr_{scenario_key}"
            ] = round(
                projected_mrr,
                2
            )

            month_obj[
                f"arr_{scenario_key}"
            ] = round(
                projected_arr,
                2
            )

        forecast_data.append(month_obj)

    # -----------------------------------------------------
    # Return result
    # -----------------------------------------------------

    return {

        "generated_at": now.isoformat(),

        "starting_mrr": round(
            base_mrr,
            2
        ),

        "starting_arr": round(
            base_mrr * 12.0,
            2
        ),

        "warehouse_metrics": {

            "expansion_rate": round(
                expansion_rate,
                2
            ),

            "revenue_churn_rate": round(
                revenue_churn_rate,
                2
            ),

            "net_annual_growth": round(
                base_net_annual_growth * 100,
                2
            )
        },

        "horizon_months": horizon_months,

        "scenarios": scenarios,

        "projections": forecast_data
    }


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":

    print("========== Revenue Forecast ==========")

    forecast = generate_revenue_forecast(
        horizon_months=12
    )

    print(
        f"Starting MRR: "
        f"${forecast['starting_mrr']:,.2f}"
    )

    print(
        f"Starting ARR: "
        f"${forecast['starting_arr']:,.2f}"
    )

    print(
        f"Expansion Rate: "
        f"{forecast['warehouse_metrics']['expansion_rate']:.2f}%"
    )

    print(
        f"Revenue Churn Rate: "
        f"{forecast['warehouse_metrics']['revenue_churn_rate']:.2f}%"
    )

    print(
        f"Net Annual Growth: "
        f"{forecast['warehouse_metrics']['net_annual_growth']:.2f}%"
    )

    print("\nScenario Growth:")

    for scenario_name, config in forecast["scenarios"].items():

        print(
            f"{scenario_name.upper()}: "
            f"{config['annual_growth'] * 100:.2f}% annual | "
            f"{config['monthly_growth'] * 100:.2f}% monthly"
        )

    print("\n12-Month Forecast:")

    for row in forecast["projections"]:

        print(
            f"{row['period']}: "
            f"Base MRR=${row['mrr_base']:,.2f} | "
            f"Bull MRR=${row['mrr_bull']:,.2f} | "
            f"Bear MRR=${row['mrr_bear']:,.2f}"
        )