"""
SaaSCommand 360 - Realistic Synthetic Data Generator
Conforms to Section 4 of the assignment brief:
- Accounts: account_id, industry, size, region, owner, created_at
- Users: user_id, account_id, role, created_at
- Product Events: event_id, user_id, account_id, feature, timestamp
- Subscriptions: subscription_id, account_id, plan, start_date, status, mrr
- Invoices: invoice_id, account_id, amount, due_date, status, paid_at
- Support: ticket_id, account_id, severity, created_at, resolved_at, status
"""

import os
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.join(DATA_DIR, "bronze")
os.makedirs(BRONZE_DIR, exist_ok=True)

INDUSTRIES = ["Fintech", "Healthtech", "DevTools", "E-commerce", "Logistics", "CyberSecurity", "EdTech"]
SIZES = ["1-50", "51-200", "201-1000", "1000+"]
REGIONS = ["North America", "EMEA", "APAC", "LATAM"]
CSM_OWNERS = ["Sarah Jenkins", "Michael Chang", "Amara Okafor", "Elena Rostova", "David Kim"]
ROLES = ["admin", "developer", "data_analyst", "product_manager", "viewer"]
FEATURES = [
    "dashboard_view", "query_execution", "report_export", 
    "pipeline_run", "api_call", "alert_configuration", 
    "user_invite", "integration_sync"
]
PLANS = {
    "Starter": {"mrr": 299.0, "seat_limit": 5, "event_quota": 50000},
    "Professional": {"mrr": 999.0, "seat_limit": 25, "event_quota": 250000},
    "Enterprise": {"mrr": 3499.0, "seat_limit": 100, "event_quota": 1000000},
    "Enterprise Plus": {"mrr": 7499.0, "seat_limit": 500, "event_quota": 5000000},
}

COMPANY_NAMES = [
    "Acme Analytics", "Bolt Logistics", "CloudScale Networks", "DataPulse AI", "Echo FinTech",
    "Forge Health", "GridFlow Energy", "Helix Genomics", "InfraShield Cyber", "JumpStart SaaS",
    "Kite Commerce", "Loom Video Labs", "MetricStream Systems", "Nexus Cloud", "OmniChannel Retail",
    "Peak Dynamics", "Quantum Ledger", "RapidDeploy Inc", "SwiftPay Solutions", "Terra Robotics",
    "Union Media Group", "Vortex Security", "Waveform Audio", "XenoBio Labs", "YieldPoint Capital",
    "Zenith Workforce", "Apex Global", "Beacon AI", "Catalyst Bio", "Delta Payments",
    "Epoch Software", "Frontier Data", "Gravitas Finance", "Hyperion Dev", "Ion Space",
    "Javelin Logistics", "Kronos Security", "Luminary Media", "Matrix Systems", "Nova Health",
    "Optima Retail", "Pinnacle Cloud", "Quasar Tech", "Resilience Cyber", "Stratum IoT",
    "Titan Freight", "Ubiquity AI", "Veritas LegalTech", "Waypoint Travel", "Xcelerate Labs"
]

def generate_dataset(num_accounts=50, days_history=90):
    random.seed(42)
    now = datetime.now(timezone.utc)
    base_date = now - timedelta(days=days_history)

    accounts = []
    users = []
    subscriptions = []
    invoices = []
    support_tickets = []
    product_events = []

    # Assign accounts into cohorts:
    # 0: Healthy Champion (~60%)
    # 1: Churn Risk (~15%)
    # 2: Expansion Ready (~15%)
    # 3: Underutilized / Contraction Risk (~10%)
    
    for i in range(num_accounts):
        account_id = f"acc_{i+1:03d}"
        company_name = COMPANY_NAMES[i % len(COMPANY_NAMES)] + (f" {i//len(COMPANY_NAMES)+1}" if i >= len(COMPANY_NAMES) else "")
        created_days_ago = random.randint(30, days_history + 180)
        account_created_at = (now - timedelta(days=created_days_ago)).isoformat()
        
        cohort_roll = random.random()
        if cohort_roll < 0.60:
            cohort = "healthy"
        elif cohort_roll < 0.75:
            cohort = "churn_risk"
        elif cohort_roll < 0.90:
            cohort = "expansion_ready"
        else:
            cohort = "underutilized"

        industry = random.choice(INDUSTRIES)
        size = random.choice(SIZES)
        region = random.choice(REGIONS)
        owner = random.choice(CSM_OWNERS)

        accounts.append({
            "account_id": account_id,
            "company_name": company_name,
            "industry": industry,
            "size": size,
            "region": region,
            "owner": owner,
            "created_at": account_created_at,
            "cohort": cohort
        })

        # Plan selection
        if cohort == "expansion_ready":
            plan_name = random.choice(["Starter", "Professional"])
        elif cohort == "underutilized":
            plan_name = random.choice(["Enterprise", "Enterprise Plus"])
        else:
            plan_name = random.choice(list(PLANS.keys()))

        plan_info = PLANS[plan_name]
        sub_status = "active" if cohort != "churn_risk" or random.random() > 0.4 else "past_due"
        sub_id = f"sub_{account_id}"

        subscriptions.append({
            "subscription_id": sub_id,
            "account_id": account_id,
            "plan": plan_name,
            "start_date": account_created_at,
            "status": sub_status,
            "mrr": plan_info["mrr"]
        })

        # Users
        user_count = random.randint(3, min(12, plan_info["seat_limit"]))
        acc_users = []
        for u_idx in range(user_count):
            user_id = f"usr_{account_id}_{u_idx+1:02d}"
            role = "admin" if u_idx == 0 else random.choice(ROLES)
            u_created = (datetime.fromisoformat(account_created_at) + timedelta(days=random.randint(0, 10))).isoformat()
            user_record = {
                "user_id": user_id,
                "account_id": account_id,
                "email": f"user{u_idx+1}@{company_name.lower().replace(' ', '')}.com",
                "role": role,
                "created_at": u_created
            }
            users.append(user_record)
            acc_users.append(user_id)

        # Invoices (Past 3 months)
        for m in range(3):
            inv_date = now - timedelta(days=30 * (2 - m) + random.randint(0, 5))
            inv_id = f"inv_{account_id}_{m+1}"
            amount = plan_info["mrr"]
            
            if m == 2 and cohort == "churn_risk" and random.random() > 0.3:
                status = "failed"
                paid_at = None
            elif m == 2 and random.random() > 0.8:
                status = "open"
                paid_at = None
            else:
                status = "paid"
                paid_at = (inv_date + timedelta(days=random.randint(1, 5))).isoformat()

            invoices.append({
                "invoice_id": inv_id,
                "account_id": account_id,
                "amount": amount,
                "due_date": (inv_date + timedelta(days=15)).isoformat(),
                "status": status,
                "paid_at": paid_at
            })

        # Support Tickets
        ticket_count = random.randint(1, 4)
        if cohort == "churn_risk":
            ticket_count += random.randint(3, 7)
        
        for t_idx in range(ticket_count):
            t_id = f"tkt_{account_id}_{t_idx+1}"
            days_ago = random.randint(1, days_history)
            t_created = now - timedelta(days=days_ago, hours=random.randint(1, 23))
            
            if cohort == "churn_risk":
                severity = random.choice(["high", "critical", "medium"])
                is_resolved = random.random() > 0.6
            else:
                severity = random.choice(["low", "medium", "high"])
                is_resolved = random.random() > 0.15

            if is_resolved:
                res_hours = random.randint(2, 48) if severity != "critical" else random.randint(4, 72)
                t_resolved = (t_created + timedelta(hours=res_hours)).isoformat()
                t_status = "resolved"
            else:
                t_resolved = None
                t_status = "open"

            support_tickets.append({
                "ticket_id": t_id,
                "account_id": account_id,
                "severity": severity,
                "status": t_status,
                "created_at": t_created.isoformat(),
                "resolved_at": t_resolved
            })

        # Product Events (Generating realistic telemetry)
        for d in range(days_history):
            day_ts = base_date + timedelta(days=d)
            is_weekend = day_ts.weekday() >= 5
            
            if cohort == "healthy":
                base_daily = random.randint(15, 45)
            elif cohort == "expansion_ready":
                growth_factor = 1.0 + (d / days_history) * 1.8
                base_daily = int(random.randint(25, 60) * growth_factor)
            elif cohort == "churn_risk":
                decay_factor = max(0.05, 1.0 - (d / days_history) * 0.95)
                base_daily = int(random.randint(20, 50) * decay_factor)
            else: # underutilized
                base_daily = random.randint(2, 6)

            if is_weekend:
                base_daily = max(1, int(base_daily * 0.2))

            for _ in range(base_daily):
                evt_user = random.choice(acc_users)
                evt_feature = random.choice(FEATURES)
                evt_time = day_ts + timedelta(seconds=random.randint(0, 86399))
                
                if evt_time > now:
                    continue

                product_events.append({
                    "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                    "user_id": evt_user,
                    "account_id": account_id,
                    "feature": evt_feature,
                    "timestamp": evt_time.isoformat()
                })

    # Save to Bronze Data Lake
    datasets = {
        "accounts.json": accounts,
        "users.json": users,
        "subscriptions.json": subscriptions,
        "invoices.json": invoices,
        "support_tickets.json": support_tickets,
        "product_events.json": product_events
    }

    for filename, data in datasets.items():
        filepath = os.path.join(BRONZE_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    summary = {
        "accounts": len(accounts),
        "users": len(users),
        "subscriptions": len(subscriptions),
        "invoices": len(invoices),
        "support_tickets": len(support_tickets),
        "product_events": len(product_events),
        "bronze_path": BRONZE_DIR
    }
    return summary

if __name__ == "__main__":
    print("Generating enterprise SaaS telemetry and operational dataset...")
    res = generate_dataset()
    print(f"Data generation complete! Summary: {res}")
