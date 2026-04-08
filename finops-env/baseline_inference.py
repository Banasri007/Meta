import json
import os
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = os.getenv("FINOPS_BASE_URL", "https://mahekgupta312006-finops-optimizer.hf.space")


def _create_session_with_retries():
    """Create a requests session with retry strategy."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_session = _create_session_with_retries()


def parse_json_response(response: requests.Response) -> Dict:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Expected object response")
    return payload


def post(path: str, payload: Dict) -> Dict:
    return parse_json_response(_session.post(f"{BASE_URL}{path}", json=payload, timeout=30))


def get(path: str) -> Dict:
    return parse_json_response(_session.get(f"{BASE_URL}{path}", timeout=30))


def _run_cleanup_policy() -> Dict:
    state = post("/reset", {})
    inventory: List[Dict] = state["inventory"]
    for resource in inventory:
        is_unattached_volume = resource["category"] == "storage" and not resource["is_attached"]
        is_idle_test = resource["category"] == "compute" and resource.get("tags", {}).get("lifecycle") == "idle"
        if is_unattached_volume or is_idle_test:
            post("/step", {"action_type": "delete_resource", "resource_id": resource["id"]})
    return get("/state")


def _run_rightsize_policy() -> Dict:
    post("/reset", {})
    state = get("/state")
    for resource in state["inventory"]:
        if resource["category"] == "compute" and resource.get("cpu_usage_pct_30d", 0) < 5.0:
            post(
                "/step",
                {
                    "action_type": "modify_instance",
                    "instance_id": resource["id"],
                    "new_type": "t3.small",
                },
            )
    return get("/state")


def _run_fleet_policy() -> Dict:
    post("/reset", {})
    state = get("/state")
    for resource in state["inventory"]:
        is_safe_delete = (
            (resource["category"] == "storage" and not resource["is_attached"])
            or (resource["category"] == "compute" and resource.get("tags", {}).get("lifecycle") == "idle")
            or (resource.get("is_legacy") and not resource.get("is_production"))
        )
        if is_safe_delete:
            post("/step", {"action_type": "delete_resource", "resource_id": resource["id"]})

    state = get("/state")
    for resource in state["inventory"]:
        if resource["category"] == "compute" and resource.get("cpu_usage_pct_30d", 0) < 5.0:
            post(
                "/step",
                {
                    "action_type": "modify_instance",
                    "instance_id": resource["id"],
                    "new_type": "t3.small",
                },
            )

    post("/step", {"action_type": "purchase_savings_plan", "plan_type": "compute", "duration": "1y"})
    post("/step", {"action_type": "purchase_savings_plan", "plan_type": "database", "duration": "1y"})
    return get("/state")


def run_baseline() -> None:
    print("Starting deterministic FinOps baseline rollout...")
    print("Assumes environment uses FINOPS_SEED (default 42 in this repo).")

    cleanup_state = _run_cleanup_policy()
    cleanup_score = get("/tasks/cleanup_unattached/score")["score"]

    rightsize_state = _run_rightsize_policy()
    rightsize_score = get("/tasks/rightsize_compute/score")["score"]

    fleet_state = _run_fleet_policy()
    fleet_score = get("/tasks/fleet_strategy/score")["score"]

    result = {
        "cleanup_unattached": cleanup_score,
        "rightsize_compute": rightsize_score,
        "fleet_strategy": fleet_score,
        "cleanup_final_bill": cleanup_state["cost_data"]["projected_monthly_bill"],
        "rightsize_final_bill": rightsize_state["cost_data"]["projected_monthly_bill"],
        "fleet_final_bill": fleet_state["cost_data"]["projected_monthly_bill"],
        "fleet_final_latency_ms": fleet_state["health_status"]["system_latency_ms"],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_baseline()