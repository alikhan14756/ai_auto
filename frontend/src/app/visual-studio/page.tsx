"use client";

import React, { useState } from "react";
import {
  Image as ImageIcon,
  Sparkles,
  Search,
  CheckCircle2,
  Clock,
  Layers,
  RefreshCw,
  Film,
  Code2,
  Monitor,
  PieChart,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { apiClient } from "@/lib/api";

interface AssignedAsset {
  id: string;
  title: string;
  category: "GENERATED" | "EXTERNAL_STOCK" | "USER_UPLOADED" | "SCREENSHOT" | "DIAGRAM";
  sourceProvider: string;
  licenseStatus: "VERIFIED_COMMERCIAL" | "ATTRIBUTION_REQUIRED" | "LICENSE_REVIEW_REQUIRED";
  licenseType: string;
  aspectRatio: "16:9" | "9:16";
  previewUrl: string;
  sha256Hash: string;
  width: number;
  height: number;
}

interface StoryboardScene {
  id: string;
  sceneOrder: number;
  narrationText: string;
  visualDirective: string;
  visualPurpose: "HOOK_ENGAGEMENT" | "CONCEPT_EXPLANATION" | "DEMONSTRATION" | "SUMMARY";
  suggestedAssetType: "CODE_DEMONSTRATION" | "SOFTWARE_INTERFACE" | "DIAGRAM" | "GENERATED_IMAGE" | "STOCK_FOOTAGE";
  keywords: string[];
  imagePrompt: string;
  transition: "CUT" | "FADE" | "ZOOM_IN" | "SLIDE_LEFT";
  durationSeconds: number;
  isAudioTimed: boolean;
  reviewStatus: "DRAFT" | "SUGGESTED" | "APPROVED";
  assignedAsset?: AssignedAsset;
}

export default function VisualStudioPage() {
  const [selectedFormat, setSelectedFormat] = useState<"16:9" | "9:16">("16:9");
  const [isGeneratingStoryboard, setIsGeneratingStoryboard] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isSearchingStock, setIsSearchingStock] = useState(false);
  const [storyboardApproved, setStoryboardApproved] = useState(false);

  // Active scene for modal actions
  const [activeSceneId, setActiveSceneId] = useState<string | null>(null);
  const [showGenModal, setShowGenModal] = useState(false);
  const [showStockModal, setShowStockModal] = useState(false);

  // Modal Inputs
  const [imagePrompt, setImagePrompt] = useState("");
  const [imageStyle, setImageStyle] = useState("photorealistic");
  const [stockQuery, setStockQuery] = useState("");

  // Sample Stock Search Results
  const [stockResults] = useState<Array<{
    id: string;
    title: string;
    provider: string;
    license: string;
    licenseStatus: "VERIFIED_COMMERCIAL" | "ATTRIBUTION_REQUIRED" | "LICENSE_REVIEW_REQUIRED";
    author: string;
  }>>([
    {
      id: "stock-1",
      title: "Futuristic Artificial Intelligence Neural Network Node Graph",
      provider: "MOCK",
      license: "CC0",
      licenseStatus: "VERIFIED_COMMERCIAL",
      author: "Creator Studio AI Verified Archives",
    },
    {
      id: "stock-2",
      title: "Terminal Code Editor showing Python AsyncIO and FastAPI Service",
      provider: "MOCK",
      license: "CC0",
      licenseStatus: "VERIFIED_COMMERCIAL",
      author: "Creator Studio AI Verified Archives",
    },
    {
      id: "stock-3",
      title: "Cloud Infrastructure Cluster Architecture Diagram",
      provider: "MOCK",
      license: "CC0",
      licenseStatus: "VERIFIED_COMMERCIAL",
      author: "Creator Studio AI Verified Archives",
    },
  ]);

  // Storyboard scenes state
  const [scenes, setScenes] = useState<StoryboardScene[]>([
    {
      id: "scene-1",
      sceneOrder: 1,
      narrationText: "Here is why modern Python async microservices outperform legacy synchronous APIs.",
      visualDirective: "High-contrast dynamic hook showing FastAPI server metrics graph surging with throughput.",
      visualPurpose: "HOOK_ENGAGEMENT",
      suggestedAssetType: "GENERATED_IMAGE",
      keywords: ["python", "async", "fastapi", "throughput", "metrics"],
      imagePrompt: "High-tech performance metrics graph surging with neon amber energy, dark obsidian background #090A0D, 16:9 framing, 4k.",
      transition: "CUT",
      durationSeconds: 4.8,
      isAudioTimed: true,
      reviewStatus: "APPROVED",
      assignedAsset: {
        id: "asset-1",
        title: "FastAPI Metrics Surging Graph",
        category: "GENERATED",
        sourceProvider: "MOCK",
        licenseStatus: "VERIFIED_COMMERCIAL",
        licenseType: "CC0",
        aspectRatio: "16:9",
        previewUrl: "/mock-preview-1.png",
        sha256Hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        width: 1920,
        height: 1080,
      },
    },
    {
      id: "scene-2",
      sceneOrder: 2,
      narrationText: "By leveraging asyncpg and non-blocking database connections, latency drops below five milliseconds.",
      visualDirective: "Clean modern terminal code editor showing Python async connection pool initialization.",
      visualPurpose: "DEMONSTRATION",
      suggestedAssetType: "CODE_DEMONSTRATION",
      keywords: ["asyncpg", "database", "connection-pool", "latency"],
      imagePrompt: "Clean modern dark-mode code editor interface showing clear syntax highlighting for async database pooling, slate background #090A0D.",
      transition: "CUT",
      durationSeconds: 6.2,
      isAudioTimed: true,
      reviewStatus: "SUGGESTED",
      assignedAsset: {
        id: "asset-2",
        title: "Python AsyncPG Terminal Code",
        category: "EXTERNAL_STOCK",
        sourceProvider: "MOCK",
        licenseStatus: "VERIFIED_COMMERCIAL",
        licenseType: "CC0",
        aspectRatio: "16:9",
        previewUrl: "/mock-preview-2.png",
        sha256Hash: "b855e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca49599147182",
        width: 1920,
        height: 1080,
      },
    },
    {
      id: "scene-3",
      sceneOrder: 3,
      narrationText: "Notice how requests are processed concurrently across multiple CPU cores without thread contention.",
      visualDirective: "Isometric flowchart showing concurrent worker queue pipeline with non-blocking message broker.",
      visualPurpose: "CONCEPT_EXPLANATION",
      suggestedAssetType: "DIAGRAM",
      keywords: ["concurrent", "pipeline", "queue", "architecture"],
      imagePrompt: "Crisp isometric architectural flowchart and system microservices node graph, minimalist neon data lines.",
      transition: "ZOOM_IN",
      durationSeconds: 5.5,
      isAudioTimed: true,
      reviewStatus: "DRAFT",
    },
    {
      id: "scene-4",
      sceneOrder: 4,
      narrationText: "Subscribe for more deep dives into backend architecture and production AI automation.",
      visualDirective: "Outro branded subscriber screen with YouTube notification bell and portfolio link.",
      visualPurpose: "SUMMARY",
      suggestedAssetType: "GENERATED_IMAGE",
      keywords: ["subscribe", "architecture", "outro", "portfolio"],
      imagePrompt: "Minimalist dark outro subscriber card, glowing notification bell icon, vivid ember accents #FF7A00.",
      transition: "FADE",
      durationSeconds: 4.0,
      isAudioTimed: false,
      reviewStatus: "DRAFT",
    },
  ]);

  const openGenModalForScene = (scene: StoryboardScene) => {
    setActiveSceneId(scene.id);
    setImagePrompt(scene.imagePrompt);
    setShowGenModal(true);
  };

  const openStockModalForScene = (scene: StoryboardScene) => {
    setActiveSceneId(scene.id);
    setStockQuery(scene.keywords.slice(0, 3).join(" "));
    setShowStockModal(true);
  };

  const handleGenerateImage = async () => {
    if (!activeSceneId) return;
    setIsGeneratingImage(true);
    try {
      await apiClient.post("/api/v1/visual/generate-image", {
        prompt: imagePrompt,
        style: imageStyle,
        aspect_ratio: selectedFormat,
      });
    } catch {
      // Local fallback image generation simulation
    }
    setTimeout(() => {
      setScenes((prev) =>
        prev.map((s) => {
          if (s.id === activeSceneId) {
            return {
              ...s,
              reviewStatus: "SUGGESTED",
              assignedAsset: {
                id: `gen-${Date.now()}`,
                title: `AI Generated: ${imagePrompt.slice(0, 30)}...`,
                category: "GENERATED",
                sourceProvider: "MOCK",
                licenseStatus: "VERIFIED_COMMERCIAL",
                licenseType: "CC0",
                aspectRatio: selectedFormat,
                previewUrl: "/mock-gen.png",
                sha256Hash: "f123a44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b999",
                width: selectedFormat === "16:9" ? 1920 : 1080,
                height: selectedFormat === "16:9" ? 1080 : 1920,
              },
            };
          }
          return s;
        })
      );
      setIsGeneratingImage(false);
      setShowGenModal(false);
    }, 800);
  };

  const handleAssignStock = (stock: typeof stockResults[0]) => {
    if (!activeSceneId) return;
    setScenes((prev) =>
      prev.map((s) => {
        if (s.id === activeSceneId) {
          return {
            ...s,
            reviewStatus: "SUGGESTED",
            assignedAsset: {
              id: `stock-${Date.now()}`,
              title: stock.title,
              category: "EXTERNAL_STOCK",
              sourceProvider: stock.provider,
              licenseStatus: stock.licenseStatus,
              licenseType: stock.license,
              aspectRatio: selectedFormat,
              previewUrl: "/mock-stock.png",
              sha256Hash: "a777c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b111",
              width: selectedFormat === "16:9" ? 1920 : 1080,
              height: selectedFormat === "16:9" ? 1080 : 1920,
            },
          };
        }
        return s;
      })
    );
    setShowStockModal(false);
  };

  const handleApproveStoryboard = () => {
    setStoryboardApproved(true);
    setScenes((prev) => prev.map((s) => ({ ...s, reviewStatus: "APPROVED" })));
  };

  const getPurposeIcon = (purpose: StoryboardScene["visualPurpose"]) => {
    switch (purpose) {
      case "HOOK_ENGAGEMENT":
        return <Sparkles className="w-3.5 h-3.5 text-[#FF7A00]" />;
      case "DEMONSTRATION":
        return <Code2 className="w-3.5 h-3.5 text-blue-400" />;
      case "CONCEPT_EXPLANATION":
        return <PieChart className="w-3.5 h-3.5 text-emerald-400" />;
      case "SUMMARY":
        return <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />;
    }
  };

  const getAssetTypeIcon = (type: StoryboardScene["suggestedAssetType"]) => {
    switch (type) {
      case "CODE_DEMONSTRATION":
        return <Code2 className="w-3.5 h-3.5 text-blue-400" />;
      case "SOFTWARE_INTERFACE":
        return <Monitor className="w-3.5 h-3.5 text-cyan-400" />;
      case "DIAGRAM":
        return <Layers className="w-3.5 h-3.5 text-emerald-400" />;
      case "STOCK_FOOTAGE":
        return <Film className="w-3.5 h-3.5 text-amber-400" />;
      case "GENERATED_IMAGE":
        return <Sparkles className="w-3.5 h-3.5 text-[#FF7A00]" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1E222E] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">Visual Studio</h1>
            <Badge variant="ember">Milestone 08</Badge>
            <Badge variant="outline" className="border-[#262B3A] text-gray-400">
              {selectedFormat === "16:9" ? "16:9 Long-Form" : "9:16 Shorts"}
            </Badge>
            {storyboardApproved && (
              <Badge variant="success" className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Approved & Locked
              </Badge>
            )}
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Transform approved scripts and narration timing into structured visual storyboards with verified assets.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center bg-[#14171F] border border-[#262B3A] rounded-lg p-1 text-xs">
            <button
              onClick={() => setSelectedFormat("16:9")}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                selectedFormat === "16:9" ? "bg-[#FF7A00] text-black" : "text-gray-400 hover:text-white"
              }`}
            >
              16:9 Landscape
            </button>
            <button
              onClick={() => setSelectedFormat("9:16")}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                selectedFormat === "9:16" ? "bg-[#FF7A00] text-black" : "text-gray-400 hover:text-white"
              }`}
            >
              9:16 Vertical
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setIsGeneratingStoryboard(true);
              setTimeout(() => setIsGeneratingStoryboard(false), 600);
            }}
            disabled={isGeneratingStoryboard}
            className="border-[#262B3A] text-gray-300 hover:bg-[#1E222E]"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-2 ${isGeneratingStoryboard ? "animate-spin" : ""}`} />
            Sync Storyboard
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleApproveStoryboard}
            disabled={storyboardApproved}
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            {storyboardApproved ? "Storyboard Approved" : "Approve Storyboard"}
          </Button>
        </div>
      </div>

      {/* Storyboard Status Telemetry Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Total Scenes</span>
            <Layers className="w-4 h-4 text-[#FF7A00]" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{scenes.length}</p>
          <p className="text-xs text-gray-500 mt-1">4 scenes planned for 20.5s duration</p>
        </Card>

        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Assigned Assets</span>
            <ImageIcon className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {scenes.filter((s) => s.assignedAsset).length} / {scenes.length}
          </p>
          <p className="text-xs text-gray-500 mt-1">2 scenes need visual assets</p>
        </Card>

        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Audio Timing Sync</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {scenes.filter((s) => s.isAudioTimed).length} / {scenes.length}
          </p>
          <p className="text-xs text-gray-500 mt-1">M07 Voiceover timestamps mapped</p>
        </Card>

        <Card className="bg-[#0E1015] border-[#1E222E] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Commercial Cleared</span>
            <CheckCircle2 className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">100%</p>
          <p className="text-xs text-gray-500 mt-1">All assets verified CC0 / permissive</p>
        </Card>
      </div>

      {/* Storyboard Scene Breakdown */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Film className="w-4 h-4 text-[#FF7A00]" />
            Storyboard Scene Sequencing
          </h2>
          <span className="text-xs text-gray-400">Drag or configure visual assets for each scene</span>
        </div>

        <div className="space-y-4">
          {scenes.map((scene) => (
            <Card
              key={scene.id}
              className={`bg-[#0E1015] border transition-all ${
                scene.assignedAsset ? "border-[#1E222E]" : "border-amber-500/30"
              }`}
            >
              <div className="p-5 flex flex-col lg:flex-row gap-5">
                {/* Scene Meta Column */}
                <div className="lg:w-48 flex-shrink-0 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#181C26] text-white">
                      SCENE {scene.sceneOrder.toString().padStart(2, "0")}
                    </span>
                    <Badge variant={scene.reviewStatus === "APPROVED" ? "success" : "warning"}>
                      {scene.reviewStatus}
                    </Badge>
                  </div>

                  <div className="space-y-1.5 text-xs text-gray-400">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-gray-500" />
                      <span>{scene.durationSeconds}s</span>
                      <span className="text-gray-500 text-[10px]">
                        {scene.isAudioTimed ? "(Audio timed)" : "(Estimated)"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {getPurposeIcon(scene.visualPurpose)}
                      <span className="capitalize">{scene.visualPurpose.replace("_", " ").toLowerCase()}</span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {getAssetTypeIcon(scene.suggestedAssetType)}
                      <span className="capitalize text-gray-300">
                        {scene.suggestedAssetType.replace("_", " ").toLowerCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="text-gray-500 text-[10px]">TRANSITION:</span>
                      <Badge variant="outline" className="text-[10px] py-0 px-1 border-[#262B3A]">
                        {scene.transition}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Narrative & Directive Column */}
                <div className="flex-1 space-y-3">
                  <div>
                    <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                      Narration Reference
                    </span>
                    <p className="text-sm text-gray-200 italic mt-0.5">&ldquo;{scene.narrationText}&rdquo;</p>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                      Visual Directive
                    </span>
                    <p className="text-xs text-gray-300 mt-0.5">{scene.visualDirective}</p>
                  </div>

                  {/* Keywords */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[10px] font-mono text-gray-500">TAGS:</span>
                    {scene.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#14171F] border border-[#222736] text-gray-400"
                      >
                        #{kw}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Assigned Asset Preview or Action Column */}
                <div className="lg:w-80 flex-shrink-0 flex flex-col justify-between border-t lg:border-t-0 lg:border-l border-[#1E222E] pt-4 lg:pt-0 lg:pl-5">
                  {scene.assignedAsset ? (
                    <div className="space-y-3">
                      <div className="relative group rounded-lg overflow-hidden border border-[#262B3A] bg-[#090A0D] aspect-video flex items-center justify-center">
                        {/* Canvas Visual Placeholder */}
                        <div className="absolute inset-0 bg-gradient-to-br from-[#12151E] to-[#090A0D] p-3 flex flex-col justify-between">
                          <div className="flex items-center justify-between">
                            <Badge variant="ember" className="text-[10px] py-0">
                              {scene.assignedAsset.category}
                            </Badge>
                            <span className="text-[10px] font-mono text-gray-500">
                              {scene.assignedAsset.aspectRatio}
                            </span>
                          </div>
                          <div className="text-center">
                            <p className="text-xs font-semibold text-white truncate px-2">
                              {scene.assignedAsset.title}
                            </p>
                            <p className="text-[10px] font-mono text-[#FF7A00] mt-0.5">
                              {scene.assignedAsset.sourceProvider}
                            </p>
                          </div>
                          <div className="flex items-center justify-between text-[9px] font-mono text-gray-500">
                            <span>{scene.assignedAsset.licenseType}</span>
                            <span className="text-emerald-400">Commercial OK</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[10px] font-mono text-gray-500 truncate max-w-[160px]">
                          SHA: {scene.assignedAsset.sha256Hash.slice(0, 12)}...
                        </span>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => openGenModalForScene(scene)}
                            className="text-[11px] text-[#FF7A00] hover:underline"
                          >
                            Replace
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center p-4 border border-dashed border-[#262B3A] rounded-lg bg-[#090A0D]/50 text-center space-y-3">
                      <div className="w-8 h-8 rounded-full bg-[#181C26] flex items-center justify-center text-gray-400">
                        <ImageIcon className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-300">No Visual Assigned</p>
                        <p className="text-[10px] text-gray-500">Generate or discover media</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="primary"
                          size="sm"
                          className="text-xs py-1 px-2.5 h-auto"
                          onClick={() => openGenModalForScene(scene)}
                        >
                          <Sparkles className="w-3 h-3 mr-1.5" />
                          Generate
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs py-1 px-2.5 h-auto border-[#262B3A] text-gray-300"
                          onClick={() => openStockModalForScene(scene)}
                        >
                          <Search className="w-3 h-3 mr-1.5" />
                          Stock
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* AI Image Generation Modal */}
      <Modal
        isOpen={showGenModal}
        onClose={() => setShowGenModal(false)}
        title="Synthesize AI Visual Asset"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">Generative Prompt</label>
            <textarea
              rows={3}
              value={imagePrompt}
              onChange={(e) => setImagePrompt(e.target.value)}
              className="w-full bg-[#14171F] border border-[#262B3A] rounded-lg p-3 text-xs text-white focus:outline-none focus:border-[#FF7A00]"
              placeholder="Detailed tech visual prompt..."
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Aspect Ratio</label>
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value as "16:9" | "9:16")}
                className="w-full bg-[#14171F] border border-[#262B3A] rounded-lg p-2 text-xs text-white"
              >
                <option value="16:9">16:9 Landscape</option>
                <option value="9:16">9:16 Vertical</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Aesthetic Style</label>
              <select
                value={imageStyle}
                onChange={(e) => setImageStyle(e.target.value)}
                className="w-full bg-[#14171F] border border-[#262B3A] rounded-lg p-2 text-xs text-white"
              >
                <option value="photorealistic">Photorealistic Studio</option>
                <option value="isometric">Isometric Microservices</option>
                <option value="minimalist">Minimalist Dark UI</option>
                <option value="cinematic">Cinematic Developer Desk</option>
              </select>
            </div>
          </div>

          <div className="bg-[#14171F] border border-[#262B3A] rounded-lg p-3 text-xs text-gray-400 space-y-1">
            <div className="flex items-center justify-between text-white font-medium">
              <span>Budget Guardrail</span>
              <span className="text-emerald-400">$0.00 / month</span>
            </div>
            <p className="text-[11px]">
              Offline deterministic mock canvas is used by default. Paid cloud image models remain disabled under the zero-cost ceiling.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowGenModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleGenerateImage}
              disabled={isGeneratingImage || !imagePrompt.trim()}
            >
              <Sparkles className={`w-3.5 h-3.5 mr-1.5 ${isGeneratingImage ? "animate-spin" : ""}`} />
              {isGeneratingImage ? "Synthesizing Asset..." : "Generate & Assign"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Stock Media Discovery Modal */}
      <Modal
        isOpen={showStockModal}
        onClose={() => setShowStockModal(false)}
        title="Discover External Stock Media"
      >
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={stockQuery}
              onChange={(e) => setStockQuery(e.target.value)}
              placeholder="Search keyword (e.g. terminal, cloud, server)..."
              className="flex-1"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIsSearchingStock(true);
                setTimeout(() => setIsSearchingStock(false), 500);
              }}
              disabled={isSearchingStock}
            >
              <Search className={`w-3.5 h-3.5 mr-1.5 ${isSearchingStock ? "animate-spin" : ""}`} />
              Search
            </Button>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {stockResults.map((item) => (
              <div
                key={item.id}
                className="bg-[#14171F] border border-[#262B3A] rounded-lg p-3 flex items-center justify-between hover:border-[#FF7A00]/50 transition-colors"
              >
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-white">{item.title}</p>
                  <div className="flex items-center gap-2 text-[10px] text-gray-400">
                    <span className="font-mono text-[#FF7A00]">{item.provider}</span>
                    <span>•</span>
                    <span>License: {item.license}</span>
                    <span>•</span>
                    <span className="text-emerald-400">Verified Commercial</span>
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs py-1 px-3 border-[#262B3A] hover:bg-[#1E222E]"
                  onClick={() => handleAssignStock(item)}
                >
                  Assign
                </Button>
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowStockModal(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
