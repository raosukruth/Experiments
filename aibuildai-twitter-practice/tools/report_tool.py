from __future__ import annotations

import json
import os
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def results_to_markdown(input_path: Optional[str] = None, output_path: Optional[str] = None) -> str:
    input_path = input_path or os.path.join(_PROJECT_ROOT, "output.json")
    output_path = output_path or os.path.join(_PROJECT_ROOT, "output.md")

    with open(input_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    def _cell(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ").strip()

    lines = [
        "# AIBuildAI Reply Pipeline Results",
        "",
        f"Total tweets: {len(results)}",
        "",
        "| # | Input Tweet | Generated Reply |",
        "|---|-------------|-----------------|",
    ]

    for i, entry in enumerate(results, 1):
        tweet = _cell(entry.get("question") or "")
        reply = _cell(entry.get("response") or "") or "*—*"
        lines.append(f"| {i} | {tweet} | {reply} |")

    lines.append("")
    markdown = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return output_path
