#!/usr/bin/env python3
"""
Display hook for quibbler feedback.

Supports both Claude Code and Cursor hook formats:
- Claude Code: extracts session_id from "session_id" field, outputs to stderr
- Cursor: extracts session_id from "conversation_id" field, outputs JSON with followup_message

This script:
1. Reads hook event JSON from stdin to extract session_id
2. Checks if .quibbler/{session_id}.txt exists in the current working directory
3. If exists: reads contents, displays via platform-specific output, deletes file
4. If not exists: exits silently

Platform-specific output:
- Claude Code: Prints to stderr so feedback is visible in the agent's context
- Cursor: Outputs JSON with followup_message field, which becomes an automatic user message
"""

import json
import sys
from pathlib import Path

from quibbler.types import Platform


def display_feedback(platform: Platform) -> int:
    """
    Display quibbler feedback to the agent.

    Args:
        platform: The platform type ("cursor" or "claude")

    Returns:
        Exit code (0 for no feedback, 2 for feedback displayed)
    """
    # Read hook event from stdin to extract session_id
    hook_input = sys.stdin.read().strip()
    if not hook_input:
        return 0

    hook_event = json.loads(hook_input)

    # Extract session_id based on platform
    match platform:
        case "cursor":
            session_id = hook_event.get("conversation_id")
        case "claude":
            session_id = hook_event.get("session_id")

    if not session_id:
        return 0

    # Look for session-specific quibbler feedback file in .quibbler directory
    quibbler_file = Path.cwd() / ".quibbler" / f"{session_id}.txt"
    if not quibbler_file.exists():
        return 0

    # Read the quibbler feedback
    feedback = quibbler_file.read_text()

    # Output based on platform
    match platform:
        case "cursor":
            # Cursor: output JSON with followup_message to stdout
            output = {"followup_message": f"QUIBBLER FEEDBACK\n\n{feedback}"}
            print(json.dumps(output))
        case "claude":
            # Claude Code: output to stderr
            print("=" * 80, file=sys.stderr)
            print("QUIBBLER FEEDBACK", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(feedback, file=sys.stderr)
            print("=" * 80, file=sys.stderr)

    # Delete the file after displaying
    quibbler_file.unlink()

    return 2
