"""Groq client (OpenAI-compatible Chat Completions)."""

import os
from typing import Any

import httpx

from app.config import get_settings


class GroqClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = os.getenv("GROQ_API_KEY") or settings.groq_api_key
        self.base_url = os.getenv("GROQ_BASE_URL") or settings.groq_base_url
        self.model = os.getenv("GROQ_MODEL") or settings.groq_model

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY가 설정되어 있지 않습니다.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_json(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 1200) -> dict[str, Any]:
        """
        Calls Groq OpenAI-compatible endpoint and returns the raw JSON response.
        """
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            return r.json()

