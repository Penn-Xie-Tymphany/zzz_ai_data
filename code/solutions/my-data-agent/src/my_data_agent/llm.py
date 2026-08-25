"""OpenAI-compatible LLM backend."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMClient:
    def __init__(self, model: str | None = None):
        self.client = OpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")

    def complete(self, messages: list[dict], system: str | None = None, temperature: float = 0.0) -> str:
        full = ([{"role": "system", "content": system}] if system else []) + messages
        resp = self.client.chat.completions.create(model=self.model, messages=full, temperature=temperature)
        return resp.choices[0].message.content or ""
