import {
  LayoutDashboard,
  Film,
  Calendar,
  FolderKanban,
  Video,
  Sparkles,
  FileText,
  Mic2,
  MonitorPlay,
  Scissors,
  Image,
  SearchCode,
  UploadCloud,
  BarChart3,
  TrendingUp,
  Cpu,
  HardDrive,
  Boxes,
  CreditCard,
  Settings,
  HelpCircle,
  Activity,
  LucideIcon,
} from "lucide-react";

export interface NavItem {
  id: string;
  title: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
  badgeVariant?: "ember" | "success" | "warning" | "neutral" | "info";
  description?: string;
}

export interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
}

export const NAVIGATION_GROUPS: NavGroup[] = [
  {
    id: "workspace",
    title: "Workspace",
    items: [
      {
        id: "dashboard",
        title: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
        description: "Executive channel overview, active production pipelines, and schedule.",
      },
      {
        id: "production-studio",
        title: "Production Studio",
        href: "/production",
        icon: Film,
        badge: "Live",
        badgeVariant: "ember",
        description: "Active video state machine pipeline, background workers, and rendering queue.",
      },
      {
        id: "content-calendar",
        title: "Content Calendar",
        href: "/calendar",
        icon: Calendar,
        description: "Scheduled video publication timeline, peak posting windows, and cadence planner.",
      },
      {
        id: "projects",
        title: "Projects",
        href: "/projects",
        icon: FolderKanban,
        description: "All historical and active video projects across long-form and shorts.",
      },
      {
        id: "video-library",
        title: "Video Library",
        href: "/library",
        icon: Video,
        description: "Rendered master videos, published YouTube videos, and archive recordings.",
      },
    ],
  },
  {
    id: "ai-production",
    title: "AI Production",
    items: [
      {
        id: "topic-research",
        title: "Topic Research",
        href: "/topics",
        icon: Sparkles,
        badge: "Scored",
        badgeVariant: "info",
        description: "Opportunity scoring engine, trends crawler, and competitor video gap analysis.",
      },
      {
        id: "script-studio",
        title: "Script Studio",
        href: "/script-studio",
        icon: FileText,
        description: "Structured multi-part scriptwriter, retention hooks, and claim verification matrix.",
      },
      {
        id: "voice-studio",
        title: "Voice Studio",
        href: "/voice-studio",
        icon: Mic2,
        description: "Local neural TTS synthesis, pronunciation dictionary, and -14 LUFS loudness mastering.",
      },
      {
        id: "visual-studio",
        title: "Visual Studio",
        href: "/visual-studio",
        icon: MonitorPlay,
        description: "Headless Playwright web capture, code syntax animator, and b-roll manager.",
      },
      {
        id: "video-editor",
        title: "Video Editor",
        href: "/video-editor",
        icon: Scissors,
        description: "Procedural FFmpeg assembly, kinetic subtitles, and audio ducking.",
      },
      {
        id: "thumbnail-studio",
        title: "Thumbnail Studio",
        href: "/thumbnail-studio",
        icon: Image,
        description: "3-variant high-contrast thumbnail generator with bold typography and glow accents.",
      },
      {
        id: "seo-studio",
        title: "SEO Studio",
        href: "/seo-studio",
        icon: SearchCode,
        description: "YouTube title optimizer, chaptered descriptions, and synthetic media tagging.",
      },
    ],
  },
  {
    id: "management",
    title: "Management",
    items: [
      {
        id: "publishing",
        title: "Publishing",
        href: "/publishing",
        icon: UploadCloud,
        description: "YouTube Data API v3 chunked resumable upload and scheduled publishing.",
      },
      {
        id: "analytics",
        title: "Analytics",
        href: "/analytics",
        icon: BarChart3,
        description: "Real-time channel performance, views velocity, and CTR benchmarks.",
      },
      {
        id: "content-performance",
        title: "Content Performance",
        href: "/performance",
        icon: TrendingUp,
        description: "30-second audience retention curves and topic feedback optimization loop.",
      },
      {
        id: "automation",
        title: "Automation",
        href: "/automation",
        icon: Cpu,
        badge: "Auto",
        badgeVariant: "success",
        description: "Weekly production cadence engine (2 Long, 3 Shorts) and hands-off publishing rules.",
      },
      {
        id: "media-library",
        title: "Media Library",
        href: "/media",
        icon: HardDrive,
        description: "Raw screencasts, B-roll clips, audio soundscapes, and Creative Commons licensing tracker.",
      },
    ],
  },
  {
    id: "system",
    title: "System",
    items: [
      {
        id: "ai-providers",
        title: "AI Providers",
        href: "/settings/providers",
        icon: Boxes,
        description: "Google Gemini 1.5 Flash/Pro quota tracking, search providers, and TTS models.",
      },
      {
        id: "usage-budget",
        title: "Usage & Budget",
        href: "/settings/usage",
        icon: CreditCard,
        badge: "$0.00",
        badgeVariant: "ember",
        description: "Real-time token burn monitoring, free-tier guardrails, and $0 spending caps.",
      },
      {
        id: "system-health",
        title: "System Health",
        href: "/settings/health",
        icon: Activity,
        badge: "Live",
        badgeVariant: "success",
        description: "Worker heartbeat, queue depth, watchdog, and operational telemetry.",
      },
      {
        id: "settings",
        title: "Settings",
        href: "/settings",
        icon: Settings,
        description: "Channel defaults, YouTube OAuth credentials, and system health logs.",
      },
      {
        id: "help-docs",
        title: "Help & Documentation",
        href: "/help",
        icon: HelpCircle,
        description: "Platform runbooks, YouTube policy guides, and architectural blueprints.",
      },
    ],
  },
];
