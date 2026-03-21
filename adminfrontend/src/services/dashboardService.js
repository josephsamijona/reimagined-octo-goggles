/**
 * Dashboard API service
 * All endpoints require Admin authentication (JWT injected by api.js interceptor).
 */
import api from "./api";

export const dashboardService = {
  /** Real-time KPIs: active missions, revenue, rates, etc. */
  getKPIs: () => api.get("/api/v1/dashboard/kpis/"),

  /** Actionable alerts: unassigned, stalled, overdue, etc. */
  getAlerts: () => api.get("/api/v1/dashboard/alerts/"),

  /** Monthly revenue & expense data for the last 12 months. */
  getRevenueChart: () => api.get("/api/v1/dashboard/revenue-chart/"),

  /** Assignments scheduled for today. */
  getTodayMissions: () => api.get("/api/v1/dashboard/today-missions/"),

  /** Payroll KPIs: pending payments count/amount, MTD paid. */
  getPayrollKPIs: () => api.get("/api/v1/dashboard/payroll-kpis/"),

  /** Quote pipeline counts by status + 30-day conversion rate. */
  getQuotePipeline: () => api.get("/api/v1/dashboard/quote-pipeline-summary/"),
};

export default dashboardService;
