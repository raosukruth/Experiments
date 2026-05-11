"""researcher-agent: looks up facts about a topic (canned file or Wikipedia),
then asks the LLM to compress them into bullets.

Run: `python -m bots.researcher` (port 8001).
"""
from __future__ import annotations

import json
import pathlib
import urllib.parse

import httpx

from bots._adapter import make_adapter, serve
from bots._llm import complete

PORT = 8001
SOURCES_FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "sources.json"

SYSTEM_PROMPT = (
    "You are a meticulous research assistant. Given facts about a topic, "
    "produce 5–8 concise bullet points and a final 'References:' line listing "
    "the sources. Do not invent facts beyond what was provided."
)

_cache: dict[str, str] = {}


def _load_canned() -> dict[str, str]:
    if not SOURCES_FILE.exists():
        return {}
    return json.loads(SOURCES_FILE.read_text())


async def _fetch_wikipedia(topic: str) -> str:
    slug = urllib.parse.quote(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(url, headers={"User-Agent": "openclaw-demo/0.1"})
            r.raise_for_status()
            data = r.json()
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", url)
            return f"{extract}\n\nSource: {page_url}" if extract else ""
        except (httpx.HTTPError, ValueError):
            return ""


async def _gather_facts(topic: str) -> tuple[str, str]:
    canned = _load_canned()
    key = topic.strip().lower()
    if key in canned:
        return canned[key], "canned"
    if key in _cache:
        return _cache[key], "cache"
    fetched = await _fetch_wikipedia(topic)
    if fetched:
        _cache[key] = fetched
        return fetched, "wikipedia"
    return f"(no external data found for: {topic})", "stub"


async def handler(user_msg: str) -> str:
    topic = user_msg.removeprefix("Research this topic:").strip(" :\n") or user_msg.strip()
    facts, source = await _gather_facts(topic)
    prompt = (
        f"Topic: {topic}\n\n"
        f"Source ({source}):\n{facts}\n\n"
        f"Produce the bullets now."
    )
    return await complete(prompt, system=SYSTEM_PROMPT, max_tokens=600)


app = make_adapter("researcher", handler)


if __name__ == "__main__":
    serve(app, PORT)
