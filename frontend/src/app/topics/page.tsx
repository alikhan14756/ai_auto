"use client";

import React, { useState } from "react";
import {
  Sparkles,
  TrendingUp,
  Search,
  CheckCircle2,
  Archive,
  ExternalLink,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Flame,
  Layers,
  Target,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatCard } from "@/components/ui/StatCard";
import { Input } from "@/components/ui/Input";

interface ResearchSource {
  id?: string;
  source_url: string;
  source_title: string;
  extracted_summary: string;
  relevance_score: number;
}

interface TopicItem {
  id: string;
  title: string;
  niche_category: string;
  opportunity_score: number;
  search_volume_score: number;
  competition_score: number;
  status: "DISCOVERED" | "SELECTED" | "ARCHIVED";
  angle: string;
  target_audience: string;
  rationale: string;
  research_sources: ResearchSource[];
}

const INITIAL_TOPICS: TopicItem[] = [
  {
    id: "top-1",
    title: "PostgreSQL 17 Hidden Features: SKIP LOCKED and Parallel Worker Tricks",
    niche_category: "Backend Performance",
    opportunity_score: 91.5,
    search_volume_score: 84.0,
    competition_score: 32.0,
    status: "DISCOVERED",
    angle: "Why modern high-scale apps are throwing away Redis to run zero-loss durable queue workers directly inside PostgreSQL.",
    target_audience: "Senior backend engineers, system architects, and DevOps leads.",
    rationale: "Devs are actively seeking ways to simplify architecture without adding complex multi-cluster queue systems.",
    research_sources: [
      {
        source_url: "https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE",
        source_title: "PostgreSQL Official Documentation: Locking and SKIP LOCKED Clauses",
        extracted_summary: "Guarantees lock-free, zero-blocking row acquisition across concurrent worker daemons.",
        relevance_score: 0.98,
      },
      {
        source_url: "https://brandur.org/postgres-queues",
        source_title: "Postgres Queues in Modern Architectures",
        extracted_summary: "Detailed case study illustrating 5,000 jobs/sec throughput with transactional ACID rollback.",
        relevance_score: 0.94,
      },
    ],
  },
  {
    id: "top-2",
    title: "Autonomous AI Agents in Production: 5 Failure Modes You Must Avoid",
    niche_category: "AI Architecture & Engineering",
    opportunity_score: 88.0,
    search_volume_score: 89.0,
    competition_score: 41.0,
    status: "SELECTED",
    angle: "Pragmatic engineering breakdown of multi-agent loops, state drift, and race conditions in production systems.",
    target_audience: "AI engineers and software team leads deploying LLM workflows.",
    rationale: "Surging demand for real operational reliability patterns beyond naive demo tutorials.",
    research_sources: [
      {
        source_url: "https://arxiv.org/abs/2402.01234",
        source_title: "Empirical Analysis of Multi-Agent Divergence in Autonomous Workflows",
        extracted_summary: "Multi-agent systems without checkpointing suffer state degradation in 38% of long-running workflows.",
        relevance_score: 0.95,
      },
    ],
  },
  {
    id: "top-3",
    title: "Why SQLite is Taking Over Cloud-Native Edge Applications in 2026",
    niche_category: "Database Systems",
    opportunity_score: 83.5,
    search_volume_score: 79.0,
    competition_score: 36.0,
    status: "DISCOVERED",
    angle: "Architectural shift from heavy distributed clusters toward replicated edge SQLite with streaming Litestream.",
    target_audience: "Full-stack engineers and microservice builders looking for sub-millisecond query latency.",
    rationale: "Cloud database bills are driving microservices toward embedded, replicated SQLite nodes.",
    research_sources: [
      {
        source_url: "https://fly.io/blog/all-in-on-sqlite/",
        source_title: "I'm All-In On SQLite for Production SaaS",
        extracted_summary: "Benchmark data showing 10x lower latency and zero managed database infrastructure cost.",
        relevance_score: 0.92,
      },
    ],
  },
  {
    id: "top-4",
    title: "10 CSS Tricks Everyone Forgets",
    niche_category: "Frontend Basics",
    opportunity_score: 54.0,
    search_volume_score: 65.0,
    competition_score: 85.0,
    status: "ARCHIVED",
    angle: "Generic roundup of basic CSS pseudo-classes.",
    target_audience: "Junior web learners.",
    rationale: "Over-saturated topic with minimal technical authority and low audience retention for this channel.",
    research_sources: [],
  },
];

export default function TopicsPage() {
  const [topics, setTopics] = useState<TopicItem[]>(INITIAL_TOPICS);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const toggleSources = (id: string) => {
    setExpandedSources((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleApprove = (id: string) => {
    setTopics((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: "SELECTED" } : t))
    );
  };

  const handleArchive = (id: string) => {
    setTopics((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: "ARCHIVED" } : t))
    );
  };

  const runDiscovery = async () => {
    setIsDiscovering(true);
    // Simulate real discovery latency with fresh technical topics
    await new Promise((r) => setTimeout(r, 1200));

    const newTopic: TopicItem = {
      id: `top-${Date.now()}`,
      title: "Building Deterministic State Machines for Long-Running LLM Queues",
      niche_category: "Distributed Systems & AI",
      opportunity_score: 93.0,
      search_volume_score: 87.0,
      competition_score: 28.0,
      status: "DISCOVERED",
      angle: "How to prevent non-deterministic agent crashes using durable event log schemas.",
      target_audience: "System architects and senior backend developers.",
      rationale: "High conversion topic addressing the biggest developer pain point in agent deployments.",
      research_sources: [
        {
          source_url: "https://temporal.io/blog/reliable-ai-agents",
          source_title: "Temporal: Durable Execution for Generative AI Workflows",
          extracted_summary: "Formal state transitions guarantee replayability without re-billing model tokens.",
          relevance_score: 0.97,
        },
      ],
    };

    setTopics((prev) => [newTopic, ...prev]);
    setIsDiscovering(false);
  };

  const filteredTopics = topics.filter((t) => {
    const matchesSearch =
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.niche_category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "ALL" ? true : t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const highOpportunityCount = topics.filter((t) => t.opportunity_score >= 80).length;
  const selectedCount = topics.filter((t) => t.status === "SELECTED").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Topic Research Engine</h1>
            <Badge variant="ember" size="sm">Gemini 1.5 Flash</Badge>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Algorithmic opportunity scoring, competitive gap analysis, and factual citation discovery.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            onClick={runDiscovery}
            disabled={isDiscovering}
            className="flex items-center gap-2 shadow-lg shadow-ember/20"
          >
            {isDiscovering ? (
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Sparkles className="w-4 h-4 text-white" />
            )}
            {isDiscovering ? "Analyzing Feeds & Sources..." : "Discover Topics"}
          </Button>
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Discovered Topics"
          value={topics.length}
          change="Updated live"
          changeType="positive"
          icon={Layers}
        />
        <StatCard
          title="High Opportunity (≥80)"
          value={highOpportunityCount}
          change="Prime candidates"
          changeType="positive"
          icon={Flame}
        />
        <StatCard
          title="Selected for Production"
          value={selectedCount}
          change="Ready for M06"
          changeType="neutral"
          icon={Target}
        />
        <StatCard
          title="Free Tier AI Spend"
          value="$0.00"
          change="Hard cap active"
          changeType="neutral"
          icon={TrendingUp}
        />
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-canvas-card border border-canvas-border p-4 rounded-xl">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            placeholder="Search topics or niches..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-canvas-subtle border-canvas-border"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0">
          {["ALL", "DISCOVERED", "SELECTED", "ARCHIVED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === tab
                  ? "bg-ember text-white shadow-sm"
                  : "bg-canvas-subtle text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Topics Feed */}
      <div className="space-y-4">
        {filteredTopics.map((topic) => {
          const isHigh = topic.opportunity_score >= 80;
          const isMedium = topic.opportunity_score >= 60 && topic.opportunity_score < 80;
          const scoreBadgeVariant = isHigh ? "success" : isMedium ? "warning" : "neutral";
          const hasSources = topic.research_sources && topic.research_sources.length > 0;
          const isExpanded = !!expandedSources[topic.id];

          return (
            <Card
              key={topic.id}
              className={`border transition-all duration-200 ${
                topic.status === "SELECTED"
                  ? "border-emerald-500/30 bg-emerald-950/10"
                  : topic.status === "ARCHIVED"
                  ? "border-zinc-800 opacity-60"
                  : "border-canvas-border hover:border-zinc-700"
              }`}
            >
              <CardContent className="p-5 space-y-4">
                {/* Header row */}
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="neutral" size="sm">{topic.niche_category}</Badge>
                      <Badge
                        variant={
                          topic.status === "SELECTED"
                            ? "success"
                            : topic.status === "ARCHIVED"
                            ? "neutral"
                            : "ember"
                        }
                        size="sm"
                      >
                        {topic.status}
                      </Badge>
                      {topic.status === "SELECTED" && (
                        <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Approved for Video
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold text-white tracking-tight leading-snug">
                      {topic.title}
                    </h3>
                  </div>

                  {/* Opportunity Score Pill */}
                  <div className="flex items-center gap-3 self-start">
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] uppercase font-mono text-zinc-400 tracking-wider">Opportunity</span>
                      <div className="flex items-center gap-1">
                        <Badge variant={scoreBadgeVariant} size="md" className="font-mono font-bold text-sm">
                          {topic.opportunity_score.toFixed(1)}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Narrative Angle & Target Audience */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-canvas-subtle p-3.5 rounded-lg border border-canvas-border/50">
                  <div>
                    <span className="font-semibold text-zinc-300 block mb-0.5">Narrative Angle:</span>
                    <p className="text-zinc-400 leading-relaxed">{topic.angle}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-zinc-300 block mb-0.5">Target Audience:</span>
                    <p className="text-zinc-400 leading-relaxed">{topic.target_audience}</p>
                  </div>
                </div>

                {/* Score Breakdown Bar */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-400 pt-1 border-t border-canvas-border/40">
                  <div className="flex items-center gap-1.5">
                    <span className="text-zinc-400 font-medium">Search Volume:</span>
                    <span className="font-mono text-zinc-200">{topic.search_volume_score}</span>
                  </div>
                  <span className="text-zinc-700">•</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-zinc-400 font-medium">Competition:</span>
                    <span className="font-mono text-zinc-200">{topic.competition_score}</span>
                  </div>
                  <span className="text-zinc-700">•</span>
                  <div className="flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-zinc-400" />
                    <span>{topic.research_sources.length} Factual Sources</span>
                  </div>
                </div>

                {/* Expandable Sources Drawer */}
                {hasSources && (
                  <div className="pt-2">
                    <button
                      onClick={() => toggleSources(topic.id)}
                      className="flex items-center gap-1.5 text-xs text-ember hover:text-ember-light font-medium transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      {isExpanded ? "Hide Evidence Sources" : "View Verified Research Evidence"}
                    </button>

                    {isExpanded && (
                      <div className="mt-3 space-y-2 border-l-2 border-ember/30 pl-4">
                        {topic.research_sources.map((src, idx) => (
                          <div
                            key={idx}
                            className="bg-canvas-card border border-canvas-border p-3 rounded-lg text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <a
                                href={src.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-1 truncate"
                              >
                                {src.source_title}
                                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                              </a>
                              <Badge variant="success" size="sm" className="text-[10px]">
                                {(src.relevance_score * 100).toFixed(0)}% Relevant
                              </Badge>
                            </div>
                            <p className="text-zinc-400 italic">&ldquo;{src.extracted_summary}&rdquo;</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-canvas-border/40">
                  {topic.status !== "ARCHIVED" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleArchive(topic.id)}
                      className="text-zinc-400 hover:text-rose-400 hover:border-rose-500/30"
                    >
                      <Archive className="w-3.5 h-3.5 mr-1" /> Archive
                    </Button>
                  )}
                  {topic.status !== "SELECTED" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleApprove(topic.id)}
                      className="border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Approve for Video
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}

        {filteredTopics.length === 0 && (
          <Card className="p-8 text-center border-dashed border-zinc-800">
            <p className="text-zinc-400 text-sm">No topics match your current filter.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
