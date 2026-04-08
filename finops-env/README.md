# FinOps Agent Environment (OpenEnv)

## Description And Motivation

Cloud cost optimization (FinOps) is a real operational workflow in companies running production infrastructure. This environment simulates decisions a FinOps engineer makes daily: deleting idle resources, rightsizing underutilized compute, and purchasing savings plans while protecting latency and uptime.

## Action Space

- `modify_instance(instance_id, new_type)`
- `delete_resource(resource_id)`
- `purchase_savings_plan(plan_type, duration)`
- `tag_resource(resource_id, tag_key, tag_value)`

These are implemented as typed Pydantic models in `env/models.py`.

## Observation Space

- `inventory`: compute, database, and storage resources
- 30-day metrics: `cpu_usage_pct_30d`, `memory_usage_pct_30d`, `network_io_mbps_30d`
- cost view: `daily_burn_rate`, `projected_monthly_bill`
- health view: `system_latency_ms`, throttling count, downtime count

## Reward Model

Reward is continuous and shaped over the full trajectory.

- Positive reward for deleting idle resources and cost reduction
- Penalty for risky downsizing that causes throttling
- Critical penalty for attempted production DB deletion
- Progress signal from projected monthly bill delta each step

Reward is represented by a typed Pydantic `Reward` model (`total`, `action_reward`, `bill_change_reward`).

## Tasks And Difficulty

- `cleanup_unattached` (easy): delete unattached volumes and idle test instances
- `rightsize_compute` (medium): rightsize low-utilization compute while preserving latency
- `fleet_strategy` (hard): combine decommissioning, rightsizing, and savings plans for ROI

Programmatic graders are implemented in `env/tasks.py` and each task score is normalized to `[0.0, 1.0]`.

## API Surface (OpenEnv)

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /tasks`
- `GET /tasks/{task_id}/score`

## Setup And Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

Run baseline policy:

```bash
python baseline_inference.py
```

Run OpenAI-driven inference policy:

```bash
python inference.py
```

Required environment variables for `inference.py`:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN` (or `OPENAI_API_KEY`)
- `ENV_BASE_URL`

## Baseline Scores (Latest Run)

Example output from `baseline_inference.py`:

- `cleanup_unattached`: `1.00`
- `rightsize_compute`: `1.00`
- `fleet_strategy`: `1.00`

Note: scores vary slightly because the environment includes randomized initial utilization values.

## Containerization

- `Dockerfile` included for HF Space deployment
- `.dockerignore` included for smaller and cleaner builds

## Project Structure

- `main.py`: FastAPI entrypoint
- `openenv.yaml`: environment metadata and tasks
- `env/models.py`: typed Action/Observation/Reward models
- `env/engine.py`: transition and reward logic (`step`, `reset`, `get_observation`)
- `env/tasks.py`: task definitions and graders
- `baseline_inference.py`: deterministic baseline across all tasks
- `inference.py`: OpenAI-client policy runner with structured logs
