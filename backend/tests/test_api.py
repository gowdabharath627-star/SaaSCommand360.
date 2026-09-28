"""
SaaSCommand 360 - Automated Backend API Test Suite
Tests all core Section 12 endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root_health():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["documentation"] == "/docs"

def test_get_revenue():
    response = client.get("/api/revenue")
    assert response.status_code == 200
    data = response.json()
    assert "total_mrr" in data
    assert "total_arr" in data
    assert data["total_mrr"] > 0

def test_get_dashboard():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "revenue" in data
    assert "health_distribution" in data
    assert "top_risk_accounts" in data

def test_get_churn_risk():
    response = client.get("/api/churn-risk")
    assert response.status_code == 200
    data = response.json()
    assert "high_risk_count" in data
    assert "accounts" in data
    assert len(data["accounts"]) > 0

def test_get_forecasts():
    response = client.get("/api/forecasts?months=6")
    assert response.status_code == 200
    data = response.json()
    assert data["horizon_months"] == 6
    assert len(data["projections"]) == 6

def test_get_data_quality():
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["PASSED", "WARNING"]
    assert data["total_checks"] >= 5

def test_post_customer_action():
    payload = {
        "account_id": "acc_001",
        "action_type": "schedule_csm_call",
        "notes": "Initiated automated retention review",
        "assigned_to": "CSM Sarah"
    }
    response = client.post("/api/customer-action", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "acc_001"
    assert data["status"] == "SCHEDULED"
