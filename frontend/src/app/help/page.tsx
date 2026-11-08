"use client";

import React, { useState } from "react";
import {
  BookOpen,
  ShieldCheck,
  Terminal,
  Server,
  Database,
  ExternalLink,
  CheckCircle2,
  Copy,
  Check,
  Layers,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState<"ARCHITECTURE" | "POLICY" | "RUNBOOK" | "QA" | "DEPLOYMENT">("ARCHITECTURE");
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  return (
    <div className="space-y-6 pb-16 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[#262B3D] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-[#FF7A00]" />
              Help & System Documentation
            </h1>
            <Badge variant="ember" size="sm">
              M01–M15 Spec
            </Badge>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Complete architectural blueprints, runbooks, YouTube policy guides, and deployment operations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            className="border-zinc-800 text-zinc-300 hover:bg-zinc-800 gap-1.5 text-xs"
            onClick={() => window.open("https://alibuild.site", "_blank")}
          >
            <ExternalLink className="w-3.5 h-3.5 text-[#FF7A00]" />
            Owner Portfolio (alibuild.site)
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 pb-3">
        {[
          { id: "ARCHITECTURE", label: "Architecture & Schema", icon: Layers },
          { id: "POLICY", label: "YouTube Policy & Fair Use", icon: ShieldCheck },
          { id: "RUNBOOK", label: "CLI & Operator Runbook", icon: Terminal },
          { id: "QA", label: "14-Point Deterministic QA", icon: CheckCircle2 },
          { id: "DEPLOYMENT", label: "Zero-Cost Staging Setup", icon: Server },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as "ARCHITECTURE" | "POLICY" | "RUNBOOK" | "QA" | "DEPLOYMENT")}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                isActive
                  ? "bg-[#FF7A00]/10 text-[#FF7A00] border border-[#FF7A00]/30"
                  : "bg-zinc-900/60 text-zinc-400 border border-zinc-800 hover:text-zinc-200 hover:bg-zinc-800"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content: Architecture */}
      {activeTab === "ARCHITECTURE" && (
        <div className="space-y-6">
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-[#FF7A00]" />
                System Topology &amp; Database Architecture
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-zinc-300 leading-relaxed">
              <p>
                Creator Studio AI is built as a fully decoupled, multi-tier autonomous video production platform.
                The frontend is built on Next.js 15.1.0 (React 19) and static HTML export. The backend is powered by
                FastAPI 0.115 with SQLAlchemy 2.0 Async, managing 52 tables across 10 functional domains.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800">
                  <div className="text-xs font-bold uppercase tracking-wider text-[#FF7A00]">52 Tables</div>
                  <p className="text-xs text-zinc-400 mt-1">
                    Channel management, projects, scripts, claims, voice tracks, storyboards, media assets, renders, thumbnails, and QA runs.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800">
                  <div className="text-xs font-bold uppercase tracking-wider text-[#FF7A00]">SKIP LOCKED Queue</div>
                  <p className="text-xs text-zinc-400 mt-1">
                    Zero-loss durable background queue running natively inside PostgreSQL. Prevents worker double-processing without Redis.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800">
                  <div className="text-xs font-bold uppercase tracking-wider text-[#FF7A00]">$0.00 Spend Governor</div>
                  <p className="text-xs text-zinc-400 mt-1">
                    Hard circuit breaker embedded into middleware and provider factories, guaranteeing zero unwanted cloud API expenditures.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Content: Policy */}
      {activeTab === "POLICY" && (
        <div className="space-y-6">
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                YouTube Partner Program &amp; Synthetic Media Guidelines
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-zinc-300 leading-relaxed">
              <p>
                To maintain 100% compliance with YouTube monetization rules, Creator Studio AI automatically adheres to:
              </p>
              <ul className="list-disc pl-5 space-y-2 text-xs text-zinc-400">
                <li>
                  <strong className="text-white">Altered or Synthetic Content Disclosure:</strong> Every published video includes the mandatory disclosure flag in metadata: <code className="bg-zinc-950 px-1 py-0.5 rounded text-amber-300">hasCustomThumbnail: true, containsSyntheticMedia: true</code>.
                </li>
                <li>
                  <strong className="text-white">Commercial Asset Licensing:</strong> All media items must carry verified commercial licenses (CC0, Pexels Free Commercial, or User-Uploaded).
                </li>
                <li>
                  <strong className="text-white">Human-in-the-Loop Veto Gate:</strong> Videos cannot be automatically uploaded to public visibility without satisfying the 14-Point Deterministic QA evaluation.
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Content: Runbook */}
      {activeTab === "RUNBOOK" && (
        <div className="space-y-6">
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-[#FF7A00]" />
                Local Operator Commands (Windows PowerShell)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  id: "cmd1",
                  title: "Start Backend Server (FastAPI on Port 8000)",
                  cmd: "powershell -File .\\scripts\\start-backend.ps1",
                },
                {
                  id: "cmd2",
                  title: "Start Persistent Queue Worker Daemon",
                  cmd: "powershell -File .\\scripts\\start-worker.ps1",
                },
                {
                  id: "cmd3",
                  title: "Run Monorepo Test Runner (Pytest & Frontend Check)",
                  cmd: "powershell -File .\\scripts\\test.ps1",
                },
                {
                  id: "cmd4",
                  title: "Frontend Development Server (Next.js)",
                  cmd: "npm --prefix frontend run dev",
                },
              ].map((c) => (
                <div key={c.id} className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-semibold text-zinc-300">{c.title}</div>
                    <code className="text-xs font-mono text-[#FF7A00] block mt-1">{c.cmd}</code>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-zinc-800 text-zinc-400 hover:text-white shrink-0 text-xs"
                    onClick={() => copyToClipboard(c.cmd, c.id)}
                  >
                    {copiedCmd === c.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400 mr-1" />
                    ) : (
                      <Copy className="w-3.5 h-3.5 mr-1" />
                    )}
                    {copiedCmd === c.id ? "Copied" : "Copy"}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Content: QA */}
      {activeTab === "QA" && (
        <div className="space-y-6">
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                14-Point Deterministic Quality Assurance Categories
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {[
                  { cat: "FACTUAL_ACCURACY (15%)", desc: "100% of factual statements cross-referenced with citation URLs." },
                  { cat: "VIDEO_TECHNICAL (15%)", desc: "1080p 60fps compliance, zero black frames, faststart atom verified." },
                  { cat: "NARRATION_AUDIO (10%)", desc: "Integrated loudness at -14.0 LUFS ±1.0, zero digital clipping." },
                  { cat: "VISUAL_ASSETS (10%)", desc: "Aspect ratio consistency (16:9 or 9:16), no watermarked stock." },
                  { cat: "SCRIPT_QUALITY (10%)", desc: "Hook engagement within 5 seconds, structured section flow." },
                  { cat: "PACKAGE_COMPLETENESS (10%)", desc: "Video, thumbnail, title, description, and tags present." },
                  { cat: "THUMBNAIL_QUALITY (5%)", desc: "Exact 1280x720 composition, readable mobile typography." },
                  { cat: "METADATA_SEO (5%)", desc: "Target keyword density, structured chapter timestamps." },
                  { cat: "COPYRIGHT_LICENSING (5%)", desc: "Valid commercial licenses for all embedded visual assets." },
                  { cat: "CAPTION_INTEGRITY (5%)", desc: "Word-level timestamp synchronization with audio narration." },
                ].map((item, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-zinc-950/60 border border-zinc-800">
                    <span className="font-bold text-[#FF7A00] block">{item.cat}</span>
                    <span className="text-zinc-400 mt-1 block">{item.desc}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Content: Deployment */}
      {activeTab === "DEPLOYMENT" && (
        <div className="space-y-6">
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Server className="w-5 h-5 text-[#FF7A00]" />
                Zero-Cost Staging Deployment Architecture
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-zinc-300 leading-relaxed">
              <p>
                Creator Studio AI runs on a strictly enforced <strong>$0.00/month</strong> hosting budget using:
              </p>
              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <strong className="text-white block">Frontend: GitHub Pages</strong>
                  <span className="text-zinc-400">Next.js 15 static export deployed to github.io via GitHub Actions.</span>
                </div>
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <strong className="text-white block">Database: Supabase Free Tier</strong>
                  <span className="text-zinc-400">PostgreSQL 15 with 500MB storage, connection pooling, and SSL encryption.</span>
                </div>
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <strong className="text-white block">Backend: Local-First FastAPI Host</strong>
                  <span className="text-zinc-400">FastAPI server running with Uvicorn on localhost:8000, connected to Supabase PostgreSQL.</span>
                </div>
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                  <strong className="text-white block">Task Workers: Persistent Local Daemons</strong>
                  <span className="text-zinc-400">Durable queue processor continuously pulling jobs from PostgreSQL with FOR UPDATE SKIP LOCKED.</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
