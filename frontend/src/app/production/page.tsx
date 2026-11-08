"use client";

import * as React from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Lock,
  Unlock,
  Layers,
  Sparkles,
  Check,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

interface CategoryScore {
  category: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  passed_count: number;
  warning_count: number;
  failed_count: number;
}

interface Finding {
  id: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "ACCEPTED_WITH_EXCEPTION";
  affected_artifact: string;
  title: string;
  explanation: string;
  evidence: Record<string, unknown>;
  recommended_correction: string;
  requires_human_review: boolean;
  resolution_notes?: string;
  exception_reason?: string;
}

const INITIAL_CATEGORIES: CategoryScore[] = [
  { category: "FACTUAL_ACCURACY", weight: 0.15, raw_score: 95.0, weighted_score: 14.25, passed_count: 4, warning_count: 1, failed_count: 0 },
  { category: "VIDEO_TECHNICAL", weight: 0.15, raw_score: 100.0, weighted_score: 15.0, passed_count: 5, warning_count: 0, failed_count: 0 },
  { category: "NARRATION_AUDIO", weight: 0.10, raw_score: 98.0, weighted_score: 9.8, passed_count: 3, warning_count: 1, failed_count: 0 },
  { category: "VISUAL_ASSETS", weight: 0.10, raw_score: 100.0, weighted_score: 10.0, passed_count: 6, warning_count: 0, failed_count: 0 },
  { category: "SCRIPT_QUALITY", weight: 0.10, raw_score: 94.0, weighted_score: 9.4, passed_count: 3, warning_count: 1, failed_count: 0 },
  { category: "PACKAGE_COMPLETENESS", weight: 0.10, raw_score: 100.0, weighted_score: 10.0, passed_count: 4, warning_count: 0, failed_count: 0 },
  { category: "THUMBNAIL_QUALITY", weight: 0.05, raw_score: 100.0, weighted_score: 5.0, passed_count: 3, warning_count: 0, failed_count: 0 },
  { category: "METADATA_SEO", weight: 0.05, raw_score: 92.0, weighted_score: 4.6, passed_count: 4, warning_count: 1, failed_count: 0 },
  { category: "COPYRIGHT_LICENSING", weight: 0.05, raw_score: 100.0, weighted_score: 5.0, passed_count: 4, warning_count: 0, failed_count: 0 },
  { category: "CAPTION_INTEGRITY", weight: 0.05, raw_score: 100.0, weighted_score: 5.0, passed_count: 2, warning_count: 0, failed_count: 0 },
  { category: "SECURITY_PRIVACY", weight: 0.05, raw_score: 100.0, weighted_score: 5.0, passed_count: 1, warning_count: 0, failed_count: 0 },
  { category: "YOUTUBE_POLICY", weight: 0.05, raw_score: 100.0, weighted_score: 5.0, passed_count: 2, warning_count: 0, failed_count: 0 },
];

const INITIAL_FINDINGS: Finding[] = [
  {
    id: "find-1",
    category: "FACTUAL_ACCURACY",
    severity: "MEDIUM",
    status: "OPEN",
    affected_artifact: "script_claim",
    title: "Citation Confidence Metric (0.68 < 0.70)",
    explanation: "Claim regarding PostgreSQL horizontal write scaling has single-source citation with moderate confidence.",
    evidence: { claim_text: "PostgreSQL scaling benchmark", confidence: 0.68 },
    recommended_correction: "Cross-reference with second independent source or official PostgreSQL manual.",
    requires_human_review: false,
  },
  {
    id: "find-2",
    category: "NARRATION_AUDIO",
    severity: "LOW",
    status: "OPEN",
    affected_artifact: "narration_track",
    title: "Minor Silence Interval (1.1s at Scene 4 Transition)",
    explanation: "Detected pause between scene 4 and scene 5 is 1.1s. Within 1.5s tolerance, but slightly slow pacing.",
    evidence: { silence_duration_s: 1.1, timestamp: "03:42" },
    recommended_correction: "Trim transition dead-air to under 0.6s for snappier narrative delivery.",
    requires_human_review: false,
  },
  {
    id: "find-3",
    category: "METADATA_SEO",
    severity: "LOW",
    status: "RESOLVED",
    affected_artifact: "tags",
    title: "Tags Count Approaching Character Ceiling",
    explanation: "Tags total 468 characters, within the 500 character ceiling.",
    evidence: { length: 468, max: 500 },
    recommended_correction: "Prune redundant tags.",
    requires_human_review: false,
    resolution_notes: "Removed 2 low-volume tags. Total characters reduced to 412.",
  },
];

export default function ProductionQACenter() {
  const [isRunningQA, setIsRunningQA] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState<"ALL" | "BLOCKERS" | "WARNINGS" | "RESOLVED">("ALL");
  const [findings, setFindings] = React.useState<Finding[]>(INITIAL_FINDINGS);
  const [categories] = React.useState<CategoryScore[]>(INITIAL_CATEGORIES);
  const [selectedFinding, setSelectedFinding] = React.useState<Finding | null>(null);
  const [resolveModalOpen, setResolveModalOpen] = React.useState(false);
  const [resolveNotes, setResolveNotes] = React.useState("");
  const [exceptionModalOpen, setExceptionModalOpen] = React.useState(false);
  const [exceptionReason, setExceptionReason] = React.useState("");

  // Calculate composite score
  const overallScore = Number(
    categories.reduce((acc, c) => acc + c.weighted_score, 0).toFixed(1)
  );

  // Veto Decision computation
  const hasCritical = findings.some(
    (f) => f.severity === "CRITICAL" && f.status !== "RESOLVED"
  );
  const hasUnexemptedHigh = findings.some(
    (f) => f.severity === "HIGH" && f.status === "OPEN"
  );
  const hasMedium = findings.some(
    (f) => f.severity === "MEDIUM" && f.status === "OPEN"
  );

  const vetoDecision: "BLOCKED" | "NEEDS_REVIEW" | "READY_FOR_APPROVAL" | "APPROVED" = React.useMemo(() => {
    if (hasCritical || hasUnexemptedHigh) {
      return "BLOCKED";
    }
    if (hasMedium) {
      return "NEEDS_REVIEW";
    }
    if (overallScore < 80.0) {
      return "BLOCKED";
    }
    if (overallScore < 95.0) {
      return "READY_FOR_APPROVAL";
    }
    return "APPROVED";
  }, [hasCritical, hasUnexemptedHigh, hasMedium, overallScore]);

  const canPublish = vetoDecision === "APPROVED" || vetoDecision === "READY_FOR_APPROVAL" || (vetoDecision === "NEEDS_REVIEW" && overallScore >= 75.0);

  const handleRerunQA = () => {
    setIsRunningQA(true);
    setTimeout(() => {
      setIsRunningQA(false);
    }, 1200);
  };

  const handleResolve = () => {
    if (!selectedFinding) return;
    setFindings((prev) =>
      prev.map((f) =>
        f.id === selectedFinding.id
          ? { ...f, status: "RESOLVED", resolution_notes: resolveNotes }
          : f
      )
    );
    setResolveModalOpen(false);
    setResolveNotes("");
    setSelectedFinding(null);
  };

  const handleAuthorizeException = () => {
    if (!selectedFinding) return;
    setFindings((prev) =>
      prev.map((f) =>
        f.id === selectedFinding.id
          ? { ...f, status: "ACCEPTED_WITH_EXCEPTION", exception_reason: exceptionReason }
          : f
      )
    );
    setExceptionModalOpen(false);
    setExceptionReason("");
    setSelectedFinding(null);
  };

  const filteredFindings = findings.filter((f) => {
    if (activeTab === "ALL") return true;
    if (activeTab === "BLOCKERS") return f.severity === "CRITICAL" || f.severity === "HIGH";
    if (activeTab === "WARNINGS") return f.severity === "MEDIUM" || f.severity === "LOW";
    if (activeTab === "RESOLVED") return f.status === "RESOLVED" || f.status === "ACCEPTED_WITH_EXCEPTION";
    return true;
  });

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#FF7A00]/10 border border-[#FF7A00]/20 text-[#FF7A00]">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
                  Autonomous Quality Assurance & Final Approval Veto Gate
                </h1>
                <Badge variant="outline" className="text-xs text-[#FF7A00] border-[#FF7A00]/30 font-mono">
                  M11 VETO GATE
                </Badge>
              </div>
              <p className="text-sm text-zinc-400 mt-1">
                Zero circular trust verification across 12 inspection categories before YouTube publication release.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            onClick={handleRerunQA}
            disabled={isRunningQA}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isRunningQA ? "animate-spin text-[#FF7A00]" : ""}`} />
            {isRunningQA ? "Auditing Containers..." : "Re-Run QA Inspection"}
          </Button>

          <Button
            className={`${
              canPublish
                ? "bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
                : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
            }`}
            disabled={!canPublish}
          >
            {canPublish ? <Unlock className="w-4 h-4 mr-2" /> : <Lock className="w-4 h-4 mr-2" />}
            {canPublish ? "Release Lock & Publish" : "Publication Vetoed"}
          </Button>
        </div>
      </div>

      {/* Veto Decision Hero Banner */}
      <div
        className={`p-6 rounded-2xl border transition-all ${
          vetoDecision === "APPROVED"
            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
            : vetoDecision === "READY_FOR_APPROVAL"
            ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
            : vetoDecision === "NEEDS_REVIEW"
            ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
            : "bg-red-500/10 border-red-500/30 text-red-300"
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={`p-3 rounded-xl ${
                vetoDecision === "APPROVED"
                  ? "bg-emerald-500/20 text-emerald-400"
                  : vetoDecision === "NEEDS_REVIEW"
                  ? "bg-amber-500/20 text-amber-400"
                  : "bg-red-500/20 text-red-400"
              }`}
            >
              {vetoDecision === "APPROVED" ? (
                <ShieldCheck className="w-8 h-8" />
              ) : vetoDecision === "NEEDS_REVIEW" ? (
                <AlertTriangle className="w-8 h-8" />
              ) : (
                <ShieldAlert className="w-8 h-8" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider opacity-80">
                  Publication Veto Status
                </span>
                <Badge
                  className={`font-bold ${
                    vetoDecision === "APPROVED"
                      ? "bg-emerald-500 text-black"
                      : vetoDecision === "NEEDS_REVIEW"
                      ? "bg-amber-500 text-black"
                      : "bg-red-500 text-white"
                  }`}
                >
                  {vetoDecision}
                </Badge>
              </div>
              <h2 className="text-xl font-bold mt-0.5">
                {vetoDecision === "APPROVED"
                  ? "Ready for Publication: All Quality & Policy Gates Satisfied"
                  : vetoDecision === "NEEDS_REVIEW"
                  ? "Review Required: Non-Blocking Warnings Flagged"
                  : "Publication Blocked: Unresolved Critical or High Defects"}
              </h2>
              <p className="text-sm opacity-90 mt-1">
                {vetoDecision === "APPROVED"
                  ? "Deterministic checks confirm valid MP4 container, -14 LUFS loudness, 1280x720 thumbnail, and zero secret leaks."
                  : vetoDecision === "NEEDS_REVIEW"
                  ? "Quality score exceeds 75.0 minimum, but creator review of advisory items is recommended."
                  : "Hard veto is active. Critical findings (secret leaks, black frame glitches, corrupt media) cannot be bypassed."}
              </p>
            </div>
          </div>

          <div className="flex md:flex-col items-center md:items-end justify-between border-t md:border-t-0 md:border-l border-zinc-800/80 pt-3 md:pt-0 md:pl-6">
            <span className="text-xs text-zinc-400 font-mono">Weighted Quality Score</span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-4xl font-extrabold text-zinc-100 font-mono">{overallScore}</span>
              <span className="text-sm text-zinc-500 font-mono">/ 100.0</span>
            </div>
            <span className="text-xs text-emerald-400 font-medium mt-1">Threshold: 80.0</span>
          </div>
        </div>
      </div>

      {/* 12-Category Score Matrix */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-[#FF7A00]" />
            <h3 className="text-lg font-semibold text-zinc-200">12 Independent Inspection Categories</h3>
          </div>
          <span className="text-xs text-zinc-500 font-mono">Weights sum to 100%</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {categories.map((cat) => {
            const isPerfect = cat.raw_score >= 95;
            const hasIssue = cat.failed_count > 0;
            return (
              <Card key={cat.category} className="bg-zinc-900/60 border-zinc-800 hover:border-zinc-700 transition-all">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-zinc-300 font-mono">
                          {cat.category.replace(/_/g, " ")}
                        </span>
                      </div>
                      <span className="text-[11px] text-zinc-500 font-mono">
                        Weight: {Math.round(cat.weight * 100)}%
                      </span>
                    </div>
                    <Badge
                      variant="outline"
                      className={`font-mono text-xs ${
                        isPerfect
                          ? "text-emerald-400 border-emerald-500/30"
                          : hasIssue
                          ? "text-red-400 border-red-500/30"
                          : "text-amber-400 border-amber-500/30"
                      }`}
                    >
                      {cat.raw_score.toFixed(0)}%
                    </Badge>
                  </div>

                  <div className="mt-3">
                    <ProgressBar
                      value={cat.raw_score}
                      variant={isPerfect ? "success" : hasIssue ? "warning" : "ember"}
                      showPercentage={false}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-zinc-400 mt-2 font-mono">
                    <span className="flex items-center gap-1 text-emerald-400">
                      <Check className="w-3 h-3" /> {cat.passed_count} passed
                    </span>
                    {cat.warning_count > 0 && (
                      <span className="flex items-center gap-1 text-amber-400">
                        <AlertTriangle className="w-3 h-3" /> {cat.warning_count} warn
                      </span>
                    )}
                    {cat.failed_count > 0 && (
                      <span className="flex items-center gap-1 text-red-400">
                        <XCircle className="w-3 h-3" /> {cat.failed_count} fail
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Findings & Remediation Center */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#FF7A00]" />
            <h3 className="text-lg font-semibold text-zinc-200">Findings & Targeted Remediation</h3>
          </div>

          <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded-lg p-1 text-xs">
            {(["ALL", "BLOCKERS", "WARNINGS", "RESOLVED"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                  activeTab === tab
                    ? "bg-[#FF7A00] text-black font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {tab.charAt(0) + tab.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Findings List */}
        <div className="space-y-3">
          {filteredFindings.length === 0 ? (
            <Card className="bg-zinc-900/40 border-zinc-800 p-8 text-center text-zinc-400">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
              <p className="text-sm font-medium">No findings match this filter.</p>
            </Card>
          ) : (
            filteredFindings.map((finding) => (
              <Card
                key={finding.id}
                className="bg-zinc-900/70 border-zinc-800 hover:border-zinc-700 transition-all"
              >
                <CardContent className="p-5">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          className={`font-mono text-xs font-bold ${
                            finding.severity === "CRITICAL"
                              ? "bg-red-500 text-white"
                              : finding.severity === "HIGH"
                              ? "bg-[#FF7A00] text-black"
                              : finding.severity === "MEDIUM"
                              ? "bg-amber-500 text-black"
                              : "bg-blue-500 text-white"
                          }`}
                        >
                          {finding.severity}
                        </Badge>

                        <Badge variant="outline" className="text-zinc-400 border-zinc-700 text-xs font-mono">
                          {finding.category}
                        </Badge>

                        <span className="text-xs text-zinc-500 font-mono">
                          Artifact: <span className="text-zinc-300 font-semibold">{finding.affected_artifact}</span>
                        </span>

                        {finding.status === "RESOLVED" && (
                          <Badge className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-mono">
                            RESOLVED
                          </Badge>
                        )}
                        {finding.status === "ACCEPTED_WITH_EXCEPTION" && (
                          <Badge className="bg-purple-500/20 text-purple-400 border border-purple-500/30 text-xs font-mono">
                            ADMIN EXCEPTION
                          </Badge>
                        )}
                      </div>

                      <h4 className="text-base font-semibold text-zinc-100">{finding.title}</h4>
                      <p className="text-sm text-zinc-400">{finding.explanation}</p>

                      {/* Remediation Box */}
                      <div className="p-3 bg-zinc-950/80 border border-zinc-800 rounded-lg text-xs space-y-1">
                        <span className="text-[#FF7A00] font-semibold flex items-center gap-1">
                          <Sparkles className="w-3.5 h-3.5" /> Recommended Remediation:
                        </span>
                        <p className="text-zinc-300">{finding.recommended_correction}</p>
                      </div>

                      {/* Resolution notes if resolved */}
                      {finding.resolution_notes && (
                        <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-xs text-emerald-300">
                          <span className="font-semibold">Resolution Note:</span> {finding.resolution_notes}
                        </div>
                      )}

                      {/* Exception reason if accepted */}
                      {finding.exception_reason && (
                        <div className="p-2.5 bg-purple-500/10 border border-purple-500/20 rounded text-xs text-purple-300">
                          <span className="font-semibold">Authorized Exception Justification:</span> {finding.exception_reason}
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex md:flex-col items-center gap-2 shrink-0">
                      {finding.status === "OPEN" && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 w-full"
                            onClick={() => {
                              setSelectedFinding(finding);
                              setResolveModalOpen(true);
                            }}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                            Resolve
                          </Button>

                          {finding.severity !== "CRITICAL" ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs border-purple-500/30 text-purple-400 hover:bg-purple-500/10 w-full"
                              onClick={() => {
                                setSelectedFinding(finding);
                                setExceptionModalOpen(true);
                              }}
                            >
                              <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                              Exception
                            </Button>
                          ) : (
                            <span className="text-[10px] text-zinc-500 font-mono italic text-center max-w-[120px]">
                              CRITICAL veto non-bypassable
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Resolve Finding Modal */}
      <Modal
        isOpen={resolveModalOpen}
        onClose={() => setResolveModalOpen(false)}
        title="Mark Finding as Resolved"
      >
        <div className="space-y-4">
          <p className="text-sm text-zinc-400">
            Document the remediation action taken to resolve this finding. Resolving findings triggers an automated recalculation of the veto gate.
          </p>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-300">Resolution Notes</label>
            <Input
              placeholder="e.g. Regenerated narration audio and confirmed EBU R128 loudness at -14.1 LUFS."
              value={resolveNotes}
              onChange={(e) => setResolveNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setResolveModalOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
              disabled={resolveNotes.trim().length < 3}
              onClick={handleResolve}
            >
              Confirm Resolution
            </Button>
          </div>
        </div>
      </Modal>

      {/* Authorize Exception Modal */}
      <Modal
        isOpen={exceptionModalOpen}
        onClose={() => setExceptionModalOpen(false)}
        title="Authorize Administrative Exception"
      >
        <div className="space-y-4">
          <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg text-xs text-purple-300">
            <span className="font-bold">Administrative Override:</span> Exceptions are permitted for HIGH and MEDIUM severity findings under verified editorial discretion. All exceptions are permanently logged in the audit ledger.
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-300">Business / Editorial Justification</label>
            <Input
              placeholder="e.g. Metric verified via author's direct GitHub commit record; secondary URL unavailable."
              value={exceptionReason}
              onChange={(e) => setExceptionReason(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setExceptionModalOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-purple-600 hover:bg-purple-700 text-white font-semibold"
              disabled={exceptionReason.trim().length < 5}
              onClick={handleAuthorizeException}
            >
              Authorize Exception
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
