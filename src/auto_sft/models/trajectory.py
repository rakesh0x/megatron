"""Trajectory model mirroring the fields specified in the implementation plan.

Every trajectory records:
  1. Tool ID
  2. Model ID
  3. Model conversation
  4. Tool calls
  5. Tool output
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    role: Role
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: str


class ToolOutput(BaseModel):
    tool_call_id: str
    content: str


class Trajectory(BaseModel):
    """A single agent run against a task.

    ``tool_id`` identifies the environment/tool interface used (e.g. the
    terminal session id or tool name). ``model_id`` identifies the model that
    produced the trajectory.
    """

    tool_id: str
    model_id: str
    task_id: str
    attempt: int = 0
    messages: list[Message] = Field(default_factory=list)
    reward: float | None = None
    verified: bool | None = None
    success: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def conversation(self) -> list[dict[str, Any]]:
        """Return the message list as plain dicts (JSON-serializable)."""
        return [m.model_dump(exclude_none=True) for m in self.messages]

    def to_sft_messages(self) -> list[dict[str, Any]]:
        """Return the successful behavior as chat messages for SFT.

        Only the *successful* behavior is training data here — the task itself
        is not part of the SFT example.
        """
        return self.conversation()


Message.model_rebuild()
