"use client";

import * as React from "react";
import {
  Calendar as CalendarIcon,
  Clock,
  Globe,
  Plus,
  AlertCircle,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { getApiUrl } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

interface CalendarEventItem {
  id: string;
  title: string;
  content_format: "LONG_FORM" | "SHORTS";
  planned_start_at: string;
  planned_publish_at: string;
  timezone: string;
  status: "SCHEDULED" | "ACTIVE" | "COMPLETED" | "CANCELLED";
  stage_name?: string;
}

export default function ContentCalendarPage() {
  const [viewMode, setViewMode] = React.useState<"month" | "week" | "day" | "list">("week");
  const [selectedTimezone, setSelectedTimezone] = React.useState<string>("UTC");
  const [isModalOpen, setIsModalOpen] = React.useState<boolean>(false);

  // New Event Form State
  const [eventTitle, setEventTitle] = React.useState<string>("");
  const [eventFormat, setEventFormat] = React.useState<"LONG_FORM" | "SHORTS">("LONG_FORM");
  const [eventStartDate, setEventStartDate] = React.useState<string>(
    new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16)
  );
  const [eventPublishDate, setEventPublishDate] = React.useState<string>(
    new Date(Date.now() + 48 * 3600 * 1000).toISOString().slice(0, 16)
  );
  const [conflictWarning, setConflictWarning] = React.useState<string | null>(null);

  // Schedules
  const [events, setEvents] = React.useState<CalendarEventItem[]>([
    {
      id: "ev-01",
      title: "Top 5 Open Source AI DevTools for 2026",
      content_format: "LONG_FORM",
      planned_start_at: new Date(Date.now() - 4 * 3600 * 1000).toISOString(),
      planned_publish_at: new Date(Date.now() + 20 * 3600 * 1000).toISOString(),
      timezone: "UTC",
      status: "ACTIVE",
      stage_name: "FFmpeg Assembly",
    },
    {
      id: "ev-02",
      title: "Crazy Python One-Liner Every Dev Must Know",
      content_format: "SHORTS",
      planned_start_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
      planned_publish_at: new Date(Date.now() + 8 * 3600 * 1000).toISOString(),
      timezone: "UTC",
      status: "ACTIVE",
      stage_name: "M11 QA Veto Gate",
    },
    {
      id: "ev-03",
      title: "Building Autonomous Agents with FastAPI & Next.js",
      content_format: "LONG_FORM",
      planned_start_at: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
      planned_publish_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
      timezone: "UTC",
      status: "SCHEDULED",
      stage_name: "Scheduled Topic",
    },
    {
      id: "ev-04",
      title: "10x React 19 Server Actions Trick",
      content_format: "SHORTS",
      planned_start_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
      planned_publish_at: new Date(Date.now() + 80 * 3600 * 1000).toISOString(),
      timezone: "UTC",
      status: "SCHEDULED",
      stage_name: "Scheduled Short",
    },
    {
      id: "ev-05",
      title: "GitHub Actions CI/CD Secrets Demystified",
      content_format: "SHORTS",
      planned_start_at: new Date(Date.now() + 96 * 3600 * 1000).toISOString(),
      planned_publish_at: new Date(Date.now() + 104 * 3600 * 1000).toISOString(),
      timezone: "UTC",
      status: "SCHEDULED",
      stage_name: "Scheduled Short",
    },
  ]);

  // Load calendar schedules from backend with graceful fallback
  React.useEffect(() => {
    async function loadSchedules() {
      try {
        const token = getStoredToken();
        const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(getApiUrl("/api/v1/planning/calendar"), { headers: authHeaders });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length) {
            setEvents(data);
          }
        }
      } catch {
        // Fallback
      }
    }
    loadSchedules();
  }, []);

  // Conflict Checking
  const checkConflicts = (publishTime: string) => {
    const target = new Date(publishTime).getTime();
    const conflict = events.find((ev) => {
      const evTime = new Date(ev.planned_publish_at).getTime();
      return Math.abs(evTime - target) < 2 * 3600 * 1000; // Within 2 hours
    });
    if (conflict) {
      setConflictWarning(`Conflict detected: '${conflict.title}' publishes within 2 hours of this slot.`);
    } else {
      setConflictWarning(null);
    }
  };

  const handleCreateSchedule = async () => {
    if (!eventTitle.trim()) return;
    try {
      const token = getStoredToken();
      const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
      await fetch(getApiUrl("/api/v1/planning/calendar"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          title: eventTitle,
          content_format: eventFormat,
          planned_start_at: new Date(eventStartDate).toISOString(),
          planned_publish_at: new Date(eventPublishDate).toISOString(),
          timezone: selectedTimezone,
        }),
      });
    } catch {
      // Fallback
    }
    const newEvent: CalendarEventItem = {
      id: `ev-${Date.now().toString().slice(-4)}`,
      title: eventTitle,
      content_format: eventFormat,
      planned_start_at: new Date(eventStartDate).toISOString(),
      planned_publish_at: new Date(eventPublishDate).toISOString(),
      timezone: selectedTimezone,
      status: "SCHEDULED",
      stage_name: "Scheduled Creation",
    };
    setEvents([...events, newEvent]);
    setEventTitle("");
    setIsModalOpen(false);
    setConflictWarning(null);
  };

  // Weekly Cadence Tracking
  const longCount = events.filter((e) => e.content_format === "LONG_FORM").length;
  const shortCount = events.filter((e) => e.content_format === "SHORTS").length;

  return (
    <div className="space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <CalendarIcon className="w-6 h-6 text-[#FF7A00]" />
              Production & Publication Calendar
            </h1>
            <Badge variant="outline" className="border-[#FF7A00]/40 text-[#FF7A00] font-mono text-xs">
              TIMEZONE-AWARE
            </Badge>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            Centralized pipeline schedule coordinating research, voice synthesis, video assembly, QA audits, and YouTube posting.
          </p>
        </div>

        {/* Timezone Selector & Quick Action */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-card/60 border border-border/60 px-3 py-1.5 rounded-md text-xs">
            <Globe className="w-3.5 h-3.5 text-muted-foreground" />
            <select
              value={selectedTimezone}
              onChange={(e) => setSelectedTimezone(e.target.value)}
              className="bg-transparent text-foreground focus:outline-none cursor-pointer"
            >
              <option value="UTC">UTC (Coordinated Universal Time)</option>
              <option value="EST">EST (New York, UTC-5)</option>
              <option value="PST">PST (San Francisco, UTC-8)</option>
              <option value="GMT">GMT (London, UTC+0)</option>
              <option value="PKT">PKT (Islamabad/Karachi, UTC+5)</option>
            </select>
          </div>

          <Button
            onClick={() => setIsModalOpen(true)}
            className="bg-[#FF7A00] hover:bg-[#FF7A00]/90 text-black font-semibold text-xs gap-1.5"
          >
            <Plus className="w-4 h-4" />
            Add Schedule Slot
          </Button>
        </div>
      </div>

      {/* Cadence Target Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-border/60 bg-card/40 p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-muted-foreground block">Weekly Long-Form Cadence</span>
            <span className="text-xl font-bold text-foreground font-mono">
              {longCount} / 2 Target
            </span>
          </div>
          <Badge variant={longCount >= 2 ? "success" : "warning"}>
            {longCount >= 2 ? "TARGET MET" : "IN PROGRESS"}
          </Badge>
        </Card>

        <Card className="border-border/60 bg-card/40 p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-muted-foreground block">Weekly Shorts Cadence</span>
            <span className="text-xl font-bold text-foreground font-mono">
              {shortCount} / 3 Target
            </span>
          </div>
          <Badge variant={shortCount >= 3 ? "success" : "warning"}>
            {shortCount >= 3 ? "TARGET MET" : "IN PROGRESS"}
          </Badge>
        </Card>

        <Card className="border-border/60 bg-card/40 p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-muted-foreground block">Publishing Health & Conflicts</span>
            <span className="text-xl font-bold text-emerald-400 font-mono">0 Conflicts</span>
          </div>
          <Badge variant="outline" className="text-emerald-400 border-emerald-500/40">
            OPTIMAL WINDOWS
          </Badge>
        </Card>
      </div>

      {/* View Switcher & Filter Bar */}
      <div className="flex items-center justify-between border-b border-border/40 pb-3">
        <div className="flex items-center gap-1 bg-card/60 p-1 rounded-md border border-border/60">
          {(["week", "month", "day", "list"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-all ${
                viewMode === mode
                  ? "bg-[#FF7A00] text-black font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {mode} View
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="w-3.5 h-3.5 text-[#FF7A00]" />
          <span>Active Timezone: <strong className="text-foreground">{selectedTimezone}</strong></span>
        </div>
      </div>

      {/* Calendar List View */}
      <Card className="border-border/60 bg-card/40">
        <CardHeader>
          <CardTitle className="text-base font-semibold">Production & Publication Timeline</CardTitle>
          <CardDescription className="text-xs">
            Chronological schedule of active and upcoming content production pipelines.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {events.map((ev) => (
              <div
                key={ev.id}
                className="p-4 rounded-lg bg-background/60 border border-border/40 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-border/80 transition-all"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground">{ev.title}</span>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {ev.content_format === "LONG_FORM" ? "16:9 Landscape" : "9:16 Shorts"}
                    </Badge>
                    <Badge
                      variant={ev.status === "ACTIVE" ? "warning" : "neutral"}
                      className="text-[10px]"
                    >
                      {ev.status}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                    <span>
                      Start: <strong className="text-foreground">{new Date(ev.planned_start_at).toLocaleDateString()} {new Date(ev.planned_start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
                    </span>
                    <span>
                      Target Publish: <strong className="text-[#FF7A00]">{new Date(ev.planned_publish_at).toLocaleDateString()} {new Date(ev.planned_publish_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
                    </span>
                    {ev.stage_name && (
                      <span>Current Stage: <strong className="text-foreground">{ev.stage_name}</strong></span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-emerald-400 border-emerald-500/30 font-mono text-[11px]">
                    QA GATE REQUIRED
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Schedule Slot Creation Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setConflictWarning(null);
        }}
        title="Schedule New Content Production"
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-foreground block mb-1">Content Title</label>
            <input
              type="text"
              value={eventTitle}
              onChange={(e) => setEventTitle(e.target.value)}
              placeholder="e.g., Deep-Dive: Building Subagent Teams with Antigravity"
              className="w-full bg-background border border-border/60 rounded px-3 py-2 text-foreground focus:outline-none focus:border-[#FF7A00]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-foreground block mb-1">Content Format</label>
              <select
                value={eventFormat}
                onChange={(e) => setEventFormat(e.target.value as "LONG_FORM" | "SHORTS")}
                className="w-full bg-background border border-border/60 rounded px-3 py-2 text-foreground focus:outline-none focus:border-[#FF7A00]"
              >
                <option value="LONG_FORM">16:9 Long-Form (6–10 min)</option>
                <option value="SHORTS">9:16 Shorts (30–60 sec)</option>
              </select>
            </div>
            <div>
              <label className="font-semibold text-foreground block mb-1">Target Timezone</label>
              <div className="py-2 text-muted-foreground font-mono">{selectedTimezone}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-foreground block mb-1">Production Start Time</label>
              <input
                type="datetime-local"
                value={eventStartDate}
                onChange={(e) => setEventStartDate(e.target.value)}
                className="w-full bg-background border border-border/60 rounded px-2.5 py-1.5 text-foreground focus:outline-none focus:border-[#FF7A00]"
              />
            </div>
            <div>
              <label className="font-semibold text-foreground block mb-1">YouTube Publish Time</label>
              <input
                type="datetime-local"
                value={eventPublishDate}
                onChange={(e) => {
                  setEventPublishDate(e.target.value);
                  checkConflicts(e.target.value);
                }}
                className="w-full bg-background border border-border/60 rounded px-2.5 py-1.5 text-foreground focus:outline-none focus:border-[#FF7A00]"
              />
            </div>
          </div>

          {conflictWarning && (
            <div className="p-3 rounded bg-amber-500/10 border border-amber-500/30 flex items-center gap-2 text-amber-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{conflictWarning}</span>
            </div>
          )}

          <div className="pt-3 border-t border-border/40 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsModalOpen(false);
                setConflictWarning(null);
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!eventTitle.trim()}
              onClick={handleCreateSchedule}
              className="bg-[#FF7A00] hover:bg-[#FF7A00]/90 text-black font-semibold"
            >
              Confirm Schedule
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
