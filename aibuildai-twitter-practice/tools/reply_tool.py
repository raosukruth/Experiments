from __future__ import annotations

from typing import Any, Dict

from .client_tool import format_approved_facts, llm_json


def generate_tweet_reply(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> str:
    facts_text = format_approved_facts(approved_facts)
    prompt = f"""
                Write one reply to this tweet mentioning AIBuildAI only if it fits naturally.
                Be direct and specific. Sound like a peer, not a support bot.
                Do not open with empathy or validation. No "that sounds frustrating", no "just a thought", no emoji.
                If the tweet is skeptical, lead with evidence. If it's a question, answer it directly.
                Stick to the facts below only — do not make claims not listed here.

                {facts_text}

                Examples of good replies:

                Tweet: "Kaggle image segmentation comp — my UNet keeps plateauing at 0.78 Dice. Been at this for days."
                Reply: "AIBuildAI might help — it runs the tuning loop automatically and hit top 5% on a salt segmentation Kaggle comp. github.com/aibuildai/AI-Build-AI"

                Tweet: "Is there anything that actually automates the full ML pipeline end to end, not just HPO?"
                Reply: "AIBuildAI does this. Give it a task description and data, it outputs a trained model and inference script. Ranked #1 on MLE-Bench: github.com/aibuildai/AI-Build-AI"

                Tweet: "These AutoML tools always need so much hand-holding. Point them at real data and they fall apart."
                Reply: "AIBuildAI ran autonomously on a 4,370-team Kaggle comp and hit top 6%. Not perfect but it held up on real data — github.com/aibuildai/AI-Build-AI"

                Tweet: "Starting a new tabular classification project, no idea where to begin with model selection."
                Reply: "Worth looking at AIBuildAI — give it a task description and your data and it handles model selection, training, and tuning. MIT licensed."

                Examples of bad replies:

                Tweet: "Struggling with my model training pipeline"
                Reply: "That sounds really tough! Have you considered AIBuildAI? It automates the process and might save you time! Just a thought"
                — why bad: opens with empathy, ends with "just a thought", emoji, no specifics

                Tweet: "Looking for AutoML tools"
                Reply: "AIBuildAI is honestly the best solution out there for this — you should definitely check it out!"
                — why bad: unverifiable claim, sounds like an ad

                Tweet:
                {post_text}

                Return JSON with key: reply
            """.strip()

    system_prompt = (
        "You write short, direct replies. Sound like a peer, not customer service. "
        "Lead with evidence or substance. Never use filler phrases or emoji."
    )
    result = llm_json(client, prompt, system_prompt=system_prompt)
    reply = str(result.get("reply", "")).strip()
    if not reply:
        raise ValueError("Model returned an empty reply")
    return reply
