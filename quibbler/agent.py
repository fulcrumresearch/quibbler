"""Quibbler agent for code review"""

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from quibbler.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def format_event_for_agent(evt: Dict[str, Any]) -> str:
    """Format hook event for the quibbler agent"""
    event_type = evt.get("event", "UnknownEvent")
    ts = evt.get("received_at", datetime.now(timezone.utc).isoformat())
    pretty_json = json.dumps(evt, indent=2, ensure_ascii=False)

    return f"HOOK EVENT: {event_type}\ntime: {ts}\n\n```json\n{pretty_json}\n```"


@dataclass
class QuibblerConfig:
    """Configuration for Quibbler agent"""

    model: str = DEFAULT_MODEL


def load_config(source_path: str) -> QuibblerConfig:
    """
    Load config with project override support.

    Checks for config in this order:
    1. Project-specific: {source_path}/.quibbler/config.json
    2. Global: ~/.quibbler/config.json
    3. Default: DEFAULT_MODEL

    Args:
        source_path: Project directory to check for project-specific config

    Returns:
        QuibblerConfig with the loaded or default model setting
    """
    # Check project-specific config first
    project_config = Path(source_path) / ".quibbler" / "config.json"
    if project_config.exists():
        try:
            with open(project_config) as f:
                data = json.load(f)
                model = data.get("model", DEFAULT_MODEL)
                logger.info(
                    f"Loaded project config from {project_config}: model={model}"
                )
                return QuibblerConfig(model=model)
        except Exception as e:
            logger.warning(f"Failed to load project config from {project_config}: {e}")

    # Fall back to global config
    global_config = Path.home() / ".quibbler" / "config.json"
    if global_config.exists():
        try:
            with open(global_config) as f:
                data = json.load(f)
                model = data.get("model", DEFAULT_MODEL)
                logger.info(f"Loaded global config from {global_config}: model={model}")
                return QuibblerConfig(model=model)
        except Exception as e:
            logger.warning(f"Failed to load global config from {global_config}: {e}")

    # Return default
    logger.info(f"No config found, using default model: {DEFAULT_MODEL}")
    return QuibblerConfig(model=DEFAULT_MODEL)


@dataclass
class Quibbler:
    """Quibbler agent that reviews code changes and maintains context"""

    system_prompt: str
    source_path: str
    model: str = DEFAULT_MODEL
    mode: str = "mcp"  # "mcp" or "hook"
    session_id: Optional[str] = None  # Required for hook mode

    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(), init=False)
    task: Optional[asyncio.Task] = field(default=None, init=False)

    async def start(self) -> None:
        """Start the quibbler agent background task"""
        if self.task is not None:
            return
        self.task = asyncio.create_task(self._run())
        logger.info(f"Started quibbler with prompt: {self.system_prompt[:100]}...")
        logger.info(f"Using model: {self.model}")

    async def stop(self) -> None:
        """Stop the quibbler agent and wait for task to complete"""
        if self.task is None:
            return
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task
        self.task = None

    async def review(self, review_request: str) -> str:
        """
        Submit a review request and wait for feedback (MCP mode).

        Args:
            review_request: The formatted review request with user instructions and agent plan

        Returns:
            The quibbler's feedback as a string
        """
        # Create a future to receive the response
        response_future = asyncio.Future()

        # Enqueue the request with its response future
        await self.queue.put((review_request, response_future))

        # Wait for the agent to process and respond
        feedback = await response_future

        return feedback

    async def enqueue(self, evt: Dict[str, Any]) -> None:
        """
        Add a hook event to the processing queue (hook mode).

        Args:
            evt: The hook event dictionary to process
        """
        await self.queue.put(evt)

    def _prepare_system_prompt(self) -> str:
        """Prepare system prompt based on mode"""
        if self.mode == "hook":
            if self.session_id is None:
                raise ValueError("session_id is required for hook mode")
            quibbler_dir = Path(self.source_path) / ".quibbler"
            message_file = str(quibbler_dir / f"{self.session_id}.txt")
            logger.info(f"Hook mode: feedback file = {message_file}")
            return self.system_prompt.format(message_file=message_file)
        else:
            return self.system_prompt

    async def _query_and_collect_text(
        self, client: ClaudeSDKClient, prompt: str
    ) -> str:
        """Send query to Claude and collect text response"""
        await client.query(prompt)

        feedback_parts = []
        async for message in client.receive_response():
            logger.info("review> type=%s", type(message).__name__)

            # Only extract text from AssistantMessage
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        feedback_parts.append(block.text)
                        logger.info("review> extracted text: %s", block.text[:100])

        return "".join(feedback_parts)

    async def _query_and_consume(self, client: ClaudeSDKClient, prompt: str) -> None:
        """Send query to Claude and consume response (don't collect)"""
        await client.query(prompt)
        async for message in client.receive_response():
            msg_type = type(message).__name__
            logger.info("event> type=%s", msg_type)

            # Log the actual content for debugging
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        logger.info(
                            "event> ASSISTANT TEXT: %s", block.text[:500]
                        )  # First 500 chars

            # Log full message to see tool use
            logger.info("event> FULL MESSAGE: %s", str(message)[:1000])

    async def _send_startup_message(self, client: ClaudeSDKClient) -> None:
        """Send mode-appropriate startup message"""
        if self.mode == "hook":
            startup_msg = (
                "Quibbler session started. Watch the events and intervene when necessary. "
                "Build understanding in your head."
            )
        else:
            startup_msg = (
                "Quibbler session started. You will receive code review requests. "
                "For each request, analyze the user's intent and the agent's proposed changes. "
                "Provide concise, actionable feedback or approval. Build understanding of the codebase over time."
            )

        await client.query(startup_msg)
        async for message in client.receive_response():
            logger.info("startup> type=%s", type(message).__name__)

    async def _run_mcp_mode(self, client: ClaudeSDKClient) -> None:
        """Process MCP review requests (synchronous responses)"""
        while True:
            review_request, response_future = await self.queue.get()
            try:
                feedback = await self._query_and_collect_text(client, review_request)
                response_future.set_result(feedback)
            except Exception as e:
                logger.error(f"Error processing review request: {e}")
                response_future.set_exception(e)
            finally:
                self.queue.task_done()

    async def _run_hook_mode(self, client: ClaudeSDKClient) -> None:
        """Process hook events (fire-and-forget)"""
        while True:
            evt = await self.queue.get()
            try:
                prompt = format_event_for_agent(evt)
                await self._query_and_consume(client, prompt)
            except Exception as e:
                logger.error(f"Error processing hook event: {e}")
            finally:
                self.queue.task_done()

    async def _run(self) -> None:
        """Main quibbler loop - dispatches to mode-specific runner"""
        # Create .quibbler directory
        quibbler_dir = Path(self.source_path) / ".quibbler"
        quibbler_dir.mkdir(exist_ok=True)

        # Prepare system prompt based on mode
        system_prompt = self._prepare_system_prompt()

        options = ClaudeAgentOptions(
            cwd=self.source_path,
            system_prompt=system_prompt,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            model=self.model,
            hooks={},
            mcp_servers={},
        )

        try:
            async with ClaudeSDKClient(options=options) as client:
                # Send startup message
                await self._send_startup_message(client)

                # Dispatch to mode-specific loop
                if self.mode == "hook":
                    await self._run_hook_mode(client)
                else:
                    await self._run_mcp_mode(client)

        except asyncio.CancelledError:
            # Normal shutdown - task was cancelled
            raise
        except Exception:
            logger.exception("Quibbler runner crashed")
