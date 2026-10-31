from collections import deque
from collections.abc import Iterator
from typing import Any

from katra.providers.llm.base import LLMMessage, LLMResponse


class FakeLLMProvider:
    """Deterministic provider for tests and offline demos.

    Queue scripted responses with `push`; otherwise it echoes the last user message.
    """

    def __init__(self) -> None:
        self.scripted: deque[LLMResponse] = deque()
        self.calls: list[dict[str, Any]] = []

    def push(self, text: str = "", data: dict[str, Any] | None = None) -> None:
        self.scripted.append(LLMResponse(text=text, data=data))

    def complete(
        self,
        *,
        task: str,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.calls.append({"task": task, "system": system, "messages": messages})
        if self.scripted:
            return self.scripted.popleft()
        last = messages[-1].content if messages else ""
        return LLMResponse(text=f"[fake:{task}] {last}", data={} if json_schema else None)

    def stream(
        self, *, task: str, system: str, messages: list[LLMMessage], max_tokens: int = 1024
    ) -> Iterator[str]:
        yield from self.complete(task=task, system=system, messages=messages).text.split(" ")
