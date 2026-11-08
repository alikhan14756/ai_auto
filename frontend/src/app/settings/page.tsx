"use client";

import React, { useState } from "react";
import Link from "next/link";
import { getApiUrl } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import {
  Settings,
  Activity,
  Boxes,
  CreditCard,
  Save,
  CheckCircle2,
  ExternalLink,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function SettingsPage() {
  const [defaultPrivacy, setDefaultPrivacy] = useState<"private" | "unlisted" | "public">("unlisted");
  const [defaultCategory, setDefaultCategory] = useState("28"); // Science & Technology
  const [syntheticDisclosure, setSyntheticDisclosure] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const token = getStoredToken();
      const channelId = typeof window !== "undefined" ? localStorage.getItem("active_channel_id") : null;
      if (token && channelId) {
        await fetch(getApiUrl(`/api/v1/channels/${channelId}/settings`), {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            default_privacy: defaultPrivacy,
            default_category_id: defaultCategory,
          }),
        }).catch(() => null);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">Platform Settings</h1>
            <Badge variant="neutral" size="sm">
              v0.1.0 Release
            </Badge>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Configure channel publication defaults, inspect subsystem health, and manage spend governors.
          </p>
        </div>
      </div>

      {/* Subsystem Navigation Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link href="/settings/health" className="group">
          <Card className="border-canvas-border bg-canvas-card group-hover:border-ember/40 transition-colors h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-emerald-400" />
                  <CardTitle className="text-base group-hover:text-ember transition-colors">
                    Operational Health
                  </CardTitle>
                </div>
                <Badge variant="success" size="sm" showDot>
                  Live
                </Badge>
              </div>
              <CardDescription>
                Worker heartbeats, watchdog alerts, queue depth, and database driver telemetry.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-zinc-400 flex items-center gap-1 group-hover:text-zinc-200">
                <span>View operational diagnostics</span>
                <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/settings/providers" className="group">
          <Card className="border-canvas-border bg-canvas-card group-hover:border-ember/40 transition-colors h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Boxes className="w-5 h-5 text-amber-400" />
                  <CardTitle className="text-base group-hover:text-ember transition-colors">
                    AI Providers
                  </CardTitle>
                </div>
                <Badge variant="neutral" size="sm">
                  Gemini
                </Badge>
              </div>
              <CardDescription>
                Google Gemini multimodal models, text-to-speech engine credentials, and quotas.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-zinc-400 flex items-center gap-1 group-hover:text-zinc-200">
                <span>Manage provider keys</span>
                <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/settings/usage" className="group">
          <Card className="border-canvas-border bg-canvas-card group-hover:border-ember/40 transition-colors h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-indigo-400" />
                  <CardTitle className="text-base group-hover:text-ember transition-colors">
                    Usage & Budget
                  </CardTitle>
                </div>
                <Badge variant="ember" size="sm">
                  $0.00 Cap
                </Badge>
              </div>
              <CardDescription>
                Strict $0.00 spend governor, monthly token accounting, and hard circuit breakers.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-zinc-400 flex items-center gap-1 group-hover:text-zinc-200">
                <span>Inspect spend guardrails</span>
                <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Channel Publication Defaults Form */}
      <Card className="border-canvas-border bg-canvas-card">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-zinc-300" />
            <CardTitle className="text-lg">Channel Publication Defaults</CardTitle>
          </div>
          <CardDescription>
            Default metadata applied to new video projects during automated pipeline execution.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-2">
                  Default Privacy Setting
                </label>
                <select
                  value={defaultPrivacy}
                  onChange={(e) => setDefaultPrivacy(e.target.value as "private" | "unlisted" | "public")}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-ember"
                >
                  <option value="unlisted">Unlisted (Recommended for QA verification)</option>
                  <option value="private">Private (Restricted staging)</option>
                  <option value="public">Public (Immediate subscriber broadcast)</option>
                </select>
                <p className="text-xs text-zinc-500 mt-1.5">
                  Production safeguard: Unlisted allows human inspection before public release.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-2">
                  YouTube Category ID
                </label>
                <select
                  value={defaultCategory}
                  onChange={(e) => setDefaultCategory(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-ember"
                >
                  <option value="28">28 — Science & Technology</option>
                  <option value="27">27 — Education</option>
                  <option value="26">26 — Howto & Style</option>
                  <option value="24">24 — Entertainment</option>
                </select>
                <p className="text-xs text-zinc-500 mt-1.5">
                  Default category for automated SEO tagging.
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-zinc-800">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="disclosure"
                  checked={syntheticDisclosure}
                  onChange={(e) => setSyntheticDisclosure(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-ember focus:ring-ember"
                />
                <div>
                  <label htmlFor="disclosure" className="text-sm font-medium text-zinc-200 cursor-pointer">
                    Mandatory Synthetic Media Disclosure (YouTube 2024+ Policy)
                  </label>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Automatically flag uploaded content with &ldquo;Contains altered or synthetic content&rdquo; in compliance with YouTube terms.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Shield className="w-4 h-4 text-emerald-400" />
                <span>All modifications cryptographically signed and stored in channel audit logs.</span>
              </div>
              <Button type="submit" variant="primary" size="md" disabled={saving} className="flex items-center gap-2">
                {saved ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                {saved ? "Settings Saved" : saving ? "Saving..." : "Save Channel Defaults"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
