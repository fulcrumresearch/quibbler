#!/usr/bin/env python3
"""
Critic server - receives hook events and routes them to critic agents.

Required environment:
  ANTHROPIC_API_KEY=...  # Required by Claude SDK

Run:
  critic-server [port]

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

from critic.critic import Critic
from critic.prompts import load_prompt
from critic.logger import logger

app = FastAPI(title="Critic Server", version="1.0")

# session_id -> Critic
_critics: Dict[str, Critic] = {}


async def get_or_create_critic(session_id: str, source_path: str) -> Critic:
    """Get or create a critic for a session"""
    critic = _critics.get(session_id)

    if critic is None:
        system_prompt = load_prompt(source_path)
        critic = Critic(
            system_prompt=system_prompt,
            source_path=source_path,
            session_id=session_id,
        )
        await critic.start()
        _critics[session_id] = critic
        logger.info("started critic for session_id=%s in %s", session_id, source_path)

    return critic


@app.on_event("shutdown")
async def _shutdown() -> None:
    for sid, c in list(_critics.items()):
        await c.stop()
        _critics.pop(sid, None)


async def _process_event_in_background(
    session_id: str, source_path: str, evt: Dict[str, Any]
) -> None:
    """Process event in background without blocking the HTTP response"""
    try:
        critic = await get_or_create_critic(session_id, source_path)
        await critic.enqueue(evt)
    except Exception as e:
        logger.error(f"Error processing event for session {session_id}: {e}")


@app.post("/hook/{session_id}")
async def hook(request: Request, session_id: str) -> Dict[str, str]:
    """Receive hook events and route to appropriate critic"""
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
    """Run the critic server on the specified port"""
    # Prevent the critic agent itself from triggering hooks (would create infinite loop)
    os.environ["CLAUDE_MONITOR_SKIP_FORWARD"] = "1"

    logger.info(f"Starting Critic Server on port {port}")
    logger.info(f"Hook endpoint: http://0.0.0.0:{port}/hook/{{session_id}}")
    logger.info(f"Feedback written to: critic-{{session_id}}.txt")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
