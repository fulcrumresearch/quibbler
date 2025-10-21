#!/usr/bin/env python3
"""Quibbler CLI - Main command-line interface"""

import sys
import json
import argparse
from pathlib import Path

from quibbler.server import run_server
from quibbler.hook_forward import forward_hook
from quibbler.hook_display import display_feedback


def cmd_server(args):
    """Run the quibbler server"""
    port = args.port if args.port else 8081
    run_server(port=port)


def cmd_hook(args):
    """Forward hook events to the server"""
    sys.exit(forward_hook())


def cmd_notify(args):
    """Display quibbler feedback to the agent"""
    sys.exit(display_feedback())


def cmd_add(args):
    """Add quibbler hooks to .claude/settings.json"""
    # Find .claude/settings.json
    claude_dir = Path.cwd() / ".claude"
    settings_file = claude_dir / "settings.json"

    if not claude_dir.exists():
        claude_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created {claude_dir}")

    # Load existing settings or create new
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)
    else:
        settings = {}

    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Add PreToolUse hook for quibbler notify
    settings["hooks"]["PreToolUse"] = [
        {"matcher": "*", "hooks": [{"type": "command", "command": "quibbler notify"}]}
    ]

    # Add PostToolUse hook for quibbler hook and quibbler notify
    settings["hooks"]["PostToolUse"] = [
        {
            "matcher": "*",
            "hooks": [
                {"type": "command", "command": "quibbler hook"},
                {"type": "command", "command": "quibbler notify"},
            ],
        }
    ]

    settings["hooks"]["UserPromptSubmit"] = [
        {"matcher": "*", "hooks": [{"type": "command", "command": "quibbler hook"}]}
    ]

    # Add Stop hook for quibbler notify
    settings["hooks"]["Stop"] = [
        {"hooks": [{"type": "command", "command": "quibbler notify"}]}
    ]

    # Write back to file
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"✓ Added quibbler hooks to {settings_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="quibbler",
        description="AI monitoring for Claude Code agents",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Available commands",
        help="Available commands",
        metavar="{server,add}",  # <-- set here
        required=True,  # <-- avoids args.func missing
    )

    # Server command
    parser_server = subparsers.add_parser("server", help="Start the quibbler server")
    parser_server.add_argument(
        "port", type=int, nargs="?", help="Port to run on (default: 8081)"
    )
    parser_server.set_defaults(func=cmd_server)

    # Add command
    parser_add = subparsers.add_parser(
        "add", help="Add quibbler hooks to .claude/settings.json"
    )
    parser_add.set_defaults(func=cmd_add)

    # Hook command (hidden from help)
    parser_hook = subparsers.add_parser("hook", help=argparse.SUPPRESS)
    parser_hook.set_defaults(func=cmd_hook)

    # Notify command (hidden from help)
    parser_notify = subparsers.add_parser("notify", help=argparse.SUPPRESS)
    parser_notify.set_defaults(func=cmd_notify)

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
