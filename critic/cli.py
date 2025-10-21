#!/usr/bin/env python3
"""Critic CLI - Main command-line interface"""

import sys
import json
import argparse
from pathlib import Path

from critic.server import run_server
from critic.hook_forward import forward_hook
from critic.hook_display import display_feedback


def cmd_server(args):
    """Run the critic server"""
    port = args.port if args.port else 8081
    run_server(port=port)


def cmd_hook(args):
    """Forward hook events to the server"""
    sys.exit(forward_hook())


def cmd_notify(args):
    """Display critic feedback to the agent"""
    sys.exit(display_feedback())


def cmd_add(args):
    """Add critic hooks to .claude/settings.json"""
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

    # Add PreToolUse hook for critic-notify
    settings["hooks"]["PreToolUse"] = [
        {"matcher": "*", "hooks": [{"type": "command", "command": "critic notify"}]}
    ]

    # Add PostToolUse hook for critic-hook and critic-notify
    settings["hooks"]["PostToolUse"] = [
        {
            "matcher": "*",
            "hooks": [
                {"type": "command", "command": "critic hook"},
                {"type": "command", "command": "critic notify"},
            ],
        }
    ]

    # Add UserMessage hook for critic-hook and critic-notify
    settings["hooks"]["Stop"] = [
        {"hooks": [{"type": "command", "command": "critic notify"}]}
    ]

    # Write back to file
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"✓ Added critic hooks to {settings_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="critic",
        description="AI monitoring for Claude Code agents",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server command
    parser_server = subparsers.add_parser("server", help="Start the critic server")
    parser_server.add_argument(
        "port", type=int, nargs="?", help="Port to run on (default: 8081)"
    )
    parser_server.set_defaults(func=cmd_server)

    # Hook command
    parser_hook = subparsers.add_parser(
        "hook", help="Forward hook events to the server"
    )
    parser_hook.set_defaults(func=cmd_hook)

    # Notify command
    parser_notify = subparsers.add_parser(
        "notify", help="Display critic feedback to the agent"
    )
    parser_notify.set_defaults(func=cmd_notify)

    # Add command
    parser_add = subparsers.add_parser(
        "add", help="Add critic hooks to .claude/settings.json"
    )
    parser_add.set_defaults(func=cmd_add)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
