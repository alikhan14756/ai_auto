"use client";

import { RoutePlaceholder } from "@/components/common/RoutePlaceholder";
import { HelpCircle } from "lucide-react";

export default function HelpPage() {
  return (
    <RoutePlaceholder
      title="Help & Documentation"
      category="System"
      description="Platform runbooks, YouTube policy guides, and architectural blueprints."
      icon={HelpCircle}
      plannedMilestone="Milestone 01–15"
      keyFeatures={[
        "Complete technical blueprint documentation links (01-PRD to 06-PLAN)",
        "14-Point Deterministic QA Veto Gate compliance runbook",
        "YouTube Partner Program monetization & fair use policy guide",
        "Free-tier Gemini and local TTS optimization strategies",
        "Troubleshooting guide for Playwright captures and FFmpeg rendering",
        "Owner documentation & operational handoff for Muhammad Ali",
      ]}
      actionLabel="Browse Architecture Docs"
    />
  );
}
