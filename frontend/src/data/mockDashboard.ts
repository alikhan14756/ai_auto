/**
 * Demonstration Data for Creator Studio AI Dashboard.
 * 
 * NOTE: This data is explicitly flagged as demonstration/mock data 
 * to provide a realistic preview of platform operations prior to M03 backend API integration.
 */

export interface DemoStat {
  id: string;
  title: string;
  value: string;
  change: string;
  changeType: "positive" | "negative" | "neutral";
  subtitle: string;
}

export interface DemoPipelineJob {
  id: string;
  title: string;
  format: "LONG_FORM" | "SHORTS";
  stage: string;
  stageBadgeVariant: "ember" | "info" | "warning" | "success";
  progress: number;
  durationEst: string;
  claimsVerified: string;
  workerPid: string;
  updatedAt: string;
}

export interface DemoScheduledItem {
  id: string;
  title: string;
  format: "LONG_FORM" | "SHORTS";
  publishDate: string;
  publishTime: string;
  qaScore: string;
  qaPassed: boolean;
  privacy: "scheduled" | "unlisted" | "private";
}

export interface DemoActivityEvent {
  id: string;
  time: string;
  type: "qa_passed" | "render_complete" | "claim_verified" | "scheduled";
  title: string;
  detail: string;
}

export const MOCK_DASHBOARD_STATS: DemoStat[] = [
  {
    id: "total_videos",
    title: "Total Videos Produced",
    value: "18",
    change: "+4 this month",
    changeType: "positive",
    subtitle: "Across long-form tutorials and shorts",
  },
  {
    id: "published_videos",
    title: "Published on YouTube",
    value: "14",
    change: "100% on schedule",
    changeType: "positive",
    subtitle: "2 long-form & 3 shorts weekly cadence",
  },
  {
    id: "scheduled_videos",
    title: "Scheduled Queue",
    value: "3",
    change: "Next in 18h",
    changeType: "neutral",
    subtitle: "All 14 QA veto checks passed",
  },
  {
    id: "total_views",
    title: "Simulated Channel Views",
    value: "128.4K",
    change: "+18.2%",
    changeType: "positive",
    subtitle: "41.6% median retention @ 3 min",
  },
  {
    id: "success_rate",
    title: "Production Success Rate",
    value: "94.4%",
    change: "1 veto auto-corrected",
    changeType: "positive",
    subtitle: "Zero black frames or audio clipping",
  },
];

export const MOCK_ACTIVE_JOBS: DemoPipelineJob[] = [
  {
    id: "proj_01",
    title: "Top 3 Open Source AI Coding Assistants in 2026",
    format: "LONG_FORM",
    stage: "RENDERING",
    stageBadgeVariant: "ember",
    progress: 74,
    durationEst: "08:14",
    claimsVerified: "12/12 (100%)",
    workerPid: "PID #1042",
    updatedAt: "2m ago",
  },
  {
    id: "proj_02",
    title: "Stop Writing SQL: 4 Instant Database Browsers",
    format: "SHORTS",
    stage: "VOICE_GENERATING",
    stageBadgeVariant: "info",
    progress: 48,
    durationEst: "00:54",
    claimsVerified: "5/5 (100%)",
    workerPid: "PID #1043",
    updatedAt: "5m ago",
  },
  {
    id: "proj_03",
    title: "Build an Autonomous Web Scraper with Playwright",
    format: "LONG_FORM",
    stage: "SCRIPTING",
    stageBadgeVariant: "warning",
    progress: 25,
    durationEst: "07:30",
    claimsVerified: "8/10 (Pending)",
    workerPid: "PID #1044",
    updatedAt: "12m ago",
  },
];

export const MOCK_SCHEDULED_VIDEOS: DemoScheduledItem[] = [
  {
    id: "sched_01",
    title: "Free AI Voice Clones: Complete Local Guide",
    format: "LONG_FORM",
    publishDate: "Tomorrow",
    publishTime: "14:00 UTC",
    qaScore: "14/14 Checks",
    qaPassed: true,
    privacy: "scheduled",
  },
  {
    id: "sched_02",
    title: "3 Terminal Tricks Every Developer Misses",
    format: "SHORTS",
    publishDate: "Thursday",
    publishTime: "16:30 UTC",
    qaScore: "14/14 Checks",
    qaPassed: true,
    privacy: "scheduled",
  },
  {
    id: "sched_03",
    title: "How Gemini 1.5 Flash Token Caching Saves 80%",
    format: "SHORTS",
    publishDate: "Saturday",
    publishTime: "14:00 UTC",
    qaScore: "14/14 Checks",
    qaPassed: true,
    privacy: "scheduled",
  },
];

export const MOCK_RECENT_ACTIVITY: DemoActivityEvent[] = [
  {
    id: "act_01",
    time: "14 mins ago",
    type: "qa_passed",
    title: "14-Point Deterministic QA Passed",
    detail: "'Free AI Voice Clones' verified with zero black frames, -13.9 LUFS loudness.",
  },
  {
    id: "act_02",
    time: "1 hour ago",
    type: "claim_verified",
    title: "Factual Claims Verified",
    detail: "12 benchmarks verified via official GitHub release notes and web search API.",
  },
  {
    id: "act_03",
    time: "3 hours ago",
    type: "render_complete",
    title: "Procedural Assembly Completed",
    detail: "FFmpeg rendered 8m 14s MP4 with burned kinetic orange subtitles (#FF7A00).",
  },
  {
    id: "act_04",
    time: "5 hours ago",
    type: "scheduled",
    title: "YouTube Upload Scheduled",
    detail: "Uploaded via Resumable API v3; privacy set to scheduled with synthetic media disclosure.",
  },
];
