"""Standard Workflow Templates catalog and helper utilities."""

from typing import Dict, Any, List, Optional

TEMPLATE_LONG_FORM = "TEMPLATE_LONG_FORM"
TEMPLATE_SHORTS = "TEMPLATE_SHORTS"
TEMPLATE_REPURPOSING = "TEMPLATE_REPURPOSING"
TEMPLATE_MINI_SERIES = "TEMPLATE_MINI_SERIES"
TEMPLATE_TOPIC_RESEARCH_ONLY = "TEMPLATE_TOPIC_RESEARCH_ONLY"
TEMPLATE_SCRIPT_ONLY = "TEMPLATE_SCRIPT_ONLY"
TEMPLATE_RECOVERY = "TEMPLATE_RECOVERY"
TEMPLATE_ANALYTICS_PLANNING = "TEMPLATE_ANALYTICS_PLANNING"

# Standard System Workflow Templates
SYSTEM_TEMPLATES: Dict[str, Dict[str, Any]] = {
    TEMPLATE_LONG_FORM: {
        "template_key": TEMPLATE_LONG_FORM,
        "name": "Standard Long-Form Production",
        "description": "Full end-to-end autonomous production for 6–10 min landscape video (16:9).",
        "content_format": "LONG_FORM",
        "estimated_duration_sec": 480,
        "stages": [
            {
                "stage_key": "stage_topic",
                "stage_name": "Topic Research & Opportunity Discovery",
                "job_type": "DISCOVER_TOPICS",
                "dependencies": [],
                "approval_required": True,
                "order_index": 0,
            },
            {
                "stage_key": "stage_script",
                "stage_name": "AI Script Generation & Fact Checking",
                "job_type": "GENERATE_SCRIPT",
                "dependencies": ["stage_topic"],
                "approval_required": True,
                "order_index": 1,
            },
            {
                "stage_key": "stage_narration",
                "stage_name": "Voice Synthesis & Audio Normalization",
                "job_type": "GENERATE_NARRATION",
                "dependencies": ["stage_script"],
                "approval_required": False,
                "order_index": 2,
            },
            {
                "stage_key": "stage_visuals",
                "stage_name": "Visual Asset Discovery & Storyboard Planning",
                "job_type": "PLAN_VISUALS",
                "dependencies": ["stage_script"],
                "approval_required": False,
                "order_index": 3,
            },
            {
                "stage_key": "stage_render",
                "stage_name": "FFmpeg Video Assembly & Dynamic Subtitles",
                "job_type": "RENDER_VIDEO",
                "dependencies": ["stage_narration", "stage_visuals"],
                "approval_required": False,
                "order_index": 4,
            },
            {
                "stage_key": "stage_seo",
                "stage_name": "Thumbnail Studio & YouTube SEO Optimization",
                "job_type": "GENERATE_THUMBNAIL_AND_METADATA",
                "dependencies": ["stage_render"],
                "approval_required": False,
                "order_index": 5,
            },
            {
                "stage_key": "stage_qa",
                "stage_name": "14-Point Quality Assurance & Veto Gate",
                "job_type": "EVALUATE_PUBLICATION_READINESS",
                "dependencies": ["stage_render", "stage_seo"],
                "approval_required": True,
                "order_index": 6,
            },
            {
                "stage_key": "stage_publishing",
                "stage_name": "Resumable YouTube Publication & Scheduling",
                "job_type": "YOUTUBE_PUBLICATION_DISPATCH",
                "dependencies": ["stage_qa"],
                "approval_required": True,
                "order_index": 7,
            },
        ],
        "default_settings": {
            "aspect_ratio": "16:9",
            "resolution": "1920x1080",
            "fps": 30,
            "target_lufs": -14.0,
            "privacy": "unlisted",
        },
    },
    TEMPLATE_SHORTS: {
        "template_key": TEMPLATE_SHORTS,
        "name": "YouTube Shorts Fast Production",
        "description": "High-velocity 30–60 second vertical video production (9:16) with hook prioritization.",
        "content_format": "SHORTS",
        "estimated_duration_sec": 45,
        "stages": [
            {
                "stage_key": "stage_topic",
                "stage_name": "Shorts Viral Hook Discovery",
                "job_type": "DISCOVER_TOPICS",
                "dependencies": [],
                "approval_required": False,
                "order_index": 0,
            },
            {
                "stage_key": "stage_script",
                "stage_name": "Rapid Script Synthesis & Hook Optimization",
                "job_type": "GENERATE_SCRIPT",
                "dependencies": ["stage_topic"],
                "approval_required": True,
                "order_index": 1,
            },
            {
                "stage_key": "stage_narration",
                "stage_name": "High-Energy Narration Synthesis",
                "job_type": "GENERATE_NARRATION",
                "dependencies": ["stage_script"],
                "approval_required": False,
                "order_index": 2,
            },
            {
                "stage_key": "stage_visuals",
                "stage_name": "Vertical Kinetic Asset Assembly",
                "job_type": "PLAN_VISUALS",
                "dependencies": ["stage_script"],
                "approval_required": False,
                "order_index": 3,
            },
            {
                "stage_key": "stage_render",
                "stage_name": "Vertical 9:16 FFmpeg Assembly",
                "job_type": "RENDER_VIDEO",
                "dependencies": ["stage_narration", "stage_visuals"],
                "approval_required": False,
                "order_index": 4,
            },
            {
                "stage_key": "stage_seo",
                "stage_name": "Shorts SEO Tags & Thumbnail Selection",
                "job_type": "GENERATE_THUMBNAIL_AND_METADATA",
                "dependencies": ["stage_render"],
                "approval_required": False,
                "order_index": 5,
            },
            {
                "stage_key": "stage_qa",
                "stage_name": "Shorts Quality & Retention Audit",
                "job_type": "EVALUATE_PUBLICATION_READINESS",
                "dependencies": ["stage_render", "stage_seo"],
                "approval_required": True,
                "order_index": 6,
            },
            {
                "stage_key": "stage_publishing",
                "stage_name": "YouTube Shorts Upload Dispatch",
                "job_type": "YOUTUBE_PUBLICATION_DISPATCH",
                "dependencies": ["stage_qa"],
                "approval_required": True,
                "order_index": 7,
            },
        ],
        "default_settings": {
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "fps": 30,
            "target_lufs": -14.0,
            "privacy": "unlisted",
        },
    },
    TEMPLATE_REPURPOSING: {
        "template_key": TEMPLATE_REPURPOSING,
        "name": "Long-Form to Shorts Repurposing",
        "description": "Extracts high-retention segments from approved long-form videos into standalone Shorts.",
        "content_format": "SHORTS",
        "estimated_duration_sec": 45,
        "stages": [
            {
                "stage_key": "stage_extract",
                "stage_name": "Identify Peak Hook Segment",
                "job_type": "SCRIPT_QUALITY_EVALUATION",
                "dependencies": [],
                "approval_required": False,
                "order_index": 0,
            },
            {
                "stage_key": "stage_reformat_script",
                "stage_name": "Reformat Script to 9:16 Cadence",
                "job_type": "GENERATE_SCRIPT",
                "dependencies": ["stage_extract"],
                "approval_required": True,
                "order_index": 1,
            },
            {
                "stage_key": "stage_render",
                "stage_name": "Render Vertical Short",
                "job_type": "RENDER_VIDEO",
                "dependencies": ["stage_reformat_script"],
                "approval_required": False,
                "order_index": 2,
            },
            {
                "stage_key": "stage_qa",
                "stage_name": "Veto Gate Audit",
                "job_type": "EVALUATE_PUBLICATION_READINESS",
                "dependencies": ["stage_render"],
                "approval_required": True,
                "order_index": 3,
            },
        ],
        "default_settings": {
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
        },
    },
    TEMPLATE_MINI_SERIES: {
        "template_key": TEMPLATE_MINI_SERIES,
        "name": "Coordinated Mini-Series (3 Episodes)",
        "description": "Plans and coordinates a 3-part educational series covering developer tools or coding techniques.",
        "content_format": "LONG_FORM",
        "estimated_duration_sec": 1440,
        "stages": [
            {
                "stage_key": "stage_curriculum",
                "stage_name": "Series Curriculum Planning",
                "job_type": "DISCOVER_TOPICS",
                "dependencies": [],
                "approval_required": True,
                "order_index": 0,
            },
            {
                "stage_key": "stage_batch_scripts",
                "stage_name": "Batch Script & Narrative Arc Synthesis",
                "job_type": "GENERATE_SCRIPT",
                "dependencies": ["stage_curriculum"],
                "approval_required": True,
                "order_index": 1,
            },
        ],
        "default_settings": {
            "series_length": 3,
            "aspect_ratio": "16:9",
        },
    },
    TEMPLATE_TOPIC_RESEARCH_ONLY: {
        "template_key": TEMPLATE_TOPIC_RESEARCH_ONLY,
        "name": "Topic Research & Opportunity Discovery Only",
        "description": "Explores the core niche and generates 5 validated, deduplicated topics with scores.",
        "content_format": "LONG_FORM",
        "estimated_duration_sec": 30,
        "stages": [
            {
                "stage_key": "stage_topic",
                "stage_name": "Topic Discovery & Search Demand Evaluation",
                "job_type": "DISCOVER_TOPICS",
                "dependencies": [],
                "approval_required": False,
                "order_index": 0,
            },
        ],
        "default_settings": {},
    },
    TEMPLATE_SCRIPT_ONLY: {
        "template_key": TEMPLATE_SCRIPT_ONLY,
        "name": "Script Synthesis & Fact-Checking Only",
        "description": "Drafts narrative outline, full script, factual citations, and scene breakdowns without media rendering.",
        "content_format": "LONG_FORM",
        "estimated_duration_sec": 60,
        "stages": [
            {
                "stage_key": "stage_script",
                "stage_name": "Procedural Script Generation",
                "job_type": "GENERATE_SCRIPT",
                "dependencies": [],
                "approval_required": True,
                "order_index": 0,
            },
            {
                "stage_key": "stage_fact_check",
                "stage_name": "Factual Verification & Citation Linking",
                "job_type": "SCRIPT_FACT_CHECK",
                "dependencies": ["stage_script"],
                "approval_required": False,
                "order_index": 1,
            },
        ],
        "default_settings": {},
    },
    TEMPLATE_RECOVERY: {
        "template_key": TEMPLATE_RECOVERY,
        "name": "Production Remediation & Re-render",
        "description": "Idempotently re-executes video assembly or QA audit reusing upstream script and voice assets.",
        "content_format": "LONG_FORM",
        "estimated_duration_sec": 180,
        "stages": [
            {
                "stage_key": "stage_render",
                "stage_name": "Re-execute FFmpeg Video Assembly",
                "job_type": "RENDER_VIDEO",
                "dependencies": [],
                "approval_required": False,
                "order_index": 0,
            },
            {
                "stage_key": "stage_qa",
                "stage_name": "Re-run 14-Point Quality Audit",
                "job_type": "EVALUATE_PUBLICATION_READINESS",
                "dependencies": ["stage_render"],
                "approval_required": True,
                "order_index": 1,
            },
        ],
        "default_settings": {},
    },
    TEMPLATE_ANALYTICS_PLANNING: {
        "template_key": TEMPLATE_ANALYTICS_PLANNING,
        "name": "Analytics-Driven Content Planning",
        "description": "Ingests historical YouTube performance and rebalances topic scoring multipliers.",
        "content_format": "LONG_FORM",
        "estimated_duration_sec": 45,
        "stages": [
            {
                "stage_key": "stage_sync",
                "stage_name": "YouTube Analytics Telemetry Sync",
                "job_type": "YOUTUBE_CHANNEL_ANALYTICS_SYNC",
                "dependencies": [],
                "approval_required": False,
                "order_index": 0,
            },
            {
                "stage_key": "stage_reconcile",
                "stage_name": "Retention Feedback Rebalancing & Opportunity Generation",
                "job_type": "YOUTUBE_ANALYTICS_RECONCILIATION",
                "dependencies": ["stage_sync"],
                "approval_required": False,
                "order_index": 1,
            },
        ],
        "default_settings": {},
    },
}


def get_standard_templates() -> List[Dict[str, Any]]:
    """Return list of all built-in workflow template definitions."""
    return list(SYSTEM_TEMPLATES.values())


def get_template_by_key(template_key: str) -> Optional[Dict[str, Any]]:
    """Lookup a standard template by unique key."""
    return SYSTEM_TEMPLATES.get(template_key)
