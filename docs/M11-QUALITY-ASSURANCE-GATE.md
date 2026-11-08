# M11 Technical Blueprint: Autonomous Quality Assurance & Final Approval Veto Gate

## 1. System Overview
The Autonomous Quality Assurance (QA) Subsystem serves as the uncompromised, automated veto gate standing between asset generation and publication dispatch. It operates with zero circular trust—meaning it directly inspects physical containers, rendered video frames, decoded audio streams, metadata constraints, claim citations, license attestations, and security leaks rather than trusting previous generation success flags.

```
+-----------------------------------------------------------------------------------------------+
|                                    Video Production Package                                   |
|   (Rendered MP4, Master Narration WAV, Pillow Thumbnails, SEO Metadata Draft, Script Claims)  |
+-----------------------------------------------------------------------------------------------+
                                                |
                                                v
                        +-----------------------------------------------+
                        |          QA Orchestration Engine              |
                        |   - Version-Aware Invalidation                |
                        |   - Snapshot State Hashing                    |
                        +-----------------------------------------------+
                                                |
        +---------------------------------------+---------------------------------------+
        |                                       |                                       |
        v                                       v                                       v
+-----------------------+           +-----------------------+           +-----------------------+
|  Factual & Script QA  |           |  Media & Technical QA |           | Compliance & Policy QA|
|  - Claim Verifications|           |  - Black/Freeze Frame |           |  - Secret/API Leak    |
|  - Trigram Repetition |           |  - Audio True Peak/LUFS|           |  - License Commercial |
|  - Hook/Pacing Audit  |           |  - 1280x720 Thumbnail |           |  - Synthetic Media Tag|
+-----------------------+           +-----------------------+           +-----------------------+
        |                                       |                                       |
        +---------------------------------------+---------------------------------------+
                                                |
                                                v
                        +-----------------------------------------------+
                        |        Deterministic Scoring & Veto Engine    |
                        |   - 12 Category Weighted Scores               |
                        |   - Hard Veto Matrix: CRITICAL / HIGH / MED   |
                        +-----------------------------------------------+
                                                |
                                                v
                        +-----------------------------------------------+
                        |       Publication Decision & Exceptions       |
                        |   - can_publish: True / False                 |
                        |   - Human Exception Logging (Admin Only)      |
                        +-----------------------------------------------+
```

---

## 2. 12 Independent Inspection Categories

1. **Factual Accuracy (`FACTUAL_ACCURACY`, Weight: 15%)**
   - Extracts all assertions from `ScriptClaim` and script narration.
   - Inspects cited research source URL, domain verification, and verification score.
   - Flags unverified assertions, contradiction hazards, or missing research sources.

2. **Script Quality (`SCRIPT_QUALITY`, Weight: 10%)**
   - Analyzes spoken cadence (~130-160 WPM), structure (hook, body, payoff, CTA).
   - Detects excessive trigram repetition, buzzword density, and readability score.

3. **Narration & Audio Quality (`NARRATION_AUDIO`, Weight: 10%)**
   - Audio container and stream inspection (WAV/AAC, sample rate $\ge 44.1$kHz).
   - Silence detector: Flags silent intervals $> 1.5$s.
   - Peak / Clipping: True Peak $> -1.0$ dBTP or clipping.
   - Integrated Loudness target: $-14 \pm 2$ LUFS.

4. **Visual Assets Quality (`VISUAL_ASSETS`, Weight: 10%)**
   - 100% Scene coverage: Verifies every scene has valid, readable visual assets.
   - Resolution compliance: Minimum $1920\times 1080$ for 16:9 or $1080\times 1920$ for 9:16.
   - Duplication audit: Flags identical asset reuse across consecutive scenes.

5. **Video Technical Quality (`VIDEO_TECHNICAL`, Weight: 15%)**
   - FFprobe container and stream analysis: `h264`, `yuv420p`, valid MOOV atom (`faststart`).
   - Frame inspection: detects black frames $> 0.25$s and frozen video $> 2.0$s.
   - Audio/Video duration sync tolerance: delta $\le 1.0$s.

6. **Caption Integrity (`CAPTION_INTEGRITY`, Weight: 5%)**
   - ASS / SRT syntax and timing validation: chronological ordering, no negative or overlapping durations.
   - Script alignment: token similarity check between captions and audio narration.

7. **Thumbnail Quality (`THUMBNAIL_QUALITY`, Weight: 10%)**
   - Exact dimensions: $1280 \times 720$ pixels (16:9).
   - Size limit: strict $< 2.0$ MB ceiling.
   - Format: valid PNG or JPEG with non-zero entropy and title text readability margin.

8. **Metadata & SEO Compliance (`METADATA_SEO`, Weight: 10%)**
   - Title length: $\le 95$ characters (optimal 50-70), no deceptive spam.
   - Chapters: mandatory timestamp starting at `00:00`, minimum 3 chapters, monotonic order.
   - Description: includes overview, citations, and synthetic media disclosure.
   - Tags: total string length $\le 500$ characters.

9. **Copyright & Commercial Licensing (`COPYRIGHT_LICENSING`, Weight: 5%)**
   - Verifies all media asset licenses (`COMMERCIAL_USE_ALLOWED`, `CC0`, `PUBLIC_DOMAIN`, or `AI_GENERATED`).
   - Flags unverified third-party assets or missing attribution.

10. **Security & Secrets Leak Detection (`SECURITY_PRIVACY`, Weight: 5%)**
    - High-entropy regex scan across script, description, metadata, and asset filenames for:
      - API keys (Google AI, OpenAI, ElevenLabs, Anthropic, AWS, GitHub tokens).
      - Private IP addresses, internal domains, credentials, or PII.
    - Result: `CRITICAL` severity veto if any secret is exposed.

11. **YouTube Policy & Risk Assessment (`YOUTUBE_POLICY`, Weight: 5%)**
    - Explicit synthetic media declaration requirement (`syntheticMedia: true`).
    - Sensational clickbait / prohibited medical or violent policy scans.
    - Reused / automated content spam risk heuristics.

12. **Publication Package Completeness (`PACKAGE_COMPLETENESS`, Weight: - Hard Gate)**
    - Verifies all required package elements exist: completed MP4 render, selected thumbnail, approved metadata draft.
    - Zero orphaned references.

---

## 3. Severity & Veto Matrix

| Severity | Definition | Veto Behavior | Override Policy |
| :--- | :--- | :--- | :--- |
| **`CRITICAL`** | Direct publication blocker (file corruption, secret leaks, missing assets, duration mismatch $>5$s). | Immediate hard veto (`can_publish = False`). | **NEVER BYPASSABLE**. Must be corrected in code/asset. |
| **`HIGH`** | Serious compliance or quality defect (unverified claims, missing chapters, audio clipping, silence $>2$s). | Blocks publication (`can_publish = False`). | Requires explicit admin exception with audit note. |
| **`MEDIUM`** | Non-optimal asset (title length $>85$, slight loudness drift, low contrast). | Flags `NEEDS_REVIEW`. Publication permitted if score $\ge 80$. | Creator acknowledgment. |
| **`LOW`** | Informational suggestion (tag density, style optimization). | Advisory. Does not block publication. | Automatic pass. |

---

## 4. Scoring Algorithm & State Transitions

- **Category Score**: Starts at 100. Deductions applied per finding:
  - Critical: $-100$ (Category score = 0)
  - High: $-25$ per occurrence
  - Medium: $-10$ per occurrence
  - Low: $-3$ per occurrence
- **Composite Score**: $\sum (\text{Category Score} \times \text{Weight})$. Range: $0.00$ to $100.00$.
- **Veto Decision**:
  - If any unresolved `CRITICAL` finding: `BLOCKED` (`can_publish = False`).
  - If any unresolved `HIGH` finding without exception: `BLOCKED` (`can_publish = False`).
  - If any unresolved `MEDIUM` finding: `NEEDS_REVIEW` (`can_publish = (overall_score >= 80)`).
  - Otherwise: `APPROVED` (`can_publish = True`).
