#!/usr/bin/env bash
# One-shot OpenClaw configuration: registers three custom-adapter providers
# (one per bot) and three corresponding agents. Idempotent: re-running
# overwrites the same config keys.
#
# Prereqs: `openclaw onboard` already run; ANTHROPIC (or other) provider key
# configured; the OpenClaw gateway reachable on localhost:18789.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
  echo "Created $ENV_FILE from .env.example — edit before re-running if needed."
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ "${ADAPTER_SECRET:-changeme}" == "changeme" ]]; then
  ADAPTER_SECRET="$(openssl rand -hex 16)"
  sed -i.bak "s/^ADAPTER_SECRET=.*/ADAPTER_SECRET=$ADAPTER_SECRET/" "$ENV_FILE"
  echo "Generated ADAPTER_SECRET and wrote it to .env"
fi
export ADAPTER_SECRET

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI not found in PATH. Install it first:"
  echo "  curl -fsSL https://openclaw.ai/install.sh | bash"
  exit 1
fi

declare -A PORTS=( [researcher]=8001 [writer]=8002 [critic]=8003 )

for name in researcher writer critic; do
  port="${PORTS[$name]}"
  provider_payload=$(cat <<JSON
{
  "baseUrl": "http://127.0.0.1:${port}/v1",
  "apiKey": "${ADAPTER_SECRET}",
  "api": "openai-responses",
  "models": [
    {
      "id": "${name}-team",
      "name": "${name} adapter",
      "input": ["text"],
      "cost": {"input": 0, "output": 0},
      "contextWindow": 128000,
      "maxTokens": 4096
    }
  ]
}
JSON
)

  echo "→ registering provider ${name}-adapter (port ${port})"
  openclaw config set "models.providers.${name}-adapter" "$provider_payload"

  echo "→ ensuring agent ${name}-agent"
  if openclaw agents list 2>/dev/null | grep -q "${name}-agent"; then
    openclaw config set "agents.list.${name}-agent.model" "${name}-adapter/${name}-team"
  else
    openclaw agents add "${name}-agent" --model "${name}-adapter/${name}-team" || \
      openclaw agents add "${name}-agent"  # fall back if --model flag not supported
    openclaw config set "agents.list.${name}-agent.model" "${name}-adapter/${name}-team"
  fi
done

echo
echo "Done. Verify with:"
echo "  openclaw agents list"
echo "  curl -sf http://127.0.0.1:18789/healthz"
