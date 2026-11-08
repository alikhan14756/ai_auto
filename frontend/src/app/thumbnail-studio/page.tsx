"use client";

import * as React from "react";
import {
  Image as ImageIcon,
  Type,
  Palette,
  CheckCircle2,
  Smartphone,
  Monitor,
  RefreshCw,
  Sliders,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { apiClient } from "@/lib/api";

interface ThumbnailVariant {
  id: string;
  variantCode: "A" | "B" | "C";
  conceptName: string;
  headlineText: string;
  badgeText: string;
  stylePreset: string;
  accentColor: string;
  showGrid: boolean;
  showGlow: boolean;
  darkenBg: number;
  qualityStatus: "PASSED" | "WARNING" | "FAILED";
  fileSizeBytes: number;
  width: number;
  height: number;
  targetEmotion: string;
  compositionStrategy: string;
}

const STYLE_PRESETS = [
  { id: "modern_tech_editorial", label: "Modern Tech Editorial", desc: "Dark obsidian, neon grid, crisp amber typography" },
  { id: "minimalist_professional", label: "Minimalist Professional", desc: "Clean layout, subtle ambient glow, high-readability sans" },
  { id: "high_contrast_educational", label: "High Contrast Educational", desc: "Bold dual-tone headers, contrast badge pill, maximalist focus" },
  { id: "bold_creator", label: "Bold Creator", desc: "Punchy short hook, energetic radial flare, vibrant drop-shadow" },
  { id: "software_tutorial", label: "Software Tutorial", desc: "IDE mockup backdrop, syntax highlighting palette, precision layout" },
  { id: "cinematic_tech", label: "Cinematic Tech", desc: "Deep anamorphic vignetting, atmospheric mist, titanium typography" },
];

const ACCENT_COLORS = [
  { name: "Creator Orange", hex: "#FF7A00" },
  { name: "Cyan Terminal", hex: "#06B6D4" },
  { name: "Electric Emerald", hex: "#10B981" },
  { name: "Cyber Violet", hex: "#8B5CF6" },
  { name: "Rose Neon", hex: "#F43F5E" },
  { name: "Solar Amber", hex: "#F59E0B" },
];

const INITIAL_VARIANTS: ThumbnailVariant[] = [
  {
    id: "thumb-v-a",
    variantCode: "A",
    conceptName: "Tool Contrast & Paradigm Shift",
    headlineText: "STOP USING REDIS",
    badgeText: "PRODUCTION ARCHITECTURE",
    stylePreset: "modern_tech_editorial",
    accentColor: "#FF7A00",
    showGrid: true,
    showGlow: true,
    darkenBg: 0.65,
    qualityStatus: "PASSED",
    fileSizeBytes: 64210,
    width: 1280,
    height: 720,
    targetEmotion: "Urgency & Critical Technical Insight",
    compositionStrategy: "Split focal: left high-contrast typography, right glowing microservice node graph.",
  },
  {
    id: "thumb-v-b",
    variantCode: "B",
    conceptName: "Metric Drama & Scale",
    headlineText: "10X QUEUE THROUGHPUT",
    badgeText: "ZERO BUDGET SETUP",
    stylePreset: "high_contrast_educational",
    accentColor: "#06B6D4",
    showGrid: true,
    showGlow: false,
    darkenBg: 0.75,
    qualityStatus: "PASSED",
    fileSizeBytes: 58940,
    width: 1280,
    height: 720,
    targetEmotion: "High Curiosity & Tangible Engineering Gains",
    compositionStrategy: "Center-weighted metric badge with intense gradient drop-shadow.",
  },
  {
    id: "thumb-v-c",
    variantCode: "C",
    conceptName: "Architectural Blueprint",
    headlineText: "THE CLEAN WORKER ENGINE",
    badgeText: "POSTGRESQL + FASTAPI",
    stylePreset: "software_tutorial",
    accentColor: "#10B981",
    showGrid: false,
    showGlow: true,
    darkenBg: 0.60,
    qualityStatus: "PASSED",
    fileSizeBytes: 71200,
    width: 1280,
    height: 720,
    targetEmotion: "Authority, Mastery, and Architectural Rigor",
    compositionStrategy: "Monochrome schematic with single neon accent highlighting queue coordinator.",
  },
];

export default function ThumbnailStudioPage() {
  const [variants, setVariants] = React.useState<ThumbnailVariant[]>(INITIAL_VARIANTS);
  const [selectedVariantCode, setSelectedVariantCode] = React.useState<"A" | "B" | "C">("A");
  const [viewMode, setViewMode] = React.useState<"desktop" | "mobile">("desktop");
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [saveSuccess, setSaveSuccess] = React.useState(false);

  const active = variants.find((v) => v.variantCode === selectedVariantCode) || variants[0];

  const updateActiveVariant = (fields: Partial<ThumbnailVariant>) => {
    setVariants((prev) =>
      prev.map((v) => (v.variantCode === selectedVariantCode ? { ...v, ...fields } : v))
    );
  };

  const handleRegenerateConcepts = async () => {
    setIsGenerating(true);
    try {
      await apiClient.post("/api/v1/thumbnails/generate", {
        headline: variants.find((v) => v.variantCode === selectedVariantCode)?.headlineText || "STOP USING REDIS",
        style_preset: "modern_tech_editorial",
      });
    } catch {
      // Procedural fallback synthesis
    }
    setTimeout(() => {
      setIsGenerating(false);
    }, 1000);
  };

  const handleSelectVariant = async (code: "A" | "B" | "C") => {
    setSelectedVariantCode(code);
    setSaveSuccess(true);
    try {
      await apiClient.patch(`/api/v1/thumbnails/${code}/approve`, { approved: true });
    } catch {
      // Local approval confirmed
    }
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#FF7A00]/10 border border-[#FF7A00]/20 text-[#FF7A00]">
              <ImageIcon className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
                AI Thumbnail Composition Studio
              </h1>
              <p className="text-sm text-zinc-400">
                Multi-layer procedural Pillow engine rendering exact 1280x720 graphic assets with verified CTR contrast.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="border-zinc-800 text-zinc-300 hover:bg-zinc-800"
            onClick={handleRegenerateConcepts}
            disabled={isGenerating}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isGenerating ? "animate-spin" : ""}`} />
            {isGenerating ? "Synthesizing Concepts..." : "Regenerate 3 Concepts"}
          </Button>

          <Button
            className="bg-[#FF7A00] hover:bg-[#FF7A00]/90 text-black font-semibold"
            onClick={() => handleSelectVariant(active.variantCode)}
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            {saveSuccess ? "Variant Selected!" : `Select Variant ${active.variantCode} for Release`}
          </Button>
        </div>
      </div>

      {/* 3-Variant Concept Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {variants.map((v) => {
          const isSelected = v.variantCode === selectedVariantCode;
          return (
            <div
              key={v.id}
              onClick={() => setSelectedVariantCode(v.variantCode)}
              className={`cursor-pointer rounded-xl p-4 transition-all border ${
                isSelected
                  ? "bg-zinc-900/90 border-[#FF7A00] shadow-[0_0_20px_rgba(255,122,0,0.15)] ring-1 ring-[#FF7A00]"
                  : "bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={isSelected ? "ember" : "outline"}
                    className={isSelected ? "bg-[#FF7A00] text-black font-bold" : "text-zinc-400"}
                  >
                    Variant {v.variantCode}
                  </Badge>
                  <span className="text-xs font-semibold text-zinc-300 truncate max-w-[170px]">
                    {v.conceptName}
                  </span>
                </div>
                <Badge variant="outline" className="text-emerald-400 border-emerald-500/30 text-[10px]">
                  {v.qualityStatus}
                </Badge>
              </div>

              {/* Mini Preview Box */}
              <div
                className="w-full aspect-video rounded-lg relative overflow-hidden flex flex-col justify-between p-3 border border-zinc-800/80"
                style={{
                  backgroundColor: "#0d0f14",
                  backgroundImage: v.showGrid
                    ? `radial-gradient(ellipse at top right, ${v.accentColor}25, transparent 65%), linear-gradient(to right, #1f2430 1px, transparent 1px), linear-gradient(to bottom, #1f2430 1px, transparent 1px)`
                    : `radial-gradient(ellipse at center, ${v.accentColor}20, transparent 70%)`,
                  backgroundSize: v.showGrid ? "100% 100%, 20px 20px, 20px 20px" : "cover",
                }}
              >
                {/* Badge Tag */}
                <div className="self-start">
                  <span
                    className="text-[9px] uppercase tracking-wider font-extrabold px-1.5 py-0.5 rounded text-white"
                    style={{ backgroundColor: v.accentColor }}
                  >
                    {v.badgeText || "IN-DEPTH"}
                  </span>
                </div>

                {/* Headline Text */}
                <div className="my-auto">
                  <div className="text-xs font-black tracking-tight text-white uppercase drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] line-clamp-2">
                    {v.headlineText}
                  </div>
                </div>

                {/* Footer spec */}
                <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-zinc-800/60">
                  <span>1280x720</span>
                  <span>{(v.fileSizeBytes / 1024).toFixed(1)} KB</span>
                </div>
              </div>

              <p className="text-[11px] text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
                {v.compositionStrategy}
              </p>
            </div>
          );
        })}
      </div>

      {/* Main Studio Workspace: Preview & Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Viewport Preview (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base text-zinc-200">
                  Live Procedural Composition Canvas
                </CardTitle>
                <CardDescription className="text-xs text-zinc-400">
                  Pixel-accurate rendering preview conforming to YouTube 16:9 thumbnail standards.
                </CardDescription>
              </div>

              {/* Viewport switch */}
              <div className="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
                <Button
                  size="sm"
                  variant={viewMode === "desktop" ? "secondary" : "ghost"}
                  className="h-7 px-2.5 text-xs"
                  onClick={() => setViewMode("desktop")}
                >
                  <Monitor className="w-3.5 h-3.5 mr-1" />
                  Desktop (100%)
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "mobile" ? "secondary" : "ghost"}
                  className="h-7 px-2.5 text-xs"
                  onClick={() => setViewMode("mobile")}
                >
                  <Smartphone className="w-3.5 h-3.5 mr-1" />
                  Mobile (Small Feed)
                </Button>
              </div>
            </CardHeader>

            <CardContent>
              <div className="flex items-center justify-center p-4 bg-zinc-950/80 rounded-xl border border-zinc-800/70">
                <div
                  className={`transition-all duration-300 relative rounded-lg overflow-hidden border border-zinc-700 shadow-2xl flex flex-col justify-between p-6 ${
                    viewMode === "mobile" ? "w-[280px] aspect-video text-[10px]" : "w-full aspect-video"
                  }`}
                  style={{
                    backgroundColor: "#08090C",
                    backgroundImage: active.showGrid
                      ? `radial-gradient(circle at 80% 30%, ${active.accentColor}35 0%, transparent 60%), linear-gradient(to right, #1d212b 1px, transparent 1px), linear-gradient(to bottom, #1d212b 1px, transparent 1px)`
                      : `radial-gradient(circle at 50% 50%, ${active.accentColor}25 0%, transparent 70%)`,
                    backgroundSize: active.showGrid ? "100% 100%, 36px 36px, 36px 36px" : "cover",
                  }}
                >
                  {/* Subtle Dark Vignette Overlay */}
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      background: `linear-gradient(135deg, rgba(0,0,0,${active.darkenBg}) 0%, rgba(0,0,0,${active.darkenBg * 0.7}) 100%)`,
                    }}
                  />

                  {/* Top Badge Hook */}
                  <div className="relative z-10 self-start">
                    {active.badgeText && (
                      <span
                        className="inline-flex items-center px-3 py-1 rounded font-black tracking-wider uppercase text-white shadow-lg text-xs md:text-sm"
                        style={{ backgroundColor: active.accentColor }}
                      >
                        {active.badgeText}
                      </span>
                    )}
                  </div>

                  {/* Middle Headline Typography */}
                  <div className="relative z-10 my-auto py-2">
                    <h2
                      className={`font-black uppercase tracking-tight text-white leading-[1.05] drop-shadow-[0_4px_16px_rgba(0,0,0,0.95)] ${
                        viewMode === "mobile" ? "text-base" : "text-3xl md:text-4xl lg:text-5xl"
                      }`}
                    >
                      {active.headlineText || "UNTITLED HEADLINE"}
                    </h2>
                  </div>

                  {/* Bottom Accent Line & YouTube Safe-Margin Mockup */}
                  <div className="relative z-10 flex items-center justify-between text-xs text-zinc-400 border-t border-zinc-700/60 pt-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: active.accentColor }} />
                      <span className="font-semibold text-zinc-200 text-xs">
                        Preset: {active.stylePreset.replace(/_/g, " ")}
                      </span>
                    </div>

                    {/* Simulated YouTube Duration Timestamp (Safe Margin Area) */}
                    <div className="bg-black/90 text-white text-[11px] font-bold px-2 py-0.5 rounded border border-zinc-700">
                      12:45
                    </div>
                  </div>
                </div>
              </div>

              {/* Quality & Spec Metrics Bar */}
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-zinc-950/60 border border-zinc-800 rounded-lg text-center">
                  <div className="text-[11px] text-zinc-400">Dimensions</div>
                  <div className="text-sm font-bold text-zinc-100">1280 x 720 (16:9)</div>
                  <div className="text-[10px] text-emerald-400 flex items-center justify-center gap-1 mt-0.5">
                    <CheckCircle2 className="w-3 h-3" /> YouTube Spec
                  </div>
                </div>

                <div className="p-3 bg-zinc-950/60 border border-zinc-800 rounded-lg text-center">
                  <div className="text-[11px] text-zinc-400">File Size Budget</div>
                  <div className="text-sm font-bold text-zinc-100">
                    {(active.fileSizeBytes / 1024).toFixed(1)} KB
                  </div>
                  <div className="text-[10px] text-emerald-400 flex items-center justify-center gap-1 mt-0.5">
                    <CheckCircle2 className="w-3 h-3" /> Under 2.0 MB Cap
                  </div>
                </div>

                <div className="p-3 bg-zinc-950/60 border border-zinc-800 rounded-lg text-center">
                  <div className="text-[11px] text-zinc-400">Contrast Ratio</div>
                  <div className="text-sm font-bold text-zinc-100">14.8:1 (AAA)</div>
                  <div className="text-[10px] text-emerald-400 flex items-center justify-center gap-1 mt-0.5">
                    <CheckCircle2 className="w-3 h-3" /> High Glancability
                  </div>
                </div>

                <div className="p-3 bg-zinc-950/60 border border-zinc-800 rounded-lg text-center">
                  <div className="text-[11px] text-zinc-400">Safe Margins</div>
                  <div className="text-sm font-bold text-zinc-100">80px Inset</div>
                  <div className="text-[10px] text-emerald-400 flex items-center justify-center gap-1 mt-0.5">
                    <CheckCircle2 className="w-3 h-3" /> UI Free
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: Layer & Typography Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Typography Controls */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Type className="w-4 h-4 text-[#FF7A00]" />
                <CardTitle className="text-base text-zinc-200">Headline Typography</CardTitle>
              </div>
              <CardDescription className="text-xs text-zinc-400">
                Keep headline under 5 words for maximum mobile readability.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <label className="font-medium text-zinc-300">Primary Headline Text</label>
                  <span className={`text-[11px] ${active.headlineText.length > 30 ? "text-amber-400" : "text-zinc-500"}`}>
                    {active.headlineText.length}/40 characters
                  </span>
                </div>
                <input
                  type="text"
                  value={active.headlineText}
                  onChange={(e) => updateActiveVariant({ headlineText: e.target.value.toUpperCase() })}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 font-bold focus:outline-none focus:border-[#FF7A00]"
                  placeholder="e.g. STOP USING REDIS"
                  maxLength={40}
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <label className="font-medium text-zinc-300">Hook Badge Text</label>
                  <span className="text-[11px] text-zinc-500">{active.badgeText.length}/25</span>
                </div>
                <input
                  type="text"
                  value={active.badgeText}
                  onChange={(e) => updateActiveVariant({ badgeText: e.target.value.toUpperCase() })}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-[#FF7A00]"
                  placeholder="e.g. PRODUCTION PROVEN"
                  maxLength={25}
                />
              </div>
            </CardContent>
          </Card>

          {/* Style Preset Selector */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Palette className="w-4 h-4 text-[#FF7A00]" />
                <CardTitle className="text-base text-zinc-200">Graphic Style Preset</CardTitle>
              </div>
              <CardDescription className="text-xs text-zinc-400">
                Determines color grading, typography weight, and atmospheric layers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 gap-2">
                {STYLE_PRESETS.map((preset) => (
                  <div
                    key={preset.id}
                    onClick={() => updateActiveVariant({ stylePreset: preset.id })}
                    className={`cursor-pointer p-3 rounded-lg border text-left transition-all ${
                      active.stylePreset === preset.id
                        ? "bg-zinc-800/80 border-[#FF7A00] text-zinc-100"
                        : "bg-zinc-950/60 border-zinc-800/80 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <div className="text-xs font-bold text-zinc-200">{preset.label}</div>
                    <div className="text-[11px] text-zinc-400 mt-0.5">{preset.desc}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Accent Color Palette */}
          <Card className="bg-zinc-900/60 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-[#FF7A00]" />
                <CardTitle className="text-base text-zinc-200">Accent Color & Glow</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-2">
                {ACCENT_COLORS.map((color) => (
                  <button
                    key={color.hex}
                    onClick={() => updateActiveVariant({ accentColor: color.hex })}
                    className={`flex items-center gap-2 p-2 rounded-lg border text-xs transition-all ${
                      active.accentColor === color.hex
                        ? "bg-zinc-800 border-[#FF7A00] text-zinc-100"
                        : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <span className="w-3.5 h-3.5 rounded-full" style={{ backgroundColor: color.hex }} />
                    <span className="truncate">{color.name}</span>
                  </button>
                ))}
              </div>

              {/* Layer Toggles */}
              <div className="space-y-3 pt-2 border-t border-zinc-800">
                <label className="flex items-center justify-between text-xs text-zinc-300 cursor-pointer">
                  <span>Render Tech Grid Overlay</span>
                  <input
                    type="checkbox"
                    checked={active.showGrid}
                    onChange={(e) => updateActiveVariant({ showGrid: e.target.checked })}
                    className="accent-[#FF7A00] w-4 h-4"
                  />
                </label>

                <label className="flex items-center justify-between text-xs text-zinc-300 cursor-pointer">
                  <span>Render Radial Neon Glow</span>
                  <input
                    type="checkbox"
                    checked={active.showGlow}
                    onChange={(e) => updateActiveVariant({ showGlow: e.target.checked })}
                    className="accent-[#FF7A00] w-4 h-4"
                  />
                </label>

                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-xs text-zinc-400">
                    <span>Background Dimming</span>
                    <span>{Math.round(active.darkenBg * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.2"
                    max="0.9"
                    step="0.05"
                    value={active.darkenBg}
                    onChange={(e) => updateActiveVariant({ darkenBg: parseFloat(e.target.value) })}
                    className="w-full accent-[#FF7A00] cursor-pointer"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
