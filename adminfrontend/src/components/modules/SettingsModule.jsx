// JHBridge Command Center - Settings Module
import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionHeader } from "@/components/shared/UIComponents";
import {
  FileText, Sparkles, Mail, Settings, Bell, Shield,
  Fingerprint, Trash2, Plus, Key, Loader2,
  Lock, KeyRound, ShieldCheck, X,
} from "lucide-react";
import { toast } from "sonner";
import authService from "@/services/authService";
import { base64urlToBuffer, bufferToBase64url } from "@/lib/webauthn";

const settingsItems = [
  { title: "Service Types", desc: "Medical, Legal, Conference, etc.", icon: FileText },
  { title: "Languages", desc: "Manage available languages & rates", icon: Sparkles },
  { title: "Email Templates", desc: "Customize all outgoing emails", icon: Mail },
  { title: "Company Info", desc: "JHBridge address, phone, branding", icon: Settings },
  { title: "Notification Rules", desc: "Auto-alerts & reminder config", icon: Bell },
];

function getDefaultDeviceName() {
  const ua = navigator.userAgent;
  if (/iPhone|iPad/.test(ua)) return "iPhone / iPad";
  if (/Android/.test(ua)) return "Android Device";
  if (/Mac/.test(ua)) return "Mac";
  if (/Windows/.test(ua)) return "Windows PC";
  if (/Linux/.test(ua)) return "Linux PC";
  return "Unknown Device";
}

function formatDate(dateStr) {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// ─── Step-Up Verification Dialog ─────────────────────────────────
function StepUpDialog({ methods, onVerified, onCancel }) {
  const [activeMethod, setActiveMethod] = useState(null);
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePassword = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await authService.stepUpVerify("password", { password });
      console.log("[STEP-UP] Password verified, got token");
      onVerified(data.step_up_token);
    } catch (err) {
      setError(err.response?.data?.detail || "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  const handleTotp = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await authService.stepUpVerify("totp", { code: totpCode });
      console.log("[STEP-UP] TOTP verified, got token");
      onVerified(data.step_up_token);
    } catch (err) {
      setError(err.response?.data?.detail || "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  const handlePasskey = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: rawOptions } = await authService.stepUpPasskeyOptions();
      const opts = rawOptions.publicKey || rawOptions;
      const publicKey = {
        ...opts,
        challenge: base64urlToBuffer(opts.challenge),
        allowCredentials: (opts.allowCredentials || []).map((c) => ({
          ...c,
          id: base64urlToBuffer(c.id),
        })),
      };
      const credential = await navigator.credentials.get({ publicKey });
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
      const { data } = await authService.stepUpPasskeyVerify(credentialJSON);
      console.log("[STEP-UP] Passkey verified, got token");
      onVerified(data.step_up_token);
    } catch (err) {
      if (err.name === "NotAllowedError") {
        setError("Passkey verification was cancelled");
      } else {
        setError(err.response?.data?.detail || "Passkey verification failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border rounded-lg bg-muted/20 p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-navy dark:text-gold" />
          <h3 className="text-sm font-semibold">Verify your identity</h3>
        </div>
        <Button size="icon" variant="ghost" className="h-7 w-7" onClick={onCancel}>
          <X className="w-4 h-4" />
        </Button>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        For security, confirm your identity before registering a new passkey.
      </p>

      {/* Method selector */}
      {!activeMethod && (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setActiveMethod("password")}
            className="gap-1.5"
          >
            <Lock className="w-3.5 h-3.5" />
            Password
          </Button>
          {methods.includes("totp") && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveMethod("totp")}
              className="gap-1.5"
            >
              <KeyRound className="w-3.5 h-3.5" />
              Authenticator Code
            </Button>
          )}
          {methods.includes("passkey") && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveMethod("passkey")}
              className="gap-1.5"
            >
              <Fingerprint className="w-3.5 h-3.5" />
              Existing Passkey
            </Button>
          )}
        </div>
      )}

      {/* Password form */}
      {activeMethod === "password" && (
        <div className="space-y-3">
          <div>
            <Label htmlFor="stepup-password" className="text-xs">Password</Label>
            <Input
              id="stepup-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && password && handlePassword()}
              placeholder="Enter your password"
              className="h-9 mt-1"
              disabled={loading}
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handlePassword}
              disabled={!password || loading}
              className="bg-navy hover:bg-navy/90 text-white"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setActiveMethod(null); setError(null); }}>
              Back
            </Button>
          </div>
        </div>
      )}

      {/* TOTP form */}
      {activeMethod === "totp" && (
        <div className="space-y-3">
          <div>
            <Label htmlFor="stepup-totp" className="text-xs">Authenticator Code</Label>
            <Input
              id="stepup-totp"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => e.key === "Enter" && totpCode.length === 6 && handleTotp()}
              placeholder="6-digit code"
              className="h-9 mt-1 font-mono tracking-widest"
              disabled={loading}
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleTotp}
              disabled={totpCode.length < 6 || loading}
              className="bg-navy hover:bg-navy/90 text-white"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setActiveMethod(null); setError(null); }}>
              Back
            </Button>
          </div>
        </div>
      )}

      {/* Passkey */}
      {activeMethod === "passkey" && (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Use your existing passkey to verify. A browser prompt should appear.
          </p>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handlePasskey}
              disabled={loading}
              className="bg-navy hover:bg-navy/90 text-white gap-1.5"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Fingerprint className="w-4 h-4" />}
              {loading ? "Waiting for device..." : "Verify with Passkey"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setActiveMethod(null); setError(null); }}>
              Back
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Settings Module ────────────────────────────────────────
export const SettingsModule = () => {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [deviceName, setDeviceName] = useState("");

  // Step-up auth state
  const [showStepUp, setShowStepUp] = useState(false);
  const [stepUpMethods, setStepUpMethods] = useState(["password"]);
  const [stepUpToken, setStepUpToken] = useState(null); // signed token from backend

  const fetchCredentials = useCallback(async () => {
    try {
      const { data } = await authService.webauthnList();
      setCredentials(data);
    } catch (err) {
      console.error("[SETTINGS] Failed to load passkeys:", err);
      toast.error("Failed to load passkeys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCredentials();
  }, [fetchCredentials]);

  // When user clicks "Register New Passkey" — fetch available methods
  const handleRegisterClick = async () => {
    try {
      const { data } = await authService.stepUpStatus();
      console.log("[SETTINGS] Step-up methods:", data.methods);
      setStepUpMethods(data.methods);
    } catch (err) {
      console.error("[SETTINGS] Failed to get step-up status:", err);
      setStepUpMethods(["password"]);
    }
    setShowStepUp(true);
    setStepUpToken(null);
  };

  const handleStepUpVerified = (token) => {
    console.log("[SETTINGS] Step-up verified, token received");
    setStepUpToken(token);
    setShowStepUp(false);
    toast.success("Identity verified");
  };

  const handleCancelStepUp = () => {
    setShowStepUp(false);
    setStepUpToken(null);
    setDeviceName("");
  };

  const handleRegister = async () => {
    if (!stepUpToken) {
      toast.error("Please verify your identity first");
      return;
    }

    const name = deviceName.trim() || getDefaultDeviceName();
    setRegistering(true);
    console.log("[SETTINGS] Starting passkey registration, device:", name);

    try {
      // 1. Get registration options (sends step-up token in header)
      console.log("[SETTINGS] Requesting register options...");
      const { data: rawOptions } = await authService.webauthnRegisterOptions(stepUpToken);
      // fido2 v2 wraps options in {publicKey: {...}}
      const opts = rawOptions.publicKey || rawOptions;
      console.log("[SETTINGS] Got register options:", JSON.stringify(opts).slice(0, 200));

      // 2. Convert for browser WebAuthn API
      const publicKey = {
        ...opts,
        challenge: base64urlToBuffer(opts.challenge),
        user: {
          ...opts.user,
          id: base64urlToBuffer(opts.user.id),
        },
        excludeCredentials: (opts.excludeCredentials || []).map((c) => ({
          ...c,
          id: base64urlToBuffer(c.id),
        })),
      };

      // 3. Browser prompt — works with any authenticator
      console.log("[SETTINGS] Calling navigator.credentials.create()...");
      const credential = await navigator.credentials.create({ publicKey });
      console.log("[SETTINGS] Browser credential received:", credential.id);

      // 4. Serialize for backend
      const credentialJSON = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        type: credential.type,
        response: {
          attestationObject: bufferToBase64url(credential.response.attestationObject),
          clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
        },
      };

      // 5. Verify with backend
      console.log("[SETTINGS] Sending credential to backend for verification...");
      await authService.webauthnRegisterVerify(credentialJSON, name, stepUpToken);

      toast.success("Passkey registered successfully");
      setDeviceName("");
      setStepUpToken(null);
      await fetchCredentials();
    } catch (err) {
      console.error("[SETTINGS] Passkey registration error:", err);
      if (err.name === "NotAllowedError") {
        toast.error("Passkey registration was cancelled");
      } else if (err.response?.data?.step_up_required) {
        toast.error("Verification expired, please re-verify");
        setStepUpToken(null);
        handleRegisterClick();
      } else {
        toast.error(err.response?.data?.detail || "Failed to register passkey");
      }
    } finally {
      setRegistering(false);
    }
  };

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      await authService.webauthnDelete(id);
      setCredentials((prev) => prev.filter((c) => c.id !== id));
      toast.success("Passkey removed");
    } catch {
      toast.error("Failed to remove passkey");
    } finally {
      setDeletingId(null);
    }
  };

  const showRegistrationForm = !!stepUpToken && !showStepUp;

  return (
    <div className="flex flex-col gap-6" data-testid="settings-module">
      <SectionHeader
        title="Settings & Configuration"
        subtitle="Service types, languages, email templates, company info"
      />

      {/* Settings cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {settingsItems.map((s, i) => {
          const Icon = s.icon;
          return (
            <Card
              key={i}
              className="shadow-sm cursor-pointer transition-colors hover:border-gold"
              data-testid={`settings-card-${s.title.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <CardContent className="p-5">
                <div className="flex items-center gap-2.5 mb-1.5">
                  <Icon className="w-4.5 h-4.5 text-navy dark:text-gold" />
                  <span className="text-sm font-semibold">{s.title}</span>
                </div>
                <span className="text-xs text-muted-foreground">{s.desc}</span>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Security Keys (Passkeys) section */}
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-navy dark:text-gold" />
              <CardTitle className="text-base">Security Keys (Passkeys)</CardTitle>
            </div>
            {!showStepUp && !showRegistrationForm && (
              <Button
                size="sm"
                onClick={handleRegisterClick}
                disabled={registering}
                className="bg-navy hover:bg-navy/90 text-white"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Register New Passkey
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Use passkeys to sign in with Windows Hello, Face ID, Touch ID, a YubiKey, or your phone — no password or MFA code needed.
          </p>
        </CardHeader>

        <CardContent className="pt-0">
          {/* Step-up verification dialog */}
          {showStepUp && (
            <StepUpDialog
              methods={stepUpMethods}
              onVerified={handleStepUpVerified}
              onCancel={handleCancelStepUp}
            />
          )}

          {/* Registration form — shown only after step-up verified */}
          {showRegistrationForm && (
            <div className="flex items-center gap-2 mb-4 p-3 border rounded-lg bg-muted/30">
              <Fingerprint className="w-5 h-5 text-navy dark:text-gold shrink-0" />
              <Input
                placeholder={`Device name (default: ${getDefaultDeviceName()})`}
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                className="flex-1 h-9"
                disabled={registering}
                onKeyDown={(e) => e.key === "Enter" && handleRegister()}
                autoFocus
              />
              <Button
                size="sm"
                onClick={handleRegister}
                disabled={registering}
                className="bg-navy hover:bg-navy/90 text-white"
              >
                {registering ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  "Register"
                )}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => { setStepUpToken(null); setDeviceName(""); }}
                disabled={registering}
              >
                Cancel
              </Button>
            </div>
          )}

          {/* Credentials list */}
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              Loading passkeys...
            </div>
          ) : credentials.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Key className="w-8 h-8 mb-2 opacity-40" />
              <p className="text-sm">No passkeys registered yet</p>
              <p className="text-xs mt-1">
                Register a passkey to sign in faster with biometrics or a security key
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {credentials.map((cred) => (
                <div
                  key={cred.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-navy/10 dark:bg-gold/10 flex items-center justify-center">
                      <Fingerprint className="w-4.5 h-4.5 text-navy dark:text-gold" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{cred.device_name}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>Added {formatDate(cred.created_at)}</span>
                        <span>Last used {formatDate(cred.last_used)}</span>
                      </div>
                    </div>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="text-muted-foreground hover:text-destructive h-8 w-8"
                    onClick={() => handleDelete(cred.id)}
                    disabled={deletingId === cred.id}
                  >
                    {deletingId === cred.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsModule;
