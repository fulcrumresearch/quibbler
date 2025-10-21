#!/usr/bin/env python3
"""
Display hook for quibbler feedback.

This script:
1. Reads hook event JSON from stdin to extract session_id
2. Checks if quibbler-$session_id.txt exists in the current working directory
3. If exists: reads contents, prints to stderr, deletes file
4. If not exists: exits silently

This is designed to be called as a hook to display quibbler feedback to the agent.
Output to stderr ensures the feedback is visible in the agent's context.
"""

import sys
import json
from pathlib import Path


def display_feedback() -> int:
    """Display quibbler feedback to the agent"""
    # Read hook event from stdin to extract session_id
    hook_input = sys.stdin.read().strip()
    if not hook_input:
        return 0

    hook_event = json.loads(hook_input)
    session_id = hook_event.get("session_id")
    if not session_id:
        return 0

    # Look for session-specific quibbler feedback file
    quibbler_file = Path.cwd() / f".quibbler-{session_id}.txt"
    if not quibbler_file.exists():
        return 0

    # Read the quibbler feedback
    feedback = quibbler_file.read_text()

    # Print to stderr so it's fed back to the agent
    print("=" * 80, file=sys.stderr)
    print("QUIBBLER FEEDBACK", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(feedback, file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    # Delete the file after displaying
    quibbler_file.unlink()

    return 2
