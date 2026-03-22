/**
 * AI Agent service — wraps FastAPI agent endpoints (port 8001).
 * Separate from api.js (Django port 8000).
 */
import axios from 'axios';

const AGENT_BASE = import.meta.env.VITE_AGENT_URL || 'http://localhost:8001';

const agentApi = axios.create({ baseURL: AGENT_BASE });

// ── Gmail (FastAPI /gmail) ────────────────────────────────────────
export const gmailService = {
  authStatus: () => agentApi.get('/gmail/auth-status'),
  getInbox: (params = {}) => agentApi.get('/gmail/inbox', { params }),
  getMessage: (id) => agentApi.get(`/gmail/messages/${id}`),
  markRead: (gmailId, isRead = true) => agentApi.patch(`/gmail/messages/${gmailId}/read`, { is_read: isRead }),
  markProcessed: (gmailId) => agentApi.patch(`/gmail/messages/${gmailId}/processed`, { is_processed: true }),
  send: (to, subject, bodyHtml, replyToId = '') =>
    agentApi.post('/gmail/send', { to, subject, body_html: bodyHtml, reply_to_id: replyToId }),
  reply: (messageId, bodyHtml) => agentApi.post(`/gmail/reply/${messageId}`, { body_html: bodyHtml }),
  search: (q, maxResults = 10) => agentApi.get('/gmail/search', { params: { q, max_results: maxResults } }),
  sync: () => agentApi.get('/gmail/sync'),
};

// ── AI Agent (FastAPI /ai) ────────────────────────────────────────
export const agentService = {
  // Classification & Analysis
  classify: (data) => agentApi.post('/ai/classify', data),
  match: (data) => agentApi.post('/ai/match', data),
  estimate: (data) => agentApi.post('/ai/estimate', data),
  analyzeCV: (data) => agentApi.post('/ai/analyze-cv', data),
  suggest: (data) => agentApi.post('/ai/suggest', data),
  generateReply: (data) => agentApi.post('/ai/reply', data),

  // Chat
  chat: (message, sessionId = '') => agentApi.post('/ai/chat', { message, session_id: sessionId }),

  // Email processing pipeline
  processEmail: (data) => agentApi.post('/ai/process-email', data),
  processUnread: (limit = 10) => agentApi.post(`/ai/process-unread?limit=${limit}`),

  // Queue
  getQueue: (params = {}) => agentApi.get('/ai/queue', { params }),
  getQueueCount: () => agentApi.get('/ai/queue/count'),
  approveItem: (id) => agentApi.post(`/ai/queue/${id}/approve`),
  rejectItem: (id, reason = '') => agentApi.post(`/ai/queue/${id}/reject`, { reason }),

  // Audit log
  getAuditLog: (params = {}) => agentApi.get('/ai/audit-log', { params }),

  // Streaming chat — returns an EventSource-compatible URL
  chatStreamUrl: () => `${AGENT_BASE}/ai/chat/stream`,
};

/**
 * Open a streaming chat session and stream tokens back.
 * onToken(text): called for each streamed text chunk
 * onToolCall(tool): called when agent calls a tool
 * onDone(sessionId, toolCalls): called when stream completes
 * onError(msg): called on error
 */
export async function streamChat(message, sessionId, { onToken, onToolCall, onDone, onError }) {
  try {
    const resp = await fetch(`${AGENT_BASE}/ai/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!resp.ok) {
      onError?.(`HTTP ${resp.status}`);
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const evt = JSON.parse(line.slice(6));
          if (evt.type === 'text') onToken?.(evt.content, evt.session_id);
          else if (evt.type === 'tool_call') onToolCall?.(evt.tool);
          else if (evt.type === 'done') onDone?.(evt.session_id, evt.tool_calls || []);
          else if (evt.type === 'error') onError?.(evt.message);
        } catch { /* skip malformed */ }
      }
    }
  } catch (err) {
    onError?.(err.message);
  }
}

export default agentService;
