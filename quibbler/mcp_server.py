#!/usr/bin/env python3
"""
Quibbler MCP server - exposes review_code tool for agents to call before making changes.

Required environment:
  ANTHROPIC_API_KEY=...  # Required by Claude SDK

The MCP client spawns this server automatically via stdio.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from quibbler.agent import Quibbler, load_config
from quibbler.logger import get_logger
from quibbler.prompts import load_prompt

logger = get_logger(__name__)

# project_path -> Quibbler
_quibblers: Dict[str, Quibbler] = {}

# Create MCP server
app = Server("quibbler")


async def get_or_create_quibbler(project_path: str) -> Quibbler:
    """Get or create a quibbler agent for a project"""
    quibbler = _quibblers.get(project_path)

    if quibbler is None:
        system_prompt = load_prompt(project_path)
        config = load_config(project_path)
        quibbler = Quibbler(
            system_prompt=system_prompt,
            source_path=project_path,
            model=config.model,
            mode="mcp",
        )
        await quibbler.start()
        _quibblers[project_path] = quibbler
        logger.info("started quibbler for project: %s", project_path)

    return quibbler


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="review_code",
            description=(
                "Review proposed code changes before implementation. "
                "Call this BEFORE writing any code to get feedback from Quibbler. "
                "Quibbler checks for quality issues, pattern violations, hallucinations, "
                "and ensures the plan aligns with user intent."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_instructions": {
                        "type": "string",
                        "description": "The exact instructions the user gave (what they actually asked for)",
                    },
                    "agent_plan": {
                        "type": "string",
                        "description": (
                            "The specific code changes you plan to make. "
                            "Include file names, function signatures, key logic, and implementation details. "
                            "NOT just a general description - be concrete and detailed."
                        ),
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to the project directory",
                    },
                },
                "required": ["user_instructions", "agent_plan", "project_path"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    if name != "review_code":
        raise ValueError(f"Unknown tool: {name}")

    user_instructions = arguments.get("user_instructions")
    agent_plan = arguments.get("agent_plan")
    project_path = arguments.get("project_path")

    if not all([user_instructions, agent_plan, project_path]):
        raise ValueError("Missing required arguments")

    logger.info(f"Review requested for project: {project_path}")
    logger.info(f"User instructions: {user_instructions[:100]}...")
    logger.info(f"Agent plan: {agent_plan[:100]}...")

    # Get or create persistent quibbler for this project
    quibbler = await get_or_create_quibbler(project_path)

    # Format review request
    review_request = f"""## Review Request

**User Instructions:**
{user_instructions}

**Agent's Proposed Changes:**
{agent_plan}

Please review this plan. Check for:
- Does it address what the user actually asked for?
- Any hallucinated claims or assumptions?
- Pattern violations or inconsistencies?
- Missing verification steps?
- Inappropriate shortcuts or mocking?

Provide concise, actionable feedback or approval."""

    # Enqueue review and wait for feedback
    feedback = await quibbler.review(review_request)

    return [TextContent(type="text", text=feedback)]


async def cleanup():
    """Cleanup all quibbler agents on shutdown"""
    for project_path, quibbler in list(_quibblers.items()):
        await quibbler.stop()
        _quibblers.pop(project_path, None)
    logger.info("Cleaned up all quibbler agents")


async def main():
    """Run the MCP server via stdio"""
    logger.info("Starting Quibbler MCP Server")
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    finally:
        await cleanup()


def run_server():
    """Entry point for running the server"""
    asyncio.run(main())
