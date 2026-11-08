"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import {
  Menu,
  Bell,
  Plus,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
} from "lucide-react";

function YoutubeIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" {...props}>
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  );
}
import { Button } from "@/components/ui/Button";
import { SearchInput } from "@/components/ui/Input";
import { Dropdown } from "@/components/ui/Dropdown";
import { Badge } from "@/components/ui/Badge";
import { NAVIGATION_GROUPS } from "@/config/navigation";

export interface HeaderProps {
  onOpenMobileMenu: () => void;
  onOpenCreateModal: () => void;
}

export function Header({
  onOpenMobileMenu,
  onOpenCreateModal,
}: HeaderProps) {
  const pathname = usePathname();

  // Find active navigation item title for breadcrumbs
  const currentItem = React.useMemo(() => {
    for (const group of NAVIGATION_GROUPS) {
      for (const item of group.items) {
        if (
          pathname === item.href ||
          (item.href !== "/dashboard" && pathname.startsWith(item.href))
        ) {
          return { group: group.title, item: item.title };
        }
      }
    }
    return { group: "Workspace", item: "Dashboard" };
  }, [pathname]);

  const notificationItems = [
    {
      id: "1",
      label: "QA Gate: 14 checks passed for 'Open Source AI Agents'",
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      badge: "Just now",
      onClick: () => {},
    },
    {
      id: "2",
      label: "Cadence: Scheduled 1 Long-Form & 1 Short this week",
      icon: <Sparkles className="w-4 h-4 text-ember" />,
      badge: "2h ago",
      onClick: () => {},
    },
    {
      id: "3",
      label: "Budget Guardrail: Monthly spend is $0.00 (within limits)",
      icon: <ShieldCheck className="w-4 h-4 text-blue-400" />,
      badge: "Today",
      onClick: () => {},
    },
  ];

  return (
    <header className="h-16 sticky top-0 z-20 bg-canvas-base/80 backdrop-blur-md border-b border-canvas-border px-4 sm:px-6 flex items-center justify-between gap-4">
      {/* Left: Mobile trigger & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="md:hidden w-9 h-9 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white hover:bg-canvas-subtle transition-colors focus-ring"
          aria-label="Open mobile navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs font-mono">
          <span className="text-zinc-500 uppercase tracking-wider">{currentItem.group}</span>
          <span className="text-zinc-600">/</span>
          <span className="text-zinc-200 font-semibold">{currentItem.item}</span>
        </div>
      </div>

      {/* Center: Search */}
      <div className="hidden lg:block w-72 max-w-xs">
        <SearchInput placeholder="Search studio..." className="py-1.5 text-xs h-9" />
      </div>

      {/* Right: Channel Status, QA Pill, Notifications, Create Action */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* YouTube Channel Connected Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-[11px] font-medium text-zinc-300">
          <YoutubeIcon className="text-red-500" />
          <span className="truncate max-w-[120px]">Muhammad Ali</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        </div>

        {/* 14-Point QA Indicator */}
        <Badge
          variant="success"
          size="sm"
          showDot
          className="hidden xl:inline-flex cursor-help"
          title="All 14 automated deterministic QA veto checks are active"
        >
          14 QA Checks Active
        </Badge>

        {/* Notifications Dropdown */}
        <Dropdown
          align="right"
          trigger={
            <button
              className="w-9 h-9 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white hover:bg-canvas-subtle transition-colors relative focus-ring"
              aria-label="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-ember shadow-[0_0_8px_rgba(255,122,0,0.8)]" />
            </button>
          }
          items={notificationItems}
        />

        {/* Primary "+ Create Video" Action */}
        <Button onClick={onOpenCreateModal} variant="primary" size="sm" className="shadow-md">
          <Plus className="w-3.5 h-3.5 mr-1" />
          <span className="hidden sm:inline">Create Video</span>
          <span className="sm:hidden">New</span>
        </Button>
      </div>
    </header>
  );
}
