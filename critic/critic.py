"""Critic agent for Claude Code"""

from dataclasses import dataclass, field
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Batch processing configuration
BATCH_WAIT_TIME = 10  # Wait 10 seconds after first event before processing
MAX_BATCH_SIZE = 10  # Process immediately if 10 events accumulate
MAX_BATCH_WAIT = 20  # Never wait more than 20 seconds total


def format_event_for_agent(evt: Dict[str, Any]) -> str:
    """Format event for the critic agent"""
    event_type = evt.get("event", "UnknownEvent")
    ts = evt.get("received_at", datetime.now(timezone.utc).isoformat())
    pretty_json = json.dumps(evt, indent=2, ensure_ascii=False)

    return f"HOOK EVENT: {event_type}\ntime: {ts}\n\n```json\n{pretty_json}\n```"


@dataclass
class Critic:
    """Critic agent that writes feedback to .critic-messages.txt"""

    system_prompt: str
    source_path: str

    client: Optional[ClaudeSDKClient] = field(default=None, init=False)
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000), init=False)
    task: Optional[asyncio.Task] = field(default=None, init=False)

    async def start(self) -> None:
        """Start the critic agent"""
        if self.client is not None:
            return

        options = ClaudeAgentOptions(
            cwd=self.source_path,
            system_prompt=self.system_prompt,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            hooks={},
            mcp_servers={},
        )

        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()
        self.task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the critic agent"""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except Exception:
                pass
            self.task = None
        if self.client:
            await self.client.__aexit__(None, None, None)
            self.client = None

    async def enqueue(self, evt: Dict[str, Any]) -> None:
        """Add an event to the processing queue"""
        self.queue.put_nowait(evt)

    async def _run(self) -> None:
        """Main critic loop - processes events one at a time"""
        # Send startup message
        await self.client.query(
            "Critic session started. Watch the events and intervene when necessary. Build understanding in your head."
        )

        async for chunk in self.client.receive_response():
            logger.info("startup> %s", chunk)

        # Process events one at a time
        while True:
            evt = await self.queue.get()

            prompt = format_event_for_agent(evt)
            await self.client.query(prompt)

            async for chunk in self.client.receive_response():
                logger.info("event> %s", chunk)

            self.queue.task_done()
