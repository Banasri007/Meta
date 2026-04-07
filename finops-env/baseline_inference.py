import json
import os

import requests


# Set this to your HF Space API URL, not the huggingface.co/spaces page.
# Example: https://mahekgupta312006-finops-optimizer.hf.space
BASE_URL = os.getenv("FINOPS_BASE_URL", "https://mahekgupta312006-finops-optimizer.hf.space")


def parse_json_response(response: requests.Response):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"HTTP {response.status_code} calling {response.url}: {response.text[:300]}"
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Expected JSON from {response.url}, but got: {response.text[:300] or '<empty response>'}"
        ) from exc

def run_baseline():
    print("🚀 Starting FinOps Agent Baseline...")
    
    # 1. Reset the environment
    print("\n--- Resetting Environment ---")
    res = requests.post(f"{BASE_URL}/reset", timeout=30)
    obs = parse_json_response(res)
    print(f"Initial Monthly Bill: ${obs['cost_data']['projected_monthly_bill']}")

    # 2. Perform 'Easy Task' - Delete unattached volumes
    print("\n--- Task 1: Deleting Unattached Volumes ---")
    for resource in obs['inventory']:
        if not resource['is_attached']:
            print(f"Cleaning up idle resource: {resource['id']}")
            requests.post(
                f"{BASE_URL}/step",
                json={
                    "action_type": "delete_resource",
                    "resource_id": resource["id"],
                },
                timeout=30,
            )

    # 3. Check Easy Task Score
    score_res = requests.get(f"{BASE_URL}/tasks/cleanup_unattached/score", timeout=30)
    print(f"✅ Easy Task Score: {parse_json_response(score_res)['score']}")

    # 4. Perform 'Medium Task' - Resize underutilized VM
    print("\n--- Task 2: Right-sizing Compute ---")
    state_res = requests.get(f"{BASE_URL}/state")
    current_obs = state_res.json()
    
    # Find a VM with low CPU
    for resource in current_obs['inventory']:
        if resource['category'] == 'compute' and resource.get('cpu_usage_pct_30d', 0) < 10:
            print(f"Scaling down {resource['id']} (CPU: {resource.get('cpu_usage_pct_30d', 0)}%)")
            requests.post(
                f"{BASE_URL}/step",
                json={
                    "action_type": "modify_instance",
                    "instance_id": resource['id'],
                    "new_type": "t3.small",
                },
                timeout=30,
            )
            break # Just do one for the baseline

    # 5. Check Final Stats
    final_state = parse_json_response(requests.get(f"{BASE_URL}/state", timeout=30))
    print("\n--- Final Results ---")
    print(f"Final Bill: ${final_state['cost_data']['projected_monthly_bill']}")
    print(f"Final Latency: {final_state['health_status']['system_latency_ms']}ms")
    
    med_score = parse_json_response(requests.get(f"{BASE_URL}/tasks/rightsize_compute/score", timeout=30))
    print(f"✅ Medium Task Score: {med_score['score']}")

if __name__ == "__main__":
    run_baseline()