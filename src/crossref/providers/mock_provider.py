from __future__ import annotations

from collections.abc import Callable

from .base import Provider


class MockProvider(Provider):
    """Deterministic, network-free provider for tests and CI.

    `responder` receives (system, user) and returns the text to hand back.
    Defaults to echoing a fixed string so tests can assert on call inputs
    without needing a real script.
    """

    name = "mock"

    def __init__(
        self,
        model: str | None = None,
        responder: Callable[[str, str], str] | None = None,
        **kwargs,
    ):
        super().__init__(model=model or "mock-model", **kwargs)
        self._responder = responder or (lambda system, user: "MOCK_RESPONSE")
        self.calls: list[tuple[str, str]] = []

    def _complete_once(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responder(system, user)
