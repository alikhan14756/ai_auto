import * as React from "react";
import { cn } from "@/lib/utils";
import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

export interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  subtitle?: string;
  icon?: LucideIcon;
  variant?: "default" | "ember";
  className?: string;
}

export function StatCard({
  title,
  value,
  change,
  changeType = "positive",
  subtitle,
  icon: Icon,
  variant = "default",
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "p-5 rounded-xl border bg-canvas-card border-canvas-border hover:border-zinc-700 transition-standard relative overflow-hidden group",
        variant === "ember" && "border-ember/30 shadow-[0_0_20px_rgba(255,122,0,0.08)]",
        className
      )}
    >
      {variant === "ember" && (
        <div className="absolute top-0 right-0 w-24 h-24 bg-ember/5 rounded-full blur-2xl pointer-events-none" />
      )}

      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-zinc-400 tracking-wider uppercase">
          {title}
        </span>
        {Icon && (
          <div
            className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center transition-colors",
              variant === "ember"
                ? "bg-ember/15 text-ember"
                : "bg-zinc-800 text-zinc-300 group-hover:text-ember group-hover:bg-ember/10"
            )}
          >
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-2xl font-bold tracking-tight text-white font-sans">
          {value}
        </span>
        {change && (
          <span
            className={cn(
              "inline-flex items-center text-xs font-mono font-medium",
              changeType === "positive" && "text-emerald-400",
              changeType === "negative" && "text-rose-400",
              changeType === "neutral" && "text-zinc-400"
            )}
          >
            {changeType === "positive" && <TrendingUp className="w-3 h-3 mr-0.5" />}
            {changeType === "negative" && <TrendingDown className="w-3 h-3 mr-0.5" />}
            {change}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="text-xs text-zinc-500 font-normal leading-relaxed">
          {subtitle}
        </p>
      )}
    </div>
  );
}
