from __future__ import annotations

from typing import Any, Dict

from .client_tool import format_approved_facts, llm_json


def generate_tweet_reply(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> str:
    facts_text = format_approved_facts(approved_facts)
    prompt = f"""
                Write one reply to this tweet.
                Keep it brief, conversational, and useful.
                Make it soft, tentative, and natural rather than assertive.
                Start with a natural, varied opening—do not always use the same phrase. Openings should sound like a real person, not a template or formula.
                Mention AI Build AI naturally if relevant.
                Sound like a normal person making a helpful suggestion, not an ad.
                If you reference the project, stick to the facts below only.
                Do not make claims that are not explicitly supported here.

                {facts_text}

                Tweet:
                {post_text}

                Return JSON with key: reply
            """.strip()

    system_prompt = (
        "You write short, natural replies. Sound helpful, human, and slightly tentative. "
        "Avoid marketing language, hype, and confident-sounding claims that are not supported by the facts."
    )
    result = llm_json(client, prompt, system_prompt=system_prompt)
    reply = str(result.get("reply", "")).strip()
    if not reply:
        raise ValueError("Model returned an empty reply")
    return reply
