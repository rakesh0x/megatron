"""Agent harness: run tasks with OpenHands agents, collect trajectories.

Entry point is :func:`run_task`, which executes a single :class:`Task`
in a local workspace with the default OpenHands agent and converts the
recorded SDK events into our :class:`Trajectory` model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auto_sft.models.trajectory import Message, ToolCall, ToolOutput, Trajectory


def _text_of_llm_message(llm_message: Any) -> tuple[str, str]:
    """Extract (role, text) from an SDK LLM message, defensively."""
    role = getattr(llm_message, "role", "assistant")
    content = getattr(llm_message, "content", "")
    if isinstance(content, str):
        return str(role), content
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
            continue
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return str(role), "\n".join(parts)


def events_to_trajectory(
    events: list[Any],
    *,
    task_id: str,
    model_id: str,
    attempt: int = 0,
    tool_id: str = "openhands-default",
) -> Trajectory:
    """Convert recorded SDK events into a :class:`Trajectory`."""
    messages: list[Message] = []
    pending_outputs: list[ToolOutput] = []
    raw: list[dict[str, Any]] = []
    counter = 0

    for event in events:
        kind = type(event).__name__
        try:
            raw.append({"type": kind, **event.model_dump(mode="json")})
        except Exception:  # noqa: BLE001 - never let tracing break conversion
            raw.append({"type": kind, "repr": repr(event)})

        llm_message = getattr(event, "llm_message", None)
        if llm_message is not None and "Message" in kind:
            role, text = _text_of_llm_message(llm_message)
            if role not in ("system", "user", "assistant", "tool"):
                role = "assistant"
            messages.append(Message(role=role, content=text))  # type: ignore[arg-type]
            continue

        if "Action" in kind:
            counter += 1
            action = getattr(event, "action", None)
            payload = (
                action.model_dump(mode="json")
                if hasattr(action, "model_dump")
                else {"repr": repr(action)}
            )
            messages.append(
                Message(
                    role="assistant",
                    content=f"<tool:{kind}>",
                    tool_calls=[
                        ToolCall(
                            id=f"call-{counter}",
                            name=kind,
                            arguments=json.dumps(payload)[:4000],
                        )
                    ],
                )
            )
            continue

        if "Observation" in kind:
            obs = getattr(event, "observation", None)
            content = getattr(obs, "content", None) or getattr(event, "content", None)
            if not isinstance(content, str):
                content = repr(content)
            pending_outputs.append(
                ToolOutput(tool_call_id=f"call-{counter}", content=content[:8000])
            )
            messages.append(
                Message(role="tool", content=content[:8000], tool_call_id=f"call-{counter}")
            )

    return Trajectory(
        tool_id=tool_id,
        model_id=model_id,
        task_id=task_id,
        attempt=attempt,
        messages=messages,
        metadata={"event_count": len(events), "raw_events": raw},
    )


def run_task(
    task: Any,
    *,
    model: str,
    workspace: str | Path,
    attempt: int = 0,
    max_iterations: int = 30,
    api_key: str | None = None,
    base_url: str | None = None,
) -> Trajectory:
    """Run one task with the default OpenHands agent; return the trajectory."""
    import os

    from openhands.sdk import LLM, LocalConversation
    from openhands.tools import get_default_agent

    # Pick credentials matching the model provider: a bare "gpt-..." id
    # routes to OpenAI, so it must NOT receive the OpenRouter key, etc.
    provider_keys = [
        ("openrouter/", ["OPENROUTER_API_KEY"]),
        ("gpt-", ["OPENAI_API_KEY"]),
        ("o1", ["OPENAI_API_KEY"]),
        ("o3", ["OPENAI_API_KEY"]),
        ("openai/", ["OPENAI_API_KEY"]),
        ("claude-", ["ANTHROPIC_AUTH_TOKEN"]),
        ("anthropic/", ["ANTHROPIC_AUTH_TOKEN"]),
        ("ollama/", []),  # local server needs no key
    ]
    key = api_key or os.environ.get("OPENHANDS_LLM_API_KEY") or os.environ.get("LLM_API_KEY")
    if key is None:
        for prefix, names in provider_keys:
            if model.startswith(prefix):
                for name in names:
                    if os.environ.get(name):
                        key = os.environ[name]
                        break
                break
    llm_kwargs: dict[str, Any] = {"model": model}
    if key:
        llm_kwargs["api_key"] = key
    url = base_url or os.environ.get("OPENHANDS_BASE_URL")
    if not url and model.startswith("ollama/"):
        url = "http://localhost:11434"
    if url:
        llm_kwargs["base_url"] = url
    llm = LLM(**llm_kwargs)
    agent = get_default_agent(llm)

    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)

    collected: list[Any] = []
    conversation = LocalConversation(
        agent=agent,
        workspace=str(ws),
        callbacks=[collected.append],
        max_iteration_per_run=max_iterations,
    )
    prompt = f"# {task.task_id}\n\n{task.description}\n\n{task.instructions}"
    if getattr(task, "starting_state", ""):
        prompt += f"\n\n## Starting state\n{task.starting_state}"
    try:
        conversation.send_message(prompt)
        conversation.run()
    finally:
        conversation.close()

    return events_to_trajectory(
        collected, task_id=task.task_id, model_id=model, attempt=attempt
    )
