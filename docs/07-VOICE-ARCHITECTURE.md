# CREATOR STUDIO AI — M07 VOICE GENERATION & NARRATION ENGINE ARCHITECTURE

**Project Owner:** Muhammad Ali ([alibuild.site](https://alibuild.site))  
**Milestone:** M07 of 15  
**Module:** Voice Generation, Narration & Audio Management  
**Status:** Completed & Verified (98/98 tests passing)

---

## 1. Subsystem Overview

Milestone 07 establishes the complete voice synthesis and audio engineering subsystem for Creator Studio AI. It takes approved video scripts from Milestone 06 (with their partitioned scene breakdowns) and synthesizes high-fidelity spoken voice tracks with word-level alignment metadata, loudness normalization, audio quality evaluation, and scene-level audio regeneration.

```mermaid
graph TD
    subgraph Input Stage
        Script[Approved Script M06] --> Scenes[Scene Breakdown]
        VoiceProfile[Voice Profile Configuration]
    end

    subgraph Provider Abstraction Layer
        VoiceProfile --> ProviderFactory[VoiceProviderFactory]
        ProviderFactory --> EdgeTTS[EdgeTTSProvider - Free Neural]
        ProviderFactory --> MockTTS[MockVoiceProvider - Offline / Tests]
        ProviderFactory --> FutureTTS[Kokoro / Cloud Provider - Optional]
    end

    subgraph Narration Pipeline
        Scenes --> ChunkGen[Scene-by-Scene Chunk Synthesis]
        EdgeTTS --> ChunkGen
        MockTTS --> ChunkGen
        ChunkGen --> ChunkVal[Audio Integrity & Duration Check]
        ChunkVal --> Stitcher[WAV Concatenation & Pause Injection]
        Stitcher --> MasterTrack[Master Narration Track]
        MasterTrack --> AudioQA[Audio Quality Evaluator]
        AudioQA --> Persistence[DB Persistence: VoiceProfile, Voiceover, NarrationTrack]
    end

    subgraph Storage & Delivery
        Persistence --> LocalStorage[storage/audio/{channel_id}/{project_id}/]
        LocalStorage --> StreamingAPI[GET /api/v1/voice/tracks/{id}/audio]
        StreamingAPI --> VoiceStudioUI[Frontend Voice Studio /voice-studio]
    end
```

---

## 2. Voice Provider Architecture

### 2.1 Abstract Interface (`app.providers.voice.base`)

Every voice provider implements `VoiceProviderInterface`:

- `list_voices() -> List[VoiceInfo]`: Returns available voices with locale, gender, and provider IDs.
- `generate_speech(text, voice_id, speed, pitch, output_format) -> GeneratedAudioResult`: Synthesizes speech to WAV/MP3 bytes and extracts word-level timestamps.
- `preview_voice(voice_id, sample_text) -> GeneratedAudioResult`: Generates a short 3-second sample for voice audition.
- `get_capabilities() -> VoiceProviderCapabilities`: Declares supported formats, rate adjustments, pitch controls, and word alignment availability.
- `estimate_usage(text) -> AudioUsageEstimate`: Calculates estimated duration and cost (strictly $0.00 for Edge-TTS and Mock).

### 2.2 Providers Implemented

1. **EdgeTTSProvider**:
   - Zero-cost, high-fidelity neural voice synthesis powered by Microsoft Edge online neural voices.
   - Provides 300+ multilingual voices and 47 high-quality English voices (`en-US-ChristopherNeural`, `en-US-GuyNeural`, `en-US-JennyNeural`, `en-GB-RyanNeural`).
   - Supports speaking rate adjustments (`-50%` to `+100%`) and pitch adjustments (`-50Hz` to `+50Hz`).
   - Streams word boundary events (`WordBoundary`) to produce exact word-level timing metadata for kinetic typography subtitles in M09.
   - No API keys required; default paid budget remains $0.00.

2. **MockVoiceProvider**:
   - Keyless, offline, deterministic provider for automated unit tests, CI/CD, and offline development.
   - Synthesizes real, fully compliant RIFF WAV audio bytes in pure Python using `wave` and `struct`.
   - Generates realistic word timestamps and loudness metrics without calling any external service or eating network bandwidth.

---

## 3. Database Schema Extensions

### 3.1 Entities Added in M07

1. **`VoiceProfile` (`voice_profiles`)**:
   - `id`: UUID (Primary Key)
   - `channel_id`: UUID (FK to `channels.id`, nullable for system defaults)
   - `display_name`: String(128)
   - `provider`: String(64) (`EDGE_TTS`, `MOCK`, `KOKORO`)
   - `provider_voice_id`: String(128)
   - `language_code`: String(32) (e.g. `en-US`)
   - `description`: Text
   - `gender`: String(32) (`MALE`, `FEMALE`, `NEUTRAL`)
   - `speed_ratio`: Numeric(4, 2) (default 1.00)
   - `pitch_semitones`: Numeric(4, 2) (default 0.00)
   - `is_default`: Boolean (default False)
   - `is_active`: Boolean (default True)
   - `settings`: JSON

2. **`NarrationTrack` (`narration_tracks`)**:
   - `id`: UUID (Primary Key)
   - `project_id`: UUID (FK to `video_projects.id`)
   - `script_id`: UUID (FK to `scripts.id`, nullable)
   - `voice_profile_id`: UUID (FK to `voice_profiles.id`, nullable)
   - `script_version`: Integer
   - `track_version`: Integer
   - `audio_storage_path`: Text
   - `file_format`: String(16) (`wav`, `mp3`)
   - `sample_rate`: Integer
   - `channels`: Integer
   - `duration_seconds`: Numeric(8, 3)
   - `file_size_bytes`: BigInteger
   - `loudness_lufs`: Numeric(5, 2)
   - `is_approved`: Boolean (default False)
   - `status`: String(32) (`PENDING`, `GENERATING`, `STITCHING`, `READY`, `FAILED`, `OUTDATED`)
   - `quality_status`: String(32) (`PASSED`, `WARNING`, `FAILED`, `NEEDS_REVIEW`)
   - `quality_report`: JSON

3. **`Voiceover` (`voiceovers`) Enhancement**:
   - Connects individual scene audio chunks to the `NarrationTrack`.
   - `narration_track_id`: UUID (FK to `narration_tracks.id`, nullable)
   - `chunk_index`: Integer
   - `status`: String(32) (`GENERATED`, `STITCHED`, `FAILED`)

---

## 4. Audio Processing & Quality Assurance

### 4.1 Audio Processing Service (`app.services.audio_processing`)
- Pure Python RIFF WAV header parsing and frame processing (no external binary dependency required for core operations).
- Calculates duration from sample rate, byte rate, and frame count.
- Detects silence by inspecting root-mean-square (RMS) energy levels across audio windows.
- Inserts clean silence pauses (default 350ms) between scenes to create natural speech pacing.
- Concatenates multiple WAV scene chunks into a single, cohesive master track with smooth frame alignments.
- Computes integrated loudness (LUFS approximation) and true peak ($d\text{BTP}$) to guarantee YouTube compliance ($-14\text{ LUFS} \pm 2\text{ LUFS}$, peak $\le -1.0\text{ dBTP}$).

### 4.2 Quality Evaluation Service (`app.services.audio_quality`)
- **Checks executed:**
  1. Header and byte integrity (no corrupted or truncated audio).
  2. Duration check against script estimated speaking duration ($140\text{ WPM} \pm 20\%$).
  3. Empty/silent chunk detection (flags audio with RMS energy $< -50\text{ dBFS}$).
  4. Audio clipping / peak level ($> -0.5\text{ dBTP}$ warning).
  5. Script scene-to-audio coverage (ensures 100% of scenes in the script have synthesized audio).
- **Status result:** `PASSED`, `WARNING`, `FAILED`, or `NEEDS_REVIEW`.

---

## 5. REST API & Queue Architecture

### 5.1 Endpoints (`/api/v1/voice`)
- `GET /providers`: List configured TTS engines.
- `GET /voices`: Query available voices with language/gender filters.
- `GET /profiles`: List channel voice profiles.
- `POST /profiles`: Create reusable custom voice profile.
- `PATCH /profiles/{id}`: Modify voice profile settings.
- `DELETE /profiles/{id}`: Delete voice profile.
- `POST /preview`: Generate voice preview audio clip.
- `POST /generate`: Enqueue durable background narration job (HTTP 202).
- `POST /generate-sync`: Synchronous narration generation.
- `GET /tracks`: List narration track history for a project.
- `GET /tracks/{id}`: Full narration track metadata, quality report, and scene chunks.
- `POST /tracks/{id}/approve`: Approve and lock narration track.
- `POST /tracks/{id}/regenerate-section`: Regenerate only a single scene's audio chunk and re-stitch master.
- `GET /tracks/{id}/audio`: Stream/download full master narration WAV file.
- `GET /chunks/{id}/audio`: Stream/download individual scene audio WAV chunk.

### 5.2 Worker Queue Integration
- Registered job handlers in `JobHandlerRegistry`:
  - `NARRATION_GENERATION`: Full pipeline worker with stage progress reporting.
  - `VOICE_PREVIEW_GENERATION`: Quick preview synthesis.
  - `NARRATION_SECTION_REGENERATE`: Surgical section repair without regenerating entire script.
  - `AUDIO_QUALITY_EVALUATION`: Deterministic audio quality audit.
