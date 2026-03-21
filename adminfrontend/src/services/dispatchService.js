/**
 * Dispatch / Assignment API service
 * All endpoints require Admin JWT (injected by api.js interceptor).
 */
import api from './api';

export const dispatchService = {
  // ---- List / CRUD --------------------------------------------------------
  getAssignments: (params = {}) => api.get('/api/v1/assignments/', { params }),
  getAssignment: (id) => api.get(`/api/v1/assignments/${id}/`),
  createAssignment: (data) => api.post('/api/v1/assignments/', data),
  updateAssignment: (id, data) => api.patch(`/api/v1/assignments/${id}/`, data),
  deleteAssignment: (id) => api.delete(`/api/v1/assignments/${id}/`),

  // ---- Lifecycle ----------------------------------------------------------
  confirmAssignment: (id) => api.post(`/api/v1/assignments/${id}/confirm/`),
  startAssignment: (id) => api.post(`/api/v1/assignments/${id}/start/`),
  cancelAssignment: (id) => api.post(`/api/v1/assignments/${id}/cancel/`),
  completeAssignment: (id) => api.post(`/api/v1/assignments/${id}/complete/`),
  noShowAssignment: (id) => api.post(`/api/v1/assignments/${id}/no-show/`),
  reassignInterpreter: (id, interpreterId) =>
    api.post(`/api/v1/assignments/${id}/reassign/`, { interpreter_id: interpreterId }),
  sendReminder: (id) => api.post(`/api/v1/assignments/${id}/send-reminder/`),
  duplicateAssignment: (id) => api.post(`/api/v1/assignments/${id}/duplicate/`),

  // ---- Notes --------------------------------------------------------------
  addNote: (id, text) => api.post(`/api/v1/assignments/${id}/add-note/`, { text }),

  // ---- Timeline -----------------------------------------------------------
  getTimeline: (id) => api.get(`/api/v1/assignments/${id}/timeline/`),

  // ---- Aggregate views ----------------------------------------------------
  getStats: (params = {}) => api.get('/api/v1/assignments/stats/', { params }),
  getCalendar: (start, end) =>
    api.get('/api/v1/assignments/calendar/', { params: { start, end } }),
  getKanban: (params = {}) => api.get('/api/v1/assignments/kanban/', { params }),

  // ---- Conflict check -----------------------------------------------------
  checkConflict: (interpreterId, startTime, endTime, excludeId = null) => {
    const params = { interpreter_id: interpreterId, start_time: startTime, end_time: endTime };
    if (excludeId) params.exclude_id = excludeId;
    return api.get('/api/v1/assignments/check-conflict/', { params });
  },

  // ---- Bulk actions -------------------------------------------------------
  bulkAction: (action, ids) =>
    api.post('/api/v1/assignments/bulk-action/', { action, ids }),

  // ---- Export CSV ---------------------------------------------------------
  exportCsv: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    const url = `/api/v1/assignments/export/${query ? `?${query}` : ''}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `assignments-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  },

  // ---- Available interpreters (for assignment) ----------------------------
  getAvailableInterpreters: (params = {}) =>
    api.get('/api/v1/interpreters/available/', { params }),

  // ---- Live locations (for map) -------------------------------------------
  getLiveLocations: () => api.get('/api/v1/interpreters/live_locations/'),

  // ---- Service types & languages for dropdowns ----------------------------
  getServiceTypes: () => api.get('/api/v1/service-types/'),
  getLanguages: (params = {}) => api.get('/api/v1/languages/', { params }),
  getClients: (params = {}) => api.get('/api/v1/clients/', { params }),

  // ---- Map: active interpreters with GPS coordinates ----------------------
  getInterpretersForMap: (params = {}) =>
    api.get('/api/v1/interpreters/', { params: { page_size: 200, active: true, ...params } }),
};

export default dispatchService;
