import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "ember"
    | "success"
    | "warning"
    | "error"
    | "info"
    | "neutral"
    | "outline";
  size?: "sm" | "md";
  showDot?: boolean;
}

export function Badge({
  className,
  variant = "neutral",
  size = "md",
  showDot = false,
  children,
  ...props
}: BadgeProps) {
  const variants = {
    ember:
      "bg-ember/10 text-ember border-ember/30",
    success:
      "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    warning:
      "bg-amber-500/10 text-amber-400 border-amber-500/30",
    error:
      "bg-rose-500/10 text-rose-400 border-rose-500/30",
    info:
      "bg-blue-500/10 text-blue-400 border-blue-500/30",
    neutral:
      "bg-zinc-800 text-zinc-300 border-zinc-700",
    outline:
      "bg-transparent text-zinc-400 border-canvas-border",
  };

  const dots = {
    ember: "bg-ember",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    error: "bg-rose-400",
    info: "bg-blue-400",
    neutral: "bg-zinc-400",
    outline: "bg-zinc-500",
  };

  const sizes = {
    sm: "text-[10px] px-2 py-0.5 font-mono font-medium gap-1",
    md: "text-xs px-2.5 py-0.5 font-medium gap-1.5",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border tracking-wide uppercase",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {showDot && (
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full animate-pulse",
            dots[variant]
          )}
        />
      )}
      {children}
    </span>
  );
}
