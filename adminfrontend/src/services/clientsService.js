/**
 * Clients & Sales API service
 * All endpoints require Admin JWT (injected by api.js interceptor).
 */
import api from './api';

export const clientsService = {
  // ---- Clients CRUD -------------------------------------------------------
  getClients: (params = {}) => api.get('/api/v1/clients/', { params }),
  getClient: (id) => api.get(`/api/v1/clients/${id}/`),
  createClient: (data) => api.post('/api/v1/clients/', data),
  updateClient: (id, data) => api.patch(`/api/v1/clients/${id}/`, data),

  // ---- Client sub-resources -----------------------------------------------
  getClientHistory: (id) => api.get(`/api/v1/clients/${id}/history/`),
  getClientInvoices: (id) => api.get(`/api/v1/clients/${id}/invoices/`),
  getClientAssignments: (id) => api.get(`/api/v1/clients/${id}/assignments/`),

  // ---- Quote Requests ------------------------------------------------------
  getQuoteRequests: (params = {}) => api.get('/api/v1/quote-requests/', { params }),
  getQuoteRequest: (id) => api.get(`/api/v1/quote-requests/${id}/`),
  generateQuote: (id, data) =>
    api.post(`/api/v1/quote-requests/${id}/generate-quote/`, data),

  // ---- Quotes --------------------------------------------------------------
  getQuotes: (params = {}) => api.get('/api/v1/quotes/', { params }),
  sendQuote: (id) => api.post(`/api/v1/quotes/${id}/send/`),

  // ---- Public Requests -----------------------------------------------------
  getPublicRequests: (params = {}) => api.get('/api/v1/public-quotes/', { params }),
  processPublicRequest: (id, adminNotes = '') =>
    api.post(`/api/v1/public-quotes/${id}/process/`, { admin_notes: adminNotes }),
};

export default clientsService;
