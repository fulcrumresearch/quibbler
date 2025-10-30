#!/usr/bin/env python3
"""
Read hook JSON from stdin and POST to /hook/<session_id>
Session ID is passed as the first argument
"""

import json
import os
import sys
from urllib.parse import quote

import requests

from quibbler.logger import get_logger


logger = get_logger(__name__)


def forward_hook() -> int:
    """Forward hook events to the quibbler server"""
    logger.info("=== Hook forward starting ===")

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

    session_id = payload.get("session_id")
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
