/**
 * SaaSCommand 360 - Frontend API Client
 * Interfaces directly with FastAPI endpoints (Section 12).
 */

const API_BASE = '/api';

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error('Failed to load dashboard metrics');
  return res.json();
}

export async function fetchRevenue() {
  const res = await fetch(`${API_BASE}/revenue`);
  if (!res.ok) throw new Error('Failed to load revenue metrics');
  return res.json();
}

export async function fetchProductUsage() {
  const res = await fetch(`${API_BASE}/product/usage`);
  if (!res.ok) throw new Error('Failed to load product analytics');
  return res.json();
}

export async function fetchChurnRisk() {
  const res = await fetch(`${API_BASE}/churn-risk`);
  if (!res.ok) throw new Error('Failed to load churn risk model');
  return res.json();
}

export async function fetchAlerts() {
  const res = await fetch(`${API_BASE}/alerts`);
  if (!res.ok) throw new Error('Failed to load active alerts');
  return res.json();
}

export async function fetchForecasts() {
  const res = await fetch(`${API_BASE}/forecasts?months=12`);
  if (!res.ok) throw new Error('Failed to load revenue forecasts');
  return res.json();
}

export async function fetchDataQuality() {
  const res = await fetch(`${API_BASE}/data-quality`);
  if (!res.ok) throw new Error('Failed to load data quality checks');
  return res.json();
}

export async function acknowledgeAlert(alertId) {
  const res = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return res.json();
}

export async function simulateTelemetryBurst(count = 10) {
  const res = await fetch(`${API_BASE}/events/simulate?count=${count}`, {
    method: 'POST'
  });
  return res.json();
}

export async function triggerCustomerAction(accountId, actionType, notes) {
  const res = await fetch(`${API_BASE}/customer-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      account_id: accountId,
      action_type: actionType,
      notes: notes
    })
  });
  return res.json();
}
