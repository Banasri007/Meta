import json
from typing import Dict, List

import requests


BASE_URL = "http://127.0.0.1:7860"


def post(path: str, payload: Dict):
    response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def get(path: str):
    response = requests.get(f"{BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def run_baseline() -> None:
    obs = post("/reset", {})
    inventory: List[Dict] = obs["inventory"]

    # 1) Clean idle storage and test instances.
    for resource in list(inventory):
        is_unattached_volume = resource["category"] == "storage" and not resource["is_attached"]
        is_idle_test = resource["category"] == "compute" and resource["tags"].get("lifecycle") == "idle"
        if is_unattached_volume or is_idle_test:
            post(
                "/step",
                {
                    "action_type": "delete_resource",
                    "resource_id": resource["id"],
                },
            )

    # 2) Right-size low CPU compute to t3.small.
    state = get("/state")
    for resource in state["inventory"]:
        if resource["category"] != "compute":
            continue
        if resource["cpu_usage_pct_30d"] < 5 and resource["resource_type"] != "t3.small":
            post(
                "/step",
                {
                    "action_type": "modify_instance",
                    "instance_id": resource["id"],
                    "new_type": "t3.small",
                },
            )

    # 3) Purchase one compute savings plan for base load.
    post(
        "/step",
        {
            "action_type": "purchase_savings_plan",
            "plan_type": "compute",
            "duration": "1y",
        },
    )

    # 4) Fetch score cards.
    task_ids = ["cleanup_unattached", "rightsize_compute", "fleet_strategy"]
    scoreboard = {task_id: get(f"/tasks/{task_id}/score")["score"] for task_id in task_ids}
    final_state = get("/state")

    print("Baseline scores:")
    print(json.dumps(scoreboard, indent=2))
    print("Final projected monthly bill:", final_state["cost_data"]["projected_monthly_bill"])
    print("Final system latency (ms):", final_state["health_status"]["system_latency_ms"])


if __name__ == "__main__":
    run_baseline()
