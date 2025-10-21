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
    """Critic agent that writes feedback to critic-$session_id.txt"""

    system_prompt: str
    source_path: str
    session_id: str

    client: Optional[ClaudeSDKClient] = field(default=None, init=False)
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000), init=False)
    task: Optional[asyncio.Task] = field(default=None, init=False)

    async def start(self) -> None:
        """Start the critic agent"""
        if self.client is not None:
            return

        # Update system prompt with session-specific filename
        updated_prompt = self.system_prompt.replace(
            ".critic-messages.txt",
            f"critic-{self.session_id}.txt"
        )

        options = ClaudeAgentOptions(
            cwd=self.source_path,
            system_prompt=updated_prompt,
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
        """Main critic loop - processes batched events"""
        # Send startup message
        await self.client.query(
            "Critic session started. Watch the events and intervene when necessary. Build understanding in your head."
        )

        async for chunk in self.client.receive_response():
            logger.info("startup> %s", chunk)

        # Process events in batches
        while True:
            # Collect batch of events
            batch = []

            # Get first event (blocking)
            first_event = await self.queue.get()
            batch.append(first_event)
            batch_start = asyncio.get_event_loop().time()

            # Collect more events with timeout
            while True:
                batch_age = asyncio.get_event_loop().time() - batch_start

                # Stop if batch is full or too old
                if len(batch) >= MAX_BATCH_SIZE or batch_age >= MAX_BATCH_WAIT:
                    break

                # Try to get more events (with timeout)
                try:
                    evt = await asyncio.wait_for(self.queue.get(), timeout=BATCH_WAIT_TIME)
                    batch.append(evt)
                except asyncio.TimeoutError:
                    break

            # Format all events and send as one message
            try:
                prompts = [format_event_for_agent(evt) for evt in batch]
                combined_prompt = "\n\n---\n\n".join(prompts)

                await self.client.query(combined_prompt)
                async for chunk in self.client.receive_response():
                    logger.info("batch[%d]> %s", len(batch), chunk)
            finally:
                # Mark all events as done
                for _ in batch:
                    self.queue.task_done()
