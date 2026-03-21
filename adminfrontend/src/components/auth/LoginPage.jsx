import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Shield, Fingerprint, Lock, User, ArrowRight, ArrowLeft,
  Smartphone, MonitorSmartphone, Usb, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export const LoginPage = () => {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [trustDevice, setTrustDevice] = useState(false);
  // "credentials" = default, "passkey" = passkey selection menu
  const [mode, setMode] = useState("credentials");

  const { handleLogin, handleWebAuthnLogin, handleDeviceTrust } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const data = await handleLogin(identifier, password);
      if (!data.mfa_required && !data.mfa_setup_required && trustDevice) {
        try {
          await handleDeviceTrust(navigator.userAgent);
        } catch {
          // Non-critical
        }
      }
    } catch (err) {
      const detail = err.response?.data?.detail || "Login failed. Please try again.";
      toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWebAuthn = async () => {
    if (!identifier) {
      toast.error("Please enter your email or username first.");
      return;
    }
    setIsLoading(true);
    try {
      await handleWebAuthnLogin(identifier);
    } catch (err) {
      if (err.name === "NotAllowedError") {
        toast.error("Authentication was cancelled.");
      } else {
        const detail = err.response?.data?.detail || err.message || "Passkey authentication failed.";
        toast.error(detail);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const passkeyOptions = [
    {
      icon: MonitorSmartphone,
      label: "This device",
      desc: "Windows Hello, Touch ID, Face ID",
    },
    {
      icon: Smartphone,
      label: "Phone or tablet",
      desc: "Scan QR code with your device",
    },
    {
      icon: Usb,
      label: "Security key",
      desc: "YubiKey or other USB/NFC key",
    },
  ];

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-navy p-4 overflow-hidden relative">
      {/* Background */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-gold blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-navy-light blur-[120px]" />
      </div>

      <div className="w-full max-w-[440px] z-10 p-4 transition-all duration-500 animate-in fade-in zoom-in-95">
        <div className="flex flex-col items-center mb-10">
          <div className="drop-shadow-2xl">
            <img
              src="https://jhbridgetranslation.com/images/logo.png"
              alt="JHBridge Logo"
              className="h-24 w-auto object-contain"
            />
          </div>
        </div>

        <Card className="border-white/10 bg-navy/50 backdrop-blur-xl shadow-2xl overflow-hidden">
          <div className="h-1 bg-gradient-to-r from-gold/50 via-gold to-gold/50" />

          {/* ── Password Login Mode ─────────────────────────── */}
          {mode === "credentials" && (
            <>
              <CardHeader className="space-y-1 pb-4">
                <CardTitle className="text-xl flex items-center gap-2 text-white">
                  <Lock className="w-4 h-4 text-gold" />
                  Secure Login
                </CardTitle>
                <CardDescription className="text-white/40">
                  Enter your credentials to access the administrative portal
                </CardDescription>
              </CardHeader>
              <form onSubmit={handleSubmit}>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="identifier" className="text-white/80">Email or Username</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                      <Input
                        id="identifier"
                        type="text"
                        placeholder="admin@jhbridge.com or username"
                        className="bg-navy/30 border-white/10 text-white pl-10 focus:border-gold/50 focus:ring-gold/20 transition-all"
                        value={identifier}
                        onChange={(e) => setIdentifier(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-white/80">Password</Label>
                    <div className="relative">
                      <Shield className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                      <Input
                        id="password"
                        type="password"
                        className="bg-navy/30 border-white/10 text-white pl-10 focus:border-gold/50 focus:ring-gold/20 transition-all"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 pt-1">
                    <Checkbox
                      id="trust"
                      checked={trustDevice}
                      onCheckedChange={setTrustDevice}
                      className="border-white/20 data-[state=checked]:bg-gold data-[state=checked]:border-gold"
                    />
                    <Label htmlFor="trust" className="text-xs text-white/60 cursor-pointer select-none">
                      Trust this device for 30 days
                    </Label>
                  </div>
                </CardContent>
                <CardFooter className="flex flex-col gap-3 pt-2">
                  <Button
                    type="submit"
                    className="w-full bg-gold hover:bg-gold/90 text-navy font-bold h-12 transition-all hover:scale-[1.01] active:scale-[0.98] rounded-md shadow-lg shadow-gold/10"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <div className="w-5 h-5 border-2 border-navy border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        Authorize Access
                        <ArrowRight className="ml-2 w-4 h-4" />
                      </>
                    )}
                  </Button>

                  <div className="relative w-full py-2">
                    <div className="absolute inset-0 flex items-center px-4">
                      <span className="w-full border-t border-white/10" />
                    </div>
                    <div className="relative flex justify-center text-[10px] uppercase font-bold">
                      <span className="bg-navy px-2 text-white/30 font-mono">no password needed</span>
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    className="w-full border-white/10 bg-white/5 hover:bg-white/10 text-white font-semibold h-11 flex items-center justify-center gap-2 group transition-all"
                    disabled={isLoading}
                    onClick={() => setMode("passkey")}
                  >
                    <Fingerprint className="w-5 h-5 text-gold group-hover:scale-110 transition-transform" />
                    Sign in with Passkey
                  </Button>
                </CardFooter>
              </form>
            </>
          )}

          {/* ── Passkey Login Mode ──────────────────────────── */}
          {mode === "passkey" && (
            <>
              <CardHeader className="space-y-1 pb-4">
                <CardTitle className="text-xl flex items-center gap-2 text-white">
                  <Fingerprint className="w-4 h-4 text-gold" />
                  Sign in with Passkey
                </CardTitle>
                <CardDescription className="text-white/40">
                  No password needed — use your biometrics, phone, or security key
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Email/Username input */}
                <div className="space-y-2">
                  <Label htmlFor="passkey-identifier" className="text-white/80">Email or Username</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-4 w-4 text-white/30" />
                    <Input
                      id="passkey-identifier"
                      type="text"
                      placeholder="admin@jhbridge.com or username"
                      className="bg-navy/30 border-white/10 text-white pl-10 focus:border-gold/50 focus:ring-gold/20 transition-all"
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      autoFocus
                    />
                  </div>
                </div>

                {/* Method selection */}
                <div className="space-y-2 pt-1">
                  <p className="text-xs text-white/50 font-medium">Choose your method</p>
                  {passkeyOptions.map((opt) => {
                    const Icon = opt.icon;
                    return (
                      <button
                        key={opt.label}
                        type="button"
                        onClick={handleWebAuthn}
                        disabled={isLoading}
                        className="w-full flex items-center gap-3 p-3 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 hover:border-gold/30 transition-all text-left group disabled:opacity-50"
                      >
                        <div className="w-9 h-9 rounded-full bg-gold/10 flex items-center justify-center shrink-0 group-hover:bg-gold/20 transition-colors">
                          <Icon className="w-4.5 h-4.5 text-gold" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-white">{opt.label}</p>
                          <p className="text-[11px] text-white/40">{opt.desc}</p>
                        </div>
                        {isLoading && (
                          <Loader2 className="w-4 h-4 text-gold animate-spin" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </CardContent>
              <CardFooter className="flex flex-col gap-2 pt-0">
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full text-white/50 hover:text-white hover:bg-white/5 h-10 gap-2"
                  onClick={() => setMode("credentials")}
                  disabled={isLoading}
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to password login
                </Button>
              </CardFooter>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
