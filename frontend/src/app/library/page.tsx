"use client";

import { RoutePlaceholder } from "@/components/common/RoutePlaceholder";
import { Video } from "lucide-react";

export default function LibraryPage() {
  return (
    <RoutePlaceholder
      title="Video Library"
      category="Workspace"
      description="Rendered master videos, published YouTube videos, and archive recordings."
      icon={Video}
      plannedMilestone="Milestone 09 & 12"
      keyFeatures={[
        "HTML5 1080p full-resolution video player",
        "Burned kinetic typography subtitle playback",
        "YouTube published video URL and ID resolver",
        "Direct MP4 download for local backup",
        "Cloudflare R2 storage integration with signed URLs",
        "14-Point QA verification certificate viewer",
      ]}
      actionLabel="Inspect Master Files"
    />
  );
}
