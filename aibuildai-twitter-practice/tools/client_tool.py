from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_API_KEY_FILE = "openai-api.txt"
DEFAULT_DOTENV_FILE = ".env"
DEFAULT_SECRETS_FILE = "credentials.json"
APPROVED_FACTS_FILE = "approved_facts.json"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_secret_from_credentials(field: str) -> Optional[str]:
    credentials_path = os.path.join(_PROJECT_ROOT, DEFAULT_SECRETS_FILE)
    if not os.path.exists(credentials_path):
        return None
    with open(credentials_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    value = payload.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _load_dotenv_values() -> Dict[str, str]:
    env_path = os.path.join(_PROJECT_ROOT, DEFAULT_DOTENV_FILE)
    if not os.path.exists(env_path):
        return {}
    values: Dict[str, str] = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for raw in f:
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
    key_file_path = os.path.join(_PROJECT_ROOT, DEFAULT_API_KEY_FILE)
    with open(key_file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


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
