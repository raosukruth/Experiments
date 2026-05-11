"""critic-agent: runs programmatic checks on an article, then asks the LLM
for a JSON verdict, and merges the two into a single JSON response.

Run: `python -m bots.critic` (port 8003).
"""
from __future__ import annotations

import json
import re
from typing import Any

from bots._adapter import make_adapter, serve
from bots._llm import complete

PORT = 8003

SYSTEM_PROMPT = (
    "You are a strict editor. Return ONLY a JSON object matching: "
    '{"score": <int 1-10>, "verdict": "<short string>", "issues": ["<string>", ...]}. '
    "No markdown, no prose, just the JSON object."
)

_SYLLABLE_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)


def _flesch_reading_ease(text: str) -> float:
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    words = [w for w in re.findall(r"\b\w+\b", text)]
    if not words:
        return 0.0
    syllables = sum(max(1, len(_SYLLABLE_RE.findall(w))) for w in words)
    return 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))


def _programmatic_checks(article: str) -> list[str]:
    issues: list[str] = []
    word_count = len(article.split())
    if word_count < 150:
        issues.append(f"too short ({word_count} words)")
    if word_count > 600:
        issues.append(f"too long ({word_count} words)")
    if not re.search(r"^#{1,6} ", article, flags=re.MULTILINE):
        issues.append("no markdown heading")
    ease = _flesch_reading_ease(article)
    if ease < 30:
        issues.append(f"reading ease very low ({ease:.0f})")
    return issues


def _parse_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object found in critic LLM output: {text[:200]}")
    return json.loads(match.group(0))


async def handler(user_msg: str) -> str:
    article = user_msg
    programmatic_issues = _programmatic_checks(article)

    raw = await complete(
        f"Critique this article and return the JSON object only:\n\n{article}",
        system=SYSTEM_PROMPT,
        max_tokens=400,
    )
    verdict = _parse_json(raw)

    score = int(verdict.get("score", 5))
    issues = list(verdict.get("issues", []))
    if programmatic_issues:
        score = max(1, score - 1)
        issues.extend(f"[programmatic] {i}" for i in programmatic_issues)

    merged = {
        "score": score,
        "verdict": str(verdict.get("verdict", "")),
        "issues": issues,
    }
    return json.dumps(merged)


app = make_adapter("critic", handler)


if __name__ == "__main__":
    serve(app, PORT)
