import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot } from "@/components/ui/input-otp";
import { ShieldCheck, ChevronLeft } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export const MFAPage = () => {
  const [otp, setOtp] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const { handleMfaVerify, setAuthPhase } = useAuth();

  const handleVerify = async () => {
    if (otp.length !== 6) return;
    setIsVerifying(true);
    try {
      await handleMfaVerify(otp);
    } catch (err) {
      const detail = err.response?.data?.detail || "Invalid verification code.";
      toast.error(detail);
      setOtp("");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleBack = () => {
    setAuthPhase("login");
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-navy p-4 overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-navy-light blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-gold blur-[120px]" />
      </div>

      <div className="w-full max-w-[440px] z-10 p-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="flex flex-col items-center mb-10">
          <img
            src="https://jhbridgetranslation.com/images/logo.png"
            alt="JHBridge Logo"
            className="h-20 w-auto object-contain drop-shadow-xl"
          />
        </div>

        <button
          onClick={handleBack}
          className="flex items-center gap-1.5 text-white/40 hover:text-white/80 transition-colors mb-4 group"
        >
          <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          <span className="text-xs font-bold uppercase tracking-wider">Back to Login</span>
        </button>

        <Card className="border-white/10 bg-navy/50 backdrop-blur-xl shadow-2xl">
          <CardHeader className="text-center">
            <div className="w-16 h-16 rounded-full bg-gold/10 flex items-center justify-center mx-auto mb-4 border border-gold/20">
              <ShieldCheck className="w-8 h-8 text-gold animate-pulse" />
            </div>
            <CardTitle className="text-2xl text-white">Identity Verification</CardTitle>
            <CardDescription className="text-white/40">
              Enter the 6-digit code from your authenticator app.
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

            <p className="mt-6 text-[11px] text-white/30 font-mono uppercase tracking-wider">
              Codes refresh every 30 seconds in your authenticator app
            </p>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button
              onClick={handleVerify}
              disabled={otp.length !== 6 || isVerifying}
              className="w-full bg-gold hover:bg-gold/90 text-navy font-extrabold h-12 text-md shadow-lg shadow-gold/20 disabled:bg-white/10 disabled:text-white/20"
            >
              {isVerifying ? (
                <div className="w-5 h-5 border-2 border-navy border-t-transparent rounded-full animate-spin" />
              ) : (
                "Verify Access"
              )}
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
};

export default MFAPage;
