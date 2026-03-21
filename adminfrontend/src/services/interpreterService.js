import api from './api';

export const interpreterService = {
  /**
   * Get paginated list of interpreters with optional filters
   * @param {Object} params - { page, search, state, language, is_blocked, is_on_mission, ordering }
   */
  getInterpreters: async (params = {}) => {
    const response = await api.get('/api/v1/interpreters/', { params });
    return response.data;
  },

  /**
   * Get single interpreter detailed profile including presigned URLs
   * @param {string|number} id 
   */
  getInterpreterById: async (id) => {
    const response = await api.get(`/api/v1/interpreters/${id}/`);
    return response.data;
  },

  /**
   * Block an interpreter manually
   * @param {string|number} id 
   * @param {string} reason 
   */
  blockInterpreter: async (id, reason) => {
    const response = await api.post(`/api/v1/interpreters/${id}/block/`, { reason });
    return response.data;
  },

  /**
   * Unblock an interpreter
   * @param {string|number} id 
   */
  unblockInterpreter: async (id) => {
    const response = await api.post(`/api/v1/interpreters/${id}/unblock/`);
    return response.data;
  },

  /**
   * Get performance metrics for an interpreter (acceptance rate, no show, etc)
   * @param {string|number} id 
   */
  getInterpreterPerformance: async (id) => {
    const response = await api.get(`/api/v1/interpreters/${id}/performance/`);
    return response.data;
  },

  /**
   * SECURE / ADMIN ONLY: Get unmasked banking details
   * @param {string|number} id 
   */
  getInterpreterBanking: async (id) => {
    const response = await api.get(`/api/v1/interpreters/${id}/banking/`);
    return response.data;
  },

  /**
   * Get recent 50 payments for an interpreter
   * @param {string|number} id 
   */
  getInterpreterPayments: async (id) => {
    const response = await api.get(`/api/v1/interpreters/${id}/payments/`);
    return response.data;
  },

  /**
   * Find available interpreters for a specific criteria (Mission Assignment Flow)
   * @param {Object} params - { date, language, state, city }
   */
  getAvailableInterpreters: async (params = {}) => {
    const response = await api.get('/api/v1/interpreters/available/', { params });
    return response.data;
  },

  /**
   * Send a password reset email to the interpreter
   * @param {string|number} id
   */
  sendPasswordReset: async (id) => {
    const response = await api.post(`/api/v1/interpreters/${id}/send-password-reset/`);
    return response.data;
  },

  /**
   * Send a direct email message to the interpreter (supports optional file attachment)
   * @param {string|number} id
   * @param {string} subject
   * @param {string} body
   * @param {File|null} attachment
   */
  sendMessage: async (id, subject, body, attachment = null) => {
    if (attachment) {
      const fd = new FormData();
      fd.append('subject', subject);
      fd.append('body', body);
      fd.append('attachment', attachment);
      const response = await api.post(`/api/v1/interpreters/${id}/send-message/`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    }
    const response = await api.post(`/api/v1/interpreters/${id}/send-message/`, { subject, body });
    return response.data;
  },

  /**
   * Update interpreter profile fields (PATCH — supports user fields too)
   * @param {string|number} id
   * @param {Object} data - partial interpreter + user fields
   */
  updateInterpreter: async (id, data) => {
    const response = await api.patch(`/api/v1/interpreters/${id}/`, data);
    return response.data;
  },

  /**
   * Execute a bulk action on multiple interpreters
   * @param {string} action - activate | deactivate | block | unblock | suspend | send_contract |
   *                          send_onboarding | send_reminder_1/2/3 | send_password_reset | send_message
   * @param {number[]} ids
   * @param {Object} options - { reason, subject, body, attachment }
   */
  bulkAction: async (action, ids, options = {}) => {
    const { reason, subject, body, attachment } = options;
    if (attachment) {
      const fd = new FormData();
      fd.append('action', action);
      ids.forEach(id => fd.append('ids', id));
      if (reason) fd.append('reason', reason);
      if (subject) fd.append('subject', subject);
      if (body) fd.append('body', body);
      fd.append('attachment', attachment);
      const response = await api.post('/api/v1/interpreters/bulk-action/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    }
    const response = await api.post('/api/v1/interpreters/bulk-action/', {
      action, ids, reason, subject, body,
    });
    return response.data;
  },

  /**
   * Get all active interpreters with address, radius and cities for map visualization
   */
  getMapData: async () => {
    const response = await api.get('/api/v1/interpreters/map/');
    return response.data;
  },
};
