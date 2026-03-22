/**
 * Finance & Accounting API service
 * All endpoints require Admin JWT (injected by api.js interceptor).
 */
import api from './api';

export const financeService = {
  // ---- Summary ------------------------------------------------------------
  getSummary: () => api.get('/api/v1/finance/summary/'),

  // ---- Invoices -----------------------------------------------------------
  getInvoices: (params = {}) => api.get('/api/v1/finance/invoices/', { params }),
  getInvoice: (id) => api.get(`/api/v1/finance/invoices/${id}/`),
  createInvoice: (data) => api.post('/api/v1/finance/invoices/', data),
  sendInvoice: (id) => api.post(`/api/v1/finance/invoices/${id}/send/`),
  markInvoicePaid: (id, paymentMethod) =>
    api.post(`/api/v1/finance/invoices/${id}/mark-paid/`, { payment_method: paymentMethod }),
  remindInvoice: (id) => api.post(`/api/v1/finance/invoices/${id}/remind/`),

  // ---- Expenses -----------------------------------------------------------
  getExpenses: (params = {}) => api.get('/api/v1/finance/expenses/', { params }),
  createExpense: (data) => api.post('/api/v1/finance/expenses/', data),
  approveExpense: (id) => api.post(`/api/v1/finance/expenses/${id}/approve/`),
  payExpense: (id) => api.post(`/api/v1/finance/expenses/${id}/pay/`),

  // ---- Analytics ----------------------------------------------------------
  getRevenueByService: () => api.get('/api/v1/finance/analytics/revenue-by-service/'),
  getRevenueByClient: () => api.get('/api/v1/finance/analytics/revenue-by-client/'),
  getRevenueByLanguage: () => api.get('/api/v1/finance/analytics/revenue-by-language/'),
  getPnl: () => api.get('/api/v1/finance/analytics/pnl/'),
};

export default financeService;
