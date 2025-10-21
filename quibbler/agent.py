"""Quibbler agent for Claude Code"""

from dataclasses import dataclass, field
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import json
import os
from pathlib import Path

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


def format_event_for_agent(evt: Dict[str, Any]) -> str:
    """Format event for the quibbler agent"""
    event_type = evt.get("event", "UnknownEvent")
    ts = evt.get("received_at", datetime.now(timezone.utc).isoformat())
    pretty_json = json.dumps(evt, indent=2, ensure_ascii=False)

    return f"HOOK EVENT: {event_type}\ntime: {ts}\n\n```json\n{pretty_json}\n```"


@dataclass
class Quibbler:
    """Quibbler agent that writes feedback to quibbler-$session_id.txt"""

    system_prompt: str
    source_path: str
    session_id: str
    model: str = DEFAULT_MODEL

    client: Optional[ClaudeSDKClient] = field(default=None, init=False)
    queue: asyncio.Queue = field(
        default_factory=lambda: asyncio.Queue(), init=False
    )
    task: Optional[asyncio.Task] = field(default=None, init=False)

    async def start(self) -> None:
        """Start the quibbler agent"""
        if self.client is not None:
            return

        # Update system prompt with session-specific filename, to have session mapped messaging
        message_file = f".quibbler-{self.session_id}.txt"
        updated_prompt = self.system_prompt.replace(
            ".quibbler-messages.txt", message_file
        )

        options = ClaudeAgentOptions(
            cwd=self.source_path,
            system_prompt=updated_prompt,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            model=_config.model,
            hooks={},
            mcp_servers={},
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()
        self.task = asyncio.create_task(self._run())
        logger.info(f"Started quibbler with model: {_config.model}")

    async def stop(self) -> None:
        """Stop the quibbler agent"""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass  # Expected during shutdown
            self.task = None
        if self.client:
            await self.client.__aexit__(None, None, None)
            self.client = None

    async def enqueue(self, evt: Dict[str, Any]) -> None:
        """Add an event to the processing queue"""
        self.queue.put_nowait(evt)

    async def _run(self) -> None:
        """Main quibbler loop - processes events one at a time"""
        # Send startup message
        await self.client.query(
            "Quibbler session started. Watch the events and intervene when necessary. Build understanding in your head."
        )

        async for chunk in self.client.receive_response():
            logger.info("startup> %s", chunk)

        # Process events one at a time
        while True:
            # Get event (blocking)
            evt = await self.queue.get()

            try:
                # Format event and send
                prompt = format_event_for_agent(evt)

                await self.client.query(prompt)
                async for chunk in self.client.receive_response():
                    logger.info("event> %s", chunk)
            finally:
                # Mark event as done
                self.queue.task_done()
