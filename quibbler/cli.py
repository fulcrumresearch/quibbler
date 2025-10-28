#!/usr/bin/env python3
"""Quibbler CLI - Main command-line interface"""

from quibbler.mcp_server import run_server


def main():
    """Main CLI entry point - runs the MCP server via stdio"""
    run_server()


if __name__ == "__main__":
    main()
