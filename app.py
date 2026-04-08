"""
FinOps Cloud Optimization Dashboard - Gradio App for Hugging Face Spaces

Deploy to Hugging Face by:
1. Create a new Space on huggingface.co
2. Upload app.py + requirements.txt
3. Set environment variable: FINOPS_API_URL to your API endpoint
"""

import os
import json
import gradio as gr
import requests
from typing import Dict, List, Tuple
import time
from datetime import datetime

# Configuration
API_URL = os.getenv("FINOPS_API_URL", "http://127.0.0.1:7860")
POLLING_INTERVAL = 1  # seconds

class FinOpsClient:
    """Client for FinOps API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.logs = []
    
    def add_log(self, message: str, log_type: str = "info"):
        """Add timestamped log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append((log_entry, log_type))
        return self.logs
    
    def reset_environment(self) -> Tuple[str, str, List]:
        """Reset the environment and return initial state."""
        try:
            self.add_log("🔄 Resetting environment...", "info")
            response = requests.post(f"{self.base_url}/reset", timeout=30)
            response.raise_for_status()
            data = response.json()
            
            bill = data['cost_data']['projected_monthly_bill']
            self.add_log(f"✅ Environment reset. Bill: ${bill:.2f}", "success")
            
            return data['cost_data'], data['inventory'], self.logs
        except Exception as e:
            error_msg = f"❌ Failed to reset: {str(e)}"
            self.add_log(error_msg, "error")
            return {}, [], self.logs
    
    def fetch_scores(self) -> Dict[str, float]:
        """Fetch task scores."""
        try:
            self.add_log("📊 Fetching task scores...", "info")
            scores = {}
            
            tasks = ["cleanup_unattached", "rightsize_compute", "fleet_strategy"]
            for task in tasks:
                response = requests.get(f"{self.base_url}/tasks/{task}/score", timeout=30)
                response.raise_for_status()
                score = response.json()['score']
                scores[task] = score
                self.add_log(f"📈 {task}: {score:.1%}", "info")
            
            self.add_log("✅ Scores fetched", "success")
            return scores
        except Exception as e:
            error_msg = f"❌ Failed to fetch scores: {str(e)}"
            self.add_log(error_msg, "error")
            return {}
    
    def execute_action(self, action_type: str, **kwargs) -> Tuple[float, str, List]:
        """Execute an action and return reward."""
        try:
            self.add_log(f"🚀 Executing: {action_type}", "info")
            payload = {"action_type": action_type, **kwargs}
            
            response = requests.post(f"{self.base_url}/step", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            reward = data['reward']
            bill = data['observation']['cost_data']['projected_monthly_bill']
            
            self.add_log(f"✅ Reward: {reward:+.3f}", "success")
            self.add_log(f"💰 New bill: ${bill:.2f}", "info")
            
            return reward, data['observation'], self.logs
        except Exception as e:
            error_msg = f"❌ Failed to execute action: {str(e)}"
            self.add_log(error_msg, "error")
            return 0, {}, self.logs

# Global client
client = FinOpsClient(API_URL)

def format_logs_html(logs: List[Tuple[str, str]]) -> str:
    """Format logs as HTML."""
    log_styles = {
        "info": "color: #3B82F6;",
        "success": "color: #10B981;",
        "error": "color: #EF4444;",
        "warning": "color: #F59E0B;"
    }
    
    html = '<div style="font-family: monospace; font-size: 12px; height: 300px; overflow-y: auto; padding: 10px; background: #1F2937; color: #E5E7EB; border-radius: 8px;">'
    
    for log_text, log_type in reversed(logs):
        style = log_styles.get(log_type, "color: #E5E7EB;")
        html += f'<div style="{style}">{log_text}</div>'
    
    html += '</div>'
    return html

def reset_environment():
    """Reset environment callback."""
    cost_data, inventory, logs = client.reset_environment()
    
    if not cost_data:
        return (
            f"## ❌ Error\nFailed to connect to API at {API_URL}",
            "0", "0", "0", "0",
            format_logs_html(logs),
            []
        )
    
    bill = cost_data['projected_monthly_bill']
    latency = cost_data.get('p99_latency_ms', 0)
    throttle = cost_data.get('throttle_events', 0)
    
    # Get scores
    scores = client.fetch_scores()
    
    status = f"""## 🚀 Environment Ready
**Bill:** ${bill:.2f}/month
**P99 Latency:** {latency:.0f}ms
**Throttle Events:** {throttle}
    """
    
    return (
        status,
        f"{bill:.2f}",
        f"{latency:.0f}",
        f"{throttle}",
        json.dumps(cost_data, indent=2),
        format_logs_html(logs),
        inventory
    )

def delete_volume(inventory_state):
    """Delete unattached volume."""
    if not inventory_state:
        return None, None, None
    
    # Find first unattached volume
    for resource in inventory_state:
        if resource.get('category') == 'storage' and not resource.get('is_attached'):
            resource_id = resource['id']
            reward, obs, logs = client.execute_action(
                "delete_resource",
                resource_id=resource_id
            )
            
            status = f"✅ Deleted volume {resource_id[:8]}\nReward: {reward:+.3f}"
            return status, format_logs_html(logs), obs.get('inventory', [])
    
    client.add_log("ℹ️ No unattached volumes found", "warning")
    return "No unattached volumes found", format_logs_html(client.logs), inventory_state

def rightsize_instance(inventory_state):
    """Downsize underutilized instance."""
    if not inventory_state:
        return None, None, None
    
    # Find underutilized instance
    for resource in inventory_state:
        if (resource.get('category') == 'compute' and 
            resource.get('cpu_usage_pct_30d', 0) < 5.0):
            instance_id = resource['id']
            reward, obs, logs = client.execute_action(
                "modify_instance",
                instance_id=instance_id,
                new_type="t3.small"
            )
            
            status = f"✅ Resized instance {instance_id[:8]} to t3.small\nReward: {reward:+.3f}"
            return status, format_logs_html(logs), obs.get('inventory', [])
    
    client.add_log("ℹ️ No underutilized instances found", "warning")
    return "No underutilized instances found", format_logs_html(client.logs), inventory_state

def purchase_plan(plan_type: str, duration: str, inventory_state):
    """Purchase savings plan."""
    reward, obs, logs = client.execute_action(
        "purchase_savings_plan",
        plan_type=plan_type,
        duration=duration
    )
    
    status = f"✅ Purchased {duration} {plan_type} savings plan\nReward: {reward:+.3f}"
    return status, format_logs_html(logs), obs.get('inventory', [])

def refresh_scores():
    """Refresh task scores."""
    scores = client.fetch_scores()
    
    cleanup = scores.get('cleanup_unattached', 0)
    rightsize = scores.get('rightsize_compute', 0)
    fleet = scores.get('fleet_strategy', 0)
    
    return (
        format_logs_html(client.logs),
        f"{cleanup:.1%}",
        f"{rightsize:.1%}",
        f"{fleet:.1%}"
    )

def format_inventory(inventory: List[Dict]) -> str:
    """Format inventory as markdown table."""
    if not inventory:
        return "No inventory data"
    
    markdown = "| Resource ID | Type | Category | CPU % | Cost |\n"
    markdown += "|---|---|---|---|---|\n"
    
    for resource in inventory[:10]:  # Show first 10
        res_id = resource['id'][:12]
        res_type = resource.get('resource_type', 'N/A')
        category = resource.get('category', 'N/A')
        cpu = resource.get('cpu_usage_pct_30d', 0)
        cost = resource.get('hourly_cost', 0)
        
        markdown += f"| {res_id} | {res_type} | {category} | {cpu:.1f}% | ${cost:.3f}/hr |\n"
    
    if len(inventory) > 10:
        markdown += f"\n... and {len(inventory) - 10} more resources"
    
    return markdown

# Gradio Interface
with gr.Blocks(title="FinOps Optimizer", theme=gr.themes.Soft(primary_hue="blue")) as demo:
    
    # State management
    inventory_state = gr.State([])
    
    gr.Markdown("""
    # ☁️ FinOps Cloud Optimizer
    
    Optimize your cloud costs with automated recommendations and cost analysis.
    """)
    
    # Connection status
    gr.Markdown(f"**API URL:** `{API_URL}`")
    
    with gr.Row():
        reset_btn = gr.Button("🔄 Reset Environment", variant="primary", size="lg")
    
    # Status section
    with gr.Row():
        status_md = gr.Markdown("Click 'Reset Environment' to start")
    
    # Metrics
    with gr.Row():
        with gr.Column():
            bill_display = gr.Textbox(label="💰 Monthly Bill", interactive=False)
        with gr.Column():
            latency_display = gr.Textbox(label="⏱️ P99 Latency (ms)", interactive=False)
        with gr.Column():
            throttle_display = gr.Textbox(label="🚨 Throttle Events", interactive=False)
        with gr.Column():
            state_display = gr.Textbox(label="📊 Raw State", interactive=False, max_lines=3)
    
    # Logs
    logs_display = gr.HTML()
    
    # Inventory
    with gr.Tab("📦 Inventory"):
        inventory_md = gr.Markdown("No data yet")
    
    # Task Scores
    with gr.Tab("📈 Task Scores"):
        with gr.Row():
            with gr.Column():
                cleanup_score = gr.Textbox(label="Cleanup Unattached", interactive=False)
            with gr.Column():
                rightsize_score = gr.Textbox(label="Rightsize Compute", interactive=False)
            with gr.Column():
                fleet_score = gr.Textbox(label="Fleet Strategy", interactive=False)
        
        refresh_scores_btn = gr.Button("🔄 Refresh Scores")
        refresh_scores_btn.click(
            fn=refresh_scores,
            outputs=[logs_display, cleanup_score, rightsize_score, fleet_score]
        )
    
    # Actions
    with gr.Tab("⚙️ Quick Actions"):
        gr.Markdown("### Cloud Optimization Actions")
        
        with gr.Row():
            delete_btn = gr.Button("🗑️ Delete Unattached Volumes", variant="stop")
            rightsize_btn = gr.Button("📉 Rightsize Instances", variant="secondary")
        
        action_status = gr.Textbox(label="Action Result", interactive=False)
        
        with gr.Row():
            with gr.Column():
                plan_type = gr.Radio(["compute", "database"], value="compute", label="Plan Type")
            with gr.Column():
                duration = gr.Radio(["1y", "3y"], value="1y", label="Duration")
            
            purchase_btn = gr.Button("💳 Purchase Savings Plan")
        
        # Action callbacks
        delete_btn.click(
            fn=delete_volume,
            inputs=inventory_state,
            outputs=[action_status, logs_display, inventory_state]
        ).then(
            fn=lambda: format_inventory(inventory_state.value),
            outputs=inventory_md
        )
        
        rightsize_btn.click(
            fn=rightsize_instance,
            inputs=inventory_state,
            outputs=[action_status, logs_display, inventory_state]
        ).then(
            fn=lambda: format_inventory(inventory_state.value),
            outputs=inventory_md
        )
        
        purchase_btn.click(
            fn=lambda pt, dur: purchase_plan(pt, dur, inventory_state.value),
            inputs=[plan_type, duration],
            outputs=[action_status, logs_display, inventory_state]
        ).then(
            fn=lambda: format_inventory(inventory_state.value),
            outputs=inventory_md
        )
    
    # Reset callback
    reset_btn.click(
        fn=reset_environment,
        outputs=[
            status_md,
            bill_display,
            latency_display,
            throttle_display,
            state_display,
            logs_display,
            inventory_state
        ]
    ).then(
        fn=lambda inv: format_inventory(inv),
        inputs=inventory_state,
        outputs=inventory_md
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
