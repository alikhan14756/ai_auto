"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
  Lock,
  Unlock,
  RotateCw,
  Clock,
  FileText,
  Save,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";
import { ProgressBar } from "@/components/ui/ProgressBar";

interface Section {
  section_id: string;
  order: number;
  title: string;
  narration: string;
  visual_directive: string;
  duration_sec: number;
}

interface Claim {
  id: string;
  text: string;
  entity: string;
  type: string;
  is_verified: boolean;
  confidence: number;
  citation_url?: string;
  citation_snippet?: string;
}

const INITIAL_SECTIONS: Section[] = [
  {
    section_id: "sec_01",
    order: 1,
    title: "1. The Hidden Bottleneck in Background Queues",
    narration:
      "Most software engineers believe that the moment their app needs background workers, they must immediately deploy Redis, Celery, or RabbitMQ. But what if the single PostgreSQL database you already run can handle 5,000 jobs per second with guaranteed transactional safety and zero data drift?",
    visual_directive:
      "Screen capture comparing complex multi-service cloud architecture against clean single-database topology.",
    duration_sec: 65,
  },
  {
    section_id: "sec_02",
    order: 2,
    title: "2. The Magic of SELECT FOR UPDATE SKIP LOCKED",
    narration:
      "PostgreSQL 9.5 introduced the SKIP LOCKED clause. When a background worker transaction requests pending rows with SELECT ... FOR UPDATE SKIP LOCKED, PostgreSQL automatically bypasses rows currently locked by other workers without blocking or waiting.",
    visual_directive:
      "Code editor typing terminal query with keyword highlighting on FOR UPDATE SKIP LOCKED.",
    duration_sec: 90,
  },
  {
    section_id: "sec_03",
    order: 3,
    title: "3. Benchmarks & Crash Recovery Architecture",
    narration:
      "Unlike Redis, where an unexpected worker crash can cause silent job loss unless complex two-phase commits are implemented, PostgreSQL maintains ACID guarantees. If your worker process dies midway through task execution, the transaction rolls back immediately and the job is returned to the queue.",
    visual_directive:
      "Terminal benchmark graph showing 5,000 jobs/sec throughput with crash fault injection.",
    duration_sec: 95,
  },
  {
    section_id: "sec_04",
    order: 4,
    title: "4. Conclusion & Production Checklist",
    narration:
      "Consolidating your queue directly inside PostgreSQL eliminates operational overhead, cuts AWS bills, and gives you relational auditability out of the box. Star the open-source repository linked below to clone the production starter kit.",
    visual_directive:
      "GitHub repository release page with star button animation and subscribe badge.",
    duration_sec: 60,
  },
];

const INITIAL_CLAIMS: Claim[] = [
  {
    id: "cl-1",
    text: "PostgreSQL 9.5 introduced the SKIP LOCKED clause for non-blocking row acquisition.",
    entity: "PostgreSQL 9.5",
    type: "RELEASE_DATE",
    is_verified: true,
    confidence: 0.98,
    citation_url: "https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE",
    citation_snippet:
      "With SKIP LOCKED, any selected rows that cannot be immediately locked are skipped rather than causing the transaction to block.",
  },
  {
    id: "cl-2",
    text: "PostgreSQL handles up to 5,000 job dispatches per second on modest cloud instances.",
    entity: "PostgreSQL Queue",
    type: "BENCHMARK",
    is_verified: true,
    confidence: 0.94,
    citation_url: "https://brandur.org/postgres-queues",
    citation_snippet:
      "Empirical benchmark data demonstrating 5,000 processed jobs/sec on 4-vCPU database instances.",
  },
  {
    id: "cl-3",
    text: "Redis queue workers require manual two-phase locks to avoid silent job loss on worker death.",
    entity: "Redis Queue",
    type: "FEATURE",
    is_verified: false,
    confidence: 0.65,
    citation_url: undefined,
    citation_snippet:
      "Relying on Redis RPOPLPUSH provides delivery guarantees, but lacks ACID multi-table rollback.",
  },
];

export default function ScriptStudioPage() {
  const [sections, setSections] = useState<Section[]>(INITIAL_SECTIONS);
  const [claims] = useState<Claim[]>(INITIAL_CLAIMS);
  const [isLocked, setIsLocked] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"FACT_CHECK" | "QUALITY">("FACT_CHECK");
  const [format, setFormat] = useState<"LONG_FORM" | "SHORTS">("LONG_FORM");

  const totalWords = sections.reduce(
    (acc, s) => acc + s.narration.split(/\s+/).filter(Boolean).length,
    0
  );
  const totalDurationSeconds = sections.reduce((acc, s) => acc + s.duration_sec, 0);
  const verifiedCount = claims.filter((c) => c.is_verified).length;
  const unverifiedCount = claims.length - verifiedCount;

  const handleUpdateNarration = (id: string, text: string) => {
    if (isLocked) return;
    setSections((prev) =>
      prev.map((s) => (s.section_id === id ? { ...s, narration: text } : s))
    );
    setIsSaved(false);
  };

  const handleRegenerateSection = async (id: string) => {
    if (isLocked) return;
    setSections((prev) =>
      prev.map((s) =>
        s.section_id === id
          ? {
              ...s,
              narration:
                s.narration +
                " [Updated]: Practical benchmark code demonstrates that indexed status lookups run in under 0.2 milliseconds.",
            }
          : s
      )
    );
  };

  const handleSaveDraft = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2500);
  };

  const handleGenerateScript = async () => {
    setIsGenerating(true);
    await new Promise((r) => setTimeout(r, 1200));
    setIsGenerating(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Script Studio & Fact-Checking Matrix
            </h1>
            <Badge variant={isLocked ? "success" : "ember"} size="sm" showDot>
              {isLocked ? "Script Approved & Locked" : "Draft v1"}
            </Badge>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Structured scene-partitioned video scripts with citation-backed factual verification.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as "LONG_FORM" | "SHORTS")}
            className="bg-canvas-card border border-canvas-border text-xs text-zinc-300 rounded-lg px-2.5 py-1.5 focus:border-ember focus:outline-none"
          >
            <option value="LONG_FORM">Long-Form (6-10 min)</option>
            <option value="SHORTS">Shorts (30-60 sec)</option>
          </select>

          <Button
            variant="outline"
            size="sm"
            onClick={handleSaveDraft}
            className="flex items-center gap-1.5"
          >
            {isSaved ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {isSaved ? "Saved" : "Save Draft"}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleGenerateScript}
            disabled={isGenerating || isLocked}
            className="flex items-center gap-1.5 shadow-lg shadow-ember/20"
          >
            <Sparkles className={`w-4 h-4 ${isGenerating ? "animate-spin" : ""}`} />
            {isGenerating ? "Synthesizing Script..." : "Generate Script"}
          </Button>

          <Button
            variant={isLocked ? "outline" : "secondary"}
            size="sm"
            onClick={() => setIsLocked(!isLocked)}
            className="flex items-center gap-1.5 border-emerald-500/40 text-emerald-400"
          >
            {isLocked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
            {isLocked ? "Unlock Script" : "Approve & Lock"}
          </Button>
        </div>
      </div>

      {/* Top Stat Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Word Count"
          value={totalWords}
          change="~140 WPM pace"
          changeType="positive"
          icon={FileText}
        />
        <StatCard
          title="Estimated Duration"
          value={`${Math.floor(totalDurationSeconds / 60)}m ${totalDurationSeconds % 60}s`}
          change="Within target range"
          changeType="positive"
          icon={Clock}
        />
        <StatCard
          title="Verified Claims"
          value={`${verifiedCount} / ${claims.length}`}
          change={unverifiedCount === 0 ? "100% verified" : `${unverifiedCount} unverified`}
          changeType={unverifiedCount === 0 ? "positive" : "neutral"}
          icon={ShieldCheck}
        />
        <StatCard
          title="Script Quality Score"
          value="92.5"
          change="High retention grade"
          changeType="positive"
          icon={Sparkles}
        />
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Scene-by-Scene Script Editor */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Scene Narrative Breakdown</h2>
            <span className="text-xs text-zinc-400">
              {sections.length} Narrative Scenes
            </span>
          </div>

          {sections.map((sec) => (
            <Card key={sec.section_id} className="border-canvas-border hover:border-zinc-700 transition-colors">
              <CardHeader className="py-3 px-4 border-b border-canvas-border/50 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-white">
                  {sec.title}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="neutral" size="sm" className="font-mono text-[11px]">
                    {sec.duration_sec}s
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={isLocked}
                    onClick={() => handleRegenerateSection(sec.section_id)}
                    className="h-7 text-xs text-zinc-400 hover:text-ember px-2"
                  >
                    <RotateCw className="w-3 h-3 mr-1" /> Regenerate
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
                    Spoken Voiceover Text
                  </label>
                  <textarea
                    rows={3}
                    disabled={isLocked}
                    value={sec.narration}
                    onChange={(e) => handleUpdateNarration(sec.section_id, e.target.value)}
                    className="w-full bg-canvas-subtle border border-canvas-border rounded-lg p-2.5 text-xs text-zinc-200 leading-relaxed focus:border-ember focus:outline-none disabled:opacity-75"
                  />
                </div>

                <div className="bg-canvas-card border border-canvas-border/60 p-2.5 rounded-lg flex items-start gap-2 text-xs">
                  <span className="font-semibold text-ember text-[11px] uppercase tracking-wider flex-shrink-0">
                    Visual Cue:
                  </span>
                  <p className="text-zinc-400 text-[11px] leading-relaxed">
                    {sec.visual_directive}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Right 1 Col: Fact-Checking & Quality Matrix */}
        <div className="space-y-4">
          <div className="flex items-center gap-1 bg-canvas-card border border-canvas-border p-1 rounded-xl">
            <button
              onClick={() => setActiveTab("FACT_CHECK")}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === "FACT_CHECK"
                  ? "bg-ember text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Fact-Checking Matrix
            </button>
            <button
              onClick={() => setActiveTab("QUALITY")}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === "QUALITY"
                  ? "bg-ember text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Quality Evaluation
            </button>
          </div>

          {activeTab === "FACT_CHECK" && (
            <div className="space-y-3">
              <div className="text-xs text-zinc-400 flex items-center justify-between">
                <span>Extracted Factual Claims</span>
                <span className="font-mono text-emerald-400">{verifiedCount} Verified</span>
              </div>

              {claims.map((claim) => (
                <Card
                  key={claim.id}
                  className={`border text-xs ${
                    claim.is_verified
                      ? "border-emerald-500/30 bg-emerald-950/5"
                      : "border-amber-500/30 bg-amber-950/5"
                  }`}
                >
                  <CardContent className="p-3.5 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <Badge
                        variant={claim.is_verified ? "success" : "warning"}
                        size="sm"
                        className="text-[10px] uppercase font-mono"
                      >
                        {claim.is_verified ? (
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Verified
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> Unverified
                          </span>
                        )}
                      </Badge>
                      <Badge variant="neutral" size="sm" className="text-[10px]">
                        {claim.type}
                      </Badge>
                    </div>

                    <p className="text-zinc-200 font-medium leading-snug">
                      &ldquo;{claim.text}&rdquo;
                    </p>

                    {claim.citation_url && (
                      <div className="pt-1.5 border-t border-canvas-border/50 text-[11px] space-y-1">
                        <a
                          href={claim.citation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:underline flex items-center gap-1 truncate font-mono text-[10px]"
                        >
                          {claim.citation_url}
                          <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                        </a>
                        {claim.citation_snippet && (
                          <p className="text-zinc-400 italic text-[11px] leading-relaxed">
                            {claim.citation_snippet}
                          </p>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {activeTab === "QUALITY" && (
            <Card className="border-canvas-border">
              <CardHeader className="p-4 border-b border-canvas-border/50">
                <CardTitle className="text-sm font-semibold text-white">
                  Audience Retention & Quality
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-4 text-xs">
                <div className="space-y-1">
                  <div className="flex justify-between text-zinc-300">
                    <span>Hook Strength (First 5s)</span>
                    <span className="font-mono text-emerald-400">92%</span>
                  </div>
                  <ProgressBar value={92} max={100} size="sm" variant="success" />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-zinc-300">
                    <span>Clarity & Readability</span>
                    <span className="font-mono text-emerald-400">95%</span>
                  </div>
                  <ProgressBar value={95} max={100} size="sm" variant="success" />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-zinc-300">
                    <span>Evidence Coverage</span>
                    <span className="font-mono text-amber-400">67%</span>
                  </div>
                  <ProgressBar value={67} max={100} size="sm" variant="warning" />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-zinc-300">
                    <span>Repetition Index</span>
                    <span className="font-mono text-emerald-400">0.0%</span>
                  </div>
                  <ProgressBar value={0} max={100} size="sm" variant="success" />
                </div>

                <div className="pt-2 border-t border-canvas-border text-[11px] text-zinc-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Historical Similarity:</span>
                    <span className="font-mono text-emerald-400">&lt; 4% (Unique)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Target Narrative Arc:</span>
                    <span className="text-zinc-200">5-Part Technical Architecture</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
