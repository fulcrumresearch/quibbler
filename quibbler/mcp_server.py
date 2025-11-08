#!/usr/bin/env python3
"""
Quibbler MCP server - exposes review_code tool for agents to call before making changes.

Optional environment:
  ANTHROPIC_API_KEY=...  # Optional - Claude SDK supports auto-login with Claude Code/Max accounts
  QUIBBLER_TOOL_NAME=...  # Optional - customize the tool name (default: review_code)

The MCP client spawns this server automatically via stdio.
"""

from __future__ import annotations

import asyncio
import os
from textwrap import dedent

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

from quibbler.agent import QuibblerMCP, load_config
from quibbler.logger import get_logger
from quibbler.prompts import load_prompt


logger = get_logger(__name__)


# project_path -> QuibblerMCP
_quibblers: dict[str, QuibblerMCP] = {}


app = FastMCP("quibbler")


async def get_or_create_quibbler(project_path: str) -> QuibblerMCP:
    """Get or create a quibbler agent for a project"""
    quibbler = _quibblers.get(project_path)

    if quibbler is None:
        system_prompt = load_prompt(project_path, mode="mcp")
        config = load_config(project_path)
        quibbler = QuibblerMCP(
            system_prompt=system_prompt,
            source_path=project_path,
            model=config.model,
            allowed_tools=config.allowed_tools,
            mcp_servers=config.mcp_servers,
        )
        await quibbler.start()
        _quibblers[project_path] = quibbler
        logger.info("started quibbler for project: %s", project_path)

    return quibbler


async def review_code_impl(
    user_instructions: str,
    agent_plan: str,
    project_path: str,
) -> str:
    """
    Review completed code changes after implementation.
    Call this AFTER writing code to get feedback from Quibbler.
    Quibbler checks for quality issues, pattern violations, hallucinations, and ensures the changes align with user intent.

    Args:
        user_instructions: The exact instructions the user gave (what they actually asked for)
        agent_plan: A summary of the specific code changes you made. Include which files were modified, what was added/changed, and key implementation details. NOT just a general description - be concrete and detailed.
        project_path: Absolute path to the project directory
    """
    logger.info("=" * 80)
    logger.info("REVIEW REQUESTED for project: %s", project_path)
    logger.info("User instructions: %s", user_instructions[:200])
    logger.info("Agent plan: %s", agent_plan[:200])
    logger.info("=" * 80)

    # Get or create persistent quibbler for this project
    quibbler = await get_or_create_quibbler(project_path)

    # Format review request
    review_request = dedent(
        f"""
        ## Review Request

        **User Instructions:**
        {user_instructions}

        **Agent's Completed Changes:**
        {agent_plan}

        Please review the implemented changes. Check for:
        - Do they address what the user actually asked for?
        - Any hallucinated claims or assumptions in the implementation?
        - Pattern violations or inconsistencies?
        - Missing verification steps?
        - Inappropriate shortcuts or mocking?

        Provide concise, actionable feedback or approval.
        """
    ).strip()

    # Enqueue review and wait for feedback
    feedback = await quibbler.review(review_request)

    logger.info("=" * 80)
    logger.info("REVIEW COMPLETED for project: %s", project_path)
    logger.info("Feedback: %s", feedback[:500])
    logger.info("=" * 80)

    return feedback


# Register tool with configured name (from env var or default)
TOOL_NAME = os.environ.get("QUIBBLER_TOOL_NAME", "review_code")
app.add_tool(review_code_impl, name=TOOL_NAME)


async def cleanup():
    """Cleanup all quibbler agents on shutdown"""
    for project_path, quibbler in list(_quibblers.items()):
        await quibbler.stop()
        _quibblers.pop(project_path, None)
    logger.info("Cleaned up all quibbler agents")


def main():
    """Run the MCP server via stdio"""
    logger.info("Starting Quibbler MCP Server")
    try:
        app.run()
    finally:
        asyncio.run(cleanup())


def run_server():
    """Entry point for running the server"""
    main()
