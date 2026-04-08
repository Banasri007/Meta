"""
Automated RL agent that learns from rewards and optimizes cloud costs.
Run with: python rl_agent.py
"""

import json
import os
import time
import requests
from typing import Dict, List, Tuple

BASE_URL = os.getenv("FINOPS_BASE_URL", "http://127.0.0.1:7860")

class SimpleRLAgent:
    """A simple reinforcement learning agent for cloud cost optimization."""
    
    def __init__(self, learning_rate=0.1, epsilon=0.1):
        self.learning_rate = learning_rate
        self.epsilon = epsilon  # Exploration rate
        self.q_values = {}  # Action quality estimates
        self.step_count = 0
        self.total_reward = 0.0
        self.action_history = []
        
    def post(self, path: str, payload: dict) -> dict:
        """Make POST request to API."""
        response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get(self, path: str) -> dict:
        """Make GET request to API."""
        response = requests.get(f"{BASE_URL}{path}", timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_possible_actions(self, observation) -> List[Dict]:
        """Generate possible actions from current state."""
        actions = []
        
        # Action 1: Delete unattached volumes
        for resource in observation['inventory']:
            if resource['category'] == 'storage' and not resource['is_attached']:
                actions.append({
                    'type': 'delete_resource',
                    'resource_id': resource['id'],
                    'name': f"Delete unattached volume {resource['id'][:8]}",
                    'category': 'cleanup'
                })
        
        # Action 2: Delete idle test instances
        for resource in observation['inventory']:
            if (resource['category'] == 'compute' and 
                resource.get('tags', {}).get('lifecycle') == 'idle'):
                actions.append({
                    'type': 'delete_resource',
                    'resource_id': resource['id'],
                    'name': f"Delete idle instance {resource['id'][:8]}",
                    'category': 'cleanup'
                })
        
        # Action 3: Downsize underutilized compute
        for resource in observation['inventory']:
            if (resource['category'] == 'compute' and 
                resource.get('cpu_usage_pct_30d', 0) < 5.0 and
                resource['resource_type'] != 't3.small'):
                actions.append({
                    'type': 'modify_instance',
                    'instance_id': resource['id'],
                    'new_type': 't3.small',
                    'name': f"Downsize {resource['id'][:8]} to t3.small",
                    'category': 'rightsize'
                })
        
        # Action 4: Buy savings plans
        actions.extend([
            {
                'type': 'purchase_savings_plan',
                'plan_type': 'compute',
                'duration': '1y',
                'name': 'Buy 1y compute savings plan',
                'category': 'savings'
            },
            {
                'type': 'purchase_savings_plan',
                'plan_type': 'database',
                'duration': '1y',
                'name': 'Buy 1y database savings plan',
                'category': 'savings'
            }
        ])
        
        return actions
    
    def select_action(self, actions: List[Dict]) -> Dict:
        """Select action using epsilon-greedy strategy."""
        if not actions:
            return None
        
        # Epsilon-greedy: explore vs exploit
        import random
        if random.random() < self.epsilon:
            # Explore: random action
            action = random.choice(actions)
        else:
            # Exploit: best known action
            best_action = max(
                actions,
                key=lambda a: self.q_values.get((a['type'], a.get('resource_id', '')), 0)
            )
            action = best_action
        
        return action
    
    def execute_action(self, action: Dict) -> Tuple[float, Dict]:
        """Execute action and return reward."""
        payload = {
            'action_type': action['type'],
        }
        
        if action['type'] == 'delete_resource':
            payload['resource_id'] = action['resource_id']
        elif action['type'] == 'modify_instance':
            payload['instance_id'] = action['instance_id']
            payload['new_type'] = action['new_type']
        elif action['type'] == 'purchase_savings_plan':
            payload['plan_type'] = action['plan_type']
            payload['duration'] = action['duration']
        
        response = self.post('/step', payload)
        reward = response['reward']
        observation = response['observation']
        
        return reward, observation
    
    def update_q_value(self, action_key: Tuple, reward: float):
        """Update Q-value using simple learning rule."""
        current_q = self.q_values.get(action_key, 0)
        new_q = current_q + self.learning_rate * (reward - current_q)
        self.q_values[action_key] = new_q
    
    def run_episode(self, max_steps=20):
        """Run one episode of learning."""
        print("\n" + "="*70)
        print("STARTING RL EPISODE")
        print("="*70)
        
        # Reset environment
        observation = self.post('/reset', {})
        initial_bill = observation['cost_data']['projected_monthly_bill']
        print(f"Initial state: Bill=${initial_bill}")
        
        episode_reward = 0.0
        
        for step in range(max_steps):
            # Get possible actions
            actions = self.get_possible_actions(observation)
            if not actions:
                print(f"[Step {step+1}] No more actions available")
                break
            
            # Select action
            action = self.select_action(actions)
            print(f"\n[Step {step+1}] {action['name']}")
            
            # Execute action
            reward, observation = self.execute_action(action)
            episode_reward += reward
            
            # Update Q-value
            action_key = (action['type'], action.get('resource_id', action.get('instance_id', '')))
            self.update_q_value(action_key, reward)
            
            # Log results
            print(f"  Reward: {reward:+.3f}")
            print(f"  Bill: ${observation['cost_data']['projected_monthly_bill']:.2f}")
            
            self.action_history.append({
                'step': step + 1,
                'action': action['name'],
                'reward': reward,
                'bill': observation['cost_data']['projected_monthly_bill']
            })
            
            self.step_count += 1
            self.total_reward += reward
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Get final scores
        final_bill = observation['cost_data']['projected_monthly_bill']
        cost_reduction = (initial_bill - final_bill) / initial_bill * 100
        
        print(f"\n" + "-"*70)
        print(f"Episode Summary:")
        print(f"  Initial bill: ${initial_bill:.2f}")
        print(f"  Final bill: ${final_bill:.2f}")
        print(f"  Cost reduction: {cost_reduction:.1f}%")
        print(f"  Episode reward: {episode_reward:.3f}")
        print(f"  Total steps: {step + 1}")
        
        # Fetch final scores
        try:
            cleanup_score = self.get('/tasks/cleanup_unattached/score')['score']
            rightsize_score = self.get('/tasks/rightsize_compute/score')['score']
            fleet_score = self.get('/tasks/fleet_strategy/score')['score']
            
            print(f"\nTask Scores:")
            print(f"  Cleanup: {cleanup_score:.1%}")
            print(f"  Rightsize: {rightsize_score:.1%}")
            print(f"  Fleet Strategy: {fleet_score:.1%}")
        except Exception as e:
            print(f"  (Could not fetch scores: {e})")
        
        return episode_reward

def main():
    print("\n" + "#"*70)
    print("# SIMPLE RL AGENT FOR CLOUD COST OPTIMIZATION")
    print("#"*70)
    print(f"Target API: {BASE_URL}")
    print("Strategy: Epsilon-greedy with Q-learning")
    print("Learning Rate: 0.1, Exploration Rate: 0.1\n")
    
    agent = SimpleRLAgent(learning_rate=0.1, epsilon=0.1)
    
    try:
        # Run 2 episodes to show learning
        for episode in range(2):
            print(f"\n{'#'*70}")
            print(f"# EPISODE {episode + 1}/2")
            print(f"{'#'*70}")
            agent.run_episode(max_steps=15)
            time.sleep(1)
        
        # Show learned Q-values
        print(f"\n{'#'*70}")
        print("# LEARNED Q-VALUES (Action Quality Estimates)")
        print(f"{'#'*70}")
        
        if agent.q_values:
            sorted_q = sorted(agent.q_values.items(), key=lambda x: x[1], reverse=True)
            for (action_type, resource_id), q_value in sorted_q[:10]:
                print(f"  {action_type:20} Q-value: {q_value:+.3f}")
        else:
            print("  No Q-values learned yet")
        
        print(f"\n{'#'*70}")
        print(f"# FINAL STATISTICS")
        print(f"{'#'*70}")
        print(f"Total steps taken: {agent.step_count}")
        print(f"Total cumulative reward: {agent.total_reward:.3f}")
        print(f"Average reward per step: {agent.total_reward / agent.step_count if agent.step_count > 0 else 0:.3f}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify API is running at: https://mahekgupta312006-finops-optimizer.hf.space")
        print("2. Check your internet connection")
        print("3. Try again in a few moments (server may be temporarily down)")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
