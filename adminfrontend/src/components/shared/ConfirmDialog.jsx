// JHBridge - Confirm Dialog Component
import { Modal } from "./Modal";
import { Button } from "@/components/ui/button";
import { AlertTriangle, AlertCircle, Info, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const ConfirmDialog = ({
  isOpen,
  onConfirm,
  onCancel,
  title = "Confirm Action",
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "warning", // danger, warning, info
  loading = false,
}) => {
  const variants = {
    danger: {
      icon: Trash2,
      iconBg: "bg-danger/10",
      iconColor: "text-danger",
      buttonVariant: "destructive",
    },
    warning: {
      icon: AlertTriangle,
      iconBg: "bg-warning/10",
      iconColor: "text-warning",
      buttonVariant: "default",
    },
    info: {
      icon: Info,
      iconBg: "bg-info/10",
      iconColor: "text-info",
      buttonVariant: "default",
    },
  };

  const v = variants[variant] || variants.warning;
  const Icon = v.icon;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      size="sm"
      showClose={false}
      closeOnOverlay={!loading}
      closeOnEscape={!loading}
    >
      <div className="flex flex-col items-center text-center py-2">
        {/* Icon */}
        <div className={cn("w-12 h-12 rounded-full flex items-center justify-center mb-4", v.iconBg)}>
          <Icon className={cn("w-6 h-6", v.iconColor)} />
        </div>
        
        {/* Title */}
        <h3 className="text-lg font-semibold mb-2" data-testid="confirm-dialog-title">
          {title}
        </h3>
        
        {/* Message */}
        {message && (
          <p className="text-sm text-muted-foreground mb-6" data-testid="confirm-dialog-message">
            {message}
          </p>
        )}
        
        {/* Actions */}
        <div className="flex gap-3 w-full">
          <Button
            variant="outline"
            className="flex-1"
            onClick={onCancel}
            disabled={loading}
            data-testid="confirm-dialog-cancel"
          >
            {cancelText}
          </Button>
          <Button
            variant={v.buttonVariant}
            className={cn(
              "flex-1",
              variant === "danger" && "bg-danger hover:bg-danger/90",
              variant === "warning" && "bg-warning hover:bg-warning/90 text-white",
              variant === "info" && "bg-info hover:bg-info/90"
            )}
            onClick={onConfirm}
            disabled={loading}
            data-testid="confirm-dialog-confirm"
          >
            {loading ? "Processing..." : confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfirmDialog;
