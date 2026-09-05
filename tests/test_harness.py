"""Tests for the harness event converter (no LLM calls)."""

from types import SimpleNamespace

from auto_sft.harness import events_to_trajectory


class FakeMessageEvent:
    def __init__(self, role, text):
        self.llm_message = SimpleNamespace(role=role, content=text)

    def model_dump(self, mode="json"):
        return {"llm_message": {"role": "x", "content": "y"}}


def test_events_to_trajectory_maps_messages():
    events = [
        FakeMessageEvent("user", "do the thing"),
        FakeMessageEvent("assistant", "on it"),
    ]
    # Patch class names so the converter recognises them.
    FakeMessageEvent.__name__ = "MessageEvent"
    try:
        traj = events_to_trajectory(events, task_id="dummy-001", model_id="test-model")
    finally:
        FakeMessageEvent.__name__ = "FakeMessageEvent"
    assert traj.task_id == "dummy-001"
    assert [m.content for m in traj.messages] == ["do the thing", "on it"]
    assert traj.metadata["event_count"] == 2


def test_events_to_trajectory_empty():
    traj = events_to_trajectory([], task_id="dummy-001", model_id="test-model")
    assert traj.messages == []
