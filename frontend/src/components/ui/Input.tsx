import * as React from "react";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", icon, label, error, ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label className="block text-xs font-medium text-zinc-300">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {icon && (
            <div className="absolute left-3 text-zinc-400 pointer-events-none">
              {icon}
            </div>
          )}
          <input
            type={type}
            ref={ref}
            className={cn(
              "w-full bg-canvas-base border border-canvas-border rounded-lg text-sm text-zinc-100 placeholder:text-zinc-500 focus-ring py-2 px-3.5 transition-standard",
              icon ? "pl-9" : "pl-3.5",
              error ? "border-rose-500 focus-visible:ring-rose-500" : "hover:border-zinc-700",
              className
            )}
            {...props}
          />
        </div>
        {error && <p className="text-xs text-rose-400">{error}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

export function SearchInput({
  className,
  placeholder = "Search topics, videos, assets...",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Input
      icon={<Search className="w-4 h-4 text-zinc-400" />}
      placeholder={placeholder}
      className={cn("bg-canvas-subtle/80 border-canvas-border", className)}
      {...props}
    />
  );
}
