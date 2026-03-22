/**
 * Hiring / Onboarding API service
 * All endpoints require Admin JWT (injected by api.js interceptor).
 */
import api from './api';

export const hiringService = {
  // ---- List / Detail -------------------------------------------------------
  getInvitations: (params = {}) => api.get('/api/v1/onboarding/', { params }),
  getInvitation: (id) => api.get(`/api/v1/onboarding/${id}/`),

  // ---- Create --------------------------------------------------------------
  createInvitation: (data) => api.post('/api/v1/onboarding/', data),

  // ---- Lifecycle -----------------------------------------------------------
  resend: (id) => api.post(`/api/v1/onboarding/${id}/resend/`),
  void: (id, reason = '') => api.post(`/api/v1/onboarding/${id}/void/`, { reason }),
  advance: (id) => api.post(`/api/v1/onboarding/${id}/advance/`),
  extend: (id, days = 14) => api.post(`/api/v1/onboarding/${id}/extend/`, { days }),

  // ---- Pipeline (Kanban grouped by phase) ----------------------------------
  getPipeline: () => api.get('/api/v1/onboarding/pipeline/'),
};

export default hiringService;
