from __future__ import annotations

from typing import Any, Dict, List, Optional

from .relevance_tool import classify_relevance
from .reply_tool import generate_tweet_reply
from .safety_tool import detect_hard_blocks, safety_and_tone_check


def process_tweet(
    post_text: str,
    client: Any,
    approved_facts: Dict[str, Any],
) -> Dict[str, Any]:
    if not post_text.strip():
        return {
            "relevant": False,
            "reason": "Input post_text is empty.",
            "reply": None,
            "safety_flags": [],
            "confidence": 0.0,
        }

    block_flags = detect_hard_blocks(post_text)
    if block_flags:
        return {
            "relevant": False,
            "reason": "Post triggered safety hard blocks.",
            "reply": None,
            "safety_flags": sorted(set(block_flags)),
            "confidence": 0.99,
        }

    relevance = classify_relevance(post_text, client, approved_facts)
    relevant = bool(relevance["relevant"])
    reason = str(relevance["reason"])
    confidence = float(relevance["confidence"])

    reply: Optional[str] = None
    if relevant:
        reply = generate_tweet_reply(post_text, client, approved_facts)

    flags = safety_and_tone_check(post_text, reply)
    if flags:
        return {
            "relevant": False,
            "reason": "Reply blocked by safety/tone checks.",
            "reply": None,
            "safety_flags": flags,
            "confidence": round(confidence, 4),
        }

    if not relevant:
        return {
            "relevant": False,
            "reason": reason,
            "reply": None,
            "safety_flags": [],
            "confidence": round(confidence, 4),
        }

    return {
        "relevant": True,
        "reason": reason,
        "reply": reply,
        "safety_flags": [],
        "confidence": round(confidence, 4),
    }


def process_batch(
    tweets: List[Dict[str, Any]],
    client: Any,
    approved_facts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for tweet in tweets:
        text = str(tweet.get("text", "")).strip()
        if not text:
            continue
        result = process_tweet(post_text=text, client=client, approved_facts=approved_facts)
        result["text"] = text
        result["tweet_id"] = tweet.get("id")
        result["author_id"] = tweet.get("author_id")
        result["created_at"] = tweet.get("created_at")
        results.append(result)
    return results
