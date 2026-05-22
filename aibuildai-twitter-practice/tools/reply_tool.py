from __future__ import annotations

from typing import Any, Dict

from .client_tool import format_approved_facts, llm_json


def generate_tweet_reply(post_text: str, client: Any, approved_facts: Dict[str, Any]) -> str:
    facts_text = format_approved_facts(approved_facts)
    prompt = f"""
                Write one reply to this tweet mentioning AIBuildAI only if it fits naturally.
                Sound like a person who's actually used it, not someone promoting it.
                Don't open by explaining what AIBuildAI is — get to the point.
                No empathy openers, no "just a thought", no emoji, no "check it out".
                If the tweet is skeptical, lead with a specific result. If it's a question, answer it first.
                Vary the structure — don't always start with "AIBuildAI".
                Stick to the facts below only — do not make claims not listed here.

                {facts_text}

                Examples of good replies:

                Tweet: "Kaggle image segmentation comp — my UNet keeps plateauing at 0.78 Dice. Been at this for days."
                Reply: "Might be worth trying AIBuildAI — it hit top 5% on a salt segmentation Kaggle comp running the tuning loop automatically. github.com/aibuildai/AI-Build-AI"

                Tweet: "Is there anything that actually automates the full ML pipeline end to end, not just HPO?"
                Reply: "AIBuildAI does — give it a task description and data, it outputs a trained model and inference script. Ranked #1 on MLE-Bench: github.com/aibuildai/AI-Build-AI"

                Tweet: "These AutoML tools always need so much hand-holding. Point them at real data and they fall apart."
                Reply: "It ran autonomously on a real 4,370-team Kaggle comp and hit top 6%. Not perfect but it held up — github.com/aibuildai/AI-Build-AI"

                Tweet: "Starting a new tabular classification project, no idea where to begin with model selection."
                Reply: "Give AIBuildAI a shot — you describe the task, hand it your data, it handles model selection and tuning. MIT licensed, worth a look."

                Tweet: "I have labeled MRI scans and need a classifier. Not sure what architecture to start with."
                Reply: "If you don't want to hand-pick architectures, AIBuildAI takes a task description and data and figures it out — designs, trains, tunes. github.com/aibuildai/AI-Build-AI"

                Examples of bad replies:

                Tweet: "Struggling with my model training pipeline"
                Reply: "That sounds really tough! Have you considered AIBuildAI? It automates the process and might save you time! Just a thought"
                — why bad: opens with empathy, ends with "just a thought", no specifics

                Tweet: "Looking for AutoML tools"
                Reply: "AIBuildAI automates the full ML pipeline automation. It is the best solution out there — check it out!"
                — why bad: explains what it is before getting to the point, unverifiable claim, sounds like an ad

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
