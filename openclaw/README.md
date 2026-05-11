# OpenClaw multi-agent demo

A toy demo that wires three Python "agent" processes through an
[OpenClaw](https://openclaw.ai/) gateway:

```
run.py (orchestrator, openclaw-sdk)
        │
        ▼
   OpenClaw Gateway   (dev profile: ws://127.0.0.1:19001)
        │  POST /v1/responses  (Bearer auth)
        ├──────────► bots/researcher.py  :8001  (HTTP fetch + LLM bullets)
        ├──────────► bots/writer.py      :8002  (LLM draft + word-count loop)
        └──────────► bots/critic.py      :8003  (programmatic checks + LLM JSON)
```

Each bot is a FastAPI server implementing the OpenAI-compatible Responses
API (`POST /v1/responses`). OpenClaw routes messages addressed to a given
`agent_id` to the corresponding adapter URL. Bots make their own LLM calls
directly to Anthropic via the `anthropic` SDK (decoupled from OpenClaw).

## Status of this scaffold

This was built and partially exercised on one machine; you're picking it up
on another. What's done and what's left:

- ✅ Project structure, three bot adapters, orchestrator
- ✅ FastAPI adapter responding 200 on `/healthz` and `/v1/responses`
- ✅ OpenClaw 2026.5.7 installed locally (`./node_modules/.bin/openclaw`)
- ✅ OpenClaw dev profile onboarded at `~/.openclaw-dev/` (port 19001)
- ⛔ **LLM call**: blocked because the `ANTHROPIC_API_KEY` available in the
  Claude Code shell is rejected by `api.anthropic.com` (looks like a
  Claude-Code-scoped token, not a regular Anthropic API key). You'll need a
  real Anthropic API key to run the LLM hop.
- ⏳ **Not yet done**: patching OpenClaw config to register the three
  `*-adapter` providers + three `*-agent` records, and starting the gateway.
  See "Finishing on the new machine" below.

## Prerequisites

- Python 3.11+ (tested on 3.12)
- Node.js 22.16+ or 24+
- A real Anthropic API key (or swap to OpenAI — see [bots/_llm.py](bots/_llm.py))

## One-time setup

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# OpenClaw (local install — keeps state under ./node_modules)
npm install                # picks up package.json
```

## Configure OpenClaw (dev profile, isolated)

```bash
# 1. Onboard without provider creds (we add them below).
./node_modules/.bin/openclaw --dev onboard \
  --non-interactive --accept-risk --flow quickstart \
  --auth-choice skip \
  --workspace "$HOME/.openclaw-dev/workspace" \
  --gateway-bind loopback --gateway-port 19001

# 2. Register the three adapter providers + three agents (see TODO below).
bash scripts/setup_openclaw.sh

# 3. Pull the auto-generated gateway token into .env.
GATEWAY_TOKEN=$(python -c "import json; print(json.load(open('$HOME/.openclaw-dev/openclaw.json'))['gateway']['auth']['token'])")
cp .env.example .env
sed -i "s/^OPENCLAW_GATEWAY_TOKEN=.*/OPENCLAW_GATEWAY_TOKEN=$GATEWAY_TOKEN/" .env
```

## Set the LLM key

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # a real one, not Claude Code's
```

## Run

```bash
# Terminal 1: the gateway
./node_modules/.bin/openclaw --dev gateway

# Terminal 2: bots + orchestrator
bash scripts/run_all.sh "small modular reactors"
```

Bot stdout/stderr lands in `.logs/<bot>.log`.

## Direct adapter sanity check (no gateway, no openclaw-sdk)

Skip the gateway and the orchestrator — just verify a bot does its job:

```bash
.venv/bin/python -m bots.researcher &
sleep 2
curl -s -H "Authorization: Bearer demo-secret-1234" \
     -H 'Content-Type: application/json' \
     -d '{"input":"Research this topic: superconductors"}' \
     http://127.0.0.1:8001/v1/responses | jq .output[0].content[0].text
```

This is what we got working on the source machine; it confirms the FastAPI
adapter + OpenResponses envelope are correct. Failure here means the LLM
call is broken (most likely the API key issue noted above).

## Finishing on the new machine — TODO list

1. **Make sure `scripts/setup_openclaw.sh` works against the actual schema.**
   The script as written uses `openclaw config set "models.providers.X" '<json>'`
   for each adapter. The CLI's batch syntax may want `openclaw config patch
   --stdin` with a single JSON5 object covering everything. Schema cheat
   sheet for `models.providers.<name>`:
   ```jsonc
   {
     baseUrl: "http://127.0.0.1:8001",
     apiKey: "demo-secret-1234",            // string OR SecretRef object
     auth: "api-key",
     models: [{ id: "researcher-team", api: "openai-responses", input: ["text"] }]
   }
   ```
   And for `agents.list[*]`: `{ id: "researcher-agent", model: "researcher-adapter/researcher-team" }`.
2. **Verify `openclaw-sdk` reaches the gateway.** `OpenClawClient.connect()`
   auto-detects via `OPENCLAW_GATEWAY_WS_URL`; pass `api_key` (the gateway
   token) explicitly if auto-detect isn't picking up `OPENCLAW_GATEWAY_TOKEN`.
3. **Verify the adapter→Anthropic LLM call** with a real key (the blocker
   we hit). Once the LLM responds, the rest of the chain should work.
4. **Run [run.py](run.py)** end-to-end and watch `~/.openclaw-dev/logs/` for
   the three `POST /v1/responses` entries proving the gateway is in the
   path.

## Layout

| Path | Purpose |
|------|---------|
| [run.py](run.py) | Orchestrator: `client.get_agent(...).execute(...)` x3 |
| [bots/_adapter.py](bots/_adapter.py) | FastAPI factory: `/v1/responses`, Bearer auth, OpenResponses JSON envelope |
| [bots/_llm.py](bots/_llm.py) | Async Anthropic SDK wrapper |
| [bots/researcher.py](bots/researcher.py) | Wikipedia / canned fetch + LLM bullets, port 8001 |
| [bots/writer.py](bots/writer.py) | LLM draft + Python word-count control loop, port 8002 |
| [bots/critic.py](bots/critic.py) | Programmatic checks + LLM JSON merged, port 8003 |
| [data/sources.json](data/sources.json) | Canned topic→facts (offline fallback) |
| [scripts/setup_openclaw.sh](scripts/setup_openclaw.sh) | One-shot OpenClaw config (needs verification on first run, see TODO) |
| [scripts/run_all.sh](scripts/run_all.sh) | Background-launch bots + run orchestrator |

## Troubleshooting

- **`invalid x-api-key`** when a bot calls Anthropic → wrong key. The
  `ANTHROPIC_API_KEY` Claude Code injects is *not* a general API key; you
  need a real one from the Anthropic console.
- **`Non-interactive setup requires explicit risk acknowledgement`** →
  add `--accept-risk` to the onboard command.
- **401 from a bot** → `ADAPTER_SECRET` mismatch between `.env` and the
  provider's `apiKey` in `~/.openclaw-dev/openclaw.json`.
- **Connection refused on :8001/2/3** → bot didn't start; check
  `.logs/<bot>.log`.
