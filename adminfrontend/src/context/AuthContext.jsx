import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import authService from "@/services/authService";
import { base64urlToBuffer, bufferToBase64url } from "@/lib/webauthn";
import {
  setTokens,
  getTokens,
  clearTokens,
  setStoredUser,
  setDeviceTrustToken,
} from "@/services/api";

const AuthContext = createContext(null);

function decodeBase64Url(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return atob(padded);
}

function getTokenExpiryMs(token) {
  if (!token) return null;

  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;

    const payload = JSON.parse(decodeBase64Url(parts[1]));
    if (!payload?.exp) return null;

    return payload.exp * 1000;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authPhase, setAuthPhase] = useState("loading"); // loading | login | mfa_setup | mfa_verify | authenticated
  const [mfaSetupData, setMfaSetupData] = useState(null);
  const [error, setError] = useState(null);

  const initRef = useRef(false);
  const sessionTimerRef = useRef(null);

  const clearSessionTimeout = useCallback(() => {
    if (sessionTimerRef.current) {
      window.clearTimeout(sessionTimerRef.current);
      sessionTimerRef.current = null;
    }
  }, []);

  const resetAuthState = useCallback(() => {
    clearSessionTimeout();
    clearTokens();
    setUser(null);
    setMfaSetupData(null);
    setAuthPhase("login");
  }, [clearSessionTimeout]);

  const scheduleSessionTimeout = useCallback((accessToken) => {
    clearSessionTimeout();

    const expiryMs = getTokenExpiryMs(accessToken);
    if (!expiryMs) return;

    const remainingMs = expiryMs - Date.now();
    if (remainingMs <= 0) {
      console.log("[AUTH_CONTEXT] Access token expired, forcing logout");
      resetAuthState();
      return;
    }

    sessionTimerRef.current = window.setTimeout(() => {
      console.log("[AUTH_CONTEXT] Session reached 1h limit, forcing logout");
      resetAuthState();
    }, remainingMs);

    console.log("[AUTH_CONTEXT] Session timeout scheduled in ms:", remainingMs);
  }, [clearSessionTimeout, resetAuthState]);

  // Init: check existing tokens on mount
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

    const expiryMs = getTokenExpiryMs(access);
    if (expiryMs && expiryMs <= Date.now()) {
      console.log("[AUTH_CONTEXT] Stored token already expired");
      resetAuthState();
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
        scheduleSessionTimeout(access);
      })
      .catch((err) => {
        console.error("[AUTH_CONTEXT] /auth/me/ failed:", err.response?.status, err.response?.data);
        resetAuthState();
      });
  }, [resetAuthState, scheduleSessionTimeout]);

  // Listen for forced logout from interceptor
  useEffect(() => {
    const onForceLogout = () => {
      console.log("[AUTH_CONTEXT] Force logout event received");
      resetAuthState();
    };

    window.addEventListener("auth:logout", onForceLogout);
    return () => window.removeEventListener("auth:logout", onForceLogout);
  }, [resetAuthState]);

  // Ensure timer cleanup on unmount
  useEffect(() => {
    return () => clearSessionTimeout();
  }, [clearSessionTimeout]);

  const handleLogin = useCallback(async (identifier, password) => {
    console.log("[AUTH_CONTEXT] handleLogin() called with identifier:", JSON.stringify(identifier));
    setError(null);

    const { data } = await authService.login(identifier, password);
    console.log("[AUTH_CONTEXT] Login response data:", JSON.stringify(data, null, 2));

    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);
    scheduleSessionTimeout(data.access);

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
  }, [scheduleSessionTimeout]);

  const handleGoogleLogin = useCallback(async (idToken) => {
    console.log("[AUTH_CONTEXT] handleGoogleLogin() called");
    setError(null);

    const { data } = await authService.googleAuth(idToken);
    console.log("[AUTH_CONTEXT] Google login response data:", JSON.stringify(data, null, 2));

    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);
    scheduleSessionTimeout(data.access);

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
  }, [scheduleSessionTimeout]);

  const handleMfaSetup = useCallback(async () => {
    console.log("[AUTH_CONTEXT] handleMfaSetup() called");
    setError(null);

    const { data } = await authService.mfaSetup();
    console.log("[AUTH_CONTEXT] MFA setup response, has qr_code:", !!data.qr_code, "has secret:", !!data.secret);
    setMfaSetupData(data);
    return data;
  }, []);

  const handleMfaVerify = useCallback(async (code) => {
    console.log("[AUTH_CONTEXT] handleMfaVerify() called with code length:", code?.length);
    setError(null);

    const { data } = await authService.mfaVerify(code);
    console.log("[AUTH_CONTEXT] MFA verify response, mfa_verified:", data.mfa_verified);

    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);
    setMfaSetupData(null);
    setAuthPhase("authenticated");
    scheduleSessionTimeout(data.access);

    return data;
  }, [scheduleSessionTimeout]);

  const handleMfaBackupCodes = useCallback(async () => {
    console.log("[AUTH_CONTEXT] handleMfaBackupCodes() called");
    const { data } = await authService.mfaBackupCodes();
    console.log("[AUTH_CONTEXT] Got", data.backup_codes?.length, "backup codes");
    return data;
  }, []);

  const handleWebAuthnLogin = useCallback(async (email) => {
    console.log("[AUTH_CONTEXT] handleWebAuthnLogin() called with:", email);
    setError(null);

    const { data: rawOptions } = await authService.webauthnLoginOptions(email);
    const opts = rawOptions.publicKey || rawOptions;
    console.log("[AUTH_CONTEXT] WebAuthn options received");

    const publicKey = {
      ...opts,
      challenge: base64urlToBuffer(opts.challenge),
      allowCredentials: (opts.allowCredentials || []).map((cred) => ({
        ...cred,
        id: base64urlToBuffer(cred.id),
      })),
    };

    console.log("[AUTH_CONTEXT] Requesting browser credential...");
    const credential = await navigator.credentials.get({ publicKey });
    console.log("[AUTH_CONTEXT] Browser credential received");

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

    const { data } = await authService.webauthnLoginVerify(credentialJSON);
    console.log("[AUTH_CONTEXT] WebAuthn login verified, user:", data.user?.email);

    setTokens(data.access, data.refresh);
    setStoredUser(data.user);
    setUser(data.user);
    setAuthPhase("authenticated");
    scheduleSessionTimeout(data.access);

    return data;
  }, [scheduleSessionTimeout]);

  const handleDeviceTrust = useCallback(async (fingerprint) => {
    console.log("[AUTH_CONTEXT] handleDeviceTrust() called");
    const { data } = await authService.deviceTrust(fingerprint);
    setDeviceTrustToken(data.trust_token);
    return data;
  }, []);

  const handleLogout = useCallback(async () => {
    console.log("[AUTH_CONTEXT] handleLogout() called");
    const { refresh } = getTokens();

    try {
      if (refresh) await authService.logout(refresh);
    } catch {
      // Ignore errors, we still clear local auth state
    }

    resetAuthState();
    console.log("[AUTH_CONTEXT] Logout complete, phase: login");
  }, [resetAuthState]);

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
    handleGoogleLogin,
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
