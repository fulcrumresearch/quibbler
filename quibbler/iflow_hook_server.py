#!/usr/bin/env python3
"""
Quibbler hook server for iFlow CLI.

Enhanced version with:
- Automatic token authentication from iFlow settings
- Token-efficient context management
- Smart event filtering (only process critical events)
- Auto-summarization for long sessions
- Enhanced prompts optimized for iFlow

No ANTHROPIC_API_KEY needed - uses iFlow authentication automatically.

Run:
    quibbler iflow-hook server [port]

Default port: 8082 (different from standard Quibbler to avoid conflicts)
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from quibbler.iflow_agent import IFlowQuibblerHook, load_iflow_quibbler_config
from quibbler.iflow_prompts import load_iflow_prompt
from quibbler.logger import get_logger

logger = get_logger(__name__)

# Global registry: session_id -> IFlowQuibblerHook
_quibblers: dict[str, IFlowQuibblerHook] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    logger.info("iFlow Hook Server starting up...")
    yield
    logger.info("iFlow Hook Server shutting down...")
    # Cleanup all quibblers
    for sid, quibbler in list(_quibblers.items()):
        await quibbler.stop()
        _quibblers.pop(sid, None)
    logger.info("Cleanup complete")


app = FastAPI(title="Quibbler iFlow Hook Server", version="1.0", lifespan=lifespan)


async def get_or_create_quibbler(
    session_id: str, source_path: str
) -> IFlowQuibblerHook:
    """Get or create a quibbler for a session"""
    quibbler = _quibblers.get(session_id)

    if quibbler is None:
        system_prompt = load_iflow_prompt(source_path, mode="hook")
        config = load_iflow_quibbler_config(source_path)

        quibbler = IFlowQuibblerHook(
            system_prompt=system_prompt,
            source_path=source_path,
            config=config,
            session_id=session_id,
        )

        await quibbler.start()
        _quibblers[session_id] = quibbler

        logger.info("=" * 80)
        logger.info(f"Started iFlow Quibbler for session: {session_id}")
        logger.info(f"  Project: {source_path}")
        logger.info(f"  Model: {config.model}")
        logger.info(f"  Auto-summary: {config.enable_auto_summary}")
        logger.info(f"  Smart triggers: {config.enable_smart_triggers}")
        logger.info("=" * 80)

    return quibbler


async def _process_event_in_background(
    session_id: str, source_path: str, evt: dict[str, Any]
) -> None:
    """Process event in background without blocking HTTP response"""
    try:
        quibbler = await get_or_create_quibbler(session_id, source_path)
        await quibbler.enqueue(evt)
    except Exception as e:
        logger.error(
            f"Error processing event for session {session_id}: {e}", exc_info=True
        )


@app.post("/hook/{session_id}")
async def hook(request: Request, session_id: str) -> dict[str, str]:
    """
    Receive hook events from iFlow CLI and route to appropriate quibbler.

    Expected payload format:
    {
        "event": "PostToolUse" | "UserPromptSubmit" | "Stop" | ...,
        "source_path": "/absolute/path/to/project",
        "payload": { ... hook event data ... },
        "timestamp": "2025-11-22T12:00:00Z"
    }
    """
    body = await request.body()
    data = json.loads(body.decode("utf-8"))

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    source_path = data.get("source_path")
    if not source_path:
        raise HTTPException(status_code=400, detail="source_path is required")

    # Create event with received timestamp
    evt = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    event_type = evt.get("event", "UnknownEvent")
    logger.info(
        f"Received event: {event_type} for session {session_id[:8]}... in {source_path}"
    )

    # Process in background - don't block response
    asyncio.create_task(_process_event_in_background(session_id, source_path, evt))

    return {"status": "ok", "session_id": session_id}


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(_quibblers),
        "sessions": [
            {
                "session_id": sid[:8] + "...",
                "reviews": q.context.total_reviews,
                "messages": len(q.context.messages),
                "has_summary": q.context.summary is not None,
            }
            for sid, q in _quibblers.items()
        ],
    }


def run_server(port: int = 8082):
    """
    Run the iFlow hook server on specified port.

    Default port is 8082 (different from standard Quibbler's 8081)
    to allow running both versions simultaneously.
    """
    # Prevent the quibbler agent from triggering hooks (would create infinite loop)
    os.environ["CLAUDE_MONITOR_SKIP_FORWARD"] = "1"

    logger.info("=" * 80)
    logger.info("Starting Quibbler iFlow Hook Server")
    logger.info(f"Port: {port}")
    logger.info(f"Hook endpoint: http://127.0.0.1:{port}/hook/{{session_id}}")
    logger.info(f"Health endpoint: http://127.0.0.1:{port}/health")
    logger.info("")
    logger.info("Enhanced features:")
    logger.info("  ✓ Automatic iFlow authentication (no API key needed)")
    logger.info("  ✓ Token-efficient context management")
    logger.info("  ✓ Smart event filtering (critical events only)")
    logger.info("  ✓ Auto-summarization for long sessions")
    logger.info("  ✓ Enhanced prompts")
    logger.info("")
    logger.info("Feedback written to: .quibbler/{session_id}.txt")
    logger.info("Logs written to: ~/.quibbler/quibbler.log")
    logger.info("=" * 80)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    run_server()
