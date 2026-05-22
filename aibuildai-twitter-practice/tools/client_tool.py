from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DEFAULT_DOTENV_FILE = ".env"
APPROVED_FACTS_FILE = "approved_facts.json"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_openai_api_key() -> str:
    env_path = os.path.join(_PROJECT_ROOT, DEFAULT_DOTENV_FILE)
    with open(env_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "OPENAI_API_KEY":
                return value.strip().strip('"').strip("'")
    raise ValueError("OPENAI_API_KEY not found in .env")


def get_client() -> Any:
    return OpenAI(api_key=_resolve_openai_api_key())


def get_approved_facts() -> Dict[str, Any]:
    facts_path = os.path.join(_PROJECT_ROOT, APPROVED_FACTS_FILE)
    with open(facts_path, "r", encoding="utf-8") as f:
        return json.load(f)


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
