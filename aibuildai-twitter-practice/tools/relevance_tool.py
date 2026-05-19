from __future__ import annotations

from typing import Any, Dict

from .client_tool import format_approved_facts, llm_json

RELEVANCE_THRESHOLD = 0.65


def classify_relevance(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> Dict[str, Any]:
    facts_text = format_approved_facts(approved_facts)
    prompt = f"""
                Classify whether this tweet is relevant to AI Build AI.

                Return only valid JSON.

                {facts_text}

                Output keys:
                - relevant: boolean
                - reason: short one-sentence explanation
                - confidence: number between 0 and 1

                Relevant only if the post is about practical AI building, such as agents, workflows, tooling, implementation, or open-source references.
                If the signal is weak, return relevant=false.

                Tweet:
                {post_text}
            """.strip()

    system_prompt = (
        "You are a strict classifier. Do not be verbose. Do not invent project facts. "
        "Use only the provided repository facts."
    )
    result = llm_json(client, prompt, system_prompt=system_prompt)
    confidence = float(result.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))
    relevant = bool(result.get("relevant", False)) and confidence >= RELEVANCE_THRESHOLD
    return {
        "relevant": relevant,
        "reason": str(result.get("reason", "No reason provided.")),
        "confidence": confidence,
    }
