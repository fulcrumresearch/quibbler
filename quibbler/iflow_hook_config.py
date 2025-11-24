#!/usr/bin/env python3
"""
Configuration helper for iFlow CLI hooks.

Adds Quibbler hooks to .iflow/settings.json to enable
event-driven monitoring with iFlow CLI.
"""

import json
from pathlib import Path

from quibbler.logger import get_logger

logger = get_logger(__name__)


def add_iflow_hooks():
    """
    Add Quibbler hooks to .iflow/settings.json.

    This configures iFlow CLI to forward events to the Quibbler hook server
    and display feedback to the agent.

    The hooks work similarly to Claude Code hooks but are configured in
    .iflow/settings.json instead of .claude/settings.json.
    """
    # Find .iflow/settings.json
    iflow_dir = Path.cwd() / ".iflow"
    settings_file = iflow_dir / "settings.json"

    if not iflow_dir.exists():
        iflow_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created {iflow_dir}")
        print(f"Created {iflow_dir}")

    # Load existing settings or create new
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)
        logger.info(f"Loaded existing settings from {settings_file}")
    else:
        settings = {}
        logger.info("Creating new settings file")

    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Add PreToolUse hook for quibbler hook notify
    # This displays any pending feedback before each tool use
    settings["hooks"]["PreToolUse"] = [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": "quibbler hook notify"}],
        }
    ]

    # Add PostToolUse hook for quibbler hook forward and notify
    # This forwards tool usage to the server and displays any new feedback
    settings["hooks"]["PostToolUse"] = [
        {
            "matcher": "*",
            "hooks": [
                {"type": "command", "command": "quibbler hook forward"},
                {"type": "command", "command": "quibbler hook notify"},
            ],
        }
    ]

    # Add UserPromptSubmit hook to forward user prompts to the server
    settings["hooks"]["UserPromptSubmit"] = [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": "quibbler hook forward"}],
        }
    ]

    # Add Stop hook for final feedback display
    settings["hooks"]["Stop"] = [
        {"hooks": [{"type": "command", "command": "quibbler hook notify"}]}
    ]

    # Write back to file
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"✓ Added Quibbler hooks to {settings_file}")
    print()
    print("Next steps:")
    print("1. Start the Quibbler iFlow hook server:")
    print("   quibbler iflow hook server")
    print()
    print("2. The server will run on port 8082 by default")
    print("   (Use a different port: quibbler iflow hook server 9000)")
    print()
    print("3. Use iFlow CLI in this project - Quibbler will automatically")
    print("   observe and provide feedback when needed")
    print()
    print("Features enabled:")
    print("  ✓ Automatic iFlow authentication (no API key needed)")
    print("  ✓ Token-efficient context management")
    print("  ✓ Smart event filtering")
    print("  ✓ Auto-summarization for long sessions")
    print()
    print("Logs: ~/.quibbler/quibbler.log")
    print("Feedback: .quibbler/{session_id}.txt")

    logger.info("Successfully added iFlow hooks")


if __name__ == "__main__":
    add_iflow_hooks()
