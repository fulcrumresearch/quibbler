#!/usr/bin/env python3
"""
Read hook JSON from stdin and POST to /hook/<session_id>
Session ID is passed as the first argument
"""

import json
import logging
import os
import sys
from urllib.parse import quote

import requests

from critic.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def forward_hook() -> int:
    """Forward hook events to the critic server"""
    if os.getenv("CLAUDE_MONITOR_SKIP_FORWARD") == "1":
        return 0

    # Read hook JSON from stdin
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception as e:
        logger.error(f"Invalid stdin JSON: {e}")
        return 1

    session_id = payload.get("session_id")
    source_path = os.getcwd()

    base = os.getenv("CRITIC_MONITOR_BASE", "http://127.0.0.1:8081")
    session_id_enc = quote(session_id, safe="")
    url = f"{base.rstrip('/')}/hook/{session_id_enc}"

    envelope = {
        "event": payload["hook_event_name"],
        "receivedAt": payload.get("timestamp") or payload.get("time"),
        "payload": payload,
        "source_path": source_path,
    }

    try:
        logger.info(f"Forwarding {payload['hook_event_name']} to {url}")
        response = requests.post(url, json=envelope, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully forwarded to server: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to forward hook: {e}")
        return 1

    return 0
