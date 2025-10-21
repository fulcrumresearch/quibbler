#!/usr/bin/env python3
"""
Display hook for critic feedback.

This script:
1. Checks if .critic-messages.txt exists in the current working directory
2. If exists: reads contents, prints to stderr, deletes file
3. If not exists: exits silently

This is designed to be called as a hook to display critic feedback to the agent.
Output to stderr ensures the feedback is visible in the agent's context.
"""

import sys
from pathlib import Path


def display_feedback() -> int:
    """Display critic feedback to the agent"""
    # Look for critic feedback file in current working directory
    critic_file = Path.cwd() / ".critic-messages.txt"

    if not critic_file.exists():
        # No feedback to display - exit silently
        return 0

    # Read the critic feedback
    feedback = critic_file.read_text()

    # Print to stderr so it's fed back to the agent
    print("=" * 80, file=sys.stderr)
    print("CRITIC FEEDBACK", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(feedback, file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    # Delete the file after displaying
    critic_file.unlink()

    return 2
