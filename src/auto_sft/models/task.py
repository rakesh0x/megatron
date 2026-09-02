"""Task model mirroring the fields specified in the implementation plan.

A task carries:
  1. Task ID
  2. Task description and instructions
  3. Environment
  4. Required dependencies
  5. Starting state
  6. Terminal or tool interface
  7. Verifier
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VerifierSpec(BaseModel):
    """Specification for the task verifier.

    ``type`` selects the verifier strategy:

    - ``regex``: match ``pattern`` against the final agent output. ``success_on``
      is ``match`` (default) or ``no_match``.
    - ``command``: run ``command`` in the task environment; exit code 0 means
      success (or the opposite when ``success_on == "nonzero"``).
    - ``script``: run ``script`` (a shell script body) in the task environment;
      exit code 0 means success.
    """

    type: Literal["regex", "command", "script"] = "regex"
    pattern: str | None = None
    command: str | None = None
    script: str | None = None
    success_on: Literal["match", "no_match", "zero", "nonzero"] = "match"
    timeout_seconds: int = 60


class Task(BaseModel):
    task_id: str
    description: str
    instructions: str = ""
    environment: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    starting_state: str = ""
    interface: Literal["terminal", "tool"] = "terminal"
    verifier: VerifierSpec = Field(default_factory=VerifierSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_terminal_bench_dict(self) -> dict[str, Any]:
        """Convert to a dict compatible with the terminal-bench task format.

        https://github.com/terminal-bench-hq/terminal-bench
        """
        return {
            "id": self.task_id,
            "category": self.metadata.get("category", "general"),
            "description": self.description,
            "instructions": [self.instructions] if self.instructions else [],
            "setup": {
                "pip_packages": self.dependencies,
                "github_repo": self.metadata.get("github_repo"),
                "files": self.metadata.get("files", {}),
            },
            "source": self.metadata.get("source", "auto_sft"),
        }
