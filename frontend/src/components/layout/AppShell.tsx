"use client";

import * as React from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Film,
  Smartphone,
  Sliders,
  CheckCircle2,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAVIGATION_GROUPS } from "@/config/navigation";

export interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = React.useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = React.useState(false);

  // New video modal form state
  const [videoTitle, setVideoTitle] = React.useState("");
  const [videoFormat, setVideoFormat] = React.useState<"LONG_FORM" | "SHORTS">(
    "LONG_FORM"
  );
  const [nicheCategory, setNicheCategory] = React.useState("Artificial Intelligence");
  const [isSubmitted, setIsSubmitted] = React.useState(false);

  const pathname = usePathname();

  // Close mobile drawer on route change
  React.useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  const handleCreateVideoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);
    setTimeout(() => {
      setIsSubmitted(false);
      setIsCreateModalOpen(false);
      setVideoTitle("");
    }, 1500);
  };

  return (
    <div className="min-h-screen flex bg-canvas-base text-zinc-100">
      {/* Desktop Persistent Sidebar */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        className="hidden md:flex"
      />

      {/* Mobile Drawer Backdrop & Sidebar */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div className="relative w-72 max-w-[80vw] bg-canvas-card border-r border-canvas-border h-full z-10 flex flex-col animate-in slide-in-from-left duration-200">
            <div className="p-4 flex items-center justify-between border-b border-canvas-border">
              <span className="font-bold text-sm text-white">Navigation</span>
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
              {NAVIGATION_GROUPS.map((group) => (
                <div key={group.id} className="space-y-1">
                  <h4 className="text-[10px] uppercase font-mono font-bold text-zinc-500 px-2">
                    {group.title}
                  </h4>
                  <div className="space-y-0.5">
                    {group.items.map((item) => {
                      const isActive =
                        pathname === item.href ||
                        (item.href !== "/dashboard" && pathname.startsWith(item.href));
                      return (
                        <Link
                          key={item.id}
                          href={item.href}
                          className={cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium",
                            isActive
                              ? "bg-canvas-subtle text-white font-semibold border border-canvas-border"
                              : "text-zinc-400 hover:text-white hover:bg-canvas-subtle/50"
                          )}
                        >
                          <item.icon
                            className={cn(
                              "w-4 h-4",
                              isActive ? "text-ember" : "text-zinc-400"
                            )}
                          />
                          <span>{item.title}</span>
                          {item.badge && (
                            <Badge size="sm" variant={item.badgeVariant} className="ml-auto">
                              {item.badge}
                            </Badge>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Viewport */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
          onOpenCreateModal={() => setIsCreateModalOpen(true)}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto animate-in fade-in duration-200">
          {children}
        </main>
      </div>

      {/* Interactive Quick Action Modal: Create New Video */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Initialize New Video Project"
        description="Configure video format, concept angle, and target audience profile."
        maxWidth="md"
        footer={
          !isSubmitted ? (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsCreateModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleCreateVideoSubmit}
                disabled={!videoTitle.trim()}
              >
                Launch Pipeline
              </Button>
            </>
          ) : null
        }
      >
        {!isSubmitted ? (
          <form onSubmit={handleCreateVideoSubmit} className="space-y-4">
            <Input
              label="Working Concept Title"
              placeholder="e.g. Top 3 Local AI Agents for Coding in 2026"
              value={videoTitle}
              onChange={(e) => setVideoTitle(e.target.value)}
              required
              autoFocus
            />

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-2">
                Target Format
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setVideoFormat("LONG_FORM")}
                  className={cn(
                    "flex flex-col items-start p-3.5 rounded-xl border text-left transition-standard focus-ring",
                    videoFormat === "LONG_FORM"
                      ? "bg-canvas-subtle border-ember text-white shadow-sm"
                      : "bg-canvas-card border-canvas-border text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  )}
                >
                  <div className="flex items-center gap-2 font-semibold text-xs mb-1">
                    <Film className="w-4 h-4 text-ember" />
                    <span>Long-Form (16:9)</span>
                  </div>
                  <span className="text-[11px] text-zinc-500">
                    6–10 min comprehensive tutorial & analysis
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setVideoFormat("SHORTS")}
                  className={cn(
                    "flex flex-col items-start p-3.5 rounded-xl border text-left transition-standard focus-ring",
                    videoFormat === "SHORTS"
                      ? "bg-canvas-subtle border-ember text-white shadow-sm"
                      : "bg-canvas-card border-canvas-border text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  )}
                >
                  <div className="flex items-center gap-2 font-semibold text-xs mb-1">
                    <Smartphone className="w-4 h-4 text-ember" />
                    <span>YouTube Shorts (9:16)</span>
                  </div>
                  <span className="text-[11px] text-zinc-500">
                    30–60 sec fast-paced breakdown
                  </span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Niche Taxonomy
              </label>
              <select
                value={nicheCategory}
                onChange={(e) => setNicheCategory(e.target.value)}
                className="w-full bg-canvas-base border border-canvas-border rounded-lg text-xs text-zinc-100 py-2 px-3 focus-ring"
              >
                <option value="Artificial Intelligence">AI Tools & Comparisons</option>
                <option value="Developer Productivity">Developer Productivity & Automation</option>
                <option value="Technology Tutorials">Beginner-Friendly Coding Tutorials</option>
                <option value="Useful Websites">Useful Web Tools & Open Source</option>
              </select>
            </div>

            <div className="p-3 rounded-lg bg-zinc-900/80 border border-canvas-border/80 text-[11px] text-zinc-400 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-ember" />
                Deterministic 14-Point QA Gate:
              </span>
              <span className="text-emerald-400 font-mono font-medium">
                Mandatory Prior to Upload
              </span>
            </div>
          </form>
        ) : (
          <div className="py-8 text-center space-y-3 animate-in fade-in duration-300">
            <div className="w-12 h-12 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-semibold text-white">
              Project Concept Initialized!
            </h4>
            <p className="text-xs text-zinc-400 max-w-xs mx-auto">
              Draft queued in state <code className="text-ember font-mono">IDEA</code>. Fact verification and scene planning will commence.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
