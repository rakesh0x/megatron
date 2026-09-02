"""Tests for the core pydantic models."""

from auto_sft.models import Message, RunRecord, RunStatus, Task, Trajectory


def test_task_to_terminal_bench_dict():
    task = Task(
        task_id="example-001",
        description="Find the secret token.",
        instructions="Print the token to stdout.",
        environment={"image": "ubuntu:22.04", "shell": "/bin/bash"},
        verifier={"type": "regex", "pattern": "[a-f0-9]{32}"},
    )
    data = task.to_terminal_bench_dict()
    assert data["id"] == "example-001"
    assert data["category"] == "general"
    assert data["setup"]["pip_packages"] == []


def test_trajectory_to_sft_messages():
    trajectory = Trajectory(
        tool_id="term-1",
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        task_id="example-001",
        messages=[
            Message(role="assistant", content="find /home/user -type f"),
            Message(role="tool", content="token=9f86d081884c7d65", tool_call_id="c1"),
        ],
    )
    messages = trajectory.to_sft_messages()
    assert messages[0] == {"role": "assistant", "content": "find /home/user -type f"}
    assert messages[1]["tool_call_id"] == "c1"


def test_run_record_lifecycle():
    record = RunRecord(task_id="example-001", model_id="Qwen/Qwen2.5-Coder-7B-Instruct")
    assert record.status == RunStatus.PENDING
    record.start()
    assert record.status == RunStatus.RUNNING
    record.finish(success=True)
    assert record.status == RunStatus.SUCCESS
    assert record.finished_at is not None
