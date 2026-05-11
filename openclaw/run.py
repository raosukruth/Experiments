"""Orchestrator: chains researcher-agent → writer-agent → critic-agent through
the OpenClaw gateway. Each step is routed by OpenClaw to the corresponding
Python adapter process.

Uses `client.get_agent(id, session_name=...).execute(...)` directly rather
than `Pipeline`, so per-agent session scoping is explicit and visible.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

from openclaw_sdk import OpenClawClient
from openclaw_sdk.callbacks.handler import CallbackHandler


class LogCb(CallbackHandler):
    async def on_execution_start(self, agent_id: str, query: str):
        snippet = query.replace("\n", " ")[:80]
        print(f"[{agent_id}] ▶ {snippet}", flush=True)

    async def on_execution_end(self, agent_id: str, result):
        latency = getattr(result, "latency_ms", "?")
        print(f"[{agent_id}] ✓ {latency} ms", flush=True)


async def run(topic: str, *, fresh_session: bool):
    session = uuid.uuid4().hex[:8] if fresh_session else "main"

    async with await OpenClawClient.connect(callbacks=[LogCb()]) as client:
        researcher = client.get_agent("researcher-agent", session_name=session)
        writer     = client.get_agent("writer-agent",     session_name=session)
        critic     = client.get_agent("critic-agent",     session_name=session)

        research = await researcher.execute(f"Research this topic: {topic}")
        if not research.success:
            sys.exit(f"researcher-agent failed: {research.content}")

        draft = await writer.execute(
            f"Write an article using these bullets:\n{research.content}"
        )
        if not draft.success:
            sys.exit(f"writer-agent failed: {draft.content}")

        review = await critic.execute(
            f"Critique this article and return JSON only:\n{draft.content}"
        )
        if not review.success:
            sys.exit(f"critic-agent failed: {review.content}")

        print("\n=== ARTICLE ===\n")
        print(draft.content)

        try:
            critique = json.loads(review.content)
            print("\n=== CRITIQUE ===\n")
            print(f"score:   {critique.get('score')}/10")
            print(f"verdict: {critique.get('verdict')}")
            for issue in critique.get("issues", []):
                print(f"  - {issue}")
        except json.JSONDecodeError:
            print("\n=== CRITIQUE (raw) ===\n")
            print(review.content)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw multi-agent demo")
    parser.add_argument("topic", nargs="*", default=["small", "modular", "reactors"])
    parser.add_argument(
        "--fresh-session",
        action="store_true",
        help="Use a unique session per agent so each run starts with no memory.",
    )
    args = parser.parse_args()

    topic = " ".join(args.topic)
    try:
        asyncio.run(run(topic, fresh_session=args.fresh_session))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
