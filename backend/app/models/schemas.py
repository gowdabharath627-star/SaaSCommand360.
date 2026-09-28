"""
SaaSCommand 360 - Pydantic Request & Response Schemas
Conforms to Section 12 API requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    account_id: str
    company_name: str
    industry: str
    plan: str
    mrr: float
    csm_owner: str
    health_score: float
    health_tier: str
    events_last_30d: int
    active_users_30d: int
    open_tickets: int
    critical_tickets: int
    sla_compliance_rate: float
    payment_status: str
    churn_risk_score: float
    expansion_score: float
    anomaly_detected: bool
    last_updated_at: str

class RevenueSummaryResponse(BaseModel):
    total_mrr: float
    total_arr: float
    paid_invoices_amount: float
    unpaid_invoices_amount: float
    active_accounts: int
    past_due_accounts: int
    net_retention_rate: float
    logo_churn_rate: float
    revenue_churn_rate: float
    expansion_rate: float
    calculated_at: str

class ProductUsageResponse(BaseModel):
    total_events: int
    active_users: int
    top_features: List[Dict[str, Any]]
    daily_usage_trends: List[Dict[str, Any]]

class ChurnRiskResponse(BaseModel):
    high_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    accounts: List[Dict[str, Any]]

class CustomerActionRequest(BaseModel):
    account_id: str
    action_type: str = Field(..., json_schema_extra={"example": "schedule_csm_call"}) # schedule_csm_call, send_dunning_email, trigger_upsell
    notes: Optional[str] = "Initiated by CSM via Command Center"
    assigned_to: Optional[str] = "CSM Agent"

class CustomerActionResponse(BaseModel):
    action_id: str
    account_id: str
    action_type: str
    status: str
    assigned_to: str
    timestamp: str

class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: Optional[str] = "Admin / CSM Agent"
    notes: Optional[str] = "Issue under active review"
