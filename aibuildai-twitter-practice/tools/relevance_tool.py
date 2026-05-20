from __future__ import annotations

from typing import Any, Dict

from .client_tool import format_approved_facts, llm_json

RELEVANCE_THRESHOLD = 0.60


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

                Mark as relevant if the post fits ANY of these:
                - Struggling with or asking for help on ML model training, hyperparameter tuning, or AutoML
                - Working on a Kaggle competition or structured ML task (tabular, image classification, segmentation, NLP)
                - Comparing AutoML tools or ML pipelines and open to suggestions
                - Frustrated with manual ML iteration and looking for a better approach
                - Asking where to start with building a model from data
                - Mentioning MLE-Bench, automated model building, or autonomous ML agents
                - Working on tasks AIBuildAI explicitly supports: tabular classification, image segmentation, protein prediction, NLP scoring
                - Skeptical or critical of automated ML / "AI builds AI" tools — these are valid openings to cite AIBuildAI's real-world Kaggle results as evidence

                Do NOT mark as relevant if the post is about:
                - LLM app development, RAG pipelines, LangChain, prompt engineering, or AI agents for task automation
                - Model serving, inference optimization, or deployment
                - AI news, regulation, hiring, or general commentary
                - Crypto, spam, or self-promotion

                If the signal is weak or ambiguous, return relevant=false.

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
