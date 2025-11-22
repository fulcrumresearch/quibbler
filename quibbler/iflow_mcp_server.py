#!/usr/bin/env python3
"""
Quibbler MCP server for iFlow CLI.

Enhanced version with:
- Automatic token authentication from iFlow settings
- Token-efficient context management
- Smart summarization for long conversations
- Enhanced prompts optimized for iFlow

No ANTHROPIC_API_KEY needed - uses iFlow authentication automatically.

Setup for iFlow CLI:
    ~/.iflow/mcp.json:
    {
      "mcpServers": {
        "quibbler": {
          "command": "quibbler iflow-mcp"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
from textwrap import dedent

from mcp.server.fastmcp import FastMCP

from quibbler.iflow_agent import (
    IFlowQuibblerMCP,
    load_iflow_quibbler_config,
)
from quibbler.iflow_prompts import load_iflow_prompt
from quibbler.logger import get_logger

logger = get_logger(__name__)

# Global registry: project_path -> IFlowQuibblerMCP
_quibblers: dict[str, IFlowQuibblerMCP] = {}

app = FastMCP("quibbler-iflow")


async def get_or_create_quibbler(project_path: str) -> IFlowQuibblerMCP:
    """Get or create a quibbler agent for a project"""
    quibbler = _quibblers.get(project_path)

    if quibbler is None:
        # Load prompt and config
        system_prompt = load_iflow_prompt(project_path, mode="mcp")
        config = load_iflow_quibbler_config(project_path)

        quibbler = IFlowQuibblerMCP(
            system_prompt=system_prompt,
            source_path=project_path,
            config=config,
        )

        await quibbler.start()
        _quibblers[project_path] = quibbler
        logger.info(f"Started iFlow Quibbler for project: {project_path}")
        logger.info(f"  Model: {config.model}")
        logger.info(f"  Auto-summary: {config.enable_auto_summary}")
        logger.info(f"  Smart triggers: {config.enable_smart_triggers}")

    return quibbler


@app.tool()
async def review_code(
    user_instructions: str,
    agent_plan: str,
    project_path: str,
) -> str:
    """
    Review completed code changes after implementation.

    Call this AFTER writing code to get Quibbler's critical review.
    Quibbler checks for quality issues, pattern violations, hallucinations,
    and ensures changes align with user intent.

    This iFlow-enhanced version features:
    - Automatic context summarization for long sessions
    - Token-efficient conversation management
    - Smart caching of learned rules
    - Enhanced pattern detection

    Args:
        user_instructions: Exact instructions the user gave (what they asked for)
        agent_plan: Detailed summary of specific changes made. Include:
                   - Which files were modified
                   - What was added/changed
                   - Key implementation details
                   NOT just a vague description - be concrete!
        project_path: Absolute path to project directory

    Returns:
        Quibbler's feedback (issues found or approval)

    Example:
        User asks: "Add error handling to the API endpoints"

        After implementing, call:
        review_code(
            user_instructions="Add error handling to the API endpoints",
            agent_plan='''Changes made:
1. Added try-catch blocks in routes/api.py endpoints
2. Created custom error classes in errors/api_errors.py
3. Added error response formatting in utils/responses.py
4. Updated tests in tests/test_api.py to verify error cases
5. All tests passing''',
            project_path="/home/user/my-project"
        )
    """
    logger.info("=" * 80)
    logger.info("REVIEW REQUEST")
    logger.info(f"Project: {project_path}")
    logger.info(f"User instructions: {user_instructions[:100]}...")
    logger.info(f"Agent plan length: {len(agent_plan)} chars")

    try:
        # Get or create persistent quibbler
        quibbler = await get_or_create_quibbler(project_path)

        # Format review request
        review_request = dedent(
            f"""
            ## Review Request

            **User Instructions:**
            {user_instructions}

            **Agent's Completed Changes:**
            {agent_plan}

            Review the implementation. Check:
            - Does it address what user actually asked for?
            - Any hallucinated claims or assumptions?
            - Pattern violations or inconsistencies?
            - Missing verification steps?
            - Inappropriate shortcuts or mocking?

            Provide concise, actionable feedback or approval.
            """
        ).strip()

        # Get review feedback
        feedback = await quibbler.review(review_request)

        logger.info(f"Review completed, feedback length: {len(feedback)} chars")
        logger.info(f"Total reviews this session: {quibbler.context.total_reviews}")
        logger.info(
            f"Context: {len(quibbler.context.messages)} messages, "
            f"summary present: {quibbler.context.summary is not None}"
        )
        logger.info("=" * 80)

        return feedback

    except Exception as e:
        logger.error(f"Error during review: {e}", exc_info=True)
        return f"❌ Quibbler Error: {str(e)}\n\nPlease check the logs at ~/.quibbler/quibbler.log"


async def cleanup():
    """Cleanup all quibbler agents on shutdown"""
    logger.info("Shutting down iFlow Quibbler MCP server...")
    for project_path, quibbler in list(_quibblers.items()):
        await quibbler.stop()
        _quibblers.pop(project_path, None)
    logger.info("Cleanup complete")


def main():
    """Run the iFlow MCP server via stdio"""
    logger.info("=" * 80)
    logger.info("Starting Quibbler iFlow MCP Server")
    logger.info("Enhanced features:")
    logger.info("  ✓ Automatic iFlow authentication (no API key needed)")
    logger.info("  ✓ Token-efficient context management")
    logger.info("  ✓ Auto-summarization for long conversations")
    logger.info("  ✓ Smart event filtering")
    logger.info("  ✓ Enhanced prompts")
    logger.info("=" * 80)

    try:
        app.run()
    finally:
        asyncio.run(cleanup())


def run_server():
    """Entry point for running the server"""
    main()


if __name__ == "__main__":
    main()
