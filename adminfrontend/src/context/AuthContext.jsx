import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import authService from "@/services/authService";
import {
  setTokens,
  getTokens,
  clearTokens,
  setStoredUser,
  getStoredUser,
  setDeviceTrustToken,
} from "@/services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authPhase, setAuthPhase] = useState("loading"); // loading | login | mfa_setup | mfa_verify | authenticated
  const [mfaSetupData, setMfaSetupData] = useState(null);
  const [error, setError] = useState(null);
  const initRef = useRef(false);

  // ── Init: check existing tokens on mount ───────────────────────
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    console.log("[AUTH_CONTEXT] Init: checking existing tokens...");
    const { access } = getTokens();
    if (!access) {
      console.log("[AUTH_CONTEXT] No access token found, going to login");
      setAuthPhase("login");
      return;
    }

    console.log("[AUTH_CONTEXT] Found access token, calling /auth/me/...");
    authService
      .me()
      .then(({ data }) => {
        console.log("[AUTH_CONTEXT] /auth/me/ success:", data.email, data.role);
        setUser(data);
        setStoredUser(data);
        setAuthPhase("authenticated");
      })
      .catch((err) => {
        console.error("[AUTH_CONTEXT] /auth/me/ failed:", err.response?.status, err.response?.data);
        clearTokens();
        setAuthPhase("login");
      });
  }, []);

  // ── Listen for forced logout from interceptor ──────────────────
  useEffect(() => {
    const onForceLogout = () => {
      console.log("[AUTH_CONTEXT] Force logout event received");
      setUser(null);
      setAuthPhase("login");
    };
    window.addEventListener("auth:logout", onForceLogout);
    return () => window.removeEventListener("auth:logout", onForceLogout);
  }, []);

  // ── Login ──────────────────────────────────────────────────────
  const handleLogin = useCallback(async (identifier, password) => {
    console.log("[AUTH_CONTEXT] handleLogin() called with identifier:", JSON.stringify(identifier));
    setError(null);
    const { data } = await authService.login(identifier, password);
    console.log("[AUTH_CONTEXT] Login response data:", JSON.stringify(data, null, 2));

    // Store tokens (partial if MFA required, full otherwise)
    console.log("[AUTH_CONTEXT] Storing tokens...");
    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);

    if (data.mfa_setup_required) {
      console.log("[AUTH_CONTEXT] -> Phase: mfa_setup");
      setAuthPhase("mfa_setup");
    } else if (data.mfa_required) {
      console.log("[AUTH_CONTEXT] -> Phase: mfa_verify");
      setAuthPhase("mfa_verify");
    } else {
      console.log("[AUTH_CONTEXT] -> Phase: authenticated");
      setAuthPhase("authenticated");
    }

    return data;
  }, []);

  // ── MFA Setup ──────────────────────────────────────────────────
  const handleMfaSetup = useCallback(async () => {
    console.log("[AUTH_CONTEXT] handleMfaSetup() called");
    setError(null);
    const { data } = await authService.mfaSetup();
    console.log("[AUTH_CONTEXT] MFA setup response, has qr_code:", !!data.qr_code, "has secret:", !!data.secret);
    setMfaSetupData(data);
    return data;
  }, []);

  // ── MFA Verify ─────────────────────────────────────────────────
  const handleMfaVerify = useCallback(async (code) => {
    console.log("[AUTH_CONTEXT] handleMfaVerify() called with code length:", code?.length);
    setError(null);
    const { data } = await authService.mfaVerify(code);
    console.log("[AUTH_CONTEXT] MFA verify response, mfa_verified:", data.mfa_verified);

    // Replace partial tokens with full tokens
    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);
    setMfaSetupData(null);
    setAuthPhase("authenticated");

    return data;
  }, []);

  // ── MFA Backup Codes ──────────────────────────────────────────
  const handleMfaBackupCodes = useCallback(async () => {
    console.log("[AUTH_CONTEXT] handleMfaBackupCodes() called");
    const { data } = await authService.mfaBackupCodes();
    console.log("[AUTH_CONTEXT] Got", data.backup_codes?.length, "backup codes");
    return data;
  }, []);

  // ── WebAuthn Login ─────────────────────────────────────────────
  const handleWebAuthnLogin = useCallback(async (email) => {
    console.log("[AUTH_CONTEXT] handleWebAuthnLogin() called with:", email);
    setError(null);

    // 1. Get challenge options
    const { data: options } = await authService.webauthnLoginOptions(email);
    console.log("[AUTH_CONTEXT] WebAuthn options received");

    // 2. Convert base64url to ArrayBuffer for WebAuthn API
    const publicKey = {
      ...options,
      challenge: base64urlToBuffer(options.challenge),
      allowCredentials: (options.allowCredentials || []).map((cred) => ({
        ...cred,
        id: base64urlToBuffer(cred.id),
      })),
    };

    // 3. Get credential from browser
    console.log("[AUTH_CONTEXT] Requesting browser credential...");
    const credential = await navigator.credentials.get({ publicKey });
    console.log("[AUTH_CONTEXT] Browser credential received");

    // 4. Serialize response for backend
    const credentialJSON = {
      id: credential.id,
      rawId: bufferToBase64url(credential.rawId),
      type: credential.type,
      response: {
        authenticatorData: bufferToBase64url(credential.response.authenticatorData),
        clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
        signature: bufferToBase64url(credential.response.signature),
        userHandle: credential.response.userHandle
          ? bufferToBase64url(credential.response.userHandle)
          : null,
      },
    };

    // 5. Verify with backend
    const { data } = await authService.webauthnLoginVerify(credentialJSON);
    console.log("[AUTH_CONTEXT] WebAuthn login verified, user:", data.user?.email);

    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);
    setAuthPhase("authenticated");

    return data;
  }, []);

  // ── Device Trust ───────────────────────────────────────────────
  const handleDeviceTrust = useCallback(async (fingerprint) => {
    console.log("[AUTH_CONTEXT] handleDeviceTrust() called");
    const { data } = await authService.deviceTrust(fingerprint);
    setDeviceTrustToken(data.trust_token);
    return data;
  }, []);

  // ── Logout ─────────────────────────────────────────────────────
  const handleLogout = useCallback(async () => {
    console.log("[AUTH_CONTEXT] handleLogout() called");
    const { refresh } = getTokens();
    try {
      if (refresh) await authService.logout(refresh);
    } catch {
      // Ignore errors — we're logging out regardless
    }
    clearTokens();
    setUser(null);
    setMfaSetupData(null);
    setAuthPhase("login");
    console.log("[AUTH_CONTEXT] Logout complete, phase: login");
  }, []);

  // Log phase changes
  useEffect(() => {
    console.log("[AUTH_CONTEXT] authPhase changed to:", authPhase);
  }, [authPhase]);

  const value = {
    user,
    authPhase,
    mfaSetupData,
    error,
    isAuthenticated: authPhase === "authenticated",
    handleLogin,
    handleMfaSetup,
    handleMfaVerify,
    handleMfaBackupCodes,
    handleWebAuthnLogin,
    handleDeviceTrust,
    handleLogout,
    setAuthPhase,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// ── WebAuthn encoding helpers ────────────────────────────────────
function base64urlToBuffer(base64url) {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4 === 0 ? "" : "=".repeat(4 - (base64.length % 4));
  const binary = atob(base64 + pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function bufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
