"""Process-local passive observation: callbacks + final OpenAI SDK arguments."""

import functools
import time

REQUEST_FIELDS = {
    "model",
    "input",
    "messages",
    "instructions",
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    "max_output_tokens",
    "max_completion_tokens",
    "max_tokens",
    "temperature",
    "top_p",
    "stream",
    "reasoning",
    "text",
    "previous_response_id",
    "truncation",
    "store",
    "include",
}


def observe_create(original, recorder, route):
    @functools.wraps(original)
    async def create(client, *args, **kwargs):
        if args:
            raise SystemExit(
                "Unexpected SDK positional arguments; telemetry unavailable"
            )
        request_id = recorder.emit(
            "sdk_request",
            {
                "route": route,
                "payload": {
                    key: value for key, value in kwargs.items() if key in REQUEST_FIELDS
                },
            },
        )
        started = time.monotonic()
        try:
            result = await original(client, *args, **kwargs)
        except BaseException as exc:
            recorder.emit(
                "sdk_error",
                {
                    "request_id": request_id,
                    "type": type(exc).__name__,
                    "seconds": time.monotonic() - started,
                },
            )
            raise
        if kwargs.get("stream") is True:
            result._goop_observer_request_id = request_id
        else:
            recorder.emit(
                "sdk_response",
                {
                    "request_id": request_id,
                    "response": result,
                    "seconds": time.monotonic() - started,
                },
            )
        return result

    return create


def observe_iterator(original, recorder):
    async def iterate(stream):
        request_id = getattr(stream, "_goop_observer_request_id", None)
        async for event in original(stream):
            if request_id is not None:
                kind = getattr(event, "type", None)
                if kind in {
                    "response.completed",
                    "response.incomplete",
                    "response.failed",
                }:
                    recorder.emit(
                        "sdk_response", {"request_id": request_id, "event": event}
                    )
                elif kind == "response.output_text.done":
                    recorder.emit(
                        "public_text",
                        {"request_id": request_id, "text": getattr(event, "text", "")},
                    )
                elif getattr(event, "object", None) == "chat.completion.chunk":
                    # Chat fallback: only usage and public text/tool deltas, never reasoning.
                    choices = [
                        {
                            "index": c.index,
                            "text": c.delta.content,
                            "tool_calls": c.delta.tool_calls,
                            "finish_reason": c.finish_reason,
                        }
                        for c in event.choices
                    ]
                    recorder.emit(
                        "chat_public_delta",
                        {
                            "request_id": request_id,
                            "choices": choices,
                            "usage": event.usage,
                        },
                    )
            yield event

    return iterate


def install(recorder, cell):
    from code_puppy import config
    from code_puppy.callbacks import register_callback
    from openai import AsyncStream
    from openai.resources.chat.completions import AsyncCompletions
    from openai.resources.responses import AsyncResponses

    AsyncResponses.create = observe_create(AsyncResponses.create, recorder, "responses")
    AsyncCompletions.create = observe_create(AsyncCompletions.create, recorder, "chat")
    AsyncStream.__aiter__ = observe_iterator(AsyncStream.__aiter__, recorder)

    def pre_tool(tool_name, tool_args, context=None):
        recorder.emit(
            "tool_start",
            {
                "name": tool_name,
                "args": tool_args,
                "call_id": getattr(context, "tool_call_id", None),
            },
        )

    def post_tool(tool_name, tool_args, result, duration_ms, context=None):
        recorder.emit(
            "tool_end",
            {
                "name": tool_name,
                "args": tool_args,
                "result": result,
                "duration_ms": duration_ms,
                "call_id": getattr(context, "tool_call_id", None),
            },
        )
        recorder.snapshot_sources(cell)

    def pre_compact(agent_name, strategy, message_count, token_count):
        recorder.emit(
            "pre_compact",
            {
                "agent": agent_name,
                "strategy": strategy,
                "messages": message_count,
                "tokens": token_count,
            },
        )

    register_callback("pre_tool_call", pre_tool)
    register_callback("post_tool_call", post_tool)
    register_callback("pre_compact", pre_compact)
    # Display/storage only: no alteration of in-memory model messages or requests.
    config.get_auto_save_session = lambda: False
    register_callback("thinking_display_filter", lambda text, **kwargs: "")
    recorder.emit(
        "observer_installed",
        {
            "sdk_boundary": True,
            "callback_results_may_precede_or_follow_spill": True,
            "private_reasoning_stored": False,
            "autosave_disabled_for_this_process": True,
            "instructions_or_tool_results_modified": False,
        },
    )
