"""writer-agent: drafts an article from research bullets, then runs a Python
control loop to re-prompt once if the word count is well off-target.

Run: `python -m bots.writer` (port 8002).
"""
from __future__ import annotations

from bots._adapter import make_adapter, serve
from bots._llm import complete

PORT = 8002

SYSTEM_PROMPT = (
    "You are a feature writer. Given research bullets, write a clear article with "
    "a punchy lede and at least one Markdown heading (e.g. '## ...'). Aim for the "
    "requested word count; do not hedge or pad."
)


def _target_words(bullet_text: str) -> int:
    bullets = [b for b in bullet_text.splitlines() if b.strip().startswith(("-", "*", "•"))]
    n = len(bullets) or 5
    if n <= 4:
        return 200
    if n <= 7:
        return 300
    return 400


async def _draft(bullets: str, target: int) -> str:
    return await complete(
        f"Write an article of about {target} words using these bullets:\n\n{bullets}",
        system=SYSTEM_PROMPT,
        max_tokens=900,
    )


async def handler(user_msg: str) -> str:
    bullets = user_msg
    target = _target_words(bullets)

    article = await _draft(bullets, target)
    actual = len(article.split())

    drift = abs(actual - target) / target
    if drift > 0.25:
        verb = "expand" if actual < target else "trim"
        article = await complete(
            f"This article is {actual} words but the target is {target}. "
            f"Please {verb} it to about {target} words while keeping the same "
            f"structure (lede + heading + body):\n\n{article}",
            system=SYSTEM_PROMPT,
            max_tokens=900,
        )

    return article


app = make_adapter("writer", handler)


if __name__ == "__main__":
    serve(app, PORT)
