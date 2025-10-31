"""LLM client abstractions for different backends"""

import json
import os
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from quibbler.logger import get_logger

logger = get_logger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    async def query(self, prompt: str) -> None:
        """Send a query to the LLM"""
        pass

    @abstractmethod
    async def receive_response(self) -> AsyncIterator[Any]:
        """Receive responses from the LLM"""
        pass

    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass


class AnthropicClient(LLMClient):
    """Wrapper for Claude SDK Client to match our interface"""

    def __init__(self, options: ClaudeAgentOptions):
        self.client = ClaudeSDKClient(options=options)

    async def query(self, prompt: str) -> None:
        await self.client.query(prompt)

    async def receive_response(self) -> AsyncIterator[Any]:
        async for message in self.client.receive_response():
            yield message

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.client.__aexit__(exc_type, exc_val, exc_tb)


class BedrockClient(LLMClient):
    """AWS Bedrock client implementation"""

    def __init__(
        self,
        model: str,
        system_prompt: str,
        cwd: str,
        allowed_tools: list[str],
    ):
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for Bedrock backend. Install with: pip install boto3"
            )

        self.model = model
        self.system_prompt = system_prompt
        self.cwd = cwd
        self.allowed_tools = allowed_tools
        self.bedrock = None
        self.conversation_history = []

        # Map model name to Bedrock model ID if needed
        self.bedrock_model_id = self._map_model_to_bedrock_id(model)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return the result"""
        from pathlib import Path

        if tool_name == "read_file":
            try:
                file_path = tool_input.get("file_path", "")
                full_path = Path(self.cwd) / file_path
                with open(full_path, "r") as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {e}"

        elif tool_name == "write_file":
            try:
                file_path = tool_input.get("file_path", "")
                content = tool_input.get("content", "")
                full_path = Path(self.cwd) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
                return f"Successfully wrote to {file_path}"
            except Exception as e:
                return f"Error writing file: {e}"

        return f"Unknown tool: {tool_name}"

    def _map_model_to_bedrock_id(self, model: str) -> str:
        """Map friendly model names to Bedrock inference profile IDs or model IDs"""
        # If it's already a full ARN, model ID, or inference profile, use as-is
        if (
            model.startswith("anthropic.")
            or model.startswith("arn:")
            or model.startswith("us.")
            or model.startswith("eu.")
            or model.startswith("global.")
        ):
            return model

        # Map common model names to Bedrock global inference profile IDs
        # These work with on-demand throughput across all regions
        model_map = {
            "claude-haiku-4-5": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "claude-sonnet-4-5": "global.anthropic.claude-sonnet-4-5-20250514-v1:0",
            "claude-sonnet-4-5-20250514": "global.anthropic.claude-sonnet-4-5-20250514-v1:0",
            "claude-opus-4": "us.anthropic.claude-opus-4-1-20250805-v1:0",
            "claude-opus-4-1-20250805": "us.anthropic.claude-opus-4-1-20250805-v1:0",
            # Legacy fallbacks for older models
            "claude-sonnet-3-5": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-5-sonnet-20241022": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-5-haiku-20241022": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        }

        return model_map.get(model, model)

    def _convert_tool_to_bedrock_format(self, tool_name: str) -> dict:
        """Convert tool names to Bedrock tool definitions"""
        # Basic tool definitions - can be expanded
        tools = {
            "Read": {
                "name": "read_file",
                "description": "Read contents of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read",
                        }
                    },
                    "required": ["file_path"],
                },
            },
            "Write": {
                "name": "write_file",
                "description": "Write content to a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to write",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        }
        return tools.get(tool_name, {})

    async def __aenter__(self):
        import boto3

        # Initialize Bedrock client
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
        logger.info(f"Initialized Bedrock client with model: {self.bedrock_model_id}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.bedrock = None
        return False

    async def query(self, prompt: str) -> None:
        """Send a query to Bedrock"""
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": prompt})

    async def receive_response(self) -> AsyncIterator[AssistantMessage]:
        """Receive response from Bedrock and yield in Claude SDK format"""
        if not self.bedrock:
            raise RuntimeError("Bedrock client not initialized")

        # Prepare tools
        tools = [
            self._convert_tool_to_bedrock_format(tool) for tool in self.allowed_tools
        ]
        tools = [t for t in tools if t]  # Filter out empty tools

        # Tool execution loop
        while True:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": self.conversation_history,
                "system": self.system_prompt,
            }

            if tools:
                request_body["tools"] = tools

            try:
                # Invoke Bedrock
                response = self.bedrock.invoke_model(
                    modelId=self.bedrock_model_id,
                    body=json.dumps(request_body),
                )

                # Parse response
                response_body = json.loads(response["body"].read())
                content_blocks = response_body.get("content", [])

                # Add assistant response to conversation history
                self.conversation_history.append(
                    {"role": "assistant", "content": content_blocks}
                )

                # Check for tool_use blocks
                tool_use_blocks = [
                    block for block in content_blocks if block.get("type") == "tool_use"
                ]

                if tool_use_blocks:
                    # Execute tools and collect results
                    tool_results = []
                    for tool_block in tool_use_blocks:
                        tool_name = tool_block.get("name")
                        tool_input = tool_block.get("input", {})
                        tool_use_id = tool_block.get("id")

                        # Execute the tool
                        result = self._execute_tool(tool_name, tool_input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result,
                        })

                    # Add tool results to conversation
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results,
                    })

                    # Continue loop to get next response
                    continue

                # No tools used, extract text and yield
                text_blocks = []
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_blocks.append(TextBlock(text=block.get("text", "")))

                if text_blocks:
                    yield AssistantMessage(content=text_blocks, model=self.bedrock_model_id)

                # Done with this turn
                break

            except Exception as e:
                logger.error(f"Bedrock invocation error: {e}")
                raise


@asynccontextmanager
async def create_client(
    backend: str,
    options: ClaudeAgentOptions,
) -> AsyncIterator[LLMClient]:
    """
    Factory function to create the appropriate LLM client based on backend.

    Args:
        backend: Either "anthropic" or "bedrock"
        options: ClaudeAgentOptions for configuration

    Returns:
        An LLMClient instance (either AnthropicClient or BedrockClient)
    """
    if backend == "anthropic":
        client = AnthropicClient(options)
    elif backend == "bedrock":
        client = BedrockClient(
            model=options.model,
            system_prompt=options.system_prompt,
            cwd=options.cwd,
            allowed_tools=options.allowed_tools,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}. Must be 'anthropic' or 'bedrock'")

    async with client as c:
        yield c
