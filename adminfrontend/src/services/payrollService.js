/**
 * Payroll API service
 * All endpoints require Admin authentication (JWT injected by api.js interceptor).
 */
import api from './api';

/** Trigger a browser file download from a blob response. */
const downloadBlob = (blobData, filename) => {
  const url = URL.createObjectURL(new Blob([blobData], { type: 'application/pdf' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

export const payrollService = {
  // ---- KPIs ----
  getKPIs: () => api.get('/api/v1/dashboard/payroll-kpis/'),

  // ---- Payments ----
  getPayments: (params = {}) => api.get('/api/v1/payroll/payments/', { params }),
  processPayment: (id) => api.post(`/api/v1/payroll/payments/${id}/process/`),
  completePayment: (id) => api.post(`/api/v1/payroll/payments/${id}/complete/`),

  // ---- Pay Stubs ----
  getStubs: (params = {}) => api.get('/api/v1/payroll/stubs/', { params }),
  createStub: (data) => api.post('/api/v1/payroll/stubs/', data),
  batchStubs: (data) => api.post('/api/v1/payroll/stubs/batch/', data),
  getStubDetail: (id) => api.get(`/api/v1/payroll/stubs/${id}/`),

  downloadStubPdf: async (id, interpreterName, docNumber) => {
    const response = await api.get(`/api/v1/payroll/stubs/${id}/pdf/`, { responseType: 'blob' });
    downloadBlob(response.data, `paystub-${docNumber || id}.pdf`);
  },

  sendStub: (id) => api.post(`/api/v1/payroll/stubs/${id}/send/`),

  // ---- Earnings Summary (Tax) ----
  /** params: { interpreter_id, year } or { interpreter_id, period_start, period_end } */
  getEarningsSummary: (params) => api.get('/api/v1/payroll/earnings-summary/', { params }),

  downloadEarningsSummaryPdf: async (params) => {
    const response = await api.get('/api/v1/payroll/earnings-summary-pdf/', {
      params,
      responseType: 'blob',
    });
    const name = `earnings-summary-${params.interpreter_id}-${params.year || 'custom'}.pdf`;
    downloadBlob(response.data, name);
  },

  sendEarningsSummary: (data) => api.post('/api/v1/payroll/earnings-summary-send/', data),

  // ---- Stub from selected payments (grouped by interpreter) ----
  stubsFromPayments: (data) => api.post('/api/v1/payroll/stubs/from-payments/', data),

  // ---- Manual stub for non-registered payees ----
  manualStub: (data) => api.post('/api/v1/payroll/stubs/manual/', data),
};

export default payrollService;
