"""LLM provider interface. Application code talks to models only through this."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class LLMMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class LLMResponse:
    text: str
    # Parsed structured output when a JSON schema was requested.
    data: dict[str, Any] | None = None
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(Protocol):
    def complete(
        self,
        *,
        task: str,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """`task` (e.g. "interview", "extract") selects the configured model for that task."""
        ...

    def stream(
        self, *, task: str, system: str, messages: list[LLMMessage], max_tokens: int = 1024
    ) -> Iterator[str]: ...


def get_llm_provider() -> LLMProvider:
    from katra.config import get_settings

    name = get_settings().llm_provider
    if name == "fake":
        from katra.providers.llm.fake import FakeLLMProvider

        return FakeLLMProvider()
    # The Anthropic provider arrives in M4.
    raise ValueError(f"Unknown LLM provider: {name}")
