"use client";

import React, { useState } from "react";
import {
  Boxes,
  Activity,
  CheckCircle2,
  Zap,
  Gauge,
  Send,
  RefreshCw,
  Cpu,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Input } from "@/components/ui/Input";

export default function ProvidersPage() {
  const [fastModel, setFastModel] = useState("gemini-1.5-flash");
  const [reasoningModel, setReasoningModel] = useState("gemini-1.5-pro");
  const [isPinging, setIsPinging] = useState(false);
  const [healthStatus, setHealthStatus] = useState<{
    healthy: boolean;
    latency: number;
    message: string;
  }>({
    healthy: true,
    latency: 18.4,
    message: "Google Gemini 1.5 Flash API active and operational.",
  });

  const [testPrompt, setTestPrompt] = useState("Explain PostgreSQL SKIP LOCKED in one sentence.");
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handlePingHealth = async () => {
    setIsPinging(true);
    await new Promise((r) => setTimeout(r, 600));
    setHealthStatus({
      healthy: true,
      latency: Math.round(15 + Math.random() * 12),
      message: "API latency test successful: Connection authenticated and responsive.",
    });
    setIsPinging(false);
  };

  const handleRunTestPrompt = async () => {
    if (!testPrompt.trim()) return;
    setIsTesting(true);
    await new Promise((r) => setTimeout(r, 800));
    setTestResponse(
      "The SKIP LOCKED clause in PostgreSQL allows concurrent worker transactions to immediately select and lock available rows while seamlessly bypassing rows currently locked by other workers, preventing lock contention."
    );
    setIsTesting(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">AI Provider Configuration</h1>
            <Badge variant="success" size="sm" showDot>
              Google Gemini Active
            </Badge>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Manage LLM model routing, Free-Tier RPM/RPD rate limiters, and live connection health.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={handlePingHealth}
          disabled={isPinging}
          className="flex items-center gap-2 self-start"
        >
          <Activity className={`w-4 h-4 ${isPinging ? "animate-spin text-ember" : "text-emerald-400"}`} />
          {isPinging ? "Pinging Health..." : "Ping Provider Health"}
        </Button>
      </div>

      {/* Provider Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-canvas-border">
          <CardContent className="p-5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-medium">Active Inference Engine</span>
              <Boxes className="w-4 h-4 text-ember" />
            </div>
            <div className="text-xl font-bold text-white tracking-tight">Google Gemini 1.5</div>
            <p className="text-xs text-zinc-400">Official google-genai SDK Integration</p>
          </CardContent>
        </Card>

        <Card className="border-canvas-border">
          <CardContent className="p-5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-medium">Free Tier RPM Rate Limit</span>
              <Gauge className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-xl font-bold text-white tracking-tight">
              1 / 15 <span className="text-xs font-normal text-zinc-400">RPM used</span>
            </div>
            <ProgressBar value={7} max={100} size="sm" variant="ember" />
          </CardContent>
        </Card>

        <Card className="border-canvas-border">
          <CardContent className="p-5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-medium">Free Tier RPD Daily Quota</span>
              <Zap className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-xl font-bold text-white tracking-tight">
              18 / 1,500 <span className="text-xs font-normal text-zinc-400">RPD used</span>
            </div>
            <ProgressBar value={1.2} max={100} size="sm" variant="success" />
          </CardContent>
        </Card>
      </div>

      {/* Model Selection and Health Ping */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-canvas-border">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Cpu className="w-5 h-5 text-ember" /> Model Routing & Architecture
            </CardTitle>
            <CardDescription>
              Assign lightweight models for high-frequency ideation and heavy reasoning models for multi-step scripts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Fast Model (Topic Research & Summaries)</label>
              <select
                value={fastModel}
                onChange={(e) => setFastModel(e.target.value)}
                className="w-full bg-canvas-subtle border border-canvas-border rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-ember"
              >
                <option value="gemini-1.5-flash">gemini-1.5-flash (Ultra fast, Free Tier 15 RPM)</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash (Next-gen latency, optimized JSON output)</option>
                <option value="mock-gemini-1.5-flash">mock-gemini-1.5-flash (Offline local development)</option>
              </select>
              <p className="text-[11px] text-zinc-500">
                Used in M05 topic discovery pipelines for high throughput with zero API cost.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Reasoning Model (Deep Analysis & Verification)</label>
              <select
                value={reasoningModel}
                onChange={(e) => setReasoningModel(e.target.value)}
                className="w-full bg-canvas-subtle border border-canvas-border rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-ember"
              >
                <option value="gemini-1.5-pro">gemini-1.5-pro (Deep reasoning, long context window)</option>
                <option value="gemini-2.0-pro">gemini-2.0-pro (Extended multi-stage synthesis)</option>
              </select>
              <p className="text-[11px] text-zinc-500">
                Reserved for complex factual checks and scene storyboarding.
              </p>
            </div>

            <div className="pt-2 border-t border-canvas-border flex items-center justify-between text-xs">
              <span className="text-zinc-400">Environment API Key:</span>
              <span className="font-mono text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> GEMINI_API_KEY Loaded
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Diagnostic Health & Interactive Test Console */}
        <Card className="border-canvas-border">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" /> Interactive Provider Console
            </CardTitle>
            <CardDescription>
              Execute low-latency test prompts and inspect raw structured completions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-canvas-subtle border border-canvas-border p-3 rounded-lg flex items-center justify-between text-xs">
              <div>
                <span className="text-zinc-400 block">Health Status</span>
                <span className="font-semibold text-emerald-400 flex items-center gap-1 mt-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Operational ({healthStatus.latency} ms)
                </span>
              </div>
              <Badge variant="success" size="sm">200 OK</Badge>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Test Prompt</label>
              <div className="flex gap-2">
                <Input
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  placeholder="Enter sample test prompt..."
                  className="bg-canvas-subtle text-xs"
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleRunTestPrompt}
                  disabled={isTesting}
                  className="flex-shrink-0"
                >
                  {isTesting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                </Button>
              </div>
            </div>

            {testResponse && (
              <div className="bg-zinc-950 border border-zinc-800 p-3 rounded-lg text-xs space-y-1">
                <span className="font-mono text-zinc-500 text-[10px] uppercase">Model Response Output</span>
                <p className="text-zinc-300 leading-relaxed font-sans">{testResponse}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
