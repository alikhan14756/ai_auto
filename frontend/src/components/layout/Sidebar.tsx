"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { NAVIGATION_GROUPS } from "@/config/navigation";
import {
  ChevronLeft,
  ChevronRight,
  Video,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { Badge } from "@/components/ui/Badge";

export interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  className?: string;
}

export function Sidebar({
  isCollapsed,
  onToggleCollapse,
  className,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "h-screen sticky top-0 flex flex-col bg-canvas-card border-r border-canvas-border transition-all duration-300 z-30 select-none",
        isCollapsed ? "w-16" : "w-64",
        className
      )}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-3.5 border-b border-canvas-border shrink-0">
        <Link
          href="/dashboard"
          className="flex items-center gap-3 overflow-hidden group focus-ring rounded-lg p-1"
        >
          <div className="w-9 h-9 rounded-xl bg-ember/15 border border-ember/30 flex items-center justify-center text-ember shrink-0 shadow-[0_0_15px_rgba(255,122,0,0.2)] group-hover:scale-105 transition-transform">
            <Video className="w-4.5 h-4.5" />
          </div>

          {!isCollapsed && (
            <div className="flex flex-col overflow-hidden animate-in fade-in duration-200">
              <span className="text-sm font-bold text-white tracking-tight leading-tight flex items-center gap-1.5">
                CREATOR STUDIO
                <span className="text-[9px] font-mono text-ember px-1 py-0.2 rounded bg-ember/10 border border-ember/20">
                  AI
                </span>
              </span>
              <span className="text-[10px] text-zinc-500 font-mono">
                v0.1.0 &bull; Pro Suite
              </span>
            </div>
          )}
        </Link>

        {/* Desktop Collapse Toggle */}
        <button
          onClick={onToggleCollapse}
          className="hidden md:flex w-7 h-7 rounded-lg items-center justify-center text-zinc-400 hover:text-white hover:bg-canvas-subtle transition-colors focus-ring"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation Groups (Scrollable) */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-6">
        {NAVIGATION_GROUPS.map((group) => (
          <div key={group.id} className="space-y-1">
            {!isCollapsed ? (
              <h4 className="text-[10px] uppercase font-mono font-bold text-zinc-500 tracking-wider px-2.5 pb-1">
                {group.title}
              </h4>
            ) : (
              <div className="h-2" />
            )}

            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));

                const content = (
                  <Link
                    key={item.id}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-2.5 py-2 rounded-lg text-xs font-medium transition-standard focus-ring relative group",
                      isActive
                        ? "bg-canvas-subtle text-white font-semibold shadow-sm border border-canvas-border"
                        : "text-zinc-400 hover:text-zinc-200 hover:bg-canvas-subtle/50"
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-ember rounded-r-full shadow-[0_0_8px_rgba(255,122,0,0.8)]" />
                    )}

                    <item.icon
                      className={cn(
                        "w-4 h-4 shrink-0 transition-colors",
                        isActive
                          ? "text-ember"
                          : "text-zinc-400 group-hover:text-zinc-200"
                      )}
                    />

                    {!isCollapsed && (
                      <div className="flex-1 flex items-center justify-between overflow-hidden">
                        <span className="truncate">{item.title}</span>
                        {item.badge && (
                          <Badge
                            size="sm"
                            variant={item.badgeVariant || "neutral"}
                            className="ml-auto"
                          >
                            {item.badge}
                          </Badge>
                        )}
                      </div>
                    )}
                  </Link>
                );

                if (isCollapsed) {
                  return (
                    <Tooltip key={item.id} content={item.title} position="right">
                      {content}
                    </Tooltip>
                  );
                }

                return content;
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Profile & Quota Section */}
      <div className="p-2 border-t border-canvas-border shrink-0 bg-canvas-card/90">
        {!isCollapsed ? (
          <div className="p-2 rounded-xl bg-canvas-base border border-canvas-border space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-bold text-white font-mono">
                  MA
                </div>
                <div className="overflow-hidden">
                  <div className="text-xs font-semibold text-white truncate">
                    Muhammad Ali
                  </div>
                  <a
                    href="https://alibuild.site"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] text-zinc-400 hover:text-ember flex items-center gap-0.5 truncate transition-colors"
                  >
                    alibuild.site
                    <ExternalLink className="w-2.5 h-2.5 ml-0.5" />
                  </a>
                </div>
              </div>

              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Channel Connected" />
            </div>

            <div className="flex items-center justify-between pt-1 border-t border-canvas-border/50 text-[10px] font-mono text-zinc-400">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                QA Veto Active
              </span>
              <span className="text-ember font-semibold">$0.00 / Free</span>
            </div>
          </div>
        ) : (
          <Tooltip content="Muhammad Ali (alibuild.site) - Free Tier Active" position="right">
            <div className="w-10 h-10 mx-auto rounded-xl bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-bold text-white font-mono cursor-pointer hover:border-ember transition-colors">
              MA
            </div>
          </Tooltip>
        )}
      </div>
    </aside>
  );
}
