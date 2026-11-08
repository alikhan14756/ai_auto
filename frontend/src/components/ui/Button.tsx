import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "destructive" | "emberGlow";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-lg transition-standard focus-ring disabled:opacity-50 disabled:pointer-events-none select-none cursor-pointer";

    const variants = {
      primary:
        "bg-ember text-black font-semibold hover:bg-ember-hover active:bg-ember-active shadow-[0_1px_8px_rgba(255,122,0,0.3)]",
      secondary:
        "bg-canvas-subtle text-zinc-100 border border-canvas-border hover:bg-zinc-800 hover:border-zinc-600 active:bg-zinc-900",
      ghost:
        "text-zinc-400 hover:text-white hover:bg-canvas-subtle active:bg-zinc-800",
      outline:
        "bg-transparent text-zinc-200 border border-canvas-border hover:border-ember/50 hover:text-white hover:bg-ember/5",
      destructive:
        "bg-rose-500/15 text-rose-400 border border-rose-500/30 hover:bg-rose-500/25 active:bg-rose-500/30",
      emberGlow:
        "bg-ember text-black font-semibold hover:bg-ember-hover shadow-[0_0_20px_rgba(255,122,0,0.4)] animate-pulse",
    };

    const sizes = {
      sm: "text-xs px-2.5 py-1.5 gap-1.5",
      md: "text-sm px-4 py-2 gap-2",
      lg: "text-base px-6 py-2.5 gap-2.5",
      icon: "h-9 w-9 p-0",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && (
          <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin mr-1.5" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
