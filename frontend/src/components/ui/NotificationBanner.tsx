import * as React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from "lucide-react";

export interface NotificationBannerProps {
  type?: "info" | "success" | "warning" | "error";
  title?: string;
  message: string;
  onDismiss?: () => void;
  className?: string;
}

export function NotificationBanner({
  type = "info",
  title,
  message,
  onDismiss,
  className,
}: NotificationBannerProps) {
  const styles = {
    info: "bg-blue-500/10 border-blue-500/30 text-blue-300",
    success: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
    warning: "bg-amber-500/10 border-amber-500/30 text-amber-300",
    error: "bg-rose-500/10 border-rose-500/30 text-rose-300",
  };

  const icons = {
    info: <Info className="w-4 h-4 text-blue-400 shrink-0" />,
    success: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
    error: <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />,
  };

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3.5 rounded-xl border text-xs leading-relaxed transition-standard",
        styles[type],
        className
      )}
      role="alert"
    >
      {icons[type]}
      <div className="flex-1">
        {title && <span className="font-semibold block mb-0.5">{title}</span>}
        <span>{message}</span>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-zinc-400 hover:text-white transition-colors p-0.5 rounded focus-ring"
          aria-label="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
