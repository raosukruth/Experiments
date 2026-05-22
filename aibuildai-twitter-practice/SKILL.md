---
name: aibuildai-twitter-reply
description: >
  Use this skill to monitor Twitter/X for relevant tweets about AI building,
  agents, workflows, and tooling, then automatically generate natural,
  non-promotional replies that mention AIBuildAI where appropriate.
  Trigger when the user asks to: run the Twitter pipeline, check for new tweets,
  process mentions, generate replies, or run the reply bot.
  Also trigger when the user asks to: run the test pipeline, run with tweets.txt,
  test locally, run without Twitter, or test with ingested tweets.
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
| `twitter_ingest.py` | Fetch tweets from Twitter API, write to `ingest_tweets.jsonl` |
| `tools/ingest_tool.py` | `ingest_tweets()` — live API; `load_tweets_from_file()` — reads `tweets.txt`; `load_tweets_from_jsonl()` — reads `ingest_tweets.jsonl` |
| `tools/relevance_tool.py` | Classify whether a tweet is relevant (threshold: 0.65 confidence) |
| `tools/safety_tool.py` | Check for hard-block patterns (harassment, self-harm, illegal activity) |
| `tools/reply_tool.py` | Generate a natural, human-sounding reply |
| `tools/pipeline_tool.py` | `process_tweet()` and `process_batch()` — orchestrate the full pipeline |
| `tools/client_tool.py` | Build the OpenAI client and load approved facts |
| `tools/report_tool.py` | `results_to_markdown()` — converts `output.json` or `tweet_eval_results.json` to a markdown report |
| `main.py` | CLI entrypoint: single tweet, `--test` reads `tweets.txt`, `--test --source ingest` reads `ingest_tweets.jsonl` |

---

## When to Use

There are two pipeline modes:

**Live mode** — ingests real tweets from the Twitter API, writes to `output.json`:
- User says: "run the Twitter pipeline", "check for new tweets", "process mentions", "run the reply bot", "start the bot"

**Test mode (tweets.txt)** — runs against hand-written tweets in `tweets.txt`, no Twitter API required, writes to `tweet_eval_results.json`:
- User says: "run the test pipeline", "run with tweets.txt", "test locally", "run without Twitter", "test the pipeline"

**Test mode (ingest file)** — runs against previously ingested real tweets from `ingest_tweets.jsonl`, no Twitter API required, writes to `tweet_eval_results.json`:
- User says: "test with ingested tweets", "run the test pipeline from ingest", "run against ingest file"

**Report mode** — converts the latest results JSON to a readable markdown report:
- User says: "generate a report", "convert to markdown", "show me the results as markdown", "export to markdown"

Do NOT use for general Twitter browsing, posting tweets manually, or unrelated LLM tasks.

---

## Instructions

> **Choose the mode based on what the user asked for.**
> - Live mode: follow Steps 1 → 2 → 3 below (requires `TWITTER_BEARER_TOKEN`)
> - Test mode: skip to [Test Mode](#test-mode) (only requires `OPENAI_API_KEY`)
> - Report mode: skip to [Report Mode](#report-mode) (no API keys needed)

---

### Test Mode

**Option A — from `tweets.txt`** (hand-written test tweets, no Twitter API needed):

```bash
python3 main.py --test
```

**Option B — from `ingest_tweets.jsonl`** (previously ingested real tweets, no Twitter API needed):

```bash
python3 main.py --test --source ingest
```

Both options write results to `tweet_eval_results.json` and print to the terminal.

Then report the summary to the user the same way as Step 3 below.

Alternatively, you can call the ingest tools directly in Python:

```bash
python3 -c "
import json
from tools.client_tool import get_client, get_approved_facts
from tools.ingest_tool import load_tweets_from_file, load_tweets_from_jsonl
from tools.pipeline_tool import process_batch

client = get_client()
approved_facts = get_approved_facts()

# Use load_tweets_from_file() for tweets.txt or load_tweets_from_jsonl() for ingest_tweets.jsonl
tweets = load_tweets_from_file()

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

with open('tweet_eval_results.json', 'w', encoding='utf-8') as out:
  json.dump(output, out, indent=2, ensure_ascii=False)

print(json.dumps({'processed': len(results), 'output_path': 'tweet_eval_results.json'}, indent=2))
"
```

---

### Report Mode

Converts a results JSON file to a readable markdown report. Each tweet is shown with its input and generated reply (or empty if none).

**From `output.json`** (live pipeline results):

```bash
python3 -c "from tools.report_tool import results_to_markdown; results_to_markdown()"
```

Output is written to `output.md`.

**From `tweet_eval_results.json`** (test pipeline results):

```bash
python3 -c "from tools.report_tool import results_to_markdown; results_to_markdown(input_path='tweet_eval_results.json', output_path='tweet_eval_results.md')"
```

Output is written to `tweet_eval_results.md`.

Tell the user which file was written when done.

---

### Live Mode

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