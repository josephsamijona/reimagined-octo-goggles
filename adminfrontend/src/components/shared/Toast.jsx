// JHBridge - Toast Notifications (using sonner)
import { Toaster, toast } from "sonner";
import { CheckCircle, XCircle, AlertTriangle, Info } from "lucide-react";

// Toast Provider Component
export const ToastProvider = () => {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        className: "font-sans",
        style: {
          background: "hsl(var(--card))",
          color: "hsl(var(--foreground))",
          border: "1px solid hsl(var(--border))",
        },
      }}
      closeButton
    />
  );
};

// Toast helper functions
export const showToast = {
  success: (message, options = {}) => {
    toast.success(message, {
      icon: <CheckCircle className="w-5 h-5 text-success" />,
      ...options,
    });
  },
  
  error: (message, options = {}) => {
    toast.error(message, {
      icon: <XCircle className="w-5 h-5 text-danger" />,
      duration: 5000,
      ...options,
    });
  },
  
  warning: (message, options = {}) => {
    toast.warning(message, {
      icon: <AlertTriangle className="w-5 h-5 text-warning" />,
      ...options,
    });
  },
  
  info: (message, options = {}) => {
    toast.info(message, {
      icon: <Info className="w-5 h-5 text-info" />,
      ...options,
    });
  },
  
  loading: (message, options = {}) => {
    return toast.loading(message, options);
  },
  
  dismiss: (toastId) => {
    toast.dismiss(toastId);
  },
  
  promise: (promise, messages) => {
    return toast.promise(promise, {
      loading: messages.loading || "Loading...",
      success: messages.success || "Success!",
      error: messages.error || "Something went wrong",
    });
  },
};

export { toast };
export default ToastProvider;
