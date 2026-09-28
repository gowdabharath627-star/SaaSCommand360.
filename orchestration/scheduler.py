"""
SaaSCommand 360 - Orchestration & Workflow Scheduler
Conforms to Section 13 of the assignment brief:
- Batch ingestion & medallion transformations
- Automated data quality checks
- ML model refresh (churn, expansion, revenue forecast)
- Decision rule evaluation & notification dispatch
- Operational run logging with error handling & retries
"""

import os
import sys
import time
import uuid
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from warehouse.pipeline import run_medallion_pipeline
from warehouse.data_quality import run_data_quality_suite
from ml.churn_model import churn_service
from decision_engine.rules import evaluate_decision_rules

def execute_daily_pipeline(max_retries: int = 2) -> dict:
    """Executes the full governed SaaS analytics orchestration workflow."""
    run_id = f"dag_run_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    print("==================================================")
    print(f"[START] SaaSCommand 360 Orchestration DAG [{run_id}]")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("==================================================")

    steps = [
        ("Step 1: Medallion Ingestion & Marts (Bronze->Silver->Gold)", lambda: run_medallion_pipeline()),
        ("Step 2: Automated Data Quality Suite", lambda: run_data_quality_suite()),
        ("Step 3: Machine Learning Model Retraining", lambda: churn_service.train()),
        ("Step 4: Decision Engine Domain Rules Evaluation", lambda: evaluate_decision_rules()),
    ]

    results = {}
    all_success = True

    for step_name, step_fn in steps:
        step_success = False
        attempts = 0
        while not step_success and attempts <= max_retries:
            attempts += 1
            try:
                print(f"[RUN] Executing: {step_name} (Attempt {attempts})...")
                res = step_fn()
                results[step_name] = {"status": "SUCCESS", "attempts": attempts}
                step_success = True
                print(f"[OK] {step_name} completed.")
            except Exception as e:
                print(f"[WARN] {step_name} failed: {e}")
                if attempts > max_retries:
                    results[step_name] = {"status": "FAILED", "error": str(e), "attempts": attempts}
                    all_success = False
                else:
                    time.sleep(1.0)

    duration = round((time.time() - start_time), 2)
    overall_status = "SUCCESS" if all_success else "PARTIAL_FAILURE"

    print("==================================================")
    print(f"[FINISH] Orchestration DAG [{run_id}] finished in {duration}s. Status: {overall_status}")
    print("==================================================")

    return {
        "run_id": run_id,
        "status": overall_status,
        "duration_seconds": duration,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "step_details": results
    }

if __name__ == "__main__":
    execute_daily_pipeline()
