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


def run_baseline() -> None:
    print("Starting FinOps baseline rollout...")
    state = post("/reset", {})
    print(f"Initial projected monthly bill: ${state['cost_data']['projected_monthly_bill']}")

    inventory: List[Dict] = state["inventory"]

    # Easy: remove unattached storage + idle test instances.
    for resource in inventory:
        is_unattached_volume = resource["category"] == "storage" and not resource["is_attached"]
        is_idle_test = resource["category"] == "compute" and resource.get("tags", {}).get("lifecycle") == "idle"
        if is_unattached_volume or is_idle_test:
            post("/step", {"action_type": "delete_resource", "resource_id": resource["id"]})

    # Medium: right-size all low-utilization compute nodes.
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

    # Hard: remove legacy non-prod and buy baseline coverage plans.
    state = get("/state")
    for resource in state["inventory"]:
        if resource.get("is_legacy") and not resource.get("is_production"):
            post("/step", {"action_type": "delete_resource", "resource_id": resource["id"]})

    post("/step", {"action_type": "purchase_savings_plan", "plan_type": "compute", "duration": "1y"})
    post("/step", {"action_type": "purchase_savings_plan", "plan_type": "database", "duration": "1y"})

    score_cleanup = get("/tasks/cleanup_unattached/score")["score"]
    score_rightsize = get("/tasks/rightsize_compute/score")["score"]
    score_fleet = get("/tasks/fleet_strategy/score")["score"]
    final_state = get("/state")

    result = {
        "cleanup_unattached": score_cleanup,
        "rightsize_compute": score_rightsize,
        "fleet_strategy": score_fleet,
        "final_projected_bill": final_state["cost_data"]["projected_monthly_bill"],
        "final_latency_ms": final_state["health_status"]["system_latency_ms"],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_baseline()