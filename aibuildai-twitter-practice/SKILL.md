---
name: aibuildai-twitter-reply
description: >
  Use this skill to monitor Twitter/X for relevant tweets about AI building,
  agents, workflows, and tooling, then automatically generate natural,
  non-promotional replies that mention AIBuildAI where appropriate.
  Trigger when the user asks to: run the Twitter pipeline, check for new tweets,
  process mentions, generate replies, or run the reply bot.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - OPENAI_API_KEY
        - TWITTER_BEARER_TOKEN
      bins:
        - python3
    primaryEnv: OPENAI_API_KEY
    envVars:
      - name: OPENAI_API_KEY
        required: true
        description: OpenAI API key used by the LLM for relevance and reply generation.
      - name: TWITTER_BEARER_TOKEN
        required: true
        description: Twitter/X Bearer Token used to search recent tweets.
      - name: OPENAI_MODEL
        required: false
        description: OpenAI model to use. Defaults to gpt-4o-mini.
      - name: TWITTER_SEARCH_QUERY
        required: false
        description: Custom search query for Twitter ingestion. Has a sensible default.
      - name: TWITTER_MAX_RESULTS
        required: false
        description: Max tweets to fetch per cycle. Defaults to 25.
      - name: TWITTER_FETCH_CYCLES
        required: false
        description: Number of polling cycles to run. Defaults to 1.
      - name: TWITTER_POLL_INTERVAL
        required: false
        description: Seconds to wait between cycles. Defaults to 60.
      - name: OPENCLAW_INGEST_OUTPUT
        required: false
        description: Output path for ingested tweets JSONL file. Defaults to ingest_tweets.jsonl.
---

# AIBuildAI Twitter Reply Bot

## Context

You are operating a Twitter/X reply pipeline for AIBuildAI, a project by Pengtao Xie.
The pipeline monitors tweets about AI building, agents, workflows, and tooling,
filters for relevant ones, and drafts natural replies that mention AIBuildAI only where it
genuinely fits — never sounding like an ad.
This workflow is read-only on Twitter/X: ingest/search tweets only. Do not post, reply, or like on Twitter.

All logic lives in the following Python files (relative to the repo root):

| File | Purpose |
|---|---|
| `twitter_ingest.py` / `tools/ingest_tool.py` | Fetch tweets from Twitter API |
| `tools/relevance_tool.py` | Classify whether a tweet is relevant (threshold: 0.65 confidence) |
| `tools/safety_tool.py` | Check for hard-block patterns (harassment, self-harm, illegal activity) |
| `tools/reply_tool.py` | Generate a natural, human-sounding reply |
| `tools/pipeline_tool.py` | Run the full pipeline over a batch of tweets |
| `tools/client_tool.py` | Build the OpenAI client and load approved facts |
| `main.py` | CLI entrypoint: runs a single tweet or `--test` batch against the tools |

---

## When to Use

- User says: "run the Twitter pipeline", "check for new tweets", "process mentions"
- User says: "generate replies", "run the reply bot", "start the bot"
- User sets up a scheduled/recurring run (e.g. "every 30 minutes")

Do NOT use for general Twitter browsing, posting tweets manually, or unrelated LLM tasks.

---

## Instructions

### Step 1 — Ingest tweets

Run the ingestion tool to fetch recent tweets:

```bash
python3 twitter_ingest.py
```

This calls `run_ingest()` from `twitter_ingest.py` and writes results to `ingest_tweets.jsonl`.
The script resolves credentials from shell env first, then `.env` in the repo root.
Each line is a JSON object with fields: `id`, `text`, `author_id`, `created_at`, `lang`.

If the user specifies custom parameters (e.g. max results, fetch cycles), pass them:

```bash
python3 -c "
from tools.ingest_tool import ingest_tweets
result = ingest_tweets(max_results=10, fetch_cycles=2, poll_interval=30)
print(result)
"
```

### Step 2 — Load tweets and run the pipeline

Read the JSONL file, run the full pipeline using `pipeline_tool.py`, and write final results to `output.json`.
On every run, refresh `output.json` by opening it in overwrite mode (`w`).

```bash
python3 -c "
import json
from tools.client_tool import get_client, get_approved_facts
from tools.pipeline_tool import process_batch

client = get_client()
approved_facts = get_approved_facts()

tweets = []
with open('ingest_tweets.jsonl') as f:
    for line in f:
        line = line.strip()
        if line:
            tweets.append(json.loads(line))

results = process_batch(tweets=tweets, client=client, approved_facts=approved_facts)
output = [
  {
    'question': r.get('text'),
    'response': r.get('reply'),
    'confidence': r.get('confidence'),
    'relevant': r.get('relevant')
  }
  for r in results
]

with open('output.json', 'w', encoding='utf-8') as out:
  json.dump(output, out, indent=2, ensure_ascii=False)

print(json.dumps({'processed': len(results), 'output_path': 'output.json'}, indent=2))
"
```

Each result contains:
- `relevant` (bool) — whether the tweet passed relevance + safety checks
- `confidence` (float) — model confidence score
- `reason` (str) — short explanation
- `reply` (str or null) — the generated reply, if applicable
- `safety_flags` (list) — any triggered safety or tone flags

### Step 3 — Report results to the user

Summarise what happened clearly. For each tweet that got a reply, show:
- The original tweet text (truncated to ~100 chars)
- The generated reply
- The confidence score

For tweets that were skipped, briefly say why (not relevant, safety block, low confidence).
Always confirm that `output.json` was updated.
Always state that `output.json` was overwritten/refreshed for the current run.

Example summary format:

```
Processed 25 tweets.
4 relevant — replies generated
18 not relevant
3 blocked by safety checks

Reply 1 (confidence: 0.87):
Tweet: "Building an AI pipeline from scratch is brutal, anyone have good resources?"
Reply: "Might be worth checking out AIBuildAI — it's designed exactly for this kind of workflow setup..."
```

---

## Scheduling

If the user asks to run this on a schedule (e.g. "every 30 minutes", "every hour"), prefer OpenClaw scheduler/tasks first.
Use cron only if the OpenClaw scheduler is unavailable.

OpenClaw scheduler example intent:

```bash
openclaw --dev tasks --help
openclaw --dev cron --help
```

Cron fallback:

```bash
# Example: run every 30 minutes
*/30 * * * * cd /path/to/skill && python3 -c "
import json
from tools.client_tool import get_client, get_approved_facts
from tools.ingest_tool import ingest_tweets
from tools.pipeline_tool import process_batch

ingest_tweets()
client = get_client()
approved_facts = get_approved_facts()
tweets = [json.loads(l) for l in open('ingest_tweets.jsonl') if l.strip()]
results = process_batch(tweets=tweets, client=client, approved_facts=approved_facts)
output = [
  {
    'question': r.get('text'),
    'response': r.get('reply'),
    'confidence': r.get('confidence'),
    'relevant': r.get('relevant')
  }
  for r in results
]
with open('output.json', 'w', encoding='utf-8') as out:
  json.dump(output, out, ensure_ascii=False)
print(json.dumps({'processed': len(results), 'output_path': 'output.json'}))
" >> /tmp/aibuildai-twitter.log 2>&1
```

The scheduled run must overwrite `output.json` each time so the file always reflects the latest run.

Ask the user to confirm the schedule and path before setting it up.

---

## Error Handling

| Error | Action |
|---|---|
| `OPENAI_API_KEY` missing | Stop. Ask user to set the env variable. |
| `TWITTER_BEARER_TOKEN` missing | Stop. Ask user to set the env variable. |
| `.env` missing or incomplete | Stop. Ask user to set required keys in repo-root `.env` (`OPENAI_API_KEY`, `TWITTER_BEARER_TOKEN`). |
| `approved_facts.json` not found | Stop. Tell user this file is required in the repo root. |
| Twitter API rate limit hit | `tweepy` handles this automatically (`wait_on_rate_limit=True`). Inform the user it may be slow. |
| LLM returns empty content | Current `process_batch()` can fail the run. Report failure and rerun (optionally with smaller batch or wrapper-level try/except). |
| No tweets ingested | Inform the user and do not proceed to pipeline. |

---

## Rules

- Twitter interaction must remain ingest-only (`search_recent_tweets`/read operations). Never post to Twitter.
- Never post replies automatically to Twitter without explicit user confirmation.
- Never hardcode or log API keys.
- Never claim facts about AIBuildAI that are not in `approved_facts.json`.
- Never proceed with the pipeline if ingestion returns 0 tweets — ask the user how to proceed.
- Always show the user a summary of results, even if all tweets were filtered out.
- If safety flags are triggered on a tweet, do not generate or show a reply for it.

---

## Output Format

Always end your response with a structured summary:

```
---
Pipeline run complete.
Tweets fetched: <n>
Relevant: <n>
Replies generated: <n>
Blocked by safety: <n>
Not relevant: <n>
---
```