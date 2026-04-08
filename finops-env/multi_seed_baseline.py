import json
import os
import statistics
from typing import Dict, List

from env.engine import FinOpsEngine
from env.models import DeleteResourceAction, ModifyInstanceAction, PurchaseSavingsPlanAction
from env.tasks import get_task_score


def _run_cleanup_policy(env: FinOpsEngine) -> float:
    env.reset()
    for resource in list(env.resources):
        is_unattached_volume = resource.category == "storage" and not resource.is_attached
        is_idle_test = resource.category == "compute" and resource.tags.get("lifecycle") == "idle"
        if is_unattached_volume or is_idle_test:
            env.step(DeleteResourceAction(resource_id=resource.id))
    return get_task_score(env, "cleanup_unattached")


def _run_rightsize_policy(env: FinOpsEngine) -> float:
    env.reset()
    for resource in list(env.resources):
        if resource.category == "compute" and resource.cpu_usage_pct_30d < 5.0:
            env.step(ModifyInstanceAction(instance_id=resource.id, new_type="t3.small"))
    return get_task_score(env, "rightsize_compute")


def _run_fleet_policy(env: FinOpsEngine) -> float:
    env.reset()
    for resource in list(env.resources):
        is_safe_delete = (
            (resource.category == "storage" and not resource.is_attached)
            or (resource.category == "compute" and resource.tags.get("lifecycle") == "idle")
            or (resource.is_legacy and not resource.is_production)
        )
        if is_safe_delete:
            env.step(DeleteResourceAction(resource_id=resource.id))

    for resource in list(env.resources):
        if resource.category == "compute" and resource.cpu_usage_pct_30d < 5.0:
            env.step(ModifyInstanceAction(instance_id=resource.id, new_type="t3.small"))

    env.step(PurchaseSavingsPlanAction(plan_type="compute", duration="1y"))
    env.step(PurchaseSavingsPlanAction(plan_type="database", duration="1y"))
    return get_task_score(env, "fleet_strategy")


def _parse_seeds() -> List[int]:
    seeds_env = os.getenv("FINOPS_SEEDS", "42,43,44,45,46")
    return [int(value.strip()) for value in seeds_env.split(",") if value.strip()]


def main() -> None:
    seeds = _parse_seeds()
    results: Dict[str, List[float]] = {
        "cleanup_unattached": [],
        "rightsize_compute": [],
        "fleet_strategy": [],
    }

    for seed in seeds:
        os.environ["FINOPS_SEED"] = str(seed)
        env = FinOpsEngine()
        results["cleanup_unattached"].append(_run_cleanup_policy(env))
        results["rightsize_compute"].append(_run_rightsize_policy(env))
        results["fleet_strategy"].append(_run_fleet_policy(env))

    summary = {
        "seeds": seeds,
        "scores_by_seed": {
            task: [round(score, 4) for score in task_scores]
            for task, task_scores in results.items()
        },
        "aggregate": {
            task: {
                "mean": round(statistics.mean(task_scores), 4),
                "stdev": round(statistics.pstdev(task_scores), 4),
                "min": round(min(task_scores), 4),
                "max": round(max(task_scores), 4),
            }
            for task, task_scores in results.items()
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
