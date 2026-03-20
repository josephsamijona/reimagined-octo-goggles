import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot } from "@/components/ui/input-otp";
import { ShieldCheck, QrCode, KeyRound, Copy, Check, ChevronLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

const STEPS = ["scan", "verify", "backup"];

export const MFASetupPage = () => {
  const { handleMfaSetup, handleMfaVerify, handleMfaBackupCodes, mfaSetupData, setAuthPhase } = useAuth();

  const [step, setStep] = useState("scan"); // scan | verify | backup
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingSetup, setIsLoadingSetup] = useState(true);
  const [backupCodes, setBackupCodes] = useState([]);
  const [codesCopied, setCodesCopied] = useState(false);
  const [codesConfirmed, setCodesConfirmed] = useState(false);

  // Fetch QR code on mount
  useEffect(() => {
    handleMfaSetup()
      .catch((err) => {
        toast.error(err.response?.data?.detail || "Failed to initialize MFA setup.");
      })
      .finally(() => setIsLoadingSetup(false));
  }, [handleMfaSetup]);

  const handleVerify = async () => {
    if (otp.length !== 6) return;
    setIsLoading(true);
    try {
      await handleMfaVerify(otp);
      // handleMfaVerify sets authPhase to "authenticated" — override back to mfa_setup
      // so we stay on this page to show backup codes
      setAuthPhase("mfa_setup");
      try {
        const data = await handleMfaBackupCodes();
        setBackupCodes(data.backup_codes || []);
        setStep("backup");
      } catch {
        // If backup codes fail, still proceed — MFA is set up
        toast.error("Could not generate backup codes, but MFA is active.");
        setAuthPhase("authenticated");
      }
    } catch (err) {
      const detail = err.response?.data?.detail || "Invalid verification code.";
      toast.error(detail);
      setOtp("");
    } finally {
      setIsLoading(false);
    }
  };

  const copyBackupCodes = () => {
    const text = backupCodes.join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCodesCopied(true);
      toast.success("Backup codes copied to clipboard.");
      setTimeout(() => setCodesCopied(false), 3000);
    });
  };

  const finishSetup = () => {
    setAuthPhase("authenticated");
  };

  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-navy p-4 overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20">
        <div className="absolute top-[-10%] right-[-5%] w-[35%] h-[35%] rounded-full bg-gold blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-5%] w-[45%] h-[45%] rounded-full bg-navy-light blur-[120px]" />
      </div>

      <div className="w-full max-w-[480px] z-10 p-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex flex-col items-center mb-8">
          <img
            src="https://jhbridgetranslation.com/images/logo.png"
            alt="JHBridge Logo"
            className="h-20 w-auto object-contain drop-shadow-xl"
          />
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  i <= stepIndex
                    ? "bg-gold text-navy"
                    : "bg-white/10 text-white/30"
                }`}
              >
                {i < stepIndex ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`w-8 h-0.5 ${i < stepIndex ? "bg-gold" : "bg-white/10"}`} />
              )}
            </div>
          ))}
        </div>

        <Card className="border-white/10 bg-navy/50 backdrop-blur-xl shadow-2xl">
          {/* ── STEP 1: Scan QR ──────────────────────────────────── */}
          {step === "scan" && (
            <>
              <CardHeader className="text-center">
                <div className="w-16 h-16 rounded-full bg-gold/10 flex items-center justify-center mx-auto mb-4 border border-gold/20">
                  <QrCode className="w-8 h-8 text-gold" />
                </div>
                <CardTitle className="text-2xl text-white">Set Up Authenticator</CardTitle>
                <CardDescription className="text-white/40">
                  Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center gap-4">
                {isLoadingSetup ? (
                  <div className="w-48 h-48 flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-gold animate-spin" />
                  </div>
                ) : mfaSetupData?.qr_code ? (
                  <>
                    <div className="bg-white p-3 rounded-lg">
                      <img
                        src={mfaSetupData.qr_code.startsWith("data:") ? mfaSetupData.qr_code : `data:image/png;base64,${mfaSetupData.qr_code}`}
                        alt="MFA QR Code"
                        className="w-48 h-48"
                      />
                    </div>
                    {mfaSetupData.secret && (
                      <div className="text-center">
                        <p className="text-[10px] uppercase tracking-widest text-white/30 font-bold mb-1">
                          Manual Entry Key
                        </p>
                        <code className="text-sm text-gold font-mono bg-white/5 px-3 py-1.5 rounded border border-white/10 select-all">
                          {mfaSetupData.secret}
                        </code>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-white/40 text-sm">Failed to load QR code.</p>
                )}
              </CardContent>
              <CardFooter>
                <Button
                  onClick={() => setStep("verify")}
                  disabled={isLoadingSetup || !mfaSetupData}
                  className="w-full bg-gold hover:bg-gold/90 text-navy font-bold h-12 shadow-lg shadow-gold/10"
                >
                  I've Scanned the Code
                </Button>
              </CardFooter>
            </>
          )}

          {/* ── STEP 2: Verify Code ──────────────────────────────── */}
          {step === "verify" && (
            <>
              <CardHeader className="text-center">
                <div className="w-16 h-16 rounded-full bg-gold/10 flex items-center justify-center mx-auto mb-4 border border-gold/20">
                  <KeyRound className="w-8 h-8 text-gold" />
                </div>
                <CardTitle className="text-2xl text-white">Confirm Setup</CardTitle>
                <CardDescription className="text-white/40">
                  Enter the 6-digit code from your authenticator app to verify setup
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center py-6">
                <InputOTP
                  maxLength={6}
                  value={otp}
                  onChange={setOtp}
                  onComplete={handleVerify}
                >
                  <InputOTPGroup className="gap-2">
                    <InputOTPSlot index={0} className="w-12 h-14 bg-navy/30 border-white/10 text-white text-xl focus:border-gold" />
                    <InputOTPSlot index={1} className="w-12 h-14 bg-navy/30 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={2} className="w-12 h-14 bg-navy/30 border-white/10 text-white text-xl" />
                  </InputOTPGroup>
                  <InputOTPSeparator className="text-white/20" />
                  <InputOTPGroup className="gap-2">
                    <InputOTPSlot index={3} className="w-12 h-14 bg-navy/30 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={4} className="w-12 h-14 bg-navy/30 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={5} className="w-12 h-14 bg-navy/30 border-white/10 text-white text-xl" />
                  </InputOTPGroup>
                </InputOTP>
              </CardContent>
              <CardFooter className="flex flex-col gap-3">
                <Button
                  onClick={handleVerify}
                  disabled={otp.length !== 6 || isLoading}
                  className="w-full bg-gold hover:bg-gold/90 text-navy font-extrabold h-12 shadow-lg shadow-gold/20 disabled:bg-white/10 disabled:text-white/20"
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-navy border-t-transparent rounded-full animate-spin" />
                  ) : (
                    "Verify Code"
                  )}
                </Button>
                <button
                  onClick={() => { setStep("scan"); setOtp(""); }}
                  className="flex items-center gap-1.5 text-white/40 hover:text-white/80 transition-colors mx-auto group"
                >
                  <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                  <span className="text-xs font-bold uppercase tracking-wider">Back to QR Code</span>
                </button>
              </CardFooter>
            </>
          )}

          {/* ── STEP 3: Backup Codes ─────────────────────────────── */}
          {step === "backup" && (
            <>
              <CardHeader className="text-center">
                <div className="w-16 h-16 rounded-full bg-gold/10 flex items-center justify-center mx-auto mb-4 border border-gold/20">
                  <ShieldCheck className="w-8 h-8 text-gold" />
                </div>
                <CardTitle className="text-2xl text-white">Save Backup Codes</CardTitle>
                <CardDescription className="text-white/40">
                  Store these codes in a safe place. Each code can only be used once if you lose access to your authenticator.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center gap-4">
                <div className="grid grid-cols-2 gap-2 w-full max-w-xs">
                  {backupCodes.map((code, i) => (
                    <code
                      key={i}
                      className="text-sm text-center text-gold font-mono bg-white/5 px-3 py-2 rounded border border-white/10"
                    >
                      {code}
                    </code>
                  ))}
                </div>
                <Button
                  variant="outline"
                  onClick={copyBackupCodes}
                  className="border-white/10 bg-white/5 hover:bg-white/10 text-white text-sm"
                >
                  {codesCopied ? (
                    <><Check className="w-4 h-4 mr-2" /> Copied!</>
                  ) : (
                    <><Copy className="w-4 h-4 mr-2" /> Copy All Codes</>
                  )}
                </Button>
              </CardContent>
              <CardFooter className="flex flex-col gap-3">
                <label className="flex items-center gap-2 text-xs text-white/60 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={codesConfirmed}
                    onChange={(e) => setCodesConfirmed(e.target.checked)}
                    className="accent-gold"
                  />
                  I have saved my backup codes securely
                </label>
                <Button
                  onClick={finishSetup}
                  disabled={!codesConfirmed}
                  className="w-full bg-gold hover:bg-gold/90 text-navy font-bold h-12 shadow-lg shadow-gold/10 disabled:bg-white/10 disabled:text-white/20"
                >
                  Continue to Dashboard
                </Button>
              </CardFooter>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};

export default MFASetupPage;
