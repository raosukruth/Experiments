"""FastAPI adapter implementing the OpenAI-compatible Responses API
(`POST /v1/responses`) so a Python process can act AS an OpenClaw agent.

OpenClaw routes inbound messages addressed to a configured agent_id to the
adapter's URL via `models.providers.<name>-adapter` config; the adapter
authenticates with a shared Bearer secret and returns OpenResponses JSON.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Awaitable, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

load_dotenv()

ADAPTER_SECRET = os.environ.get("ADAPTER_SECRET", "changeme")

Handler = Callable[[str], Awaitable[str]]


def _extract_user_message(body: dict[str, Any]) -> str:
    if "body" in body and isinstance(body["body"], dict):
        body = body["body"]
    data = body.get("input", "")
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        for item in reversed(data):
            if item.get("role") == "user":
                content = item.get("content", "")
                if isinstance(content, str):
                    return content
                for part in content:
                    if part.get("type") in ("text", "input_text"):
                        return part.get("text", "")
    return ""


def _envelope(response_id: str, model: str, output_text: str, usage_in: int, usage_out: int) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "response",
        "created": int(time.time()),
        "model": model,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": output_text}],
            }
        ],
        "usage": {
            "input_tokens": usage_in,
            "output_tokens": usage_out,
            "total_tokens": usage_in + usage_out,
        },
    }


async def _sse_stream(response_id: str, model: str, output_text: str, user_msg: str):
    """Yield OpenAI Responses API SSE events for the given output text."""
    item_id = f"msg_{uuid.uuid4().hex}"
    ts = int(time.time())

    def event(obj: dict) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    yield event({"type": "response.created", "response": {"id": response_id, "object": "response", "created": ts, "model": model}})
    yield event({"type": "response.output_item.added", "item": {"type": "message", "id": item_id, "role": "assistant", "content": []}})
    yield event({"type": "response.content_part.added", "item_id": item_id, "content_index": 0, "part": {"type": "output_text", "text": ""}})
    yield event({"type": "response.output_text.delta", "item_id": item_id, "content_index": 0, "delta": output_text})
    yield event({"type": "response.output_text.done", "item_id": item_id, "content_index": 0, "text": output_text})
    yield event({"type": "response.content_part.done", "item_id": item_id, "content_index": 0, "part": {"type": "output_text", "text": output_text}})
    yield event({"type": "response.output_item.done", "item": {"type": "message", "id": item_id, "role": "assistant", "content": [{"type": "output_text", "text": output_text}]}})
    yield event({"type": "response.completed", "response": {"id": response_id, "object": "response", "created": ts, "model": model, "output": [{"type": "message", "id": item_id, "role": "assistant", "content": [{"type": "output_text", "text": output_text}]}], "usage": {"input_tokens": len(user_msg.split()), "output_tokens": len(output_text.split()), "total_tokens": len(user_msg.split()) + len(output_text.split())}}})
    yield "data: [DONE]\n\n"


def make_adapter(name: str, handler: Handler) -> FastAPI:
    """Build a FastAPI app exposing /v1/responses backed by `handler`."""
    app = FastAPI(title=f"openclaw-adapter:{name}")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "agent": name}

    @app.post("/v1/responses")
    async def responses(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        if authorization.split(" ", 1)[1] != ADAPTER_SECRET:
            raise HTTPException(status_code=401, detail="invalid bearer token")

        body = await request.json()
        user_msg = _extract_user_message(body)
        if not user_msg:
            raise HTTPException(status_code=400, detail="empty input")

        try:
            output = await handler(user_msg)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"{name} handler failed: {exc}") from exc

        response_id = f"resp_{uuid.uuid4().hex}"
        model_name = body.get("model", f"{name}-team")

        if body.get("stream"):
            return StreamingResponse(
                _sse_stream(response_id, model_name, output, user_msg),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        return _envelope(
            response_id=response_id,
            model=model_name,
            output_text=output,
            usage_in=len(user_msg.split()),
            usage_out=len(output.split()),
        )

    return app


def serve(app: FastAPI, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
