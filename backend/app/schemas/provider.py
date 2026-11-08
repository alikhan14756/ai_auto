"""Pydantic schemas for AI Providers, Health Status, and Usage Metering."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderHealthResponse(BaseModel):
    """Health check response for AI inference provider."""
    is_healthy: bool
    provider_name: str
    model_name: str
    latency_ms: float
    message: str


class ProviderStatusResponse(BaseModel):
    """Active AI provider configuration, rate limits, and status."""
    active_provider: str
    default_model: str
    reasoning_model: str
    free_tier_rpm_limit: int
    free_tier_rpd_limit: int
    current_rpm: int
    current_rpd: int
    has_api_key: bool


class ModelUsageBreakdown(BaseModel):
    """Token consumption and cost breakdown for a specific model."""
    model_name: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class UsageSummaryResponse(BaseModel):
    """Channel token consumption, spend, and monthly budget summary."""
    current_month_spend_usd: float
    max_monthly_spend_usd: float
    is_budget_exceeded: bool
    current_month_input_tokens: int
    current_month_output_tokens: int
    current_month_total_tokens: int
    total_requests: int
    breakdown_by_model: List[ModelUsageBreakdown]


class ProviderTestRequest(BaseModel):
    """Test inference request."""
    prompt: str = Field(default="Explain what an idempotent queue worker is in two sentences.")
    model: Optional[str] = None


class ProviderTestResponse(BaseModel):
    """Test inference result."""
    text: str
    usage: Dict[str, Any]
    model_name: str
