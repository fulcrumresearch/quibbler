"""
Enhanced Quibbler agent for iFlow CLI with token-efficient context management.

Key improvements over standard Quibbler:
1. Automatic context summarization for long conversations
2. Selective message transmission (only recent + summary of old)
3. Smart triggering - reviews at important checkpoints, not every event
4. Enhanced prompt engineering for better critique quality
5. Persistent learned rules with deduplication
"""

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quibbler.iflow_client import IFlowClient, load_iflow_auth
from quibbler.logger import get_logger

logger = get_logger(__name__)

# Default model optimized for cost/performance
DEFAULT_IFLOW_MODEL = "claude-haiku-4-5"

# Context management thresholds
MAX_MESSAGES_BEFORE_SUMMARY = 15  # Summarize when conversation exceeds this
KEEP_RECENT_MESSAGES = 5  # Always keep this many recent messages


@dataclass
class ConversationMessage:
    """A message in the conversation with metadata"""

    role: str
    content: str
    timestamp: str
    token_count: int = 0  # Estimated token count


@dataclass
class ContextManager:
    """
    Manages conversation context with automatic summarization.

    Keeps recent messages and a rolling summary of older messages
    to stay within token budgets while maintaining context.
    """

    messages: list[ConversationMessage] = field(default_factory=list)
    summary: str | None = None
    total_reviews: int = 0

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation"""
        msg = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            token_count=len(content) // 4,  # Rough estimate: 1 token ≈ 4 chars
        )
        self.messages.append(msg)
        logger.debug(f"Added message: role={role}, tokens≈{msg.token_count}")

    def should_summarize(self) -> bool:
        """Check if we should summarize old messages"""
        return len(self.messages) > MAX_MESSAGES_BEFORE_SUMMARY

    async def create_summary(self, client: IFlowClient) -> None:
        """
        Summarize old messages to compress context.

        Keeps the most recent messages and creates a summary of older ones.
        """
        if not self.should_summarize():
            return

        # Split messages into old and recent
        old_messages = self.messages[:-KEEP_RECENT_MESSAGES]
        recent_messages = self.messages[-KEEP_RECENT_MESSAGES:]

        # Create summary of old messages
        old_conversation = "\n\n".join(
            [
                f"[{msg.timestamp}] {msg.role.upper()}: {msg.content}"
                for msg in old_messages
            ]
        )

        summary_prompt = f"""Summarize this code review conversation history concisely, preserving:
1. Key issues identified
2. Patterns or rules learned
3. Important decisions made
4. Recurring themes

Previous summary (if any):
{self.summary or "None"}

New conversation to summarize:
{old_conversation}

Provide a concise summary (max 500 tokens) that captures the essential context."""

        try:
            new_summary = await client.simple_query(
                system_prompt="You are a precise conversation summarizer for code reviews.",
                user_message=summary_prompt,
            )

            self.summary = new_summary
            self.messages = recent_messages
            logger.info(
                f"Summarized {len(old_messages)} old messages, kept {len(recent_messages)} recent"
            )
            logger.debug(f"New summary: {new_summary[:200]}...")

        except Exception as e:
            logger.error(f"Failed to create summary: {e}")
            # Keep original messages if summarization fails

    def get_context_messages(self) -> list[dict[str, str]]:
        """
        Get messages for API call, including summary if present.

        Returns:
            List of message dicts ready for iFlow API
        """
        messages = []

        # Add summary as a system context if present
        if self.summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"CONVERSATION HISTORY SUMMARY:\n{self.summary}",
                }
            )

        # Add recent messages
        for msg in self.messages:
            messages.append({"role": msg.role, "content": msg.content})

        return messages


@dataclass
class IFlowQuibblerConfig:
    """Configuration for iFlow Quibbler"""

    model: str = DEFAULT_IFLOW_MODEL
    enable_auto_summary: bool = True  # Auto-summarize long conversations
    enable_smart_triggers: bool = True  # Only trigger on important events
    temperature: float = 0.7
    max_tokens: int = 4096


def load_iflow_quibbler_config(source_path: str) -> IFlowQuibblerConfig:
    """
    Load iFlow Quibbler config from project or global settings.

    Args:
        source_path: Project directory to check

    Returns:
        IFlowQuibblerConfig with loaded settings
    """
    # Check project config
    project_config = Path(source_path) / ".quibbler" / "iflow_config.json"
    if project_config.exists():
        try:
            with open(project_config) as f:
                data = json.load(f)
                logger.info(f"Loaded iFlow Quibbler config from {project_config}")
                return IFlowQuibblerConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load project config: {e}")

    # Check global config
    global_config = Path.home() / ".quibbler" / "iflow_config.json"
    if global_config.exists():
        try:
            with open(global_config) as f:
                data = json.load(f)
                logger.info(f"Loaded iFlow Quibbler config from {global_config}")
                return IFlowQuibblerConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load global config: {e}")

    logger.info("Using default iFlow Quibbler config")
    return IFlowQuibblerConfig()


@dataclass
class IFlowQuibbler:
    """
    Enhanced Quibbler agent for iFlow with token-efficient context management.

    Features:
    - Automatic context summarization
    - Smart event filtering
    - Enhanced prompt engineering
    - Persistent rule learning
    """

    system_prompt: str
    source_path: str
    config: IFlowQuibblerConfig = field(default_factory=IFlowQuibblerConfig)

    context: ContextManager = field(default_factory=ContextManager, init=False)
    client: IFlowClient | None = field(default=None, init=False)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False)
    task: asyncio.Task | None = field(default=None, init=False)

    async def start(self) -> None:
        """Start the iFlow Quibbler agent"""
        if self.task is not None:
            return

        # Initialize iFlow client
        iflow_config = load_iflow_auth()
        iflow_config.model = self.config.model
        self.client = IFlowClient(iflow_config)

        self.task = asyncio.create_task(self._run())
        logger.info(f"Started iFlow Quibbler with model: {self.config.model}")
        logger.info(f"Auto-summary: {self.config.enable_auto_summary}")
        logger.info(f"Smart triggers: {self.config.enable_smart_triggers}")

    async def stop(self) -> None:
        """Stop the agent and cleanup"""
        if self.task is None:
            return

        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task

        if self.client:
            await self.client.__aexit__(None, None, None)

        self.task = None
        logger.info("Stopped iFlow Quibbler")

    def _should_process_event(self, evt: dict[str, Any]) -> bool:
        """
        Determine if event should trigger a review (smart filtering).

        Args:
            evt: Hook event dictionary

        Returns:
            True if event should be processed
        """
        if not self.config.enable_smart_triggers:
            return True  # Process all events if smart triggers disabled

        event_type = evt.get("event", "")

        # Always process these critical events
        critical_events = {
            "PostToolUse",  # After tool usage
            "Stop",  # Session end
            "UserPromptSubmit",  # User submitted prompt
        }

        if event_type in critical_events:
            return True

        # For Write/Edit tools, always review
        payload = evt.get("payload", {})
        tool_name = payload.get("tool_name", "")
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            logger.info(f"Processing event due to critical tool: {tool_name}")
            return True

        # Skip other events to reduce noise
        logger.debug(f"Skipping event: {event_type}")
        return False

    async def _query_iflow(self, user_message: str) -> str:
        """
        Send query to iFlow and collect response.

        Args:
            user_message: The user message to send

        Returns:
            Complete assistant response
        """
        if not self.client:
            raise RuntimeError("IFlow client not initialized")

        # Add user message to context
        self.context.add_message("user", user_message)

        # Check if we should summarize
        if self.config.enable_auto_summary and self.context.should_summarize():
            logger.info("Context getting large, creating summary...")
            await self.context.create_summary(self.client)

        # Build messages for API
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context.get_context_messages())

        # Call iFlow API
        response_text = ""
        try:
            async for chunk in self.client.chat_completion(
                messages=messages,
                stream=True,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                if "choices" in chunk:
                    for choice in chunk["choices"]:
                        delta = choice.get("delta", {})
                        if "content" in delta:
                            response_text += delta["content"]
                            logger.debug(f"Received chunk: {delta['content'][:50]}...")

        except Exception as e:
            logger.error(f"Error querying iFlow: {e}", exc_info=True)
            raise

        # Add assistant response to context
        self.context.add_message("assistant", response_text)
        self.context.total_reviews += 1

        logger.info(
            f"Completed review #{self.context.total_reviews}, "
            f"response length: {len(response_text)} chars"
        )

        return response_text

    async def _run(self) -> None:
        """Main agent loop - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _run")


@dataclass
class IFlowQuibblerMCP(IFlowQuibbler):
    """iFlow Quibbler for MCP mode - synchronous reviews"""

    async def review(self, review_request: str) -> str:
        """
        Submit review request and wait for feedback.

        Args:
            review_request: Formatted review request

        Returns:
            Quibbler's feedback
        """
        response_future = asyncio.Future()
        await self.queue.put((review_request, response_future))
        return await response_future

    async def _run(self) -> None:
        """Process MCP review requests"""
        # Create .quibbler directory
        quibbler_dir = Path(self.source_path) / ".quibbler"
        quibbler_dir.mkdir(exist_ok=True)

        # Send startup message
        startup_msg = (
            "Quibbler iFlow session started. You will receive code review requests "
            "AFTER changes are made. Provide concise, actionable feedback."
        )
        try:
            await self._query_iflow(startup_msg)
        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")

        # Process review requests
        try:
            while True:
                review_request, response_future = await self.queue.get()
                try:
                    feedback = await self._query_iflow(review_request)
                    response_future.set_result(feedback)
                except Exception as e:
                    logger.error(f"Error processing review: {e}")
                    response_future.set_exception(e)
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            raise


@dataclass
class IFlowQuibblerHook(IFlowQuibbler):
    """iFlow Quibbler for hook mode - event-driven reviews"""

    session_id: str = field(kw_only=True)

    async def enqueue(self, evt: dict[str, Any]) -> None:
        """Enqueue hook event for processing"""
        await self.queue.put(evt)

    def _format_event(self, evt: dict[str, Any]) -> str:
        """Format hook event for the agent"""
        event_type = evt.get("event", "UnknownEvent")
        ts = evt.get("received_at", datetime.now(timezone.utc).isoformat())
        pretty_json = json.dumps(evt, indent=2, ensure_ascii=False)
        return f"HOOK EVENT: {event_type}\ntime: {ts}\n\n```json\n{pretty_json}\n```"

    async def _run(self) -> None:
        """Process hook events"""
        # Create .quibbler directory and message file
        quibbler_dir = Path(self.source_path) / ".quibbler"
        quibbler_dir.mkdir(exist_ok=True)
        message_file = quibbler_dir / f"{self.session_id}.txt"

        # Update system prompt with message file path
        enhanced_prompt = self.system_prompt.format(message_file=str(message_file))

        # Send startup message
        startup_msg = (
            "Quibbler iFlow hook session started. Watch events and intervene when "
            "you spot issues. Write feedback to the message file."
        )
        try:
            # Use enhanced prompt for startup
            original_prompt = self.system_prompt
            self.system_prompt = enhanced_prompt
            await self._query_iflow(startup_msg)
            self.system_prompt = original_prompt
        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")

        # Process events
        try:
            while True:
                evt = await self.queue.get()
                try:
                    # Check if we should process this event
                    if not self._should_process_event(evt):
                        continue

                    prompt = self._format_event(evt)
                    # Use enhanced prompt
                    original_prompt = self.system_prompt
                    self.system_prompt = enhanced_prompt
                    await self._query_iflow(prompt)
                    self.system_prompt = original_prompt

                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            raise
