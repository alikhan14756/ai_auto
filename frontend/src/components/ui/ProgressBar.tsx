import * as React from "react";
import { cn } from "@/lib/utils";

export interface ProgressBarProps {
  value: number; // 0 to 100
  max?: number;
  label?: string;
  showPercentage?: boolean;
  variant?: "ember" | "success" | "info" | "warning";
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function ProgressBar({
  value,
  max = 100,
  label,
  showPercentage = true,
  variant = "ember",
  className,
  size = "md",
}: ProgressBarProps) {
  const percentage = Math.min(Math.max(Math.round((value / max) * 100), 0), 100);

  const colors = {
    ember: "bg-ember shadow-[0_0_12px_rgba(255,122,0,0.5)]",
    success: "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.5)]",
    info: "bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.5)]",
    warning: "bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.5)]",
  };

  const sizes = {
    sm: "h-1.5",
    md: "h-2",
    lg: "h-3",
  };

  return (
    <div className={cn("w-full space-y-1.5", className)}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between text-xs">
          {label && <span className="text-zinc-400 font-medium">{label}</span>}
          {showPercentage && (
            <span className="font-mono text-zinc-300 font-medium ml-auto">
              {percentage}%
            </span>
          )}
        </div>
      )}
      <div className={cn("w-full bg-zinc-900 rounded-full overflow-hidden border border-canvas-border/60", sizes[size])}>
        <div
          className={cn("h-full rounded-full transition-all duration-500 ease-out", colors[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
