"""
SaaSCommand 360 - Churn Risk Prediction Engine

Business Objective:
Identify accounts exhibiting behavioral, support, and billing
decay signals that may indicate elevated churn risk.

Features:
- events_last_30d
- active_users_30d
- open_tickets
- critical_tickets
- sla_compliance_rate
- mrr
- payment failure indicator

Training:
- 80/20 train-validation split

Evaluation:
- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC

Risk thresholds:
- High   >= 0.70
- Medium 0.40 - 0.69
- Low    < 0.40

Limitation:
The current dataset does not contain a true future cancellation label,
so the prototype uses the current health state as a proxy label.
A production implementation should train against future cancellation/
renewal outcomes.
"""

import os
import sys

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from warehouse.db_manager import execute_query


MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "ml",
    "models"
)

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

CHURN_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "churn_model.joblib"
)


class ChurnModel:

    def __init__(self):

        self.model = RandomForestClassifier(
            n_estimators=150,
            max_depth=6,
            random_state=42,
            class_weight="balanced"
        )

        self.feature_names = [
            "events_last_30d",
            "active_users_30d",
            "open_tickets",
            "critical_tickets",
            "sla_compliance_rate",
            "mrr",
            "is_payment_failed"
        ]

        self.metrics = {}

        self.thresholds = {
            "high": 0.70,
            "medium": 0.40
        }

    # ============================================================
    # FEATURE EXTRACTION
    # ============================================================

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

                CASE
                    WHEN payment_status != 'Good Standing'
                    THEN 1
                    ELSE 0
                END AS is_payment_failed,

                CASE
                    WHEN health_tier = 'Critical'
                    THEN 1
                    ELSE 0
                END AS churn_label

            FROM mrt_customer_health
        """

        rows = execute_query(query)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        return df

    # ============================================================
    # TRAIN MODEL
    # ============================================================

    def train(self):

        df = self.extract_features()

        if df.empty:

            print(
                "[ChurnModel] No training data available."
            )

            return

        if len(df) < 10:

            print(
                "[ChurnModel] Insufficient data to train."
            )

            return

        X = df[self.feature_names].copy()

        y = df["churn_label"].astype(int)

        # Handle missing values
        X = X.fillna(0)

        # Check class distribution
        if y.nunique() < 2:

            print(
                "[ChurnModel] Training data contains only "
                "one class. Model training skipped."
            )

            return

        # --------------------------------------------------------
        # 80/20 split
        # --------------------------------------------------------

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y
        )

        # --------------------------------------------------------
        # Train
        # --------------------------------------------------------

        self.model.fit(
            X_train,
            y_train
        )

        # --------------------------------------------------------
        # Predictions
        # --------------------------------------------------------

        y_pred = self.model.predict(
            X_test
        )

        y_prob = self.model.predict_proba(
            X_test
        )[:, 1]

        # --------------------------------------------------------
        # Metrics
        # --------------------------------------------------------

        self.metrics = {
            "accuracy": round(
                float(
                    accuracy_score(
                        y_test,
                        y_pred
                    )
                ),
                4
            ),

            "precision": round(
                float(
                    precision_score(
                        y_test,
                        y_pred,
                        zero_division=0
                    )
                ),
                4
            ),

            "recall": round(
                float(
                    recall_score(
                        y_test,
                        y_pred,
                        zero_division=0
                    )
                ),
                4
            ),

            "f1_score": round(
                float(
                    f1_score(
                        y_test,
                        y_pred,
                        zero_division=0
                    )
                ),
                4
            ),

            "roc_auc": round(
                float(
                    roc_auc_score(
                        y_test,
                        y_prob
                    )
                ),
                4
            )
        }

        # --------------------------------------------------------
        # Feature importance
        # --------------------------------------------------------

        self.metrics["feature_importances"] = {
            feature: round(
                float(importance),
                4
            )

            for feature, importance

            in zip(
                self.feature_names,
                self.model.feature_importances_
            )
        }

        # --------------------------------------------------------
        # Save model
        # --------------------------------------------------------

        joblib.dump(
            {
                "model": self.model,
                "features": self.feature_names,
                "metrics": self.metrics,
                "thresholds": self.thresholds
            },
            CHURN_MODEL_PATH
        )

        print(
            "[ChurnModel] Training completed."
        )

        print(
            f"[ChurnModel] Metrics: {self.metrics}"
        )

        print(
            f"[ChurnModel] Model saved to: "
            f"{CHURN_MODEL_PATH}"
        )

    # ============================================================
    # RISK PREDICTION
    # ============================================================

    def predict_risk(
        self,
        account_record: dict
    ) -> dict:

        features = [

            account_record.get(
                "events_last_30d",
                0
            ),

            account_record.get(
                "active_users_30d",
                0
            ),

            account_record.get(
                "open_tickets",
                0
            ),

            account_record.get(
                "critical_tickets",
                0
            ),

            account_record.get(
                "sla_compliance_rate",
                100.0
            ),

            account_record.get(
                "mrr",
                0.0
            ),

            1 if account_record.get(
                "payment_status"
            ) != "Good Standing" else 0
        ]

        X = pd.DataFrame(
            [features],
            columns=self.feature_names
        )

        # --------------------------------------------------------
        # Make sure model has been trained
        # --------------------------------------------------------

        if not hasattr(
            self.model,
            "classes_"
        ):

            return {
                "churn_probability": None,
                "risk_tier": "Unknown",
                "recommended_action":
                    "Train churn model first"
            }

        probability = float(
            self.model.predict_proba(X)[0][1]
        )

        # --------------------------------------------------------
        # Threshold selection
        # --------------------------------------------------------

        if probability >= 0.70:

            tier = "High"

            action = (
                "Schedule Executive Retention Review"
            )

        elif probability >= 0.40:

            tier = "Medium"

            action = (
                "Schedule Customer Success Check-in"
            )

        else:

            tier = "Low"

            action = (
                "Continue Monitoring"
            )

        return {
            "churn_probability": round(
                probability,
                3
            ),

            "risk_tier": tier,

            "recommended_action": action
        }


# ================================================================
# SERVICE
# ================================================================

churn_service = ChurnModel()


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":

    print(
        "========== Churn Risk Model =========="
    )

    churn_service.train()