# AIBuildAI Twitter Reply Bot

Monitors Twitter/X for tweets about AI building, agents, workflows, and tooling. Filters for relevance, runs safety checks, and drafts natural replies that mention AIBuildAI only where it genuinely fits. Read-only on Twitter — never posts.

## How It Works

1. **Ingest** — fetches recent tweets from the Twitter API matching a curated search query
2. **Relevance** — LLM classifies each tweet (threshold: 0.65 confidence)
3. **Safety** — hard-block check for harassment, self-harm, illegal activity
4. **Reply** — LLM generates a short, natural, non-promotional reply grounded in `approved_facts.json`
5. **Output** — results written to `output.json`

## Project Layout

| Path | Purpose |
|------|---------|
| `main.py` | CLI entrypoint — single tweet or `--test` batch |
| `twitter_ingest.py` | Fetches tweets from Twitter API |
| `tools/client_tool.py` | OpenAI client, key loading, `approved_facts.json`, shared `llm_json()` |
| `tools/relevance_tool.py` | Relevance classification (prompt + LLM call) |
| `tools/safety_tool.py` | Hard-block patterns and tone checks |
| `tools/reply_tool.py` | Reply generation (prompt + LLM call) |
| `tools/pipeline_tool.py` | `process_tweet()` and `process_batch()` orchestration |
| `tools/ingest_tool.py` | Wrapper around `twitter_ingest.run_ingest()` |
| `approved_facts.json` | Facts the LLM is allowed to reference in replies |
| `SKILL.md` | OpenClaw skill definition — enables running via `openclaw tui` |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set credentials

Either export as env vars:

```bash
export OPENAI_API_KEY=sk-...
export TWITTER_BEARER_TOKEN=...
```

Or create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
TWITTER_BEARER_TOKEN=...
```

The key loader checks: shell env → `.env` → `credentials.json` → `openai-api.txt`.

### 3. (Optional) Update approved facts

Edit `approved_facts.json` to control what the LLM can say about AIBuildAI. Only facts listed here will appear in replies.

## Running

### Via OpenClaw (recommended)

```bash
openclaw tui
```

Then say: **"run the Twitter pipeline"**

OpenClaw reads `SKILL.md` and runs the full ingest → process → output cycle.

### Via CLI

**Single tweet:**
```bash
python3 main.py "your tweet text here"
```

**Batch mode** (uses `prompts.txt`, one tweet per line):
```bash
python3 main.py --test
```

**Ingest only:**
```bash
python3 twitter_ingest.py
```

## Output

`output.json` is overwritten on every run:

```json
[
  {
    "question": "tweet text",
    "response": "generated reply or null",
    "confidence": 0.87,
    "relevant": true
  }
]
```

Single-tweet CLI output:

```json
{
  "relevant": true,
  "reason": "Post asks for practical AI workflow resources.",
  "reply": "Might be worth checking out AIBuildAI...",
  "safety_flags": [],
  "confidence": 0.87
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `TWITTER_BEARER_TOKEN` | Yes | — | Twitter/X Bearer Token |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for relevance and reply |
| `TWITTER_SEARCH_QUERY` | No | built-in | Custom Twitter search query |
| `TWITTER_MAX_RESULTS` | No | `25` | Tweets to fetch per cycle |
| `TWITTER_FETCH_CYCLES` | No | `1` | Number of polling cycles |
| `TWITTER_POLL_INTERVAL` | No | `60` | Seconds between cycles |
| `OPENCLAW_INGEST_OUTPUT` | No | `ingest_tweets.jsonl` | Output path for ingested tweets |
