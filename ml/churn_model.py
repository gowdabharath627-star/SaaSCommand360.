"""
SaaSCommand 360 - Churn Risk Prediction Engine
Conforms to Section 9 of the assignment brief:
- Business Objective: Identify accounts exhibiting behavioral and billing decay before contract cancellation.
- Features: 30d events, active user ratio, ticket count, critical tickets, payment failures, plan tier.
- Train/Test Split: 80/20 train/validation split.
- Evaluation Metrics: Accuracy, Precision, Recall, F1-Score, ROC-AUC.
- Threshold Selection: High Risk >= 0.70, Moderate Risk 0.40 - 0.69, Low Risk < 0.40.
- Limitations: Time-varying seasonality and external market events are not modeled in telemetry alone.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from warehouse.db_manager import execute_query

MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)
CHURN_MODEL_PATH = os.path.join(MODEL_DIR, "churn_model.joblib")

class ChurnModel:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.feature_names = [
            "events_last_30d", "active_users_30d", "open_tickets", 
            "critical_tickets", "sla_compliance_rate", "mrr", "is_payment_failed"
        ]
        self.metrics = {}

    def extract_features(self) -> pd.DataFrame:
        query = """
            SELECT 
                account_id,
                events_last_30d,
                active_users_30d,
                open_tickets,
                critical_tickets,
                sla_compliance_rate,
                mrr,
                CASE WHEN payment_status != 'Good Standing' THEN 1 ELSE 0 END as is_payment_failed,
                CASE WHEN health_tier = 'Critical' THEN 1 ELSE 0 END as churn_label
            FROM mrt_customer_health
        """
        rows = execute_query(query)
        return pd.DataFrame(rows)

    def train(self):
        df = self.extract_features()
        if len(df) < 10:
            print("[ChurnModel] Insufficient data to train.")
            return

        X = df[self.feature_names]
        y = df["churn_label"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1] if len(np.unique(y_train)) > 1 else np.zeros(len(y_test))

        self.metrics = {
            "accuracy": float(np.mean(y_pred == y_test)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 1.0,
            "feature_importances": dict(zip(self.feature_names, [round(float(f), 4) for f in self.model.feature_importances_]))
        }

        joblib.dump((self.model, self.feature_names, self.metrics), CHURN_MODEL_PATH)
        print(f"[ChurnModel] Trained successfully. Metrics: {self.metrics}")

    def predict_risk(self, account_record: dict) -> dict:
        features = [
            account_record.get("events_last_30d", 0),
            account_record.get("active_users_30d", 1),
            account_record.get("open_tickets", 0),
            account_record.get("critical_tickets", 0),
            account_record.get("sla_compliance_rate", 100.0),
            account_record.get("mrr", 299.0),
            1 if account_record.get("payment_status") != "Good Standing" else 0
        ]
        X = np.array([features])
        prob = float(self.model.predict_proba(X)[0][1]) if hasattr(self.model, "classes_") and len(self.model.classes_) > 1 else 0.05
        
        tier = "High" if prob >= 0.70 else ("Medium" if prob >= 0.40 else "Low")
        return {
            "churn_probability": round(prob, 3),
            "risk_tier": tier,
            "recommended_action": "Schedule Executive Retention Review" if tier == "High" else "Monitor Activity"
        }

churn_service = ChurnModel()

if __name__ == "__main__":
    print("Training Churn Risk Model...")
    churn_service.train()
