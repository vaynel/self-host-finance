"""Groq client (OpenAI-compatible Chat Completions)."""

import os
import json
import re
from typing import Any

import httpx

from app.config import get_settings


class GroqClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = os.getenv("GROQ_API_KEY") or settings.groq_api_key
        self.base_url = os.getenv("GROQ_BASE_URL") or settings.groq_base_url
        self.model = os.getenv("GROQ_MODEL") or settings.groq_model
        # Known decommissioned legacy defaults -> pick a sane modern default.
        if self.model in ("llama3-8b-8192", "llama3-70b-8192"):
            self.model = os.getenv("GROQ_MODEL_FALLBACK") or "llama-3.1-8b-instant"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY가 설정되어 있지 않습니다.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _loads_json_object_loose(text: str) -> dict[str, Any]:
        """
        Groq 응답 message.content가 JSON만 딱 오지 않는 케이스를 대비해
        - 1차: json.loads 그대로 시도
        - 2차: 문자열 내 첫 번째 {...} JSON 오브젝트를 찾아 파싱
        """
        if not text:
            raise ValueError("empty content")
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("no json object found in content")
        obj = json.loads(m.group(0))
        if not isinstance(obj, dict):
            raise ValueError("json is not an object")
        return obj

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        """
        Calls Groq OpenAI-compatible endpoint and returns the raw JSON response.
        """
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            last_err: Exception | None = None

            fallback_models_env = os.getenv("GROQ_FALLBACK_MODELS") or ""
            fallback_models = [m.strip() for m in fallback_models_env.split(",") if m.strip()]
            if not fallback_models:
                fallback_models = ["llama-3.1-8b-instant", "llama-3.1-70b-versatile"]

            tried = []
            for model in [self.model, *fallback_models]:
                if model in tried:
                    continue
                tried.append(model)
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                r = await client.post(url, headers=self._headers(), json=payload)
                if r.status_code < 400:
                    self.model = model  # keep the working model for this process
                    return r.json()

                # If model is decommissioned, try next model; otherwise surface the error.
                try:
                    body = r.json()
                except Exception:
                    body = {"error": {"message": r.text}}
                err = body.get("error") or {}
                code = err.get("code")
                if r.status_code == 400 and code == "model_decommissioned":
                    last_err = RuntimeError(f"Groq model decommissioned: {model} ({err.get('message')})")
                    continue
                last_err = RuntimeError(f"Groq API error: {r.status_code} {r.text}")
                break

            raise last_err or RuntimeError("Groq API error: unknown")

    async def classify_category(self, *, description: str, amount: float, categories: list[str]) -> str:
        """
        Classify a transaction into one of the provided categories.
        Returns "기타" on failure.
        """
        if not categories:
            return "기타"

        system = (
            "너는 개인 재무 거래내역을 카테고리로 분류하는 도우미다. "
            "반드시 제공된 카테고리 목록 중 하나만 선택한다."
        )
        user = (
            f"거래 설명: {description}\n"
            f"금액: {amount}\n"
            f"카테고리 목록: {categories}\n\n"
            '다음 JSON만 출력해: {"category": "카테고리명"}'
        )
        try:
            resp = await self.chat_json(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0,
                max_tokens=200,
            )
            content = resp["choices"][0]["message"]["content"]
            data = self._loads_json_object_loose(content)
            cat = str(data.get("category") or "").strip()
            if not cat:
                return "기타"
            # only allow provided categories
            for c in categories:
                if c.strip().lower() == cat.lower():
                    return c
            return "기타"
        except Exception:
            return "기타"
