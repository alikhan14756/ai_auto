"""Base job handler interfaces and exceptions."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Awaitable, Optional
from app.models.job import AutomationJob


class JobException(Exception):
    """Base exception for all job execution errors."""
    pass


class TransientException(JobException):
    """Temporary or recoverable failure that should trigger an exponential retry."""
    pass


class HardFailureException(JobException):
    """Permanent, non-retryable failure (e.g. invalid payload or schema violation)."""
    pass


class JobCancelledException(JobException):
    """Raised when a job execution was aborted due to a cancellation request."""
    pass


# Type aliases for worker callbacks
ProgressCallback = Callable[[int, Optional[str]], Awaitable[None]]
CancellationChecker = Callable[[], Awaitable[bool]]


class BaseJobHandler(ABC):
    """Abstract base class for all pipeline and system job handlers."""

    @abstractmethod
    async def validate(self, payload: Dict[str, Any]) -> None:
        """Validate input payload before execution. Raises HardFailureException if invalid."""
        pass

    @abstractmethod
    async def execute(
        self,
        job: AutomationJob,
        update_progress: ProgressCallback,
        is_cancelled: CancellationChecker,
    ) -> Dict[str, Any]:
        """Execute the job logic.
        Must periodically call `update_progress(percentage, stage)`
        and check `await is_cancelled()`.
        Returns dictionary of execution results.
        """
        pass
