"""Patch ~/.openclaw-dev/openclaw.json to register the three adapters and agents."""
import json, os

cfg_path = os.path.expanduser("~/.openclaw-dev/openclaw.json")
with open(cfg_path) as f:
    cfg = json.load(f)

secret = "changeme"

# Register all three providers
providers = cfg.setdefault("models", {}).setdefault("providers", {})
for name, port in [("researcher", 8001), ("writer", 8002), ("critic", 8003)]:
    providers[f"{name}-adapter"] = {
        "baseUrl": f"http://127.0.0.1:{port}/v1",
        "apiKey": secret,
        "api": "openai-responses",
        "models": [{
            "id": f"{name}-team",
            "name": f"{name} adapter",
            "input": ["text"],
            "cost": {"input": 0, "output": 0},
            "contextWindow": 128000,
            "maxTokens": 4096,
        }],
    }

# Register agents as an array (openclaw's expected format)
agents_list = cfg.setdefault("agents", {}).setdefault("list", [])
# Remove any existing entries for our three agents
agents_list = [
    a for a in agents_list
    if isinstance(a, dict) and a.get("id") not in {"researcher-agent", "writer-agent", "critic-agent"}
]
for name in ["researcher", "writer", "critic"]:
    agents_list.append({"id": f"{name}-agent", "model": f"{name}-adapter/{name}-team"})

cfg["agents"]["list"] = agents_list

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)

print("Done.")
print("providers:", list(cfg["models"]["providers"].keys()))
print("agents.list:", json.dumps(cfg["agents"]["list"], indent=2))
