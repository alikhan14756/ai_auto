"""Base interface, data models, and exception definitions for AI providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


# ============================================================================
# Exceptions
# ============================================================================

class AIProviderError(Exception):
    """Base exception for all AI provider communication and inference errors."""

    def __init__(self, message: str, provider: str = "unknown", status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class AIRateLimitError(AIProviderError):
    """Raised when provider returns HTTP 429 or client exceeds RPM limit."""
    pass


class AIQuotaExceededError(AIProviderError):
    """Raised when daily, monthly, or billing account quota is exhausted."""
    pass


class AITimeoutError(AIProviderError):
    """Raised when inference request exceeds configured network timeout."""
    pass


class AIAuthenticationError(AIProviderError):
    """Raised when API key is missing, invalid, or unauthorized."""
    pass


class AIBudgetExceededError(AIProviderError):
    """Raised when account or channel monthly spend cap is reached."""
    pass


# ============================================================================
# Data Contracts & Schemas
# ============================================================================

class ProviderUsageMetrics(BaseModel):
    """Token consumption and cost accounting details for an AI invocation."""
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)


class ProviderTextResponse(BaseModel):
    """Standardized response container for unstructured natural text generation."""
    text: str
    usage: ProviderUsageMetrics
    model_name: str
    raw_response: Optional[Dict[str, Any]] = None


class ProviderStructuredResponse(BaseModel):
    """Standardized response container for schema-enforced structured generation."""
    parsed: Any
    raw_text: str
    usage: ProviderUsageMetrics
    model_name: str


class ProviderHealthStatus(BaseModel):
    """Diagnostic health and connectivity status of the AI provider."""
    is_healthy: bool
    provider_name: str
    model_name: str
    latency_ms: float
    message: str


# ============================================================================
# Abstract AI Provider Interface
# ============================================================================

class AIProviderInterface(ABC):
    """Abstract base class that all AI inference engines must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the provider (e.g. GEMINI, MOCK)."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier used when none is specified."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout_seconds: float = 60.0,
    ) -> ProviderTextResponse:
        """Generate natural language text from a prompt."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
    ) -> ProviderStructuredResponse:
        """Generate schema-conforming structured output parsed into Pydantic model."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealthStatus:
        """Execute a lightweight test query to confirm provider connectivity."""
        pass
