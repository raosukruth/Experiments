import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
RELEVANCE_THRESHOLD = 0.65
DEFAULT_API_KEY_FILE = "openai-api.txt"
DEFAULT_DOTENV_FILE = ".env"
DEFAULT_SECRETS_FILE = "credentials.json"
APPROVED_FACTS_FILE = "approved_facts.json"

HARD_BLOCK_PATTERNS = {
    "harassment_context": [r"\bkill yourself\b", r"\bhate\b", r"\bslur\b"],
    "self_harm_context": [r"\bself harm\b", r"\bsuicide\b"],
    "illegal_activity_context": [r"\bhow to hack\b", r"\bfraud\b", r"\bdrug recipe\b"],
}

BANNED_REPLY_PATTERNS = [
    r"\b#1\b",
    r"\bbest solution for everyone\b",
    r"\bmiss out\b",
]

def _contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


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


def _load_secret_from_credentials(field: str) -> Optional[str]:
    credentials_path = os.path.join(os.path.dirname(__file__), DEFAULT_SECRETS_FILE)
    if not os.path.exists(credentials_path):
        return None

    with open(credentials_path, "r", encoding="utf-8") as credentials_file:
        payload = json.load(credentials_file)

    value = payload.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _load_dotenv_values() -> Dict[str, str]:
    env_path = os.path.join(os.path.dirname(__file__), DEFAULT_DOTENV_FILE)
    if not os.path.exists(env_path):
        return {}

    values: Dict[str, str] = {}
    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw in env_file:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    return values


def _load_secret_from_dotenv(field: str) -> Optional[str]:
    value = _load_dotenv_values().get(field)
    if value and value.strip():
        return value.strip()
    return None


def _resolve_openai_api_key() -> str:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    dotenv_key = _load_secret_from_dotenv("OPENAI_API_KEY")
    if dotenv_key:
        return dotenv_key

    credentials_key = _load_secret_from_credentials("openai_api_key")
    if credentials_key:
        return credentials_key

    key_file_path = os.path.join(os.path.dirname(__file__), DEFAULT_API_KEY_FILE)
    with open(key_file_path, "r", encoding="utf-8") as key_file:
        return key_file.read().strip()


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
    relevant = bool(result.get("relevant", False)) and confidence >= RELEVANCE_THRESHOLD
    return {
        "relevant": relevant,
        "reason": str(result.get("reason", "No reason provided.")),
        "confidence": confidence,
    }


def generate_reply(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> str:
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


def safety_and_tone_check(post_text: str, reply: Optional[str]) -> List[str]:
    flags = detect_hard_blocks(post_text)
    if reply and _contains_any(reply, BANNED_REPLY_PATTERNS):
        flags.append("tone_violation")
    if reply and _contains_any(reply, [r"\bthe best\b", r"\b#1\b", r"\bbest tool\b", r"\bbest platform\b", r"\bbest solution\b"]):
        flags.append("unverifiable_claim_risk")
    # Preserve deterministic order.
    return sorted(set(flags))


def process_post(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> Dict[str, Any]:
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

    relevance = determine_relevance(post_text, client, approved_facts)
    relevant = bool(relevance["relevant"])
    reason = str(relevance["reason"])
    confidence = float(relevance["confidence"])

    reply: Optional[str] = None
    if relevant:
        reply = generate_reply(post_text, client, approved_facts)

    safety_flags = safety_and_tone_check(post_text, reply)
    if safety_flags:
        return {
            "relevant": False,
            "reason": "Reply blocked by safety/tone checks.",
            "reply": None,
            "safety_flags": safety_flags,
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


def build_client() -> Any:
    return OpenAI(api_key=_resolve_openai_api_key())


def main():

    import sys
    args = sys.argv[1:]

    approved_facts = load_approved_facts()
    client = build_client()


    if args and args[0] == "--test":
        prompts_path = os.path.join(os.path.dirname(__file__), "tweets.txt")
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts = [line.strip() for line in f if line.strip()]
        results = []
        for idx, prompt in enumerate(prompts, 1):
            decision = process_post(post_text=prompt, client=client, approved_facts=approved_facts)
            results.append({
                "question": prompt,
                "response": decision.get("reply"),
                "confidence": decision.get("confidence")
            })
            print(f"Question {idx} finished.")
        output_path = os.path.join(os.path.dirname(__file__), "tweet_eval_results.json")
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
    