"""Quibbler agent for code review"""

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from quibbler.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class QuibblerConfig:
    """Configuration for Quibbler agent"""

    model: str = DEFAULT_MODEL


def load_config() -> QuibblerConfig:
    """Load config from ~/.quibbler/config.json"""
    config_file = Path.home() / ".quibbler" / "config.json"

    if config_file.exists():
        try:
            with open(config_file) as f:
                data = json.load(f)
                return QuibblerConfig(model=data.get("model", DEFAULT_MODEL))
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    return QuibblerConfig(model=DEFAULT_MODEL)


_config = load_config()


@dataclass
class Quibbler:
    """Quibbler agent that reviews code changes and maintains context"""

    system_prompt: str
    source_path: str
    model: str = DEFAULT_MODEL

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
        Submit a review request and wait for feedback.

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

    async def _run(self) -> None:
        """Main quibbler loop - maintains persistent agent and processes review requests"""
        # Create .quibbler directory for rules
        quibbler_dir = Path(self.source_path) / ".quibbler"
        quibbler_dir.mkdir(exist_ok=True)

        options = ClaudeAgentOptions(
            cwd=self.source_path,
            system_prompt=self.system_prompt,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            model=self.model,
            hooks={},
            mcp_servers={},
        )

        try:
            async with ClaudeSDKClient(options=options) as client:
                # Startup message
                await client.query(
                    "Quibbler session started. You will receive code review requests. "
                    "For each request, analyze the user's intent and the agent's proposed changes. "
                    "Provide concise, actionable feedback or approval. Build understanding of the codebase over time."
                )
                async for message in client.receive_response():
                    # Just consume startup messages
                    logger.info("startup> type=%s", type(message).__name__)

                # Process review requests one at a time
                while True:
                    review_request, response_future = await self.queue.get()
                    try:
                        # Send review request to agent
                        await client.query(review_request)

                        # Collect the full response text from AssistantMessage blocks
                        feedback_parts = []
                        async for message in client.receive_response():
                            logger.info("review> type=%s", type(message).__name__)

                            # Only extract text from AssistantMessage
                            if isinstance(message, AssistantMessage):
                                for block in message.content:
                                    if isinstance(block, TextBlock):
                                        feedback_parts.append(block.text)
                                        logger.info(
                                            "review> extracted text: %s",
                                            block.text[:100],
                                        )
                            # Other message types (SystemMessage, ResultMessage) don't contain response text

                        # Combine response and send back via future
                        feedback = "".join(feedback_parts)
                        response_future.set_result(feedback)

                    except Exception as e:
                        logger.error(f"Error processing review request: {e}")
                        response_future.set_exception(e)
                    finally:
                        self.queue.task_done()

        except asyncio.CancelledError:
            # Normal shutdown - task was cancelled
            raise
        except Exception:
            logger.exception("Quibbler runner crashed")
