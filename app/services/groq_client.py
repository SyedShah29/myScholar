from __future__ import annotations

import logging
from typing import Any, AsyncIterator

import httpx
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GroqError(Exception):
    pass


class MissingGroqKey(GroqError):
    pass


class GroqClient:
    def __init__(self, api_key: str | None, base_url: str, model: str, timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and "your-" not in self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    @retry(
        retry=retry_if_not_exception_type(MissingGroqKey),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise MissingGroqKey("Groq API key not configured.")
        client = await self._get_client()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
        if resp.status_code >= 400:
            raise GroqError(f"Groq error {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """Yields text token chunks as they stream from Groq."""
        if not self.enabled:
            raise MissingGroqKey("Groq API key not configured.")
        client = await self._get_client()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise GroqError(f"Groq stream error {resp.status_code}: {body[:500]}")
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
