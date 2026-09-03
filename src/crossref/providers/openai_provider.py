from __future__ import annotations

import os

from .base import Provider

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, model: str | None = None, **kwargs):
        super().__init__(model=model or DEFAULT_MODEL, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai  # lazy import: optional dependency

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            self._client = openai.OpenAI(api_key=api_key)
        return self._client

    def _complete_once(self, system: str, user: str) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
