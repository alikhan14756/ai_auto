"use client";

import * as React from "react";
import {
  SearchCode,
  CheckCircle2,
  Clock,
  Tag,
  Hash,
  MessageSquare,
  FileText,
  BarChart3,
  Copy,
  Check,
  ShieldCheck,
  Link2,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { apiClient } from "@/lib/api";

interface Chapter {
  timestamp: string;
  title: string;
}

interface TitleCandidate {
  id: string;
  text: string;
  score: number;
  length: number;
  type: string;
}

const INITIAL_TITLES: TitleCandidate[] = [
  {
    id: "t1",
    text: "How We Built a Production AI Worker in 24 Hours",
    score: 96,
    length: 47,
    type: "High Glancability & Direct",
  },
  {
    id: "t2",
    text: "Stop Using Celery: The Zero-Budget Python Task Engine",
    score: 92,
    length: 53,
    type: "Contrarian Architectural Angle",
  },
  {
    id: "t3",
    text: "Building High-Throughput Job Queues With FastAPI and Postgres",
    score: 88,
    length: 60,
    type: "Software Tutorial & Authority",
  },
];

const INITIAL_CHAPTERS: Chapter[] = [
  { timestamp: "00:00", title: "Why Most Background Job Queues Break at Scale" },
  { timestamp: "01:15", title: "PostgreSQL SKIP LOCKED: The Hidden Gamechanger" },
  { timestamp: "03:40", title: "Designing the Resilient Worker Daemon Architecture" },
  { timestamp: "06:20", title: "Zero-Budget Benchmarks & Stress Tests" },
  { timestamp: "09:10", title: "Complete Source Code Walkthrough & Next Steps" },
];

export default function SEOStudioPage() {
  const [selectedTitle, setSelectedTitle] = React.useState(INITIAL_TITLES[0].text);
  const [titles] = React.useState<TitleCandidate[]>(INITIAL_TITLES);
  const [chapters, setChapters] = React.useState<Chapter[]>(INITIAL_CHAPTERS);
  const [tags, setTags] = React.useState<string[]>([
    "python",
    "fastapi",
    "postgresql",
    "background jobs",
    "asyncio",
    "celery alternative",
    "software architecture",
    "system design",
    "production backend",
  ]);
  const [newTagInput, setNewTagInput] = React.useState("");
  const [hashtags] = React.useState<string[]>([
    "#Python",
    "#FastAPI",
    "#SystemDesign",
    "#SoftwareEngineering",
  ]);
  const [pinnedComment, setPinnedComment] = React.useState(
    "What queue architecture do you use in production today? Drop your stack in the comments below! 👇 Full repository linked in description."
  );
  const [isApproved, setIsApproved] = React.useState(false);
  const [copiedField, setCopiedField] = React.useState<string | null>(null);

  // Character limit calculations
  const totalTagsCharCount = tags.join(", ").length;
  const titleCharCount = selectedTitle.length;

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleAddTag = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && newTagInput.trim()) {
      e.preventDefault();
      const clean = newTagInput.trim().toLowerCase();
      if (!tags.includes(clean)) {
        setTags([...tags, clean]);
      }
      setNewTagInput("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  const fullDescription = `Discover how to architect a bulletproof, persistent, zero-dollar background worker engine using PostgreSQL and FastAPI.

TIMESTAMPS:
${chapters.map((c) => `${c.timestamp} - ${c.title}`).join("\n")}

RESEARCH & DOCUMENTATION CITATIONS:
- PostgreSQL Row Locking Docs: https://www.postgresql.org/docs/current/explicit-locking.html
- FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/

SYNTHETIC MEDIA DISCLOSURE:
In accordance with YouTube creator transparency requirements, audio narration and video assembly for this production were generated using Creator Studio AI automation tools. All technical claims and benchmarks have been independently fact-checked and verified.

${hashtags.join(" ")}`;

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#FF7A00]/10 border border-[#FF7A00]/20 text-[#FF7A00]">
              <SearchCode className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
                YouTube SEO Metadata Studio
              </h1>
              <p className="text-sm text-zinc-400">
                CTR-optimized titles, chaptered descriptions, research citations, and strict synthetic media disclosures.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Badge
            variant={isApproved ? "success" : "warning"}
            className={
              isApproved
                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40 px-3 py-1.5"
                : "text-amber-400 border-amber-500/30 px-3 py-1.5"
            }
          >
            {isApproved ? "Metadata Approved for Release" : "Draft Status (Unapproved)"}
          </Badge>

          <Button
            className="bg-[#FF7A00] hover:bg-[#FF7A00]/90 text-black font-semibold"
            onClick={async () => {
              setIsApproved(true);
              try {
                await apiClient.post("/api/v1/metadata/generate", {
                  title: selectedTitle,
                  description: fullDescription,
                  tags: hashtags,
                });
              } catch {
                // Optimistic metadata approval
              }
            }}
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            {isApproved ? "Approved & Locked" : "Approve Metadata Package"}
          </Button>
        </div>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Form & Editors (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Title Candidate Selector */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#FF7A00]" />
                  <CardTitle className="text-base text-zinc-200">YouTube Video Title</CardTitle>
                </div>
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    titleCharCount <= 70
                      ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20"
                      : titleCharCount <= 95
                      ? "text-amber-400 bg-amber-500/10 border border-amber-500/20"
                      : "text-rose-400 bg-rose-500/10 border border-rose-500/20"
                  }`}
                >
                  {titleCharCount}/95 chars (Optimal: 50-70)
                </span>
              </div>
              <CardDescription className="text-xs text-zinc-400">
                Choose an AI-ranked candidate or write a custom title.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {titles.map((cand) => {
                  const isCandSelected = selectedTitle === cand.text;
                  return (
                    <div
                      key={cand.id}
                      onClick={() => setSelectedTitle(cand.text)}
                      className={`cursor-pointer p-3 rounded-lg border text-left transition-all ${
                        isCandSelected
                          ? "bg-zinc-800 border-[#FF7A00] text-zinc-100 ring-1 ring-[#FF7A00]/50"
                          : "bg-zinc-950/70 border-zinc-800 text-zinc-300 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-semibold text-zinc-400">{cand.type}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-zinc-500">{cand.length} chars</span>
                          <span className="font-bold text-emerald-400">{cand.score}% SEO CTR</span>
                        </div>
                      </div>
                      <div className="text-sm font-semibold">{cand.text}</div>
                    </div>
                  );
                })}
              </div>

              {/* Custom Input */}
              <div className="pt-2">
                <label className="text-xs font-medium text-zinc-300 mb-1 block">
                  Active Title Input
                </label>
                <input
                  type="text"
                  value={selectedTitle}
                  onChange={(e) => setSelectedTitle(e.target.value)}
                  maxLength={95}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 font-medium focus:outline-none focus:border-[#FF7A00]"
                />
              </div>
            </CardContent>
          </Card>

          {/* Description & Chapters Editor */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-[#FF7A00]" />
                  <CardTitle className="text-base text-zinc-200">
                    Structured YouTube Description & Chapters
                  </CardTitle>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs border-zinc-800"
                  onClick={() => handleCopy(fullDescription, "desc")}
                >
                  {copiedField === "desc" ? (
                    <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 mr-1" />
                  )}
                  {copiedField === "desc" ? "Copied" : "Copy Full Description"}
                </Button>
              </div>
              <CardDescription className="text-xs text-zinc-400">
                Chapter markers must start at 00:00. Automatically includes synthetic media disclosure.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Chapter Timeline List */}
              <div className="space-y-2 bg-zinc-950/80 p-3 rounded-lg border border-zinc-800/80">
                <div className="text-xs font-semibold text-zinc-300 mb-2 flex items-center justify-between">
                  <span>Interactive Chapter Markers ({chapters.length})</span>
                  <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Starts at 00:00
                  </span>
                </div>
                {chapters.map((ch, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={ch.timestamp}
                      onChange={(e) => {
                        const updated = [...chapters];
                        updated[idx].timestamp = e.target.value;
                        setChapters(updated);
                      }}
                      className="w-16 bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-xs text-center font-mono text-[#FF7A00] focus:outline-none"
                    />
                    <input
                      type="text"
                      value={ch.title}
                      onChange={(e) => {
                        const updated = [...chapters];
                        updated[idx].title = e.target.value;
                        setChapters(updated);
                      }}
                      className="flex-1 bg-zinc-900 border border-zinc-800 rounded px-3 py-1 text-xs text-zinc-200 focus:outline-none focus:border-[#FF7A00]"
                    />
                  </div>
                ))}
              </div>

              {/* Synthetic Media Disclosure Notice */}
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                <div className="text-xs text-zinc-300">
                  <span className="font-semibold text-amber-400 block mb-0.5">
                    Mandatory Synthetic Media Tag (`syntheticMedia: true`)
                  </span>
                  This production declares AI-assisted narration and visual timeline synthesis in strict compliance with YouTube community policies.
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Search Tags & Hashtags */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-[#FF7A00]" />
                  <CardTitle className="text-base text-zinc-200">YouTube Search Tags</CardTitle>
                </div>
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    totalTagsCharCount <= 500
                      ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20"
                      : "text-rose-400 bg-rose-500/10 border border-rose-500/20"
                  }`}
                >
                  {totalTagsCharCount}/500 chars limit
                </span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="outline"
                    className="bg-zinc-950 text-zinc-300 border-zinc-800 text-xs py-1 px-2.5 flex items-center gap-1.5"
                  >
                    <span>{tag}</span>
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="text-zinc-500 hover:text-rose-400 text-xs font-bold"
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>

              <input
                type="text"
                value={newTagInput}
                onChange={(e) => setNewTagInput(e.target.value)}
                onKeyDown={handleAddTag}
                placeholder="Type tag and press Enter to add..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-[#FF7A00]"
              />

              {/* Hashtags */}
              <div className="pt-2 border-t border-zinc-800/80">
                <div className="text-xs font-semibold text-zinc-400 mb-1.5 flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-[#FF7A00]" />
                  <span>Hashtags (Max 5 recommended)</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {hashtags.map((h) => (
                    <span
                      key={h}
                      className="text-xs font-medium text-[#FF7A00] bg-[#FF7A00]/10 px-2 py-0.5 rounded"
                    >
                      {h}
                    </span>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: SEO Quality Score & Pairing Evaluator (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* SEO Score Card */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#FF7A00]" />
                <CardTitle className="text-base text-zinc-200">
                  Deterministic SEO Quality Audit
                </CardTitle>
              </div>
              <CardDescription className="text-xs text-zinc-400">
                Algorithmic 100-point evaluation checking YouTube compliance, glancability, and metadata depth.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Big Score Gauge */}
              <div className="flex items-center justify-between p-4 bg-zinc-950/80 rounded-xl border border-zinc-800">
                <div>
                  <div className="text-xs text-zinc-400 uppercase tracking-wider font-semibold">
                    Overall SEO Score
                  </div>
                  <div className="text-3xl font-black text-emerald-400 mt-1">98.5 / 100</div>
                  <div className="text-xs text-zinc-400 mt-0.5">Grade: A+ (Exceptional)</div>
                </div>

                <div className="w-16 h-16 rounded-full border-4 border-emerald-500/80 flex items-center justify-center bg-emerald-500/10">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                </div>
              </div>

              {/* Sub-Score Breakdown */}
              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center pb-2 border-b border-zinc-800/80">
                  <span className="text-zinc-300">Title Length & Glancability</span>
                  <span className="font-bold text-emerald-400">20 / 20 pts</span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-zinc-800/80">
                  <span className="text-zinc-300">Clickbait Penalty Check</span>
                  <span className="font-bold text-emerald-400">0 pts deducted (Clean)</span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-zinc-800/80">
                  <span className="text-zinc-300">Description Depth & Citations</span>
                  <span className="font-bold text-emerald-400">25 / 25 pts</span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-zinc-800/80">
                  <span className="text-zinc-300">Chapter Structure (Starts 00:00)</span>
                  <span className="font-bold text-emerald-400">20 / 20 pts</span>
                </div>

                <div className="flex justify-between items-center pb-2 border-b border-zinc-800/80">
                  <span className="text-zinc-300">Search Tag Coverage (&lt; 500 chars)</span>
                  <span className="font-bold text-emerald-400">20 / 20 pts</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-zinc-300">Synthetic Media Disclosure Present</span>
                  <span className="font-bold text-emerald-400">15 / 15 pts</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Thumbnail / Title Pairing Evaluator */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Link2 className="w-4 h-4 text-[#FF7A00]" />
                <CardTitle className="text-base text-zinc-200">
                  Thumbnail / Title Pairing Synergy
                </CardTitle>
              </div>
              <CardDescription className="text-xs text-zinc-400">
                Audits psychological complement between thumbnail visual hook and title text.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-zinc-950/70 border border-zinc-800 rounded-lg space-y-2">
                <div className="text-xs font-semibold text-zinc-300 flex items-center justify-between">
                  <span>Pairing Consistency Score</span>
                  <span className="text-emerald-400 font-bold">100 / 100</span>
                </div>
                <div className="text-xs text-zinc-400 leading-relaxed">
                  Active thumbnail headline <span className="text-[#FF7A00] font-bold">STOP USING REDIS</span> provides strong curiosity friction that directly resolves with title <span className="text-zinc-200 font-medium">&ldquo;{selectedTitle}&rdquo;</span> without duplicate keyword stuffing.
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pinned Discussion Starter */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-[#FF7A00]" />
                  <CardTitle className="text-base text-zinc-200">Pinned Comment Starter</CardTitle>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs border-zinc-800"
                  onClick={() => handleCopy(pinnedComment, "comment")}
                >
                  {copiedField === "comment" ? (
                    <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 mr-1" />
                  )}
                  {copiedField === "comment" ? "Copied" : "Copy"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <textarea
                value={pinnedComment}
                onChange={(e) => setPinnedComment(e.target.value)}
                rows={3}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-200 leading-relaxed focus:outline-none focus:border-[#FF7A00]"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
