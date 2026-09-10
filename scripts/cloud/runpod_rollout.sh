#!/bin/bash
# Turn a fresh RunPod GPU pod into an auto-sft rollout worker:
#   1. serves a quantized Qwen with vLLM (OpenAI-compatible, :8000/v1)
#   2. runs trajectory generation against it
#
# Usage (SSH into the pod, repo cloned at /workspace/auto_sft):
#   MODEL=Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
#   TASK=tasks/dummy_task.yaml \
#   bash scripts/cloud/runpod_rollout.sh
#
# Env overrides: MODEL, PORT (8000), TASK, ATTEMPTS (2), MAX_ITERS (30).
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct-AWQ}"
PORT="${PORT:-8000}"
TASK="${TASK:-tasks/dummy_task.yaml}"
ATTEMPTS="${ATTEMPTS:-2}"
MAX_ITERS="${MAX_ITERS:-30}"
REPO="${REPO:-/workspace/auto_sft}"

echo "==> [1/4] installing vLLM + project"
pip install -q vllm 2>&1 | tail -n 1
cd "$REPO"
pip install -q -e . 2>&1 | tail -n 1 || uv sync -q 2>&1 | tail -n 1

echo "==> [2/4] serving $MODEL on :$PORT"
nohup python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --port "$PORT" \
  --gpu-memory-utilization 0.85 \
  > /tmp/vllm.log 2>&1 &
echo $! > /tmp/vllm.pid

echo "==> [3/4] waiting for server health"
for i in $(seq 1 60); do
  if curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; then
    echo "server up after ~$((i * 5))s"; break
  fi
  sleep 5
done
curl -sf "http://localhost:$PORT/health" >/dev/null \
  || { echo "vLLM failed to start; tail /tmp/vllm.log"; exit 1; }

echo "==> [4/4] running generation against local endpoint"
export OPENHANDS_BASE_URL="http://localhost:$PORT/v1"
export OPENHANDS_LLM_API_KEY="local"
SERVED_ID="$(basename "$MODEL")"
for k in $(seq 0 $((ATTEMPTS - 1))); do
  echo "--- attempt $k/$((ATTEMPTS - 1)) ---"
  auto-sft run-task --task "$TASK" --model "$SERVED_ID" \
    --max-iterations "$MAX_ITERS" \
    --output "artifacts/trajectories/$(basename "$TASK" .yaml)/attempt-$k.json"
done
echo "done. trajectories in $REPO/artifacts/trajectories/"
