#!/usr/bin/env python3
"""
Read hook JSON from stdin and POST to /hook/{session_id}

Supports both Claude Code and Cursor hook formats:
- Claude Code: uses "session_id" field
- Cursor: uses "conversation_id" field

Platform is specified via --platform argument in the CLI.
"""

import json
import os
import sys
from urllib.parse import quote

import requests

from quibbler.logger import get_logger
from quibbler.types import Platform


logger = get_logger(__name__)


def forward_hook(platform: Platform) -> int:
    """
    Forward hook events to the quibbler server.

    Args:
        platform: The platform type ("cursor" or "claude")

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info(f"=== Hook forward starting (platform={platform}) ===")

    if os.getenv("CLAUDE_MONITOR_SKIP_FORWARD") == "1":
        logger.info("Skipping forward (CLAUDE_MONITOR_SKIP_FORWARD=1)")
        return 0

    # Read hook JSON from stdin
    try:
        logger.info("Reading from stdin...")
        raw = sys.stdin.read()
        logger.info(f"Read {len(raw)} bytes from stdin")

        if not raw:
            logger.error("Empty stdin - no data to forward")
            return 1

        payload = json.loads(raw)
        logger.info(f"Parsed JSON successfully: {list(payload.keys())}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid stdin JSON: {e}")
        logger.error(f"Raw input (first 200 chars): {raw[:200]}")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error reading stdin: {e}", exc_info=True)
        return 1

    match platform:
        case "cursor":
            session_id = payload.get("conversation_id")
        case "claude":
            session_id = payload.get("session_id")

    if not session_id:
        logger.error(f"No session_id found for platform {platform}")
        return 1

    source_path = os.getcwd()

    logger.info(f"Session ID: {session_id}")
    logger.info(f"Source path: {source_path}")

    base = os.getenv("QUIBBLER_MONITOR_BASE", "http://127.0.0.1:8081")
    session_id_enc = quote(session_id, safe="")
    url = f"{base.rstrip('/')}/hook/{session_id_enc}"

    envelope = {
        "event": payload.get("hook_event_name", "UnknownEvent"),
        "receivedAt": payload.get("timestamp") or payload.get("time"),
        "payload": payload,
        "source_path": source_path,
    }

    try:
        logger.info(f"Forwarding {envelope['event']} to {url}")
        response = requests.post(url, json=envelope, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully forwarded to server: {response.status_code}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout forwarding hook (10s): {e}")
        return 1
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error forwarding hook: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to forward hook: {e}", exc_info=True)
        return 1

    logger.info("=== Hook forward completed successfully ===")
    return 0
