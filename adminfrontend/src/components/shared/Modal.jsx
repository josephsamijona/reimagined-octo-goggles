// JHBridge - Modal System Component
import { useEffect, useCallback } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Modal = ({ 
  isOpen, 
  onClose, 
  title, 
  subtitle,
  size = "md", 
  children,
  footer,
  showClose = true,
  closeOnOverlay = true,
  closeOnEscape = true,
}) => {
  // Handle escape key
  const handleEscape = useCallback((e) => {
    if (e.key === "Escape" && closeOnEscape) {
      onClose();
    }
  }, [onClose, closeOnEscape]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: "max-w-md",
    md: "max-w-lg",
    lg: "max-w-2xl",
    xl: "max-w-4xl",
    full: "max-w-[90vw]",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="modal-overlay">
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={closeOnOverlay ? onClose : undefined}
      />
      
      {/* Modal Content */}
      <div 
        className={cn(
          "relative bg-card border border-border rounded-lg shadow-xl w-full mx-4",
          "animate-in fade-in slide-in-from-bottom-4 duration-300",
          sizeClasses[size]
        )}
        data-testid="modal-content"
      >
        {/* Header */}
        {(title || showClose) && (
          <div className="flex items-start justify-between p-4 border-b border-border">
            <div>
              {title && (
                <h2 className="text-lg font-semibold font-display" data-testid="modal-title">
                  {title}
                </h2>
              )}
              {subtitle && (
                <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
              )}
            </div>
            {showClose && (
              <button
                onClick={onClose}
                className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                data-testid="modal-close-btn"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}
        
        {/* Body */}
        <div className="p-4 max-h-[70vh] overflow-y-auto">
          {children}
        </div>
        
        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-2 p-4 border-t border-border bg-muted/30">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Modal;
