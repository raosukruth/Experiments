import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
RELEVANCE_THRESHOLD = 0.65
DEFAULT_API_KEY_FILE = "openai-api.txt"
APPROVED_FACTS_FILE = "approved_facts.json"

HARD_BLOCK_PATTERNS = {
    "harassment_context": [r"\bkill yourself\b", r"\bhate\b", r"\bslur\b"],
    "self_harm_context": [r"\bself harm\b", r"\bsuicide\b"],
    "illegal_activity_context": [r"\bhow to hack\b", r"\bfraud\b", r"\bdrug recipe\b"],
}

BANNED_REPLY_PATTERNS = [
    r"\bbest solution for everyone\b",
    r"\bmiss out\b",
    r"\bproduction[- ]ready\b",
    r"\bdeployment automation\b",
    r"\bautomated deployment\b",
]

WORKFLOW_SIGNAL_PATTERNS = [
    r"\btun(?:e|ing|ed)\b",
    r"\bhyperparameter\b",
    r"\bpipeline\b",
    r"\biterat(?:e|ion|ive)\b",
    r"\barchitectures?\b",
    r"\bmulti[- ]?(?:task|domain)\b",
    r"\bboilerplate\b",
    r"\bexperiment(?:ation|s)?\b",
    r"\bworkflow\b",
    r"\bml models?\b",
]

GENERIC_NEGATIVE_PATTERNS = [
    r"\bkeep up with\b",
    r"\bfavorite\b",
    r"\bbest practices?\b",
    r"\bopen[- ]source references?\b",
    r"\bprompt engineering\b",
    r"\bshare(?:ing)? ai research updates\b",
]

ALLOWED_SUPERLATIVE_CONTEXT_PATTERNS = [
    r"openai\s+mle[- ]?bench",
]

NEAR_MISS_TEMPLATES = [
    "One thing that might help here is looking at AIBuildAI for automating model iteration and tuning across tasks.",
    "A practical option to explore is AIBuildAI if you want less manual overhead in model-building workflows.",
    "Could be worth a look: AIBuildAI focuses on automating design, training, tuning, and evaluation loops.",
    "If your team is hitting workflow friction, AIBuildAI may be a useful reference for end-to-end model automation.",
]

def _contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _count_matches(text: str, patterns: List[str]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE))


def _opening_signature(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    tokens = [token for token in cleaned.split() if token]
    return " ".join(tokens[:2])


def _has_allowed_superlative_context(text: str) -> bool:
    return _contains_any(text, ALLOWED_SUPERLATIVE_CONTEXT_PATTERNS)


def _explicit_negative_relevance(text: str) -> bool:
    return _contains_any(text, GENERIC_NEGATIVE_PATTERNS)


def _workflow_signal_score(text: str) -> int:
    return _count_matches(text, WORKFLOW_SIGNAL_PATTERNS)


def detect_hard_blocks(post_text: str) -> List[str]:
    flags: List[str] = []
    for label, patterns in HARD_BLOCK_PATTERNS.items():
        if _contains_any(post_text, patterns):
            flags.append(label)
    return flags


def load_approved_facts() -> Dict[str, Any]:
    facts_path = os.path.join(os.path.dirname(__file__), APPROVED_FACTS_FILE)
    with open(facts_path, "r", encoding="utf-8") as facts_file:
        return json.load(facts_file)


def format_approved_facts(facts: Dict[str, Any]) -> str:
    lines = [f"Project: {facts.get('project_name', 'AIBuildAI')}"]
    short_description = facts.get("short_description")
    if short_description:
        lines.append(f"Description: {short_description}")

    approved = facts.get("approved_facts", [])
    if approved:
        lines.append("Approved facts:")
        lines.extend(f"- {fact}" for fact in approved)

    return "\n".join(lines)


def llm_json(client: Any, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0.8,  
    )

    text = response.choices[0].message.content if response.choices else None
    if not text:
        raise ValueError("Model returned empty message content")

    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


def determine_relevance(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> Dict[str, Any]:
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

    llm_relevant = bool(result.get("relevant", False))
    explicit_negative = _explicit_negative_relevance(post_text)
    workflow_score = _workflow_signal_score(post_text)

    # If model is highly confident in a rejection without explicit negative evidence,
    # require a second pass before keeping that confidence.
    if not llm_relevant and confidence > 0.85 and not explicit_negative:
        second_pass_prompt = f"""
                        Re-check this relevance decision.
                        Return only valid JSON with keys:
                        - relevant: boolean
                        - reason: short sentence
                        - confidence: number between 0 and 1

                        Consider this relevant if it clearly discusses practical ML workflow pain points:
                        tuning, pipelines, iteration, architecture comparison, multi-task/multi-domain setup,
                        boilerplate reduction, or experiment management.

                        Tweet:
                        {post_text}
                    """.strip()
        second = llm_json(client, second_pass_prompt, system_prompt="You are a strict classifier.")
        second_confidence = float(second.get("confidence", confidence))
        second_confidence = max(0.0, min(1.0, second_confidence))
        llm_relevant = bool(second.get("relevant", llm_relevant))
        confidence = second_confidence

    near_miss = (not llm_relevant) and (workflow_score >= 2) and not explicit_negative
    heuristic_relevant = (workflow_score >= 3) and not explicit_negative
    relevant = (llm_relevant and confidence >= RELEVANCE_THRESHOLD) or (
        heuristic_relevant and confidence >= 0.55
    )

    if not llm_relevant and not explicit_negative:
        confidence = min(confidence, 0.85)

    return {
        "relevant": relevant,
        "near_miss": near_miss,
        "reason": str(result.get("reason", "No reason provided.")),
        "confidence": confidence,
    }


def generate_reply(
    post_text: str,
    client: Any,
    approved_facts: Dict[str, Any],
    forbidden_opening_signature: Optional[str] = None,
) -> str:
    facts_text = format_approved_facts(approved_facts)

    opening_constraint = ""
    if forbidden_opening_signature:
        opening_constraint = (
            f"Do not start your reply with an opening similar to: '{forbidden_opening_signature}'."
        )

    prompt = f"""
                Write one reply to this tweet.
                Keep it brief, conversational, and useful.
                Make it soft, tentative, and natural rather than assertive.
                Start with a natural, varied opening—do not always use the same phrase. Openings should sound like a real person, not a template or formula.
                {opening_constraint}
                Mention AI Build AI naturally if relevant.
                Sound like a normal person making a helpful suggestion, not an ad.
                If you reference the project, stick to the facts below only.
                Do not make claims that are not explicitly supported here.
                Do not use "production-ready" or claim deployment automation.
                Avoid "best" or "leading" claims unless explicitly tied to OpenAI MLE-Bench.

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

    if forbidden_opening_signature and _opening_signature(reply) == forbidden_opening_signature:
        retry_prompt = prompt + "\nRewrite with a different natural opening."
        retry = llm_json(client, retry_prompt, system_prompt=system_prompt)
        retry_reply = str(retry.get("reply", "")).strip()
        if retry_reply:
            reply = retry_reply

    return reply


def generate_near_miss_reply(post_text: str, forbidden_opening_signature: Optional[str] = None) -> str:
    index = abs(hash(post_text)) % len(NEAR_MISS_TEMPLATES)
    candidate = NEAR_MISS_TEMPLATES[index]
    if forbidden_opening_signature and _opening_signature(candidate) == forbidden_opening_signature:
        candidate = NEAR_MISS_TEMPLATES[(index + 1) % len(NEAR_MISS_TEMPLATES)]
    return candidate


def safety_and_tone_check(post_text: str, reply: Optional[str]) -> List[str]:
    flags = detect_hard_blocks(post_text)
    if reply and _contains_any(reply, BANNED_REPLY_PATTERNS):
        flags.append("tone_violation")
    if reply and _contains_any(reply, [r"\bbest\b", r"\bleading\b", r"\b#1\b"]) and not _has_allowed_superlative_context(reply):
        flags.append("unverifiable_claim_risk")
    # Preserve deterministic order.
    return sorted(set(flags))


def process_post(
    post_text: str,
    client: Any,
    approved_facts: Dict[str, Any],
    previous_opening_signature: Optional[str] = None,
) -> Dict[str, Any]:
    if not post_text.strip():
        return {
            "relevant": False,
            "reason": "Input post_text is empty.",
            "reply": None,
            "safety_flags": [],
            "confidence": 0.0,
            "opening_signature": None,
        }

    block_flags = detect_hard_blocks(post_text)
    if block_flags:
        return {
            "relevant": False,
            "reason": "Post triggered safety hard blocks.",
            "reply": None,
            "safety_flags": sorted(set(block_flags)),
            "confidence": 0.99,
            "opening_signature": None,
        }

    relevance = determine_relevance(post_text, client, approved_facts)
    relevant = bool(relevance["relevant"])
    near_miss = bool(relevance.get("near_miss", False))
    reason = str(relevance["reason"])
    confidence = float(relevance["confidence"])

    reply: Optional[str] = None
    if relevant:
        reply = generate_reply(
            post_text,
            client,
            approved_facts,
            forbidden_opening_signature=previous_opening_signature,
        )
    elif near_miss:
        reply = generate_near_miss_reply(
            post_text,
            forbidden_opening_signature=previous_opening_signature,
        )

    safety_flags = safety_and_tone_check(post_text, reply)
    if safety_flags:
        return {
            "relevant": False,
            "reason": "Reply blocked by safety/tone checks.",
            "reply": None,
            "safety_flags": safety_flags,
            "confidence": round(confidence, 4),
            "opening_signature": None,
        }

    if not relevant and not near_miss:
        return {
            "relevant": False,
            "reason": reason,
            "reply": None,
            "safety_flags": [],
            "confidence": round(confidence, 4),
            "opening_signature": None,
        }

    if near_miss and not relevant:
        return {
            "relevant": False,
            "reason": f"Near miss: {reason}",
            "reply": reply,
            "safety_flags": [],
            "confidence": round(confidence, 4),
            "opening_signature": _opening_signature(reply or ""),
        }

    return {
        "relevant": True,
        "reason": reason,
        "reply": reply,
        "safety_flags": [],
        "confidence": round(confidence, 4),
        "opening_signature": _opening_signature(reply or ""),
    }


def build_client() -> Any:
    key_file_path = os.path.join(os.path.dirname(__file__), DEFAULT_API_KEY_FILE)

    with open(key_file_path, "r", encoding="utf-8") as key_file:
        api_key = key_file.read().strip()

    return OpenAI(api_key=api_key)


def main():

    import sys
    args = sys.argv[1:]

    approved_facts = load_approved_facts()
    client = build_client()


    if args and args[0] == "--test":
        prompts_path = os.path.join(os.path.dirname(__file__), "prompts.txt")
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts = [line.strip() for line in f if line.strip()]
        results = []
        previous_opening_signature: Optional[str] = None
        for idx, prompt in enumerate(prompts, 1):
            decision = process_post(
                post_text=prompt,
                client=client,
                approved_facts=approved_facts,
                previous_opening_signature=previous_opening_signature,
            )
            previous_opening_signature = decision.get("opening_signature")
            results.append({
                "question": prompt,
                "response": decision.get("reply"),
                "confidence": decision.get("confidence")
            })
            print(f"Question {idx} finished.")
        output_path = os.path.join(os.path.dirname(__file__), "output.json")
        with open(output_path, "w", encoding="utf-8") as outf:
            json.dump(results, outf, indent=2)
        print(json.dumps(results, indent=2))
        return

    # Normal mode: accept prompt from CLI argument or stdin
    if args:
        post_text = " ".join(args).strip()
    else:
        post_text = input().strip()

    decision = process_post(post_text=post_text, client=client, approved_facts=approved_facts)
    print(json.dumps(decision))

if __name__ == "__main__":
    main()
    