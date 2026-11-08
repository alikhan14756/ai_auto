"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Mic2,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  CheckCircle2,
  Download,
  Sparkles,
  Sliders,
  Radio,
  FileAudio,
  Layers,
  ShieldCheck,
  RefreshCw,
  Clock,
  Info,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";

interface VoiceOption {
  id: string;
  name: string;
  locale: string;
  gender: "MALE" | "FEMALE";
  description: string;
  provider: string;
}

interface SceneAudioChunk {
  sceneId: string;
  order: number;
  title: string;
  narration: string;
  durationSeconds: number;
  wordCount: number;
  loudnessLufs: number;
  status: "READY" | "REGENERATING";
}

interface NarrationTrackState {
  id: string;
  version: number;
  scriptVersion: number;
  durationSeconds: number;
  fileFormat: string;
  sampleRate: number;
  loudnessLufs: number;
  isApproved: boolean;
  qualityStatus: "PASSED" | "WARNING" | "FAILED";
  chunks: SceneAudioChunk[];
}

const AVAILABLE_VOICES: VoiceOption[] = [
  {
    id: "en-US-ChristopherNeural",
    name: "Christopher (Tech Lead)",
    locale: "en-US",
    gender: "MALE",
    description: "Deep, authoritative, and calm pacing. Recommended for architecture tutorials.",
    provider: "Microsoft Edge Neural",
  },
  {
    id: "en-US-GuyNeural",
    name: "Guy (Practical Engineer)",
    locale: "en-US",
    gender: "MALE",
    description: "Conversational, practical, and direct delivery. Great for code walk-throughs.",
    provider: "Microsoft Edge Neural",
  },
  {
    id: "en-US-JennyNeural",
    name: "Jenny (Fast Explainer)",
    locale: "en-US",
    gender: "FEMALE",
    description: "Crisp, energetic, high-retention tone tailored for rapid tutorials and Shorts.",
    provider: "Microsoft Edge Neural",
  },
  {
    id: "en-GB-RyanNeural",
    name: "Ryan (British Architecture)",
    locale: "en-GB",
    gender: "MALE",
    description: "British English accent offering formal technical authority.",
    provider: "Microsoft Edge Neural",
  },
];

const INITIAL_CHUNKS: SceneAudioChunk[] = [
  {
    sceneId: "scene_01",
    order: 1,
    title: "Hook: The Redis Queue Trap",
    narration:
      "Most developers think building an autonomous background queue requires spinning up Redis, Celery, or RabbitMQ. But in PostgreSQL, there is a hidden locking mechanism that handles thousands of jobs per second with zero extra infrastructure.",
    durationSeconds: 12.4,
    wordCount: 36,
    loudnessLufs: -14.1,
    status: "READY",
  },
  {
    sceneId: "scene_02",
    order: 2,
    title: "Mechanism: SELECT FOR UPDATE SKIP LOCKED",
    narration:
      "PostgreSQL 9.5 introduced SKIP LOCKED, allowing concurrent background workers to safely claim queued rows without waiting on locks or colliding with other processes in the worker pool.",
    durationSeconds: 10.8,
    wordCount: 29,
    loudnessLufs: -13.9,
    status: "READY",
  },
  {
    sceneId: "scene_03",
    order: 3,
    title: "Benchmarks: 5,000 Jobs Per Second",
    narration:
      "In empirical production benchmarks, PostgreSQL handles up to 5,000 job dispatches per second on standard cloud instances, while providing guaranteed ACID rollback if a worker daemon crashes.",
    durationSeconds: 11.2,
    wordCount: 28,
    loudnessLufs: -14.0,
    status: "READY",
  },
  {
    sceneId: "scene_04",
    order: 4,
    title: "Conclusion & Call to Action",
    narration:
      "By using PostgreSQL as your single source of truth for both application data and background tasks, you eliminate data drift and slash cloud infrastructure costs. Star the repository to grab the starter code.",
    durationSeconds: 9.6,
    wordCount: 32,
    loudnessLufs: -14.2,
    status: "READY",
  },
];

export default function VoiceStudioPage() {
  const [selectedVoice, setSelectedVoice] = useState<string>("en-US-ChristopherNeural");
  const [speedRatio, setSpeedRatio] = useState<number>(1.0);
  const [pitchSemitones, setPitchSemitones] = useState<number>(0.0);
  const [localeFilter, setLocaleFilter] = useState<string>("ALL");
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationProgress, setGenerationProgress] = useState<number>(0);
  const [generationStage, setGenerationStage] = useState<string>("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Active track state
  const [track, setTrack] = useState<NarrationTrackState>({
    id: "track_882a_01",
    version: 1,
    scriptVersion: 1,
    durationSeconds: 44.0,
    fileFormat: "wav",
    sampleRate: 24000,
    loudnessLufs: -14.0,
    isApproved: false,
    qualityStatus: "PASSED",
    chunks: INITIAL_CHUNKS,
  });

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Playback timer simulation
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= track.durationSeconds) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 1;
        });
      }, 1000 / playbackRate);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, track.durationSeconds, playbackRate]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleTogglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleAuditionVoice = (voiceId: string) => {
    showToast(`Auditioning voice sample for ${voiceId}...`);
    // Beep / audition simulation
    try {
      const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(440, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 1.2);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 1.2);
    } catch {
      // AudioContext unavailable in non-interactive environment
    }
  };

  const handleSynthesizeAll = () => {
    setIsGenerating(true);
    setGenerationProgress(10);
    setGenerationStage("Initializing TTS engine & resolving voice profile...");

    setTimeout(() => {
      setGenerationProgress(35);
      setGenerationStage("Synthesizing scene audio chunks (1 to 4)...");
    }, 700);

    setTimeout(() => {
      setGenerationProgress(70);
      setGenerationStage("Concatenating WAV chunks & inserting 350ms pauses...");
    }, 1400);

    setTimeout(() => {
      setGenerationProgress(90);
      setGenerationStage("Evaluating audio quality, duration ratio & LUFS compliance...");
    }, 2000);

    setTimeout(() => {
      setGenerationProgress(100);
      setGenerationStage("Narration track mastered and ready!");
      setIsGenerating(false);
      setTrack((prev) => ({
        ...prev,
        version: prev.version + 1,
        isApproved: false,
      }));
      showToast("Master narration generated successfully!");
    }, 2600);
  };

  const handleRegenerateChunk = (sceneId: string) => {
    setTrack((prev) => ({
      ...prev,
      chunks: prev.chunks.map((c) =>
        c.sceneId === sceneId ? { ...c, status: "REGENERATING" } : c
      ),
    }));

    showToast(`Regenerating audio for ${sceneId}...`);

    setTimeout(() => {
      setTrack((prev) => ({
        ...prev,
        chunks: prev.chunks.map((c) =>
          c.sceneId === sceneId
            ? { ...c, status: "READY", durationSeconds: Number((c.durationSeconds + 0.3).toFixed(1)) }
            : c
        ),
      }));
      showToast(`Audio chunk ${sceneId} updated and master re-stitched.`);
    }, 1200);
  };

  const handleApproveTrack = () => {
    setTrack((prev) => ({ ...prev, isApproved: true }));
    showToast("Narration track approved! Project advanced to VOICE_APPROVED.");
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const filteredVoices = AVAILABLE_VOICES.filter((v) => {
    if (localeFilter === "ALL") return true;
    return v.locale.toLowerCase().startsWith(localeFilter.toLowerCase());
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-lg border border-[#FF7A00]/40 bg-[#161922] px-4 py-3 text-sm text-white shadow-2xl shadow-[#FF7A00]/20 animate-in fade-in slide-in-from-bottom-2">
          <Sparkles className="h-4 w-4 text-[#FF7A00]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header & Broadcast Standards */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-[#262B3D] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#FF7A00]">
              Milestone 07 Active
            </span>
            <span className="text-xs text-[#8B949E]">•</span>
            <span className="text-xs text-[#8B949E]">AI Production Pipeline</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Mic2 className="h-6 w-6 text-[#FF7A00]" />
            Voice Studio &amp; Audio Mastering
          </h1>
          <p className="mt-1 text-sm text-[#8B949E]">
            High-fidelity neural voice synthesis, scene-by-scene audio alignment, and broadcast-standard mastering.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-[#262B3D] bg-[#12141A] px-3 py-1.5 text-xs text-[#E6EDF3]">
            <Radio className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
            <span>Engine: <strong>Edge Neural (Free)</strong></span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-[#262B3D] bg-[#12141A] px-3 py-1.5 text-xs text-[#E6EDF3]">
            <ShieldCheck className="h-3.5 w-3.5 text-[#FF7A00]" />
            <span>Loudness: <strong>-14.0 LUFS</strong></span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-[#262B3D] bg-[#12141A] px-3 py-1.5 text-xs text-emerald-400">
            <span>Budget: <strong>$0.00 / Zero Cost</strong></span>
          </div>
        </div>
      </div>

      {/* Generation Progress Bar */}
      {isGenerating && (
        <Card className="border-[#FF7A00]/50 bg-[#161922] p-4 animate-in fade-in">
          <div className="flex items-center justify-between text-xs text-white mb-2">
            <span className="font-semibold text-[#FF7A00] flex items-center gap-2">
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              {generationStage}
            </span>
            <span>{generationProgress}%</span>
          </div>
          <ProgressBar value={generationProgress} max={100} variant="ember" />
        </Card>
      )}

      {/* Top Configuration Grid: Voice Selection & Project Script */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Voice Selector Card */}
        <Card className="lg:col-span-2 border-[#262B3D] bg-[#12141A] p-5">
          <div className="flex items-center justify-between border-b border-[#262B3D] pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-[#FF7A00]" />
              <h2 className="text-base font-semibold text-white">Voice Model &amp; Tone Profile</h2>
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-[#8B949E]">Filter:</span>
              {["ALL", "en-US", "en-GB"].map((loc) => (
                <button
                  key={loc}
                  onClick={() => setLocaleFilter(loc)}
                  className={`rounded px-2 py-0.5 font-medium transition-colors ${
                    localeFilter === loc
                      ? "bg-[#FF7A00] text-black"
                      : "bg-[#1C212E] text-[#8B949E] hover:text-white"
                  }`}
                >
                  {loc}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
            {filteredVoices.map((voice) => {
              const isSelected = selectedVoice === voice.id;
              return (
                <div
                  key={voice.id}
                  onClick={() => setSelectedVoice(voice.id)}
                  className={`group relative flex flex-col justify-between rounded-lg border p-3.5 transition-all cursor-pointer ${
                    isSelected
                      ? "border-[#FF7A00] bg-[#1C212E] shadow-sm shadow-[#FF7A00]/10"
                      : "border-[#262B3D] bg-[#161922] hover:border-[#383F57]"
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-semibold text-sm text-white">{voice.name}</span>
                      <Badge variant={voice.gender === "MALE" ? "neutral" : "ember"} size="sm">
                        {voice.gender}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-[#8B949E] line-clamp-2">{voice.description}</p>
                  </div>

                  <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#262B3D]/60 text-[11px] text-[#8B949E]">
                    <span className="flex items-center gap-1">
                      <Radio className="h-3 w-3 text-emerald-400" />
                      {voice.locale}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAuditionVoice(voice.id);
                      }}
                      className="flex items-center gap-1 text-[#FF7A00] hover:underline"
                    >
                      <Play className="h-3 w-3 fill-[#FF7A00]" />
                      Audition
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Speed & Pitch Controls */}
          <div className="rounded-lg border border-[#262B3D] bg-[#161922] p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-xs text-white mb-1.5">
                  <span className="font-medium text-[#8B949E]">Speaking Speed Multiplier:</span>
                  <span className="font-bold text-[#FF7A00]">{speedRatio.toFixed(2)}x (~{Math.round(140 * speedRatio)} WPM)</span>
                </div>
                <input
                  type="range"
                  min="0.75"
                  max="1.35"
                  step="0.05"
                  value={speedRatio}
                  onChange={(e) => setSpeedRatio(parseFloat(e.target.value))}
                  className="w-full accent-[#FF7A00] bg-[#262B3D] h-1.5 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-white mb-1.5">
                  <span className="font-medium text-[#8B949E]">Pitch Shift:</span>
                  <span className="font-bold text-[#FF7A00]">
                    {pitchSemitones > 0 ? `+${pitchSemitones}` : pitchSemitones} semitones
                  </span>
                </div>
                <input
                  type="range"
                  min="-4"
                  max="4"
                  step="1"
                  value={pitchSemitones}
                  onChange={(e) => setPitchSemitones(parseFloat(e.target.value))}
                  className="w-full accent-[#FF7A00] bg-[#262B3D] h-1.5 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Script Selection & Generation Card */}
        <Card className="border-[#262B3D] bg-[#12141A] p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 border-b border-[#262B3D] pb-3 mb-4">
              <FileAudio className="h-4 w-4 text-[#FF7A00]" />
              <h2 className="text-base font-semibold text-white">Approved Script Target</h2>
            </div>

            <div className="rounded-lg border border-[#262B3D] bg-[#161922] p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Project:</span>
                <span className="text-xs font-semibold text-white">PostgreSQL Queues in Depth</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Script Version:</span>
                <Badge variant="ember" size="sm">
                  Script v1 (Locked)
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Spoken Word Count:</span>
                <span className="text-xs font-medium text-white">125 words (~54 sec)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#8B949E]">Storyboard Scenes:</span>
                <span className="text-xs font-medium text-white">{track.chunks.length} scenes</span>
              </div>
              <div className="flex items-center justify-between border-t border-[#262B3D] pt-2">
                <span className="text-xs text-[#8B949E]">Voice Status:</span>
                <Badge variant={track.isApproved ? "success" : "warning"} size="sm">
                  {track.isApproved ? "VOICE APPROVED" : "DRAFT READY"}
                </Badge>
              </div>
            </div>

            <div className="mt-4 flex items-start gap-2 rounded-lg bg-[#161922] border border-[#262B3D] p-3 text-xs text-[#8B949E]">
              <Info className="h-4 w-4 text-[#FF7A00] shrink-0 mt-0.5" />
              <span>
                Speech generation divides your script into discrete scene chunks, synthesizes neural audio, and stitches them with standard 350ms breath pauses.
              </span>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#262B3D]">
            <Button
              variant="primary"
              className="w-full justify-center text-sm py-2.5"
              onClick={handleSynthesizeAll}
              disabled={isGenerating}
            >
              <Sparkles className="h-4 w-4 mr-2" />
              {isGenerating ? "Synthesizing Narration..." : "Synthesize Full Narration Track"}
            </Button>
          </div>
        </Card>
      </div>

      {/* Master Narration Track Player & Audio Mastering Controls */}
      <Card className="border-[#262B3D] bg-[#12141A] p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#262B3D] pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[#FF7A00]/40 bg-[#FF7A00]/10 text-[#FF7A00]">
              <FileAudio className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  Master Narration Track (v{track.version})
                </h3>
                <Badge variant={track.qualityStatus === "PASSED" ? "success" : "warning"} size="sm">
                  QA {track.qualityStatus}
                </Badge>
              </div>
              <p className="text-xs text-[#8B949E]">
                Format: 24,000 Hz • 16-Bit Mono WAV • EBU R128 (-14.0 LUFS) • Stitched with 350ms section pauses
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                showToast("Downloading master narration WAV...");
              }}
            >
              <Download className="h-4 w-4 mr-1.5" />
              Download Master WAV
            </Button>
            <Button
              variant={track.isApproved ? "secondary" : "primary"}
              size="sm"
              onClick={handleApproveTrack}
              disabled={track.isApproved}
            >
              <CheckCircle2 className="h-4 w-4 mr-1.5" />
              {track.isApproved ? "Approved & Locked" : "Approve Narration"}
            </Button>
          </div>
        </div>

        {/* Custom Audio Player Widget */}
        <div className="rounded-lg border border-[#262B3D] bg-[#0E1016] p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-3">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleTogglePlay}
                className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FF7A00] text-black shadow-lg hover:bg-[#FF8F26] transition-transform active:scale-95"
              >
                {isPlaying ? <Pause className="h-5 w-5 fill-black" /> : <Play className="h-5 w-5 fill-black ml-0.5" />}
              </button>

              <button
                type="button"
                onClick={() => setCurrentTime(0)}
                className="p-2 text-[#8B949E] hover:text-white transition-colors"
                title="Rewind to beginning"
              >
                <RotateCcw className="h-4 w-4" />
              </button>

              <div className="text-xs font-mono text-white">
                <span className="text-[#FF7A00] font-bold">{formatSeconds(currentTime)}</span>
                <span className="text-[#8B949E]"> / {formatSeconds(track.durationSeconds)}</span>
              </div>
            </div>

            {/* Playback rate & Volume */}
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center rounded border border-[#262B3D] bg-[#161922] p-1">
                {[1.0, 1.25, 1.5].map((rate) => (
                  <button
                    key={rate}
                    onClick={() => setPlaybackRate(rate)}
                    className={`rounded px-2 py-0.5 font-mono text-xs transition-colors ${
                      playbackRate === rate
                        ? "bg-[#FF7A00] text-black font-semibold"
                        : "text-[#8B949E] hover:text-white"
                    }`}
                  >
                    {rate}x
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => setIsMuted(!isMuted)}
                className="text-[#8B949E] hover:text-white transition-colors"
              >
                {isMuted ? <VolumeX className="h-4 w-4 text-red-400" /> : <Volume2 className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Simulated Waveform & Scrub Bar */}
          <div className="relative w-full">
            {/* Visual Waveform Bars */}
            <div className="flex items-center gap-1 h-9 mb-2 px-1">
              {Array.from({ length: 48 }).map((_, i) => {
                const height = 20 + Math.sin(i * 0.4) * 15 + ((i % 5) * 4);
                const progressRatio = currentTime / (track.durationSeconds || 1);
                const isPlayed = i / 48 <= progressRatio;
                return (
                  <div
                    key={i}
                    style={{ height: `${height}px` }}
                    className={`flex-1 rounded-full transition-colors ${
                      isPlayed ? "bg-[#FF7A00]" : "bg-[#262B3D]"
                    }`}
                  />
                );
              })}
            </div>

            {/* Range Scrubber */}
            <input
              type="range"
              min="0"
              max={track.durationSeconds}
              value={currentTime}
              onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
              className="w-full accent-[#FF7A00] bg-transparent cursor-pointer"
            />
          </div>
        </div>
      </Card>

      {/* Scene-by-Scene Audio Chunks Breakdown */}
      <Card className="border-[#262B3D] bg-[#12141A] p-5">
        <div className="flex items-center justify-between border-b border-[#262B3D] pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-[#FF7A00]" />
            <h2 className="text-base font-semibold text-white">Scene Narration Breakdown &amp; Regeneration</h2>
          </div>
          <span className="text-xs text-[#8B949E]">
            {track.chunks.length} Audio Chunks • Synchronized with Video Scenes
          </span>
        </div>

        <div className="space-y-3">
          {track.chunks.map((chunk) => (
            <div
              key={chunk.sceneId}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-lg border border-[#262B3D] bg-[#161922] p-4 hover:border-[#383F57] transition-all"
            >
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" size="sm" className="font-mono text-xs">
                    Scene {chunk.order}
                  </Badge>
                  <span className="text-sm font-semibold text-white">{chunk.title}</span>
                  {chunk.status === "REGENERATING" && (
                    <Badge variant="warning" size="sm" className="animate-pulse">
                      Synthesizing...
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-[#8B949E] leading-relaxed line-clamp-2">
                  &ldquo;{chunk.narration}&rdquo;
                </p>
                <div className="flex items-center gap-4 text-[11px] text-[#8B949E] pt-1">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3 text-[#FF7A00]" />
                    {chunk.durationSeconds}s
                  </span>
                  <span>{chunk.wordCount} words</span>
                  <span>Loudness: {chunk.loudnessLufs} LUFS</span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    handleAuditionVoice(selectedVoice);
                  }}
                >
                  <Play className="h-3.5 w-3.5 mr-1" />
                  Preview Scene
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleRegenerateChunk(chunk.sceneId)}
                  disabled={chunk.status === "REGENERATING"}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" />
                  Regenerate
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Quality Evaluation & Audio Compliance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-[#262B3D] bg-[#12141A] p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#8B949E]">Technical File Integrity</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white">100% Passed</div>
          <p className="mt-1 text-xs text-[#8B949E]">
            Valid RIFF WAV container, 24kHz sample rate, 16-bit PCM uncompressed stream.
          </p>
        </Card>

        <Card className="border-[#262B3D] bg-[#12141A] p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#8B949E]">Integrated Loudness</span>
            <Badge variant="success" size="sm">-14.0 LUFS</Badge>
          </div>
          <div className="text-xl font-bold text-white">YouTube Standard</div>
          <p className="mt-1 text-xs text-[#8B949E]">
            Normalized to EBU R128 broadcast benchmark with -1.0 dBTP true-peak ceiling.
          </p>
        </Card>

        <Card className="border-[#262B3D] bg-[#12141A] p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#8B949E]">Silence &amp; Gap Inspection</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white">Zero Freeze Gaps</div>
          <p className="mt-1 text-xs text-[#8B949E]">
            RMS energy &gt; -35 dBFS throughout spoken chunks; clean 350ms inter-scene pauses.
          </p>
        </Card>
      </div>
    </div>
  );
}
