from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic_ai import Agent

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OutputT = TypeVar("OutputT")


def model_name() -> str:
    explicit = os.getenv("PR_BOT_MODEL")
    if explicit:
        return explicit
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY is not set (add it to .env)")
    return "anthropic:claude-haiku-4-5"


def _anthropic_model_id(model: str) -> str:
    prefix = "anthropic:"
    return model[len(prefix) :] if model.startswith(prefix) else model


@lru_cache(maxsize=32)
def create_agent(system_prompt: str, output_type: type[OutputT]) -> Agent[None, OutputT]:
    model = model_name()
    workspace_id = os.getenv("ANTHROPIC_WORKSPACE_ID")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if workspace_id and api_key and model.startswith("anthropic:"):
        from anthropic import AsyncAnthropic
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        client = AsyncAnthropic(
            api_key=api_key,
            default_headers={"anthropic-workspace-id": workspace_id},
        )
        provider = AnthropicProvider(anthropic_client=client)
        anthropic_model = AnthropicModel(_anthropic_model_id(model), provider=provider)
        return Agent(anthropic_model, output_type=output_type, system_prompt=system_prompt)

    return Agent(model, output_type=output_type, system_prompt=system_prompt)
