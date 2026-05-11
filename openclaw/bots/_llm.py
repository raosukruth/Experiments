"""Thin async wrapper around OpenAI's Chat Completions API.

For the dev demo, bots call OpenAI directly (not through OpenClaw) for
LLM completions. OpenClaw's role here is purely orchestration/routing.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

MODEL = os.environ.get("BASE_LLM_MODEL", "gpt-4o-mini")
API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment.")

_client = AsyncOpenAI(api_key=API_KEY)


async def complete(prompt: str, *, system: str | None = None, max_tokens: int = 1024) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = await _client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=messages,
    )
    return (resp.choices[0].message.content or "").strip()
