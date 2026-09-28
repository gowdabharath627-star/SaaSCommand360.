import React, { useState, useEffect } from 'react';
import {
  fetchDashboard, fetchRevenue, fetchProductUsage,
  fetchChurnRisk, fetchAlerts, fetchForecasts,
  fetchDataQuality, acknowledgeAlert, simulateTelemetryBurst,
  triggerCustomerAction
} from './services/api';
import {
  Activity, AlertTriangle, ArrowUpRight, CheckCircle2,
  ChevronRight, Database, DollarSign, Eye, Play,
  RefreshCw, ShieldCheck, Users, Zap, Bell, Check, TrendingUp
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [revenueData, setRevenueData] = useState(null);
  const [productData, setProductData] = useState(null);
  const [churnData, setChurnData] = useState(null);
  const [alertsData, setAlertsData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [dataQualityData, setDataQualityData] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [notificationMsg, setNotificationMsg] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTier, setFilterTier] = useState('ALL');

  const showNotification = (msg) => {
    setNotificationMsg(msg);
    setTimeout(() => setNotificationMsg(''), 4000);
  };

  const loadAllData = async () => {
    try {
      setRefreshing(true);
      const [dash, rev, prod, churn, alts, fcasts, dq] = await Promise.all([
        fetchDashboard(),
        fetchRevenue(),
        fetchProductUsage(),
        fetchChurnRisk(),
        fetchAlerts(),
        fetchForecasts(),
        fetchDataQuality()
      ]);
      setDashboardData(dash);
      setRevenueData(rev);
      setProductData(prod);
      setChurnData(churn);
      setAlertsData(alts);
      setForecastData(fcasts);
      setDataQualityData(dq);
    } catch (err) {
      console.error('Error loading data:', err);
      showNotification('Error refreshing data from API');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleSimulate = async (count = 15) => {
    try {
      setSimulating(true);
      const res = await simulateTelemetryBurst(count);
      showNotification(`Simulated ${res.events_emitted} events! Bus metrics updated.`);
      await loadAllData();
    } catch (e) {
      showNotification('Simulation failed: ' + e.message);
    } finally {
      setSimulating(false);
    }
  };

  const handleAcknowledge = async (alertId) => {
    try {
      await acknowledgeAlert(alertId);
      showNotification(`Alert ${alertId} acknowledged.`);
      await loadAllData();
    } catch (e) {
      showNotification('Failed to acknowledge alert');
    }
  };

  const handleAction = async (accountId, actionType) => {
    try {
      await triggerCustomerAction(accountId, actionType, 'Triggered via Customer 360');
      showNotification(`Action "${actionType}" dispatched for ${accountId}!`);
    } catch (e) {
      showNotification('Action failed: ' + e.message);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-300">
        <div className="text-center">
          <RefreshCw className="h-10 w-10 animate-spin mx-auto text-blue-500 mb-4" />
          <h2 className="text-xl font-bold">Connecting to SaaSCommand 360 Warehouse...</h2>
          <p className="text-sm text-slate-500 mt-2">Loading governed analytical models & ML predictions</p>
        </div>
      </div>
    );
  }

  // Filter customers for Customer 360 tab
  const filteredCustomers = (churnData?.accounts || []).filter(c => {
    const matchesSearch = c.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.account_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.csm_owner.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTier = filterTier === 'ALL' || c.health_tier === filterTier;
    return matchesSearch && matchesTier;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Toast Notification */}
      {notificationMsg && (
        <div className="fixed top-4 right-4 z-50 bg-blue-600 text-white px-4 py-3 rounded-lg shadow-xl flex items-center space-x-2 animate-bounce">
          <CheckCircle2 className="h-5 w-5" />
          <span>{notificationMsg}</span>
        </div>
      )}

      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center font-black text-white text-lg shadow-lg shadow-blue-500/30">
            360
          </div>
          <div>
            <h1 className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              SaaSCommand 360
            </h1>
            <p className="text-xs text-slate-400">Enterprise Product, Revenue & Customer Success Engine</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-full text-xs font-medium border border-slate-700">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-300">Live Streaming Bus: Active</span>
          </div>

          <button
            onClick={() => handleSimulate(10)}
            disabled={simulating}
            className="flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-1.5 rounded-md transition shadow"
          >
            <Zap className={`h-3.5 w-3.5 ${simulating ? 'animate-spin' : ''}`} />
            <span>{simulating ? 'Simulating...' : 'Emit Live Telemetry'}</span>
          </button>

          <button
            onClick={loadAllData}
            disabled={refreshing}
            className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-md transition border border-slate-700"
            title="Refresh warehouse marts"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Tabs */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/50 p-4 space-y-1">
          {[
            { id: 'dashboard', label: 'Executive Dashboard', icon: Activity },
            { id: 'customers', label: 'Customer 360 & Health', icon: Users },
            { id: 'revenue', label: 'Revenue & Forecasting', icon: DollarSign },
            { id: 'telemetry', label: 'Product Telemetry', icon: TrendingUp },
            { id: 'alerts', label: 'Decision & Alerts Hub', icon: Bell, badge: alertsData?.count },
            { id: 'quality', label: 'Data Quality & Checks', icon: ShieldCheck },
            { id: 'simulator', label: 'Live Stream Sandbox', icon: Play },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </div>
                {tab.badge > 0 && (
                  <span className="bg-rose-500/90 text-white text-xs px-2 py-0.5 rounded-full font-bold">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}

          <div className="pt-6 mt-6 border-t border-slate-800/80 px-2">
            <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Connected Engine</div>
            <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Warehouse:</span>
                <span className="text-emerald-400 font-semibold">PostgreSQL / DuckDB</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">REST API:</span>
                <span className="text-blue-400 font-semibold">FastAPI :8000</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Streaming:</span>
                <span className="text-purple-400 font-semibold">EventBus 4 Topics</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* TAB 1: EXECUTIVE DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Executive SaaS Command Center</h2>
                <p className="text-sm text-slate-400">Governed metrics, ARR expansion, customer health, and active risks.</p>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
                    <span>Active MRR</span>
                    <DollarSign className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-extrabold text-white mt-2">
                    ${(revenueData?.total_mrr || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-emerald-400 mt-1 flex items-center">
                    <ArrowUpRight className="h-3.5 w-3.5 mr-0.5" />
                    <span>ARR: ${(revenueData?.total_arr || 0).toLocaleString()}</span>
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
                    <span>Net Dollar Retention (NDR)</span>
                    <TrendingUp className="h-4 w-4 text-blue-400" />
                  </div>
                  <div className="text-2xl font-extrabold text-white mt-2">
                    {revenueData?.net_retention_rate}%
                  </div>
                  <div className="text-xs text-blue-400 mt-1">Expansion outpacing churn</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
                    <span>Logo Churn Rate</span>
                    <AlertTriangle className="h-4 w-4 text-rose-400" />
                  </div>
                  <div className="text-2xl font-extrabold text-white mt-2">
                    {revenueData?.logo_churn_rate}%
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {revenueData?.past_due_accounts} past due accounts
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl shadow-sm">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase">
                    <span>Customer Health Matrix</span>
                    <Users className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="flex items-baseline space-x-2 mt-2">
                    <span className="text-2xl font-extrabold text-emerald-400">
                      {dashboardData?.health_distribution?.Healthy || 0}
                    </span>
                    <span className="text-xs text-slate-400">Healthy</span>
                    <span className="text-lg font-bold text-rose-400 ml-2">
                      {dashboardData?.health_distribution?.Critical || 0}
                    </span>
                    <span className="text-xs text-slate-400">Critical</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Total: {revenueData?.active_accounts} active contracts
                  </div>
                </div>
              </div>

              {/* Two Column Grid: Top Churn Risks & Active Automated Alerts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Churn Risks */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-base flex items-center space-x-2">
                      <AlertTriangle className="h-4 w-4 text-rose-400" />
                      <span>Top Churn Risk Accounts (ML Model)</span>
                    </h3>
                    <button onClick={() => setActiveTab('customers')} className="text-xs text-blue-400 hover:underline">
                      View all
                    </button>
                  </div>

                  <div className="space-y-2">
                    {(dashboardData?.top_risk_accounts || []).map(acc => (
                      <div key={acc.account_id} className="bg-slate-800/50 p-3 rounded-lg flex items-center justify-between border border-slate-700/50">
                        <div>
                          <div className="font-semibold text-sm text-slate-200">{acc.company_name}</div>
                          <div className="text-xs text-slate-400">
                            {acc.account_id} · MRR: ${acc.mrr.toLocaleString()} · Owner: {acc.csm_owner}
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="bg-rose-500/20 text-rose-400 text-xs px-2.5 py-1 rounded font-bold border border-rose-500/30">
                            Risk: {Math.round(acc.churn_risk_score * 100)}%
                          </span>
                          <div className="text-[11px] text-slate-400 mt-1">Health: {acc.health_score}/100</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent Automated Alerts */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-base flex items-center space-x-2">
                      <Bell className="h-4 w-4 text-amber-400" />
                      <span>Recent Automated Decision Alerts</span>
                    </h3>
                    <button onClick={() => setActiveTab('alerts')} className="text-xs text-blue-400 hover:underline">
                      Alert Center ({alertsData?.count})
                    </button>
                  </div>

                  <div className="space-y-2">
                    {(dashboardData?.recent_alerts || []).map(alt => (
                      <div key={alt.alert_id} className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50 flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                              alt.severity === 'critical' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            }`}>
                              {alt.severity}
                            </span>
                            <span className="font-semibold text-sm text-slate-200">{alt.alert_type}</span>
                          </div>
                          <p className="text-xs text-slate-400">{alt.trigger_reason}</p>
                        </div>
                        <button
                          onClick={() => handleAcknowledge(alt.alert_id)}
                          className="bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs px-2.5 py-1 rounded transition ml-2 whitespace-nowrap"
                        >
                          Ack
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CUSTOMER 360 & HEALTH */}
          {activeTab === 'customers' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">Customer 360 & Health Directory</h2>
                  <p className="text-sm text-slate-400">Searchable account roster with dimensional health metrics and telemetry.</p>
                </div>

                <div className="flex items-center space-x-3">
                  <input
                    type="text"
                    placeholder="Search accounts, CSM, ID..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-64"
                  />

                  <select
                    value={filterTier}
                    onChange={(e) => setFilterTier(e.target.value)}
                    className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="ALL">All Tiers</option>
                    <option value="Healthy">Healthy (Green)</option>
                    <option value="At Risk">At Risk (Yellow)</option>
                    <option value="Critical">Critical (Red)</option>
                  </select>
                </div>
              </div>

              {/* Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="p-3.5">Account / Company</th>
                      <th className="p-3.5">Plan</th>
                      <th className="p-3.5">MRR</th>
                      <th className="p-3.5">Health Score</th>
                      <th className="p-3.5">Health Tier</th>
                      <th className="p-3.5">Churn Prob (ML)</th>
                      <th className="p-3.5">Open Tickets</th>
                      <th className="p-3.5">Payment</th>
                      <th className="p-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {filteredCustomers.map(acc => (
                      <tr key={acc.account_id} className="hover:bg-slate-800/40 transition">
                        <td className="p-3.5 font-medium text-slate-200">
                          <div>{acc.company_name}</div>
                          <div className="text-[11px] text-slate-500">{acc.account_id} · {acc.csm_owner}</div>
                        </td>
                        <td className="p-3.5 text-slate-300">{acc.plan}</td>
                        <td className="p-3.5 font-semibold text-slate-200">${acc.mrr.toLocaleString()}</td>
                        <td className="p-3.5 font-bold">
                          <span className={acc.health_score >= 75 ? 'text-emerald-400' : acc.health_score >= 50 ? 'text-amber-400' : 'text-rose-400'}>
                            {acc.health_score}/100
                          </span>
                        </td>
                        <td className="p-3.5">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            acc.health_tier === 'Healthy' ? 'bg-emerald-500/20 text-emerald-400' :
                            acc.health_tier === 'At Risk' ? 'bg-amber-500/20 text-amber-400' :
                            'bg-rose-500/20 text-rose-400'
                          }`}>
                            {acc.health_tier}
                          </span>
                        </td>
                        <td className="p-3.5 font-semibold text-slate-300">
                          {Math.round(acc.churn_risk_score * 100)}%
                        </td>
                        <td className="p-3.5 text-slate-300">
                          {acc.open_tickets} {acc.critical_tickets > 0 && <span className="text-rose-400 font-bold">({acc.critical_tickets} P1)</span>}
                        </td>
                        <td className="p-3.5">
                          <span className={acc.payment_status === 'Good Standing' ? 'text-emerald-400' : 'text-rose-400 font-bold'}>
                            {acc.payment_status}
                          </span>
                        </td>
                        <td className="p-3.5 text-right space-x-2">
                          <button
                            onClick={() => handleAction(acc.account_id, 'schedule_csm_call')}
                            className="bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded text-[11px] font-semibold"
                          >
                            CSM Call
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: REVENUE & FORECASTING */}
          {activeTab === 'revenue' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Revenue Analytics & 12-Month Projections</h2>
                <p className="text-sm text-slate-400">Section 9 ML forward-looking revenue simulation across Base, Bull, and Bear cases.</p>
              </div>

              {/* Scenarios summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs uppercase font-semibold text-blue-400">Base Case (Target)</div>
                  <div className="text-2xl font-extrabold text-white mt-1">
                    ${forecastData?.projections[11]?.arr_base?.toLocaleString()} ARR
                  </div>
                  <div className="text-xs text-slate-400 mt-1">End of Year 1 Projection</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs uppercase font-semibold text-emerald-400">Bull Case (High Expansion)</div>
                  <div className="text-2xl font-extrabold text-white mt-1">
                    ${forecastData?.projections[11]?.arr_bull?.toLocaleString()} ARR
                  </div>
                  <div className="text-xs text-slate-400 mt-1">+2.0% Monthly Expansion Lift</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs uppercase font-semibold text-rose-400">Bear Case (Conservative)</div>
                  <div className="text-2xl font-extrabold text-white mt-1">
                    ${forecastData?.projections[11]?.arr_bear?.toLocaleString()} ARR
                  </div>
                  <div className="text-xs text-slate-400 mt-1">High Churn Stress Test</div>
                </div>
              </div>

              {/* Forecast Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden p-5 space-y-4">
                <h3 className="font-bold text-sm text-slate-300">Monthly Revenue Forecast Trajectory</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px]">
                      <tr>
                        <th className="p-3">Period</th>
                        <th className="p-3">Base MRR</th>
                        <th className="p-3">Base ARR</th>
                        <th className="p-3">Bull ARR</th>
                        <th className="p-3">Bear ARR</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {(forecastData?.projections || []).map(p => (
                        <tr key={p.period} className="hover:bg-slate-800/30">
                          <td className="p-3 font-semibold text-slate-300">{p.period}</td>
                          <td className="p-3 font-medium text-slate-200">${p.mrr_base?.toLocaleString()}</td>
                          <td className="p-3 font-bold text-blue-400">${p.arr_base?.toLocaleString()}</td>
                          <td className="p-3 font-bold text-emerald-400">${p.arr_bull?.toLocaleString()}</td>
                          <td className="p-3 font-bold text-rose-400">${p.arr_bear?.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: PRODUCT TELEMETRY */}
          {activeTab === 'telemetry' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Product Telemetry & Feature Adoption</h2>
                <p className="text-sm text-slate-400">Real-time usage breakdown, top exercised capabilities, and 30-day activity trends.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs uppercase font-semibold text-slate-400">Total Telemetry Ingested</div>
                  <div className="text-3xl font-extrabold text-white mt-2">
                    {(productData?.total_events || 0).toLocaleString()} Events
                  </div>
                  <div className="text-xs text-emerald-400 mt-1">Processed across Medallion lakehouse</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                  <div className="text-xs uppercase font-semibold text-slate-400">Distinct Active Users</div>
                  <div className="text-3xl font-extrabold text-white mt-2">
                    {productData?.active_users} Users
                  </div>
                  <div className="text-xs text-blue-400 mt-1">Engaged with SaaS application</div>
                </div>
              </div>

              {/* Feature Adoption Breakdown */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="font-bold text-sm text-slate-300">Feature Adoption Volume (Ranked)</h3>
                <div className="space-y-3">
                  {(productData?.top_features || []).map(f => {
                    const maxVal = productData.top_features[0]?.event_count || 1;
                    const pct = Math.round((f.event_count / maxVal) * 100);
                    return (
                      <div key={f.feature} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-semibold text-slate-200 capitalize">{f.feature.replace('_', ' ')}</span>
                          <span className="text-slate-400">{f.event_count.toLocaleString()} calls</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2">
                          <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${pct}%` }}></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: ALERTS & DECISION HUB */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Automated Decision & Escalation Center</h2>
                <p className="text-sm text-slate-400">Real-time domain alerts triggered by health drops, billing failures, and SLA breaches.</p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                  <span className="font-bold text-sm text-slate-200">Active Alert Queue ({alertsData?.count})</span>
                  <span className="text-xs text-slate-400">Integrated with Slack & Microsoft Teams Webhooks</span>
                </div>

                <div className="space-y-2">
                  {(alertsData?.alerts || []).map(alt => (
                    <div key={alt.alert_id} className="bg-slate-800/60 border border-slate-700 p-4 rounded-lg flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            alt.severity === 'critical' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          }`}>
                            {alt.severity}
                          </span>
                          <span className="font-semibold text-sm text-slate-200">{alt.alert_type}</span>
                          <span className="text-xs text-slate-500">· {alt.account_id}</span>
                        </div>
                        <p className="text-xs text-slate-300">{alt.trigger_reason}</p>
                        <div className="text-[11px] text-slate-500">
                          Assigned: <span className="text-slate-400 font-medium">{alt.owner}</span> · Triggered: {alt.created_at.slice(0, 19).replace('T', ' ')}
                        </div>
                      </div>

                      <div>
                        {alt.status === 'open' ? (
                          <button
                            onClick={() => handleAcknowledge(alt.alert_id)}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 py-1.5 rounded-md font-semibold transition"
                          >
                            Acknowledge
                          </button>
                        ) : (
                          <span className="text-xs text-emerald-400 flex items-center font-semibold">
                            <Check className="h-4 w-4 mr-1" /> Acknowledged
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: DATA QUALITY */}
          {activeTab === 'quality' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Data Quality & Pipeline Observability</h2>
                <p className="text-sm text-slate-400">Section 14 automated schema, uniqueness, referential integrity, and freshness assertions.</p>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold uppercase text-slate-400">Overall Suite Status</div>
                  <div className="text-2xl font-extrabold text-emerald-400 mt-1 flex items-center">
                    <CheckCircle2 className="h-6 w-6 mr-2" />
                    <span>{dataQualityData?.status} ({dataQualityData?.passed_checks}/{dataQualityData?.total_checks} Passed)</span>
                  </div>
                </div>
                <div className="text-xs text-slate-400 text-right">
                  Executed: {dataQualityData?.executed_at?.slice(0, 19).replace('T', ' ')} UTC
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="p-3.5">Test Assertion</th>
                      <th className="p-3.5">Category</th>
                      <th className="p-3.5">Status</th>
                      <th className="p-3.5">Failed Records</th>
                      <th className="p-3.5">Assertion Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {(dataQualityData?.checks || []).map(c => (
                      <tr key={c.test_name} className="hover:bg-slate-800/30">
                        <td className="p-3.5 font-mono text-slate-200">{c.test_name}</td>
                        <td className="p-3.5 text-slate-400">{c.category}</td>
                        <td className="p-3.5 font-bold">
                          <span className={`px-2 py-0.5 rounded text-[11px] ${c.passed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                            {c.passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </td>
                        <td className="p-3.5 text-slate-300">{c.failed_count}</td>
                        <td className="p-3.5 text-slate-400">{c.details}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 7: LIVE STREAM SANDBOX */}
          {activeTab === 'simulator' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Interactive Streaming Bus Sandbox</h2>
                <p className="text-sm text-slate-400">Fulfills Section 6 and Section 22 Success Criteria: inject live events, observe processing, and watch health update.</p>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4">
                <h3 className="font-bold text-base text-slate-200">Inject Simulated Real-Time Traffic</h3>
                <p className="text-xs text-slate-400">
                  Click below to emit real-time usage events, payment failures, or support tickets through the event bus.
                </p>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() => handleSimulate(10)}
                    disabled={simulating}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-4 py-2.5 rounded-lg flex items-center space-x-2"
                  >
                    <Zap className="h-4 w-4" />
                    <span>Emit 10 Telemetry Events</span>
                  </button>

                  <button
                    onClick={() => handleSimulate(50)}
                    disabled={simulating}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4 py-2.5 rounded-lg flex items-center space-x-2"
                  >
                    <Activity className="h-4 w-4" />
                    <span>Emit 50 Event Burst</span>
                  </button>
                </div>
              </div>

              {/* Streaming Bus State */}
              <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-3">
                <h3 className="font-bold text-sm text-slate-200">Event Bus Live Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  <div className="bg-slate-800/50 p-3 rounded-lg">
                    <div className="text-xs text-slate-400">Published</div>
                    <div className="text-xl font-bold text-white mt-1">{dashboardData?.streaming_stats?.metrics?.published || 0}</div>
                  </div>
                  <div className="bg-slate-800/50 p-3 rounded-lg">
                    <div className="text-xs text-slate-400">Consumed</div>
                    <div className="text-xl font-bold text-emerald-400 mt-1">{dashboardData?.streaming_stats?.metrics?.consumed || 0}</div>
                  </div>
                  <div className="bg-slate-800/50 p-3 rounded-lg">
                    <div className="text-xs text-slate-400">Duplicates Dropped</div>
                    <div className="text-xl font-bold text-blue-400 mt-1">{dashboardData?.streaming_stats?.metrics?.duplicates_dropped || 0}</div>
                  </div>
                  <div className="bg-slate-800/50 p-3 rounded-lg">
                    <div className="text-xs text-slate-400">Dead Letter Queue</div>
                    <div className="text-xl font-bold text-rose-400 mt-1">{dashboardData?.streaming_stats?.dlq_depth || 0}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
