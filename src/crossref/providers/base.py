"""Provider abstraction: every LLM vendor implements the same narrow
interface so the orchestrator never depends on a specific SDK."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(RuntimeError):
    """Raised after retries are exhausted, or on a non-retryable failure."""


@dataclass
class RetryPolicy:
    max_retries: int = 4
    base_delay_seconds: float = 2.0

    def delay_for_attempt(self, attempt: int) -> float:
        # attempt is 0-indexed for the retry (not the first try)
        return self.base_delay_seconds * (2**attempt)


class Provider(ABC):
    """Minimal contract: turn (system prompt, user prompt) into text."""

    name: str = "base"

    def __init__(self, model: str | None = None, retry_policy: RetryPolicy | None = None):
        self.model = model
        self.retry_policy = retry_policy or RetryPolicy()

    @abstractmethod
    def _complete_once(self, system: str, user: str) -> str:
        """Single, unretried call to the underlying vendor SDK."""
        raise NotImplementedError

    def complete(self, system: str, user: str, sleep_fn=time.sleep) -> str:
        last_exc: Exception | None = None
        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                return self._complete_once(system, user)
            except Exception as exc:  # noqa: BLE001 - vendor SDKs raise varied types
                last_exc = exc
                if attempt >= self.retry_policy.max_retries:
                    break
                sleep_fn(self.retry_policy.delay_for_attempt(attempt))
        raise ProviderError(
            f"{self.name} provider failed after "
            f"{self.retry_policy.max_retries + 1} attempts: {last_exc}"
        ) from last_exc
