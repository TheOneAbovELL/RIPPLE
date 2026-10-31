"""FakeLLM: scripted responses and a call log, so router and agent tests run offline."""

from collections import deque

from ripple.llm.client import CompletionRequest, CompletionResult


class FakeLLM:
    """Replays scripted responses in order.

    A script item is either the text to return or an exception to raise, which lets a
    test simulate invalid JSON, a schema miss or a provider outage.
    """

    def __init__(self, *script: str | Exception, model: str = "fake-model") -> None:
        self._script: deque[str | Exception] = deque(script)
        self._model = model
        self.calls: list[CompletionRequest] = []

    def script(self, *items: str | Exception) -> None:
        self._script.extend(items)

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls.append(request)
        if not self._script:
            raise AssertionError("FakeLLM ran out of scripted responses")
        item = self._script.popleft()
        if isinstance(item, Exception):
            raise item
        return CompletionResult(
            text=item,
            model=request.model,
            input_tokens=len(" ".join(m.content for m in request.messages).split()),
            output_tokens=len(item.split()),
        )
