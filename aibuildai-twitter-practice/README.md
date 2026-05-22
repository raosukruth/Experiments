# AIBuildAI Twitter Reply Bot

Monitors Twitter/X for tweets about ML model building, AutoML, and Kaggle-style tasks. Filters for relevance, runs safety checks, and drafts natural replies that mention AIBuildAI only where it genuinely fits. Read-only on Twitter — never posts.

## How It Works

1. **Ingest** — fetches tweets from the Twitter API or loads from a local file (`tweets.txt` or `ingest_tweets.jsonl`)
2. **Relevance** — LLM classifies each tweet (threshold: 0.65 confidence)
3. **Safety** — hard-block check for harassment, self-harm, illegal activity
4. **Reply** — LLM generates a short, natural, non-promotional reply grounded in `approved_facts.json`
5. **Output** — results written to `output.json` (live) or `tweet_eval_results.json` (test)

## Pipeline Modes

| Mode | Source | Command | Twitter API needed |
|------|--------|---------|-------------------|
| Live | Twitter API | `python3 main.py` or OpenClaw | Yes |
| Test (hand-written) | `tweets.txt` | `python3 main.py --test` | No |
| Test (ingested) | `ingest_tweets.jsonl` | `python3 main.py --test --source ingest` | No |

## Project Layout

| Path | Purpose |
|------|---------|
| `main.py` | CLI entrypoint — single tweet, batch test mode (tweets.txt or ingest file) |
| `twitter_ingest.py` | Fetches tweets from Twitter API |
| `tools/client_tool.py` | OpenAI client, key loading, `approved_facts.json`, shared `llm_json()` |
| `tools/relevance_tool.py` | Relevance classification (prompt + LLM call) |
| `tools/safety_tool.py` | Hard-block patterns and tone checks |
| `tools/reply_tool.py` | Reply generation (prompt + LLM call) |
| `tools/pipeline_tool.py` | `process_tweet()` and `process_batch()` orchestration |
| `tools/ingest_tool.py` | `ingest_tweets()`, `load_tweets_from_file()`, `load_tweets_from_jsonl()` |
| `approved_facts.json` | Facts the LLM is allowed to reference in replies |
| `tweets.txt` | Hand-written test tweets, one per line |
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

- **"run the Twitter pipeline"** — live mode, fetches real tweets from the API
- **"run the test pipeline"** or **"test locally"** — test mode, reads from `tweets.txt`, no Twitter API needed
- **"run the test pipeline from ingest"** — test mode using previously ingested tweets from `ingest_tweets.jsonl`

OpenClaw reads `SKILL.md` and runs the appropriate pipeline based on what you ask.

### Via CLI — Live Twitter pipeline

Runs against tweets ingested from the Twitter API.

**Single tweet:**
```bash
python3 main.py "your tweet text here"
```

**Via stdin:**
```bash
echo "your tweet text here" | python3 main.py
```

**Ingest only:**
```bash
python3 twitter_ingest.py
```

### Via CLI — Test mode

`main.py` runs the full pipeline without requiring a Twitter API key.

**From `tweets.txt`** (hand-written test tweets, default):
```bash
python3 main.py --test
```

**From `ingest_tweets.jsonl`** (previously ingested real tweets):
```bash
python3 main.py --test --source ingest
```

Results are written to `tweet_eval_results.json` (overwritten each run) and printed to the terminal.

**Single tweet:**
```bash
python3 main.py "your tweet text here"
```

**Via stdin:**
```bash
echo "your tweet text here" | python3 main.py
```

## Output

**`output.json`** — written by the live pipeline (`main.py` or OpenClaw live mode), overwritten each run:

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

**`tweet_eval_results.json`** — written by `main.py --test`, overwritten each run. Same schema as above.

**Single-tweet output** (`main.py`):

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
| `TWITTER_BEARER_TOKEN` | Live mode only | — | Twitter/X Bearer Token |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for relevance and reply |
| `TWITTER_SEARCH_QUERY` | No | built-in | Custom Twitter search query |
| `TWITTER_MAX_RESULTS` | No | `25` | Tweets to fetch per cycle |
| `TWITTER_FETCH_CYCLES` | No | `1` | Number of polling cycles |
| `TWITTER_POLL_INTERVAL` | No | `60` | Seconds between cycles |
| `OPENCLAW_INGEST_OUTPUT` | No | `ingest_tweets.jsonl` | Output path for ingested tweets |
