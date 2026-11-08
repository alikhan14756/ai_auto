"""Base class for all domain-specific QA validators."""

import abc
import time
from typing import List
from app.services.qa.models import CheckResult, QAExecutionContext


class BaseQAValidator(abc.ABC):
    """Abstract validator class executing one or more checks within its domain category."""

    category: str = "GENERAL"

    @abc.abstractmethod
    async def validate(self, context: QAExecutionContext) -> List[CheckResult]:
        """Execute category checks against the execution context and return results."""
        pass

    def create_result(
        self,
        check_name: str,
        status: str,
        score: float,
        start_time: float,
        metrics: dict = None,
        findings: list = None,
        error_message: str = None,
    ) -> CheckResult:
        """Helper to assemble a standard CheckResult."""
        elapsed_ms = int((time.time() - start_time) * 1000)
        return CheckResult(
            category=self.category,
            check_name=check_name,
            status=status,
            score=max(0.0, min(100.0, float(score))),
            execution_time_ms=elapsed_ms,
            metrics=metrics or {},
            findings=findings or [],
            error_message=error_message,
        )
