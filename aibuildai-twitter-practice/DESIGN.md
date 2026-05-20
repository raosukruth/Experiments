# AIBuildAI Twitter Reply System — Design

## What This System Does

For each tweet, the system decides if a reply mentioning AIBuildAI would be genuinely helpful and safe. It:

1. Fetches tweets — either from the Twitter/X API or from a local `tweets.txt` file
2. Classifies each tweet for relevance (LLM, grounded in approved facts, threshold 0.65)
3. If relevant, generates one short natural non-promotional reply
4. Applies safety and tone checks (hard blocks, banned phrases, unverifiable claims)
5. Returns a structured result with confidence score
6. Writes all results to `output.json` (live) or `tweet_eval_results.json` (test)

## Pipeline Modes

There are two ways to run the pipeline:

| Mode | Source | Output | Twitter API needed |
|------|--------|--------|--------------------|
| **Live** | Twitter API via `twitter_ingest.py` | `output.json` | Yes |
| **Test** | `tweets.txt` or `ingest_tweets.jsonl` | `tweet_eval_results.json` | No |

## Code Structure

Logic lives in `tools/` — `main.py` and `tweets_runner.py` are thin CLI entrypoints only.

```
main.py                  ← CLI: single tweet or --test batch (live pipeline)
tweets_runner.py         ← CLI: test runner against tweets.txt or ingest_tweets.jsonl
twitter_ingest.py        ← Twitter API ingestion (tweepy)
tools/
  client_tool.py         ← OpenAI client, key loading, approved facts, llm_json()
  relevance_tool.py      ← Full relevance prompt + LLM call + threshold
  safety_tool.py         ← Hard-block patterns + tone checks
  reply_tool.py          ← Full reply prompt + LLM call
  pipeline_tool.py       ← process_tweet() + process_batch() orchestration
  ingest_tool.py         ← ingest_tweets(), load_tweets_from_file(), load_tweets_from_jsonl()
approved_facts.json      ← Ground truth facts the LLM may reference
tweets.txt               ← Hand-written test tweets, one per line
SKILL.md                 ← OpenClaw skill definition
```

## Ingest Layer (`tools/ingest_tool.py`)

Three functions cover all input sources:

| Function | Source | Use case |
|----------|--------|----------|
| `ingest_tweets()` | Twitter API | Live pipeline |
| `load_tweets_from_file()` | `tweets.txt` | Test with hand-written tweets |
| `load_tweets_from_jsonl()` | `ingest_tweets.jsonl` | Test with previously ingested real tweets |

All three return the same list-of-dicts shape (`id`, `text`, `author_id`, `created_at`, `lang`) so `process_batch()` consumes any of them without changes.

## Decision Flow

```
tweet text
  │
  ▼
detect_hard_blocks()      ← immediate block if triggered
  │ (clear)
  ▼
classify_relevance()      ← LLM classifier, confidence >= 0.65 required
  │ (relevant)
  ▼
generate_tweet_reply()    ← LLM reply, grounded in approved_facts.json
  │
  ▼
safety_and_tone_check()   ← banned phrases, unverifiable claim check
  │ (clean)
  ▼
output result
```

## Input/Output Schema

### Single tweet (CLI)

Input: string (tweet text)

Output:
```json
{
  "relevant": true,
  "reason": "Post asks for practical AI workflow resources.",
  "reply": "Might be worth checking out AIBuildAI...",
  "safety_flags": [],
  "confidence": 0.87
}
```

No-reply example:
```json
{
  "relevant": false,
  "reason": "Post is unrelated to AI model building.",
  "reply": null,
  "safety_flags": [],
  "confidence": 0.95
}
```

### Batch pipeline

Output written to `output.json` (live) or `tweet_eval_results.json` (test):
```json
[
  {
    "question": "tweet text",
    "response": "reply or null",
    "confidence": 0.87,
    "relevant": true
  }
]
```

## Relevance Rules

### Relevant
- Post is about building or automating ML models, training pipelines, or hyperparameter tuning
- Post asks for practical implementation help or open-source AutoML references
- Post compares ML build stacks where AIBuildAI is contextually useful

### Not Relevant
- Unrelated topics (sports, politics, personal updates)
- Market/stock commentary without build intent
- Crypto, spam, or promotional content
- Retweets and replies (excluded at query level with `-is:retweet -is:reply`)

### Examples
- "Stuck on hyperparameter tuning for my image classifier, any AutoML tools?" → relevant
- "Building a RAG pipeline, looking for LangChain alternatives" → not relevant
- "AI stocks are up again." → not relevant

## Tone Rules

### Allowed
- Friendly, specific, concise
- Helpful suggestion, not a pitch
- Natural language tied to the post

### Banned (enforced via regex + LLM prompt)
- Hype, superlatives, sales language
- Generic promo copy
- Pressure or urgency CTAs
- Claims not in `approved_facts.json`

## Safety Hard Blocks

If any block triggers: `relevant=false`, `reply=null`

| Flag | Trigger |
|------|---------|
| `harassment_context` | hate, harassment, abuse patterns |
| `self_harm_context` | self-harm, suicide references |
| `illegal_activity_context` | hacking instructions, fraud, drug recipes |
| `tone_violation` | banned reply phrases |
| `unverifiable_claim_risk` | superlative marketing claims in reply ("the best", "best tool", "best platform", "best solution", "#1") |

## Twitter Ingestion

- Uses `tweepy.Client` with `wait_on_rate_limit=True`
- Search query targets ML practitioners asking for help (Kaggle, AutoML, model training, hyperparameter tuning)
- Excludes retweets, replies, and crypto spam
- Default: 25 tweets per cycle, 1 cycle
- Results written to `ingest_tweets.jsonl` (overwritten each run)
- Each line: `{id, text, author_id, created_at, lang}`

## Implementation Details

- Model: `gpt-4o-mini` (configurable via `OPENAI_MODEL`)
- Temperature: 0.8 (for reply variety)
- API key loaded from: shell env → `.env` → `credentials.json` → `openai-api.txt`
- Relevance threshold: 0.65
- `llm_json()` in `client_tool.py` handles all LLM calls and JSON parsing

## Failure Modes & Mitigations

| Failure | Mitigation |
|---------|-----------|
| False positives (irrelevant tweets passing) | Raise threshold, refine search query |
| False negatives (relevant tweets filtered) | Lower threshold, expand search query |
| Ad-like tone | Banned phrase enforcement + prompt instructions |
| Hallucinated claims | Restricted to `approved_facts.json` only |
| Repetitive replies | Prompt instructs varied, natural openings |
| Unsafe context | Hard-block checks before any LLM call |
| Twitter rate limit | `wait_on_rate_limit=True` handles automatically |
| 0 tweets ingested | Pipeline stops, user informed |
