"""
Test script to validate scoring conditions for all three tasks.
Run with: python test_scoring.py
"""

import json
import requests
import os
import time
from typing import Callable, Any, TypeVar

BASE_URL = os.getenv("FINOPS_BASE_URL", "https://mahekgupta312006-finops-optimizer.hf.space")

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: The function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiply delay by this factor each retry
    """
    last_error = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.SSLError) as e:
            last_error = e
            if attempt < max_retries:
                print(f"  ⚠️  Connection error (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}")
                print(f"     Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print(f"  ❌ Failed after {max_retries + 1} attempts")
    
    raise last_error


def post(path: str, payload: dict, verbose: bool = False, max_retries: int = 3) -> dict:
    """Helper to make POST requests with retry logic."""
    def _post():
        if verbose:
            print(f"  POST {path}: {payload}")
        response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        if verbose:
            if 'reward' in result:
                print(f"    → Reward: {result['reward']}, Done: {result['done']}")
            if 'error' in result:
                print(f"    → Error: {result['error']}")
        return result
    
    return retry_with_backoff(_post, max_retries=max_retries)


def get(path: str, verbose: bool = False, max_retries: int = 3) -> dict:
    """Helper to make GET requests with retry logic."""
    def _get():
        if verbose:
            print(f"  GET {path}")
        response = requests.get(f"{BASE_URL}{path}", timeout=30)
        response.raise_for_status()
        return response.json()
    
    return retry_with_backoff(_get, max_retries=max_retries)


def test_cleanup_unattached():
    """Test the easy task: cleanup unattached storage + idle test instances."""
    print("\n" + "="*70)
    print("TEST 1: CLEANUP_UNATTACHED (Easy Task)")
    print("="*70)
    print("Requirement: Delete 5 unattached volumes + 2 idle test instances")
    
    # Test 1a: Perfect completion (delete all)
    print("\n[Test 1a] Perfect completion - delete all unattached volumes and idle tests")
    state = post("/reset", {})
    initial_bill = state['cost_data']['projected_monthly_bill']
    print(f"Initial bill: ${initial_bill}")
    
    inventory = state['inventory']
    unattached_volumes = [r for r in inventory if r['category'] == 'storage' and not r['is_attached']]
    idle_tests = [r for r in inventory if r['category'] == 'compute' and r.get('tags', {}).get('lifecycle') == 'idle']
    
    print(f"Found {len(unattached_volumes)} unattached volumes: {[r['id'] for r in unattached_volumes]}")
    print(f"Found {len(idle_tests)} idle test instances: {[r['id'] for r in idle_tests]}")
    
    print(f"  Deleting {len(unattached_volumes)} volumes...")
    for volume in unattached_volumes:
        result = post("/step", {"action_type": "delete_resource", "resource_id": volume['id']}, verbose=True)
    
    print(f"  Deleting {len(idle_tests)} idle test instances...")
    for test in idle_tests:
        result = post("/step", {"action_type": "delete_resource", "resource_id": test['id']}, verbose=True)
    
    final_state = get("/state", verbose=False)
    final_bill = final_state['cost_data']['projected_monthly_bill']
    print(f"  Bill change: ${initial_bill} → ${final_bill} (saved: ${initial_bill - final_bill})")
    
    score = get("/tasks/cleanup_unattached/score")['score']
    print(f"  Score: {score} (Expected: 1.0)")
    
    # Test 1b: Partial completion (delete only volumes, miss idle tests)
    print("\n[Test 1b] Partial completion - delete volumes only, skip idle tests")
    state = post("/reset", {})
    inventory = state['inventory']
    unattached_volumes = [r for r in inventory if r['category'] == 'storage' and not r['is_attached']]
    
    for volume in unattached_volumes:
        post("/step", {"action_type": "delete_resource", "resource_id": volume['id']})
    
    score = get("/tasks/cleanup_unattached/score")['score']
    print(f"  Score: {score} (Expected: ~0.70 = 0.7*1.0 + 0.3*0.0)")
    
    # Test 1c: Minimal completion (delete some volumes, no tests)
    print("\n[Test 1c] Minimal completion - delete 2/5 volumes, 0/2 tests")
    state = post("/reset", {})
    inventory = state['inventory']
    unattached_volumes = [r for r in inventory if r['category'] == 'storage' and not r['is_attached']]
    
    for volume in unattached_volumes[:2]:
        post("/step", {"action_type": "delete_resource", "resource_id": volume['id']})
    
    score = get("/tasks/cleanup_unattached/score")['score']
    print(f"  Score: {score} (Expected: ~0.28 = 0.7*0.4 + 0.3*0.0)")


def test_rightsize_compute():
    """Test the medium task: rightsize underutilized VMs while keeping latency < 200ms."""
    print("\n" + "="*70)
    print("TEST 2: RIGHTSIZE_COMPUTE (Medium Task)")
    print("="*70)
    print("Requirement: Downgrade low-CPU VMs to smaller types, keep latency < 200ms")
    
    # Test 2a: Perfect execution - downsize all underutilized VMs
    print("\n[Test 2a] Perfect execution - downsize all underutilized VMs to t3.small")
    state = post("/reset", {})
    initial_bill = state['cost_data']['projected_monthly_bill']
    initial_latency = state['health_status']['system_latency_ms']
    print(f"Initial bill: ${initial_bill}")
    print(f"Initial latency: {initial_latency}ms")
    
    inventory = state['inventory']
    underutilized_vms = [
        r for r in inventory 
        if r['category'] == 'compute' and r.get('cpu_usage_pct_30d', 0) < 5.0
    ]
    print(f"Found {len(underutilized_vms)} underutilized VMs (CPU < 5%)")
    
    print(f"  Downsizing {len(underutilized_vms)} VMs...")
    for i, vm in enumerate(underutilized_vms, 1):
        result = post("/step", {
            "action_type": "modify_instance",
            "instance_id": vm['id'],
            "new_type": "t3.small"
        }, verbose=(i <= 2))  # Verbose for first 2 only
    
    final_state = get("/state", verbose=False)
    score = get("/tasks/rightsize_compute/score")['score']
    final_bill = final_state['cost_data']['projected_monthly_bill']
    final_latency = final_state['health_status']['system_latency_ms']
    
    print(f"  Final bill: ${final_bill} (saved ${initial_bill - final_bill})")
    print(f"  Final latency: {final_latency}ms")
    print(f"  Latency within limit: {final_latency < 200}")
    print(f"  Score: {score}")
    
    # Test 2b: Partial execution - downsize only some VMs
    print("\n[Test 2b] Partial execution - downsize only 5/10 underutilized VMs")
    state = post("/reset", {})
    inventory = state['inventory']
    underutilized_vms = [
        r for r in inventory 
        if r['category'] == 'compute' and r.get('cpu_usage_pct_30d', 0) < 5.0
    ]
    
    for vm in underutilized_vms[:5]:
        post("/step", {
            "action_type": "modify_instance",
            "instance_id": vm['id'],
            "new_type": "t3.small"
        })
    
    final_state = get("/state")
    score = get("/tasks/rightsize_compute/score")['score']
    final_latency = final_state['health_status']['system_latency_ms']
    
    print(f"  Final latency: {final_latency}ms")
    print(f"  Score: {score}")
    
    # Test 2c: Extreme downsizing (test latency penalty)
    print("\n[Test 2c] Extreme downsizing - try t3.micro (may cause latency > 200ms)")
    state = post("/reset", {})
    inventory = state['inventory']
    underutilized_vms = [
        r for r in inventory 
        if r['category'] == 'compute' and r.get('cpu_usage_pct_30d', 0) < 5.0
    ]
    
    for vm in underutilized_vms:
        post("/step", {
            "action_type": "modify_instance",
            "instance_id": vm['id'],
            "new_type": "t3.micro"
        })
    
    final_state = get("/state")
    score = get("/tasks/rightsize_compute/score")['score']
    final_latency = final_state['health_status']['system_latency_ms']
    
    print(f"  Final latency: {final_latency}ms (limit: 200ms)")
    print(f"  Latency penalty applied: {final_latency >= 200}")
    print(f"  Score: {score} (should be heavily penalized if latency >= 200ms)")


def test_fleet_strategy():
    """Test the hard task: balance deletions, rightsizing, and savings plans."""
    print("\n" + "="*70)
    print("TEST 3: FLEET_STRATEGY (Hard Task)")
    print("="*70)
    print("Requirement: Achieve >40% cost reduction with positive ROI and no downtime")
    
    # Test 3a: Aggressive cost reduction with savings plans
    print("\n[Test 3a] Aggressive strategy - delete legacy, buy savings plans, downsize")
    state = post("/reset", {})
    initial_bill = state['cost_data']['projected_monthly_bill']
    print(f"  Initial bill: ${initial_bill}")
    
    inventory = state['inventory']
    
    # Delete legacy non-prod resources
    legacy_resources = [r for r in inventory if r.get('is_legacy') and not r.get('is_production')]
    print(f"  Deleting {len(legacy_resources)} legacy non-production resources...")
    for resource in legacy_resources:
        post("/step", {"action_type": "delete_resource", "resource_id": resource['id']})
    
    # Delete unattached volumes
    unattached = [r for r in inventory if r['category'] == 'storage' and not r['is_attached']]
    print(f"  Deleting {len(unattached)} unattached volumes...")
    for volume in unattached:
        post("/step", {"action_type": "delete_resource", "resource_id": volume['id']})
    
    # Delete idle tests
    idle_tests = [r for r in inventory if r['category'] == 'compute' and r.get('tags', {}).get('lifecycle') == 'idle']
    print(f"  Deleting {len(idle_tests)} idle test instances...")
    for test in idle_tests:
        post("/step", {"action_type": "delete_resource", "resource_id": test['id']})
    
    # Downsize underutilized VMs
    underutilized = [r for r in inventory if r['category'] == 'compute' and r.get('cpu_usage_pct_30d', 0) < 5.0]
    print(f"  Downsizing {len(underutilized)} underutilized VMs...")
    for vm in underutilized:
        post("/step", {
            "action_type": "modify_instance",
            "instance_id": vm['id'],
            "new_type": "t3.small"
        })
    
    # Buy savings plans
    print(f"  Purchasing savings plans...")
    post("/step", {"action_type": "purchase_savings_plan", "plan_type": "compute", "duration": "1y"})
    post("/step", {"action_type": "purchase_savings_plan", "plan_type": "database", "duration": "1y"})
    
    final_state = get("/state")
    score = get("/tasks/fleet_strategy/score")['score']
    final_bill = final_state['cost_data']['projected_monthly_bill']
    cost_reduction = (initial_bill - final_bill) / initial_bill if initial_bill > 0 else 0
    
    print(f"  Final bill: ${final_bill}")
    print(f"  Cost reduction: {cost_reduction:.1%} (target: >40%)")
    print(f"  Downtime events: {final_state['health_status'].get('downtime_events', 0)}")
    print(f"  Score: {score}")
    
    # Test 3b: Conservative strategy (minimal changes)
    print("\n[Test 3b] Conservative strategy - only safe deletions")
    state = post("/reset", {})
    initial_bill = state['cost_data']['projected_monthly_bill']
    print(f"  Initial bill: ${initial_bill}")
    
    inventory = state['inventory']
    unattached = [r for r in inventory if r['category'] == 'storage' and not r['is_attached']]
    idle_tests = [r for r in inventory if r['category'] == 'compute' and r.get('tags', {}).get('lifecycle') == 'idle']
    
    # Delete only unattached volumes and idle tests
    for volume in unattached:
        post("/step", {"action_type": "delete_resource", "resource_id": volume['id']})
    
    for idle in idle_tests:
        post("/step", {"action_type": "delete_resource", "resource_id": idle['id']})
    
    final_state = get("/state")
    score = get("/tasks/fleet_strategy/score")['score']
    final_bill = final_state['cost_data']['projected_monthly_bill']
    cost_reduction = (initial_bill - final_bill) / initial_bill if initial_bill > 0 else 0
    
    print(f"  Final bill: ${final_bill}")
    print(f"  Cost reduction: {cost_reduction:.1%}")
    print(f"  Score: {score}")


def main():
    """Run all tests."""
    print("\n" + "#"*70)
    print("# FINOPS SCORING VALIDATION TEST SUITE")
    print("#"*70)
    print(f"Target API: {BASE_URL}")
    print("Retry strategy: Up to 3 attempts with exponential backoff\n")
    
    try:
        test_cleanup_unattached()
        test_rightsize_compute()
        test_fleet_strategy()
        
        print("\n" + "#"*70)
        print("# ALL TESTS COMPLETED")
        print("#"*70)
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if the API is running and accessible at:")
        print(f"   {BASE_URL}")
        print("2. Or use the local API instead:")
        print("   - Start: python -m uvicorn main:app --app-dir finops-env --host 127.0.0.1 --port 7860")
        print("   - Set:   $env:FINOPS_BASE_URL = 'http://127.0.0.1:7860'")
        print("   - Retry: python test_scoring.py")
        return 1
    except requests.exceptions.SSLError as e:
        print(f"\n❌ SSL Error: {e}")
        print("\nThis usually means:")
        print("- The remote server is unreachable or overloaded")
        print("- Network connectivity issues")
        print("\nTry using the local API instead (see troubleshooting above)")
        return 1
    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
