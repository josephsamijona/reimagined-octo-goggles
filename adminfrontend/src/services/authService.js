import api from "./api";

const AUTH = "/api/v1/auth";

const authService = {
  login(identifier, password) {
    const payload = { identifier, password };
    console.log("[AUTH_SERVICE] login() called");
    console.log("[AUTH_SERVICE] identifier:", JSON.stringify(identifier));
    console.log("[AUTH_SERVICE] password length:", password?.length);
    console.log("[AUTH_SERVICE] payload keys:", Object.keys(payload));
    console.log("[AUTH_SERVICE] full payload:", JSON.stringify(payload));
    console.log("[AUTH_SERVICE] POST URL:", `${AUTH}/login/`);
    return api.post(`${AUTH}/login/`, payload);
  },

  mfaSetup() {
    console.log("[AUTH_SERVICE] mfaSetup() called");
    return api.post(`${AUTH}/mfa/setup/`);
  },

  mfaVerify(code) {
    console.log("[AUTH_SERVICE] mfaVerify() called with code length:", code?.length);
    return api.post(`${AUTH}/mfa/verify/`, { code });
  },

  mfaBackupCodes() {
    console.log("[AUTH_SERVICE] mfaBackupCodes() called");
    return api.post(`${AUTH}/mfa/backup-codes/`);
  },

  webauthnLoginOptions(email) {
    console.log("[AUTH_SERVICE] webauthnLoginOptions() called with email:", email);
    return api.post(`${AUTH}/webauthn/login/options/`, { email });
  },

  webauthnLoginVerify(response) {
    console.log("[AUTH_SERVICE] webauthnLoginVerify() called");
    return api.post(`${AUTH}/webauthn/login/verify/`, { response });
  },

  webauthnRegisterOptions() {
    console.log("[AUTH_SERVICE] webauthnRegisterOptions() called");
    return api.post(`${AUTH}/webauthn/register/options/`);
  },

  webauthnRegisterVerify(response, deviceName) {
    console.log("[AUTH_SERVICE] webauthnRegisterVerify() called");
    return api.post(`${AUTH}/webauthn/register/verify/`, {
      response,
      device_name: deviceName,
    });
  },

  deviceTrust(fingerprint) {
    console.log("[AUTH_SERVICE] deviceTrust() called");
    return api.post(`${AUTH}/device/trust/`, { fingerprint });
  },

  logout(refreshToken) {
    console.log("[AUTH_SERVICE] logout() called");
    return api.post(`${AUTH}/logout/`, { refresh: refreshToken });
  },

  me() {
    console.log("[AUTH_SERVICE] me() called");
    return api.get(`${AUTH}/me/`);
  },
};

export default authService;
