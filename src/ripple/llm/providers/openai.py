"""OpenAI adapter. Not built: a second provider is added when the pilot needs fallback
(ADR-0027). No SDK dependency until then."""

from ripple.llm.client import CompletionRequest, CompletionResult


class OpenAIClient:
    async def complete(self, request: CompletionRequest) -> CompletionResult:
        raise NotImplementedError(
            "TODO(roadmap Phase 3: provider fallback for the pilot): add the openai SDK via an "
            "ADR and implement structured-output completion."
        )
