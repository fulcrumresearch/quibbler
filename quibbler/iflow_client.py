#!/usr/bin/env python3
"""
iFlow API client with automatic token authentication.

This module handles communication with iFlow's API, automatically
reading authentication tokens from ~/.iflow/settings.json or environment
variables, eliminating the need for manual API key configuration.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Literal

import httpx

from quibbler.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IFlowConfig:
    """Configuration for iFlow API client"""

    api_key: str
    base_url: str = "https://apis.iflow.cn/v1"
    model: str = "claude-haiku-4-5"
    auth_type: Literal["iflow", "openai-compatible"] = "iflow"


def load_iflow_auth() -> IFlowConfig:
    """
    Load iFlow authentication from multiple sources in priority order:

    1. Environment variables (IFLOW_API_KEY, IFLOW_BASE_URL, etc.)
    2. ~/.iflow/settings.json (user-level config)
    3. ./.iflow/settings.json (project-level config)

    Returns:
        IFlowConfig with authentication credentials

    Raises:
        ValueError: If no authentication credentials found
    """
    # Try environment variables first
    env_api_key = os.getenv("IFLOW_API_KEY")
    if env_api_key:
        logger.info("Using iFlow credentials from environment variables")
        return IFlowConfig(
            api_key=env_api_key,
            base_url=os.getenv("IFLOW_BASE_URL", "https://apis.iflow.cn/v1"),
            model=os.getenv("IFLOW_MODEL", "claude-haiku-4-5"),
            auth_type=os.getenv("IFLOW_AUTH_TYPE", "iflow"),  # type: ignore
        )

    # Try user-level settings file
    user_settings = Path.home() / ".iflow" / "settings.json"
    if user_settings.exists():
        try:
            with open(user_settings) as f:
                data = json.load(f)
                api_key = data.get("apiKey")
                if api_key:
                    logger.info(f"Loaded iFlow credentials from {user_settings}")
                    return IFlowConfig(
                        api_key=api_key,
                        base_url=data.get("baseUrl", "https://apis.iflow.cn/v1"),
                        model=data.get("modelName", "claude-haiku-4-5"),
                        auth_type=data.get("selectedAuthType", "iflow"),  # type: ignore
                    )
        except Exception as e:
            logger.warning(f"Failed to load iFlow settings from {user_settings}: {e}")

    # Try project-level settings file
    project_settings = Path.cwd() / ".iflow" / "settings.json"
    if project_settings.exists():
        try:
            with open(project_settings) as f:
                data = json.load(f)
                api_key = data.get("apiKey")
                if api_key:
                    logger.info(f"Loaded iFlow credentials from {project_settings}")
                    return IFlowConfig(
                        api_key=api_key,
                        base_url=data.get("baseUrl", "https://apis.iflow.cn/v1"),
                        model=data.get("modelName", "claude-haiku-4-5"),
                        auth_type=data.get("selectedAuthType", "iflow"),  # type: ignore
                    )
        except Exception as e:
            logger.warning(
                f"Failed to load iFlow settings from {project_settings}: {e}"
            )

    raise ValueError(
        "No iFlow authentication found. Please either:\n"
        "1. Set IFLOW_API_KEY environment variable, or\n"
        "2. Log in using `iflow auth login`, or\n"
        "3. Create ~/.iflow/settings.json with your API key"
    )


class IFlowClient:
    """
    Async client for iFlow API with automatic authentication.

    Features:
    - Automatic token loading from settings
    - Streaming responses
    - Context-efficient message management
    """

    def __init__(self, config: IFlowConfig | None = None):
        """
        Initialize iFlow client.

        Args:
            config: Optional IFlowConfig. If not provided, loads from environment/settings.
        """
        self.config = config or load_iflow_auth()
        self.client = httpx.AsyncClient(timeout=300.0)
        logger.info(
            f"Initialized iFlow client: base_url={self.config.base_url}, "
            f"model={self.config.model}, auth_type={self.config.auth_type}"
        )

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup"""
        await self.client.aclose()

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Send chat completion request to iFlow API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to stream responses (default: True)
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum tokens in response (default: 4096)

        Yields:
            Response chunks (if streaming) or complete response
        """
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"Sending chat completion request to {url}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

        try:
            async with self.client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()

                if stream:
                    # Handle streaming response
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                yield chunk
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse chunk: {data}")
                                continue
                else:
                    # Handle non-streaming response
                    response_data = await response.json()
                    yield response_data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from iFlow API: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error calling iFlow API: {e}", exc_info=True)
            raise

    async def simple_query(self, system_prompt: str, user_message: str) -> str:
        """
        Simple synchronous query to iFlow API.

        Args:
            system_prompt: System prompt for the assistant
            user_message: User message to send

        Returns:
            Complete assistant response as string
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response_text = ""
        async for chunk in self.chat_completion(messages, stream=True):
            if "choices" in chunk:
                for choice in chunk["choices"]:
                    delta = choice.get("delta", {})
                    if "content" in delta:
                        response_text += delta["content"]

        return response_text
