from __future__ import annotations

import re
from typing import List, Optional

HARD_BLOCK_PATTERNS = {
    "harassment_context": [r"\bkill yourself\b", r"\bkys\b", r"\bi hate you\b"],
    "self_harm_context": [r"\bself harm\b", r"\bsuicide\b"],
    "illegal_activity_context": [r"\bhow to hack\b", r"\bfraud\b", r"\bdrug recipe\b"],
}

BANNED_REPLY_PATTERNS = [
    r"\bbest solution for everyone\b",
    r"\bmiss out\b",
]


def _contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def detect_hard_blocks(post_text: str) -> List[str]:
    flags = []
    for label, patterns in HARD_BLOCK_PATTERNS.items():
        if _contains_any(post_text, patterns):
            flags.append(label)
    return flags


def safety_and_tone_check(post_text: str, reply: Optional[str]) -> List[str]:
    flags = detect_hard_blocks(post_text)
    if reply and _contains_any(reply, BANNED_REPLY_PATTERNS):
        flags.append("tone_violation")
    if reply and _contains_any(reply, [r"\bthe best\b", r"\bthe #1\b", r"\bbest tool\b", r"\bbest platform\b", r"\bbest solution\b"]):
        flags.append("unverifiable_claim_risk")
    return sorted(set(flags))
