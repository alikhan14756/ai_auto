"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FolderKanban,
  Plus,
  FileText,
  Mic,
  Video,
  Clock,
  ArrowRight,
  Play,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { apiClient } from "@/lib/api";

interface ProjectItem {
  id: string;
  title: string;
  format: "LONG_FORM" | "SHORTS";
  state: string;
  target_duration_seconds: number;
  actual_duration_seconds?: number | null;
  created_at: string;
}

const FALLBACK_PROJECTS: ProjectItem[] = [
  {
    id: "proj-01-postgresql-skip-locked",
    title: "PostgreSQL 17 Hidden Features: SKIP LOCKED and Parallel Worker Tricks",
    format: "LONG_FORM",
    state: "QA_APPROVED",
    target_duration_seconds: 520,
    actual_duration_seconds: 512.4,
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
  },
  {
    id: "proj-02-fastapi-high-throughput",
    title: "Why FastAPI + Asyncpg Beats Celery for Database-Backed Tasks",
    format: "LONG_FORM",
    state: "SCRIPT_APPROVED",
    target_duration_seconds: 480,
    actual_duration_seconds: null,
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "proj-03-short-postgres-tip",
    title: "Never Use OFFSET for Pagination in PostgreSQL #shorts",
    format: "SHORTS",
    state: "PUBLISHED",
    target_duration_seconds: 45,
    actual_duration_seconds: 43.8,
    created_at: new Date(Date.now() - 86400000 * 4).toISOString(),
  },
  {
    id: "proj-04-gemini-sliding-window",
    title: "Building a Zero-Token-Loss Rate Limiter for Google Gemini in Python",
    format: "LONG_FORM",
    state: "DRAFT",
    target_duration_seconds: 600,
    actual_duration_seconds: null,
    created_at: new Date().toISOString(),
  },
];

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectItem[]>(FALLBACK_PROJECTS);
  const [filterFormat, setFilterFormat] = useState<"ALL" | "LONG_FORM" | "SHORTS">("ALL");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newFormat, setNewFormat] = useState<"LONG_FORM" | "SHORTS">("LONG_FORM");
  const [newDuration, setNewDuration] = useState("480");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLiveConnected, setIsLiveConnected] = useState(false);

  useEffect(() => {
    async function fetchProjects() {
      try {
        const channelId = typeof window !== "undefined" ? localStorage.getItem("active_channel_id") : null;
        const endpoint = channelId ? `/api/v1/projects?channel_id=${channelId}` : "/api/v1/projects";
        const data = await apiClient.get<ProjectItem[]>(endpoint);
        if (Array.isArray(data) && data.length > 0) {
          setProjects(data);
          setIsLiveConnected(true);
        }
      } catch {
        // Fallback projects remain active
      }
    }
    fetchProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setIsSubmitting(true);
    const newProject: ProjectItem = {
      id: `proj-${Date.now().toString(36)}`,
      title: newTitle.trim(),
      format: newFormat,
      state: "DRAFT",
      target_duration_seconds: parseInt(newDuration, 10) || 480,
      created_at: new Date().toISOString(),
    };

    try {
      const channelId = typeof window !== "undefined" ? localStorage.getItem("active_channel_id") : null;
      if (channelId) {
        const created = await apiClient.post<ProjectItem>("/api/v1/projects", {
          title: newTitle.trim(),
          format: newFormat,
          target_duration_seconds: parseInt(newDuration, 10) || 480,
          channel_id: channelId,
        });
        if (created?.id) {
          setProjects((prev) => [created, ...prev]);
        } else {
          setProjects((prev) => [newProject, ...prev]);
        }
      } else {
        setProjects((prev) => [newProject, ...prev]);
      }
    } catch {
      setProjects((prev) => [newProject, ...prev]);
    } finally {
      setIsSubmitting(false);
      setIsModalOpen(false);
      setNewTitle("");
    }
  };

  const filteredProjects = projects.filter((p) => {
    if (filterFormat === "ALL") return true;
    return p.format === filterFormat;
  });

  const getStateBadge = (state: string) => {
    switch (state) {
      case "PUBLISHED":
        return <Badge variant="success">PUBLISHED</Badge>;
      case "QA_APPROVED":
        return <Badge variant="success">QA APPROVED</Badge>;
      case "VIDEO_RENDERED":
        return <Badge variant="warning">RENDERED</Badge>;
      case "SCRIPT_APPROVED":
        return <Badge variant="ember">SCRIPT APPROVED</Badge>;
      case "DRAFT":
        return <Badge variant="neutral">DRAFT</Badge>;
      default:
        return <Badge variant="outline">{state}</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <FolderKanban className="w-6 h-6 text-ember" />
              Video Projects Hub
            </h1>
            <Badge variant={isLiveConnected ? "success" : "neutral"} size="sm" showDot>
              {isLiveConnected ? "PostgreSQL Connected" : "Local Staging"}
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-zinc-400">
            Manage your autonomous content production pipeline across long-form tutorials and shorts.
          </p>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => setIsModalOpen(true)}
          className="shadow-md"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          New Video Project
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 bg-canvas-card border border-canvas-border p-1 rounded-lg">
          <button
            onClick={() => setFilterFormat("ALL")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              filterFormat === "ALL"
                ? "bg-canvas-subtle text-white border border-canvas-border shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            All Projects ({projects.length})
          </button>
          <button
            onClick={() => setFilterFormat("LONG_FORM")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              filterFormat === "LONG_FORM"
                ? "bg-canvas-subtle text-white border border-canvas-border shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Long-Form ({projects.filter((p) => p.format === "LONG_FORM").length})
          </button>
          <button
            onClick={() => setFilterFormat("SHORTS")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              filterFormat === "SHORTS"
                ? "bg-canvas-subtle text-white border border-canvas-border shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Shorts ({projects.filter((p) => p.format === "SHORTS").length})
          </button>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredProjects.map((project) => (
          <Card key={project.id} className="flex flex-col justify-between hover:border-canvas-border/80 transition-standard">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-2 mb-2">
                <Badge variant={project.format === "LONG_FORM" ? "neutral" : "ember"} size="sm">
                  {project.format === "LONG_FORM" ? "Long-Form (6–10m)" : "Short (30–60s)"}
                </Badge>
                {getStateBadge(project.state)}
              </div>
              <CardTitle className="text-base line-clamp-2">{project.title}</CardTitle>
              <CardDescription className="flex items-center gap-2 text-xs font-mono text-zinc-500 mt-1">
                <Clock className="w-3 h-3" />
                <span>Target: {Math.round(project.target_duration_seconds / 60)} min</span>
                <span>&bull;</span>
                <span>{new Date(project.created_at).toLocaleDateString()}</span>
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-2 border-t border-canvas-border/40 mt-auto">
              <div className="grid grid-cols-4 gap-1.5 text-center mb-3">
                <Link
                  href="/script-studio"
                  className="p-1.5 rounded bg-canvas-subtle/60 hover:bg-canvas-subtle border border-canvas-border/60 text-[10px] text-zinc-400 hover:text-white transition-all flex flex-col items-center gap-1"
                >
                  <FileText className="w-3.5 h-3.5 text-blue-400" />
                  <span>Script</span>
                </Link>
                <Link
                  href="/voice-studio"
                  className="p-1.5 rounded bg-canvas-subtle/60 hover:bg-canvas-subtle border border-canvas-border/60 text-[10px] text-zinc-400 hover:text-white transition-all flex flex-col items-center gap-1"
                >
                  <Mic className="w-3.5 h-3.5 text-purple-400" />
                  <span>Voice</span>
                </Link>
                <Link
                  href="/video-editor"
                  className="p-1.5 rounded bg-canvas-subtle/60 hover:bg-canvas-subtle border border-canvas-border/60 text-[10px] text-zinc-400 hover:text-white transition-all flex flex-col items-center gap-1"
                >
                  <Video className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Render</span>
                </Link>
                <Link
                  href="/publishing"
                  className="p-1.5 rounded bg-canvas-subtle/60 hover:bg-canvas-subtle border border-canvas-border/60 text-[10px] text-zinc-400 hover:text-white transition-all flex flex-col items-center gap-1"
                >
                  <Play className="w-3.5 h-3.5 text-ember" />
                  <span>Publish</span>
                </Link>
              </div>

              <div className="flex items-center justify-between pt-1">
                <Link href="/production" className="w-full">
                  <Button variant="ghost" size="sm" className="w-full text-xs font-mono justify-center">
                    Open in QA Studio
                    <ArrowRight className="w-3 h-3 ml-1" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Project Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Video Project"
        description="Initialize a new autonomous production workflow."
      >
        <form onSubmit={handleCreateProject} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
              Video Title
            </label>
            <Input
              type="text"
              placeholder="e.g. Next.js 15 Server Actions Deep Dive"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                Format
              </label>
              <select
                value={newFormat}
                onChange={(e) => setNewFormat(e.target.value as "LONG_FORM" | "SHORTS")}
                className="w-full bg-canvas-subtle border border-canvas-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ember"
              >
                <option value="LONG_FORM">Long-Form Tutorial (6–10m)</option>
                <option value="SHORTS">YouTube Short (30–60s)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                Target Duration (sec)
              </label>
              <Input
                type="number"
                value={newDuration}
                onChange={(e) => setNewDuration(e.target.value)}
                min="30"
                max="1200"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2.5 pt-4 border-t border-canvas-border">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={isSubmitting || !newTitle.trim()}
            >
              {isSubmitting ? "Creating..." : "Initialize Project"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
