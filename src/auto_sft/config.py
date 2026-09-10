"""Typed configuration models and YAML loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class SplitConfig(BaseModel):
    train: float = 0.70
    validation: float = 0.15
    test: float = 0.15

    @model_validator(mode="after")
    def _sums_to_one(self) -> SplitConfig:
        total = self.train + self.validation + self.test
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"split proportions must sum to 1.0, got {total}")
        return self


class PipelineConfig(BaseModel):
    name: str = "terminal-bench-sft-v1"
    seed: int = 42
    tasks_dir: str = "tasks"
    output_dir: str = "artifacts"
    overwrite: bool = False
    splits: SplitConfig = Field(default_factory=SplitConfig)


class ModelConfig(BaseModel):
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    revision: str = "main"
    dtype: Literal["float32", "float16", "bfloat16"] = "bfloat16"
    trust_remote_code: bool = False
    local_path: str | None = None


class GenerationConfig(BaseModel):
    num_attempts: int = 4
    temperature: float = 0.7
    top_p: float = 0.95
    max_tokens: int = 1024
    max_steps: int = 30
    timeout_seconds: int = 300
    # Rollout model: LiteLLM id used by the agent harness. Defaults to the
    # fine-tune base model (self-distillation); override for a teacher model
    # (e.g. "openrouter/z-ai/glm-5.2:free") or local Ollama ("ollama/...").
    model: str | None = None
    # Endpoint override; defaults to OPENHANDS_BASE_URL env (auto localhost
    # for ollama/ models). Cloud GPU vLLM URL goes here.
    base_url: str | None = None
    # Env var holding the rollout API key (unset = keyless, e.g. Ollama).
    api_key_env: str = "OPENHANDS_LLM_API_KEY"


class LoraConfig(BaseModel):
    enabled: bool = True
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list[str] = Field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )


class TrainingConfig(BaseModel):
    # Objective: "sft" (supervised, behavior cloning on successes),
    # "dpo" (preference learning on success-vs-failure pairs),
    # "grpo" (online RL scored by task verifiers).
    method: Literal["sft", "dpo", "grpo"] = "sft"
    # Scan trajectories for unsafe content (secrets, destructive commands)
    # and drop flagged examples before training.
    safety_scan: bool = False
    output_dir: str = "artifacts/trained-model"
    num_epochs: int = 2
    per_device_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2.0e-4
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.03
    max_seq_length: int = 2048
    logging_steps: int = 10
    save_steps: int = 500
    lora: LoraConfig = Field(default_factory=LoraConfig)
    qlora: bool = False
    use_peft: bool = True
    # DPO-only: KL strength against the reference model.
    dpo_beta: float = 0.1
    # GRPO-only: generations sampled per prompt per update.
    grpo_num_generations: int = 8


class CloudConfig(BaseModel):
    provider: str = "local"
    gpu: str = "A100-80GB"
    num_gpus: int = 1
    timeout_hours: int = 24
    extra: dict[str, Any] = Field(default_factory=dict)


class StorageConfig(BaseModel):
    type: Literal["local", "s3"] = "local"
    base_dir: str = "artifacts"
    bucket: str | None = None
    prefix: str = "auto-sft"

    @model_validator(mode="after")
    def _require_bucket_for_s3(self) -> StorageConfig:
        if self.type == "s3" and not self.bucket:
            raise ValueError("storage.bucket is required when storage.type == 's3'")
        return self


class AppConfig(BaseModel):
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    cloud: CloudConfig = Field(default_factory=CloudConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @field_validator("model", mode="before")
    @classmethod
    def _allow_flat_model(cls, value: Any) -> Any:
        """Allow `model: Qwen/...` shorthand in YAML."""
        if isinstance(value, str):
            return {"base_model": value}
        return value


def load_config(path: str | Path) -> AppConfig:
    """Load an :class:`AppConfig` from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {p}")
    raw = yaml.safe_load(p.read_text()) or {}
    return AppConfig.model_validate(raw)


def dump_config(config: AppConfig, path: str | Path) -> None:
    """Serialize an :class:`AppConfig` to a YAML file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(config.model_dump(), sort_keys=False))
