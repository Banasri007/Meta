---
title: FinOps Optimizer
emoji: "💸"
colorFrom: blue
colorTo: green
sdk: docker
tags:
  - openenv
  - finops
  - reinforcement-learning
---

# FinOps Agent Environment (OpenEnv)

## Environment Description

This environment simulates a real cloud operations workflow: monthly FinOps optimization for a mixed production and non-production fleet. The agent acts like a platform/FinOps engineer by removing waste, rightsizing resources, and purchasing savings plans without breaking reliability targets.

This is explicitly **not** a toy game. It models decisions humans perform in cloud cost governance.

## OpenEnv Spec Compliance

- Typed models in `env/models.py`:
  - `Observation` (inventory, cost, health, status message)
  - `Action` (discriminated union of 4 action types)
  - `Reward` (`total`, `action_reward`, `bill_change_reward`)
- Core interface in `env/engine.py`:
  - `reset() -> Observation`
  - `step(action) -> (Observation, Reward, done, info)`
  - `state() -> Observation`
- Metadata in `openenv.yaml`
- HTTP API in `main.py`:
  - `POST /reset`
  - `POST /step`
  - `GET /state`
  - `GET /tasks`
  - `GET /tasks/{task_id}/score`

## Action Space

- `modify_instance(instance_id, new_type)`
- `delete_resource(resource_id)`
- `purchase_savings_plan(plan_type, duration)`
- `tag_resource(resource_id, tag_key, tag_value)`

## Observation Space

- `inventory`: list of compute/storage/database resources
- Utilization signals: `cpu_usage_pct_30d`, `memory_usage_pct_30d`, `network_io_mbps_30d`
- Financial view: `daily_burn_rate`, `projected_monthly_bill`
- Reliability view: `system_latency_ms`, `throttling_events`, `downtime_events`
- Status string: `status_message`

## Reward Function (Dense + Partial Progress)

The reward is trajectory-shaped and meaningful at each step:

- Positive signal for beneficial actions (safe deletions, right-sizing, useful tagging)
- Continuous progress reward from monthly bill reduction (`bill_delta / 200`)
- Penalty for risky/destructive behavior:
  - throttling-inducing downsize penalties
  - production compute deletion penalty
  - blocked production DB deletion with severe negative reward

This gives incremental learning signal instead of only end-of-episode binary reward.

## Tasks With Programmatic Graders

All graders are deterministic functions in `env/tasks.py` and return scores in `[0.0, 1.0]`:

1. `cleanup_unattached` (easy)
   - Objective: delete unattached volumes and idle test instances
2. `rightsize_compute` (medium)
   - Objective: rightsize underutilized compute while keeping latency acceptable
3. `fleet_strategy` (hard)
   - Objective: achieve strong cost reduction + ROI with no downtime events

## Setup

```bash
pip install -r requirements.txt
```

## Run Locally

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

## Validate OpenEnv Submission

```bash
openenv validate
```

## Baseline Inference (Reproducible)

`baseline_inference.py` runs deterministic policies for each task on separate resets and prints all three scores.

```bash
python baseline_inference.py
```

Determinism is controlled by `FINOPS_SEED` (default `42` in this repo).

## Multi-Seed Baseline (Recommended Reporting)

To avoid overfitting concerns from a single fixed seed, run multi-seed evaluation:

```bash
python multi_seed_baseline.py
```

Custom seeds:

```bash
FINOPS_SEEDS=42,43,44,45,46,47 python multi_seed_baseline.py
```

The script reports per-task scores by seed and aggregate `mean/stdev/min/max`.

## LLM Inference Script (OpenAI Client)

`inference.py` uses the official OpenAI client and reads credentials from environment variables.

Required:
- `OPENAI_API_KEY` (or `HF_TOKEN`)

Optional:
- `API_BASE_URL` (default: Hugging Face router)
- `MODEL_NAME`
- `ENV_BASE_URL`
- `FINOPS_TASK`
- `POLICY_SEED`

Run:

```bash
python inference.py
```

## Docker / Hugging Face Spaces

Build:

```bash
docker build -t finops-openenv .
```

Run:

```bash
docker run --rm -p 7860:7860 finops-openenv
```

The provided `Dockerfile` is compatible with Docker-based HF Spaces deployment.
