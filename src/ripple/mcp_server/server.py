"""The MCP server: tool table, schema publication, validate-then-run (ADR-0080).

Built on the SDK's low-level `Server` so that the input schemas on the wire are the
Pydantic models in `schemas.py` (unknown fields refused) and every call is validated
into one of them before an operation runs. Identity is the `BearerIdentity` middleware
(ADR-0081); the operations are `RippleTools`.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mcp.server import Server
from mcp.server.context import ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp.types import (
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)
from pydantic import BaseModel, ValidationError

from ripple.api.services import Services
from ripple.core.retrieval_contract import Retriever
from ripple.mcp_server.identity import BearerIdentity, TokenSource, current_user
from ripple.mcp_server.schemas import (
    AnswerIn,
    AnswerOut,
    ErrorOut,
    ExplainIn,
    ExplainOut,
    ForgetIn,
    ForgetOut,
    QuestionsIn,
    QuestionsOut,
    SaveIn,
    SearchIn,
    SearchOut,
    ToolInput,
    UpdateIn,
    WriteOut,
)
from ripple.mcp_server.tools import RippleTools, ToolCallError
from ripple.storage.users import User

log = logging.getLogger("ripple.mcp_server")

SERVER_NAME = "ripple"
SERVER_VERSION = "0.0.1"
INSTRUCTIONS = (
    "Ripple keeps one user's beliefs consistent: when a fact changes, every belief that "
    "depended on it is re-checked. Search before answering from memory; save facts the "
    "user states; update a memory you can name; never guess what the user did not say. "
    "Flagged results are under review or waiting for the user's answer."
)

Operation = Callable[[RippleTools, User, Any], Awaitable[BaseModel]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[ToolInput]
    output_model: type[BaseModel]
    run: Operation


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "ripple_search",
        "Search the user's memory. Returns visible memories with a relevance score, the "
        "path that found them, citable evidence and an I1 flag; retired memories never "
        "appear, flagged ones only when include_flagged is true.",
        SearchIn,
        SearchOut,
        RippleTools.search,
    ),
    ToolSpec(
        "ripple_save",
        "Save a fact the user stated. Ripple decides whether it is new or updates an "
        "existing memory, links it, and re-checks dependent beliefs. Returns the memory, "
        "the change kind and any questions the re-check parked for the user.",
        SaveIn,
        WriteOut,
        RippleTools.save,
    ),
    ToolSpec(
        "ripple_update",
        "Replace the content of a memory you can name. Writes a new version and re-checks "
        "dependent beliefs. A memory with an open question must be answered instead.",
        UpdateIn,
        WriteOut,
        RippleTools.update,
    ),
    ToolSpec(
        "ripple_forget",
        "Permanently delete a memory, every version of it and every belief derived from "
        "it. Returns the deleted ids. This cannot be undone.",
        ForgetIn,
        ForgetOut,
        RippleTools.forget,
    ),
    ToolSpec(
        "ripple_explain",
        "Why a memory is held: its live parents, its version history, and the decisions "
        "(with reasons and questions) that touched it, plus whether it is visible.",
        ExplainIn,
        ExplainOut,
        RippleTools.explain,
    ),
    ToolSpec(
        "ripple_questions",
        "Questions Ripple is waiting on the user to answer, with the memory each is about.",
        QuestionsIn,
        QuestionsOut,
        RippleTools.questions,
    ),
    ToolSpec(
        "ripple_answer",
        "Relay the user's answer to a pending question: still_holds, no_longer_holds, or "
        "correction with the corrected content.",
        AnswerIn,
        AnswerOut,
        RippleTools.answer,
    ),
)
TOOL_NAMES: tuple[str, ...] = tuple(spec.name for spec in SPECS)


def _success(result: BaseModel) -> CallToolResult:
    data = result.model_dump(mode="json")
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
        structured_content=data,
    )


def _failure(failure: ToolCallError) -> CallToolResult:
    data = ErrorOut(
        error=failure.code,
        detail=failure.detail,
        open_change_event_ids=failure.open_change_event_ids,
    ).model_dump(mode="json", exclude_none=True)
    return CallToolResult(
        content=[TextContent(type="text", text=f"{failure.code}: {failure.detail}")],
        structured_content=data,
        is_error=True,
    )


def _describe(exc: ValidationError) -> str:
    """Field names and messages only: the rejected values are the caller's data."""
    return "; ".join(
        f"{'.'.join(str(part) for part in err['loc']) or 'arguments'}: {err['msg']}"
        for err in exc.errors()
    )


def build_server(
    services: Services,
    retriever: Retriever,
    token_source: TokenSource,
    *,
    name: str = SERVER_NAME,
) -> Server[Any]:
    tools = RippleTools(services, retriever)
    specs = {spec.name: spec for spec in SPECS}

    async def list_tools(
        ctx: ServerRequestContext[Any, Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name=spec.name,
                    description=spec.description,
                    input_schema=spec.input_model.model_json_schema(),
                    output_schema=spec.output_model.model_json_schema(),
                )
                for spec in SPECS
            ]
        )

    async def call_tool(
        ctx: ServerRequestContext[Any, Any], params: CallToolRequestParams
    ) -> CallToolResult:
        spec = specs.get(params.name)
        if spec is None:
            raise MCPError(INVALID_PARAMS, f"unknown tool {params.name!r}")
        user = current_user()
        try:
            arguments = spec.input_model.model_validate(params.arguments or {})
        except ValidationError as exc:
            return _failure(ToolCallError("invalid_arguments", _describe(exc)))
        try:
            return _success(await spec.run(tools, user, arguments))
        except ToolCallError as failure:
            return _failure(failure)
        except MCPError:
            raise
        except Exception as exc:
            # The message may quote a provider or the user's content: it stays in the log.
            log.exception("tool failed", extra={"tool": spec.name, "user_id": user.id})
            return _failure(
                ToolCallError("internal_error", f"{type(exc).__name__}; see server logs")
            )

    def input_schema(tool_name: str) -> dict[str, Any] | None:
        spec = specs.get(tool_name)
        return None if spec is None else spec.input_model.model_json_schema()

    server: Server[Any] = Server(
        name,
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
        get_tool_input_schema=input_schema,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
    server.middleware.append(BearerIdentity(services.user_store, token_source))
    return server
