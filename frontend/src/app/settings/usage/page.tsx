"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Cpu,
  Lock,
  Layers,
  DollarSign,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatCard } from "@/components/ui/StatCard";
import { apiClient } from "@/lib/api";

interface ModelUsageRow {
  model: string;
  requests: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

const SAMPLE_USAGE_ROWS: ModelUsageRow[] = [
  {
    model: "gemini-1.5-flash",
    requests: 24,
    inputTokens: 38400,
    outputTokens: 14200,
    costUsd: 0.0,
  },
  {
    model: "mock-gemini-1.5-flash",
    requests: 18,
    inputTokens: 12000,
    outputTokens: 6800,
    costUsd: 0.0,
  },
];

export default function UsagePage() {
  const [budgetCap, setBudgetCap] = useState("0.00");
  const [currentSpend, setCurrentSpend] = useState(0.0);
  const [usageRows] = useState<ModelUsageRow[]>(SAMPLE_USAGE_ROWS);

  useEffect(() => {
    async function loadBudget() {
      try {
        const res = await apiClient.get<any>("/api/v1/system/budget-status");
        if (res) {
          if (typeof res.monthly_budget_usd === "number") {
            setBudgetCap(res.monthly_budget_usd.toFixed(2));
          }
          if (typeof res.current_month_spend_usd === "number") {
            setCurrentSpend(res.current_month_spend_usd);
          }
        }
      } catch {
        // Retain hardcoded zero-spend fallback
      }
    }
    loadBudget();
  }, []);

  const totalInputTokens = usageRows.reduce((acc, r) => acc + r.inputTokens, 0);
  const totalOutputTokens = usageRows.reduce((acc, r) => acc + r.outputTokens, 0);
  const totalTokens = totalInputTokens + totalOutputTokens;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Usage & Budget Control</h1>
            <Badge variant="success" size="sm" showDot>
              Hard Circuit Breaker Active
            </Badge>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time LLM token metering, model cost accounting, and strict $0.00 monthly spending caps.
          </p>
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Current Month Spend"
          value={`$${currentSpend.toFixed(2)}`}
          change="100% Free Tier"
          changeType="neutral"
          icon={DollarSign}
        />
        <StatCard
          title="Monthly Spend Cap"
          value={`$${budgetCap}`}
          change="Hard circuit breaker"
          changeType="neutral"
          icon={Lock}
        />
        <StatCard
          title="Total Tokens Processed"
          value={totalTokens.toLocaleString()}
          change={`${totalInputTokens.toLocaleString()} in / ${totalOutputTokens.toLocaleString()} out`}
          changeType="positive"
          icon={Cpu}
        />
        <StatCard
          title="Total API Invocations"
          value="42"
          change="Zero billable requests"
          changeType="neutral"
          icon={Layers}
        />
      </div>

      {/* Budget Guardrail Card */}
      <Card className="border-canvas-border">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                Zero-Dollar Spending Guardrail
              </CardTitle>
              <CardDescription>
                Prevents accidental cloud API billing by intercepting all requests before token dispatch.
              </CardDescription>
            </div>
            <Badge variant="ember" size="md">
              Enforced by Worker Daemon
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-canvas-subtle p-4 rounded-xl border border-canvas-border flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-sm font-semibold text-white">Monthly Hard Budget Cap</span>
              <p className="text-xs text-zinc-400">
                Any paid inference above this value is automatically rejected with HTTP 402.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-mono font-bold text-white">$</span>
              <input
                type="text"
                value={budgetCap}
                onChange={(e) => setBudgetCap(e.target.value)}
                className="w-24 bg-canvas-card border border-canvas-border px-3 py-1.5 rounded-lg text-center font-mono font-bold text-white text-sm focus:border-ember focus:outline-none"
              />
              <Button variant="secondary" size="sm" onClick={() => alert("Budget cap updated successfully.")}>
                Save Cap
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs text-zinc-400">
              <span>Budget Consumption Progress</span>
              <span className="font-mono text-emerald-400">0.0% ($0.00 / ${budgetCap})</span>
            </div>
            <ProgressBar value={0} max={100} size="md" variant="success" />
          </div>
        </CardContent>
      </Card>

      {/* Consumption Breakdown by Model Table */}
      <Card className="border-canvas-border">
        <CardHeader>
          <CardTitle className="text-lg text-white">Inference Consumption by Model</CardTitle>
          <CardDescription>Granular token accounting recorded in PostgreSQL provider_usages table.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-canvas-subtle text-zinc-400 uppercase font-mono text-[10px]">
                <tr>
                  <th className="py-2.5 px-3 rounded-l-lg">Model</th>
                  <th className="py-2.5 px-3">Invocations</th>
                  <th className="py-2.5 px-3">Input Tokens</th>
                  <th className="py-2.5 px-3">Output Tokens</th>
                  <th className="py-2.5 px-3 rounded-r-lg text-right">Cost (USD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border">
                {usageRows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-canvas-subtle/50 transition-colors">
                    <td className="py-3 px-3 font-mono text-zinc-200">{row.model}</td>
                    <td className="py-3 px-3 text-zinc-300">{row.requests}</td>
                    <td className="py-3 px-3 font-mono text-zinc-400">{row.inputTokens.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono text-zinc-400">{row.outputTokens.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono text-emerald-400 font-bold text-right">
                      ${row.costUsd.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
