#!/usr/bin/env python3
"""
Quibbler server - receives hook events and routes them to quibbler agents.

Required environment:
  ANTHROPIC_API_KEY=...  # Required by Claude SDK

Run:
  quibbler server [port]

  Default port: 8081
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from quibbler.agent import Quibbler
from quibbler.prompts import load_prompt
from quibbler.logger import logger

app = FastAPI(title="Quibbler Server", version="1.0")

# session_id -> Quibbler
_quibblers: Dict[str, Quibbler] = {}


async def get_or_create_quibbler(session_id: str, source_path: str) -> Quibbler:
    """Get or create a quibbler for a session"""
    quibbler = _quibblers.get(session_id)

    if quibbler is None:
        system_prompt = load_prompt(source_path)
        quibbler = Quibbler(
            system_prompt=system_prompt,
            source_path=source_path,
            session_id=session_id,
        )
        await quibbler.start()
        _quibblers[session_id] = quibbler
        logger.info("started quibbler for session_id=%s in %s", session_id, source_path)

    return quibbler


@app.on_event("shutdown")
async def _shutdown() -> None:
    for sid, c in list(_quibblers.items()):
        await c.stop()
        _quibblers.pop(sid, None)


async def _process_event_in_background(
    session_id: str, source_path: str, evt: Dict[str, Any]
) -> None:
    """Process event in background without blocking the HTTP response"""
    try:
        quibbler = await get_or_create_quibbler(session_id, source_path)
        await quibbler.enqueue(evt)
    except Exception as e:
        logger.error(f"Error processing event for session {session_id}: {e}")


@app.post("/hook/{session_id}")
async def hook(request: Request, session_id: str) -> Dict[str, str]:
    """Receive hook events and route to appropriate quibbler"""
    body = await request.body()

    data = json.loads(body.decode("utf-8"))

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    source_path = data.get("source_path")

    # Create clean event with received timestamp
    evt = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    event_type = evt.get("event", "UnknownEvent")
    logger.info(
        f"Received event {event_type} for session {session_id} in {source_path}"
    )

    # Process in background - don't block the response
    asyncio.create_task(_process_event_in_background(session_id, source_path, evt))

    return {"status": "ok", "session_id": session_id}


def run_server(port: int = 8081):
    """Run the quibbler server on the specified port"""
    # Prevent the quibbler agent itself from triggering hooks (would create infinite loop)
    os.environ["CLAUDE_MONITOR_SKIP_FORWARD"] = "1"

    logger.info(f"Starting Quibbler Server on port {port}")
    logger.info(f"Hook endpoint: http://0.0.0.0:{port}/hook/{{session_id}}")
    logger.info(f"Feedback written to: quibbler-{{session_id}}.txt")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
