import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Shield, Fingerprint, Lock, User, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export const LoginPage = () => {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [trustDevice, setTrustDevice] = useState(false);

  const { handleLogin, handleWebAuthnLogin, handleDeviceTrust } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log("[LOGIN_PAGE] Form submitted");
    console.log("[LOGIN_PAGE] identifier:", JSON.stringify(identifier));
    console.log("[LOGIN_PAGE] password length:", password?.length);
    setIsLoading(true);
    try {
      console.log("[LOGIN_PAGE] Calling handleLogin...");
      const data = await handleLogin(identifier, password);
      console.log("[LOGIN_PAGE] handleLogin returned:", JSON.stringify(data));
      // If authenticated directly (no MFA) and trust device is checked
      if (!data.mfa_required && !data.mfa_setup_required && trustDevice) {
        try {
          await handleDeviceTrust(navigator.userAgent);
        } catch {
          // Non-critical — don't block login
        }
      }
    } catch (err) {
      console.error("[LOGIN_PAGE] Login error:", err);
      console.error("[LOGIN_PAGE] Error response status:", err.response?.status);
      console.error("[LOGIN_PAGE] Error response data:", JSON.stringify(err.response?.data));
      console.error("[LOGIN_PAGE] Error response headers:", JSON.stringify(err.response?.headers));
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
      const detail = err.response?.data?.detail || err.message || "WebAuthn authentication failed.";
      toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-navy p-4 overflow-hidden relative">
      {/* Background Decorative Elements */}
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
                  <span className="bg-navy px-2 text-white/30 font-mono">Secure Options</span>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full border-white/10 bg-white/5 hover:bg-white/10 text-white font-semibold h-11 flex items-center justify-center gap-2 group transition-all"
                disabled={isLoading}
                onClick={handleWebAuthn}
              >
                <Fingerprint className="w-5 h-5 text-gold group-hover:scale-110 transition-transform" />
                Auth with WebAuthn
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
