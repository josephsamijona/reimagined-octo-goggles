import axios from "axios";

const STORAGE_KEYS = {
  access: "jh_access_token",
  refresh: "jh_refresh_token",
  user: "jh_user",
  deviceTrust: "jh_device_trust_token",
};

const baseURL = import.meta.env.VITE_API_URL || "";
console.log("[API] Axios client created with baseURL:", JSON.stringify(baseURL));

const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor: inject Bearer token ─────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_KEYS.access);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.log(`[API REQUEST] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  console.log("[API REQUEST] Headers:", JSON.stringify(config.headers));
  console.log("[API REQUEST] Body:", JSON.stringify(config.data));
  return config;
});

// ── Response interceptor: log + auto-refresh on 401 ─────────────
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => {
    console.log(`[API RESPONSE] ${response.status} ${response.config.url}`, response.data);
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    console.error(`[API ERROR] ${error.response?.status} ${originalRequest?.url}`, error.response?.data);

    // Don't retry refresh or login requests
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/token/refresh/") ||
      originalRequest.url?.includes("/auth/login/")
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      console.log("[API] Queuing request while refreshing token...");
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = localStorage.getItem(STORAGE_KEYS.refresh);
    if (!refreshToken) {
      console.warn("[API] No refresh token found, forcing logout");
      isRefreshing = false;
      clearTokens();
      window.dispatchEvent(new Event("auth:logout"));
      return Promise.reject(error);
    }

    try {
      console.log("[API] Attempting token refresh...");
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_URL || ""}/api/v1/auth/token/refresh/`,
        { refresh: refreshToken }
      );
      console.log("[API] Token refresh successful");
      localStorage.setItem(STORAGE_KEYS.access, data.access);
      if (data.refresh) {
        localStorage.setItem(STORAGE_KEYS.refresh, data.refresh);
      }
      processQueue(null, data.access);
      originalRequest.headers.Authorization = `Bearer ${data.access}`;
      return api(originalRequest);
    } catch (refreshError) {
      console.error("[API] Token refresh FAILED, forcing logout", refreshError.response?.data);
      processQueue(refreshError, null);
      clearTokens();
      window.dispatchEvent(new Event("auth:logout"));
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

// ── Token helpers ────────────────────────────────────────────────
export function setTokens(access, refresh) {
  console.log("[TOKENS] Storing tokens, access length:", access?.length, "refresh length:", refresh?.length);
  localStorage.setItem(STORAGE_KEYS.access, access);
  localStorage.setItem(STORAGE_KEYS.refresh, refresh);
}

export function getTokens() {
  const tokens = {
    access: localStorage.getItem(STORAGE_KEYS.access),
    refresh: localStorage.getItem(STORAGE_KEYS.refresh),
  };
  console.log("[TOKENS] Retrieved tokens, hasAccess:", !!tokens.access, "hasRefresh:", !!tokens.refresh);
  return tokens;
}

export function clearTokens() {
  console.log("[TOKENS] Clearing all tokens from localStorage");
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
}

export function setStoredUser(user) {
  console.log("[TOKENS] Storing user:", user?.email, user?.role);
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(user));
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.user);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setDeviceTrustToken(token) {
  localStorage.setItem(STORAGE_KEYS.deviceTrust, token);
}

export function getDeviceTrustToken() {
  return localStorage.getItem(STORAGE_KEYS.deviceTrust);
}

export { STORAGE_KEYS };
export default api;
