"""Deterministic Mock AI Provider for offline testing, local dev, and fault simulation."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID, uuid4
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from app.providers.ai.base import (
    AIProviderInterface,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    ProviderUsageMetrics,
    ProviderTextResponse,
    ProviderStructuredResponse,
    ProviderHealthStatus,
)

T = TypeVar("T", bound=BaseModel)

DEFAULT_MOCK_TOPICS = [
    {
        "title": "Autonomous AI Agents in Production: 5 Failure Modes You Must Avoid",
        "niche_category": "AI Architecture & Engineering",
        "angle": "Pragmatic engineering breakdown of multi-agent loops, state drift, and race conditions in production systems.",
        "target_audience": "Senior software engineers, AI system architects, and technical engineering leads.",
        "search_volume_score": 88.0,
        "competition_score": 42.0,
        "rationale": "High developer demand as multi-agent frameworks face reliability hurdles in real workloads.",
        "sources": [
            {
                "source_url": "https://arxiv.org/abs/2402.01234",
                "source_title": "Empirical Analysis of Multi-Agent Divergence in Autonomous Workflows",
                "extracted_summary": "Comprehensive benchmark demonstrating that unconstrained state loops lead to failure in 38% of autonomous tasks without checkpointing.",
                "relevance_score": 0.95,
            },
            {
                "source_url": "https://engineering.stripe.com/blog/reliable-agent-architecture",
                "source_title": "Designing Deterministic Gateways for Non-Deterministic Models",
                "extracted_summary": "Production case study detailing transactional recovery and idempotency patterns for LLM worker queues.",
                "relevance_score": 0.91,
            },
        ],
    },
    {
        "title": "Why SQLite is Taking Over Cloud-Native Applications in 2026",
        "niche_category": "Database Engineering",
        "angle": "Architectural shift from heavy distributed databases toward replicated edge SQLite with Litestream and Turso.",
        "target_audience": "Full-stack developers, infrastructure architects, and DevOps engineers.",
        "search_volume_score": 82.0,
        "competition_score": 38.0,
        "rationale": "Sub-millisecond query performance at zero cloud infrastructure cost makes this a viral technical topic.",
        "sources": [
            {
                "source_url": "https://fly.io/blog/all-in-on-sqlite/",
                "source_title": "I'm All-In On SQLite for Production SaaS",
                "extracted_summary": "Benchmark data demonstrating 10x lower latency and $0 monthly database bills using embedded SQLite on NVMe storage.",
                "relevance_score": 0.92,
            },
            {
                "source_url": "https://github.com/benbjohnson/litestream",
                "source_title": "Litestream: Continuous SQLite Replication to S3",
                "extracted_summary": "Open-source continuous streaming replication engine providing zero-downtime failover and disaster recovery.",
                "relevance_score": 0.88,
            },
        ],
    },
    {
        "title": "PostgreSQL 17 Hidden Features: SKIP LOCKED and Parallel Query Tricks",
        "niche_category": "Backend Performance",
        "angle": "Deep dive into building durable queue workers directly in Postgres without Redis.",
        "target_audience": "Backend developers building scalable queues and message distribution systems.",
        "search_volume_score": 79.0,
        "competition_score": 45.0,
        "rationale": "Engineers increasingly seek to consolidate tech stacks by removing unnecessary cache and queue infrastructure.",
        "sources": [
            {
                "source_url": "https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE",
                "source_title": "PostgreSQL Documentation: The SKIP LOCKED Clause",
                "extracted_summary": "Formal semantics of non-blocking row acquisition for concurrent worker queue architectures.",
                "relevance_score": 0.96,
            }
        ],
    },
]


DEFAULT_MOCK_SECTIONS = [
    {
        "section_id": "sec_01",
        "section_order": 1,
        "title": "Hook & Problem Statement",
        "narration": "Most developers think building an autonomous background queue requires spinning up Redis, Celery, or RabbitMQ. But in PostgreSQL, there is a hidden locking mechanism that handles thousands of jobs per second with zero extra infrastructure.",
        "visual_directive": "Screen capture of architecture diagram comparing heavy multi-cluster Redis setup against clean single-node Postgres queue.",
        "visual_concept": "Multi-cluster vs single-node architectural comparison",
        "key_points": ["Redis/RabbitMQ overhead", "PostgreSQL ACID durability", "Architecture simplification"],
        "estimated_seconds": 65,
        "transition_note": "Cut directly to code editor.",
    },
    {
        "section_id": "sec_02",
        "section_order": 2,
        "title": "The Power of SELECT FOR UPDATE SKIP LOCKED",
        "narration": "PostgreSQL 9.5 introduced SKIP LOCKED, allowing concurrent workers to safely claim queued rows without waiting on locks or colliding with other processes.",
        "visual_directive": "Highlighting SQL query terminal with SELECT id FROM automation_jobs FOR UPDATE SKIP LOCKED.",
        "visual_concept": "SQL terminal query demonstration",
        "key_points": ["Postgres 9.5 release history", "SKIP LOCKED semantics", "Zero race conditions"],
        "estimated_seconds": 90,
        "transition_note": "Zoom into benchmark graph.",
    },
    {
        "section_id": "sec_03",
        "section_order": 3,
        "title": "Benchmark Results and Failure Recovery",
        "narration": "In empirical benchmarks, PostgreSQL handles up to 5,000 job dispatches per second on modest cloud instances, while providing guaranteed ACID rollback if a worker crashes.",
        "visual_directive": "Throughput graphs demonstrating latency stability under high concurrent load.",
        "visual_concept": "Throughput and latency benchmark graphs",
        "key_points": ["5,000 jobs/sec performance", "ACID recovery guarantees", "Cloud instance efficiency"],
        "estimated_seconds": 85,
        "transition_note": "Transition to summary takeaways.",
    },
    {
        "section_id": "sec_04",
        "section_order": 4,
        "title": "Takeaways and Next Steps",
        "narration": "By using PostgreSQL as your single source of truth for both data and background tasks, you eliminate data drift and slash cloud infrastructure costs. Check out the repository link in the description to clone the starter project.",
        "visual_directive": "GitHub repository page and subscribe button card.",
        "visual_concept": "GitHub repo and channel call-to-action cards",
        "key_points": ["Stack consolidation", "Cost reduction", "Starter repo access"],
        "estimated_seconds": 60,
        "transition_note": "Fade to end screen.",
    },
]

DEFAULT_MOCK_CLAIMS = [
    {
        "claim_text": "PostgreSQL 9.5 introduced the SKIP LOCKED clause for non-blocking row selection.",
        "extracted_entity": "PostgreSQL 9.5",
        "claim_type": "RELEASE_DATE",
        "is_verified": True,
        "confidence_score": 0.98,
        "citation_url": "https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE",
        "citation_snippet": "SKIP LOCKED causes any concurrent rows that are locked by other transactions to be skipped rather than waiting.",
        "verification_explanation": "Directly confirmed in PostgreSQL release notes and official documentation.",
    },
    {
        "claim_text": "PostgreSQL handles up to 5,000 job dispatches per second on standard cloud instances.",
        "extracted_entity": "PostgreSQL",
        "claim_type": "BENCHMARK",
        "is_verified": True,
        "confidence_score": 0.92,
        "citation_url": "https://brandur.org/postgres-queues",
        "citation_snippet": "5,000 jobs per second benchmark verified on 4-vCPU managed cloud instances.",
        "verification_explanation": "Supported by documented production benchmarks.",
    },
]


class MockAIProvider(AIProviderInterface):
    """Deterministic, keyless AI provider for rapid testing and offline execution."""

    def __init__(
        self,
        default_model: str = "mock-gemini-1.5-flash",
        mock_latency: float = 0.0,
        simulate_rate_limit: bool = False,
        simulate_timeout: bool = False,
        simulate_error: bool = False,
    ):
        self._name = "MOCK"
        self._default_model = default_model
        self.mock_latency = mock_latency
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_timeout = simulate_timeout
        self.simulate_error = simulate_error

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_model(self) -> str:
        return self._default_model

    def _check_simulated_faults(self) -> None:
        if self.simulate_rate_limit:
            raise AIRateLimitError("Simulated 429 Too Many Requests: Rate limit exceeded", provider=self.name, status_code=429)
        if self.simulate_timeout:
            raise AITimeoutError("Simulated client timeout after 60s", provider=self.name)
        if self.simulate_error:
            raise AIProviderError("Simulated internal AI provider failure", provider=self.name, status_code=500)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout_seconds: float = 60.0,
    ) -> ProviderTextResponse:
        if self.mock_latency > 0:
            await asyncio.sleep(self.mock_latency)

        self._check_simulated_faults()

        chosen_model = model or self._default_model
        generated_text = (
            f"Mock response generated for prompt: '{prompt[:60]}...' "
            f"[model: {chosen_model}, temperature: {temperature}]"
        )
        prompt_tokens = self._estimate_tokens(prompt)
        completion_tokens = self._estimate_tokens(generated_text)
        total = prompt_tokens + completion_tokens

        return ProviderTextResponse(
            text=generated_text,
            usage=ProviderUsageMetrics(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
                estimated_cost_usd=round(total * 0.0000001, 6),
            ),
            model_name=chosen_model,
            raw_response={"mock": True, "prompt_preview": prompt[:40]},
        )

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
    ) -> ProviderStructuredResponse:
        if self.mock_latency > 0:
            await asyncio.sleep(self.mock_latency)

        self._check_simulated_faults()

        chosen_model = model or self._default_model

        # Build mock data conforming to response_schema
        mock_payload: Dict[str, Any] = {}
        schema_fields = getattr(response_schema, "model_fields", {})

        for field_name, field_info in schema_fields.items():
            if field_name == "topics":
                mock_payload["topics"] = DEFAULT_MOCK_TOPICS
            elif field_name == "candidates":
                mock_payload["candidates"] = DEFAULT_MOCK_TOPICS
            elif field_name == "sections":
                mock_payload["sections"] = DEFAULT_MOCK_SECTIONS
            elif field_name == "claims":
                mock_payload["claims"] = DEFAULT_MOCK_CLAIMS
            elif field_name in ("hook", "hook_concept"):
                mock_payload[field_name] = DEFAULT_MOCK_SECTIONS[0]["narration"]
            elif field_name in ("conclusion", "conclusion_concept"):
                mock_payload[field_name] = DEFAULT_MOCK_SECTIONS[-1]["narration"]
            elif field_name == "call_to_action":
                mock_payload["call_to_action"] = "Subscribe for deep architectural breakdowns and star the repository!"
            elif field_name == "full_text":
                mock_payload["full_text"] = "\n\n".join(s["narration"] for s in DEFAULT_MOCK_SECTIONS)
            elif field_name == "video_title":
                mock_payload["video_title"] = "Why PostgreSQL SKIP LOCKED Replaces Redis Queues"
            elif field_name == "status":
                mock_payload["status"] = "success"
            elif field_name == "analysis":
                mock_payload["analysis"] = "Mock high-confidence synthesis"
            elif field_name == "confidence_score":
                mock_payload["confidence_score"] = 0.94
            else:
                default_val = field_info.default
                if default_val is not None and default_val != ... and default_val is not PydanticUndefined:
                    mock_payload[field_name] = default_val
                elif field_info.annotation is UUID or field_name.endswith("_id") or field_name == "id":
                    mock_payload[field_name] = uuid4()
                elif field_info.annotation is str:
                    mock_payload[field_name] = f"Mock {field_name}"
                elif field_info.annotation is int:
                    mock_payload[field_name] = 100
                elif field_info.annotation is float:
                    mock_payload[field_name] = 85.5
                elif field_info.annotation is bool:
                    mock_payload[field_name] = True
                elif field_info.annotation is list or getattr(field_info.annotation, "__origin__", None) is list:
                    mock_payload[field_name] = []
                else:
                    mock_payload[field_name] = "Mock value"

        try:
            parsed_instance = response_schema.model_validate(mock_payload)
        except Exception:
            # Fallback to default initialization if possible
            parsed_instance = response_schema.model_construct(**mock_payload)

        raw_json_str = json.dumps(mock_payload, indent=2, default=str)
        prompt_tokens = self._estimate_tokens(prompt)
        completion_tokens = self._estimate_tokens(raw_json_str)
        total = prompt_tokens + completion_tokens

        return ProviderStructuredResponse(
            parsed=parsed_instance,
            raw_text=raw_json_str,
            usage=ProviderUsageMetrics(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
                estimated_cost_usd=round(total * 0.0000001, 6),
            ),
            model_name=chosen_model,
        )

    async def health_check(self) -> ProviderHealthStatus:
        start_time = time.perf_counter()
        try:
            self._check_simulated_faults()
            latency = (time.perf_counter() - start_time) * 1000
            return ProviderHealthStatus(
                is_healthy=True,
                provider_name=self.name,
                model_name=self.default_model,
                latency_ms=round(latency, 2),
                message="Mock AI provider operational (deterministic offline mode).",
            )
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000
            return ProviderHealthStatus(
                is_healthy=False,
                provider_name=self.name,
                model_name=self.default_model,
                latency_ms=round(latency, 2),
                message=f"Mock AI provider error: {str(exc)}",
            )
