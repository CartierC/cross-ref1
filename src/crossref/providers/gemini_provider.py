from __future__ import annotations

import os

from .base import Provider

DEFAULT_MODEL = "gemini-1.5-pro"


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, model: str | None = None, **kwargs):
        super().__init__(model=model or DEFAULT_MODEL, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai  # lazy import: optional dependency

            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            genai.configure(api_key=api_key)
            self._client = genai
        return self._client

    def _complete_once(self, system: str, user: str) -> str:
        genai = self._get_client()
        model = genai.GenerativeModel(model_name=self.model, system_instruction=system)
        response = model.generate_content(user)
        return response.text or ""
