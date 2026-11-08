"use client";

import { RoutePlaceholder } from "@/components/common/RoutePlaceholder";
import { FolderKanban } from "lucide-react";

export default function ProjectsPage() {
  return (
    <RoutePlaceholder
      title="Projects"
      category="Workspace"
      description="All historical and active video projects across long-form tutorials and shorts."
      icon={FolderKanban}
      plannedMilestone="Milestone 03"
      keyFeatures={[
        "Filterable project matrix by format and niche",
        "Direct link to project studio hubs and script editors",
        "Asset revision history and render benchmarks",
        "Exportable video stems (audio, SRT, MP4, thumbnail)",
        "Batch project operations and archival",
        "Relational PostgreSQL entity mapping",
      ]}
      actionLabel="Create Project"
    />
  );
}
