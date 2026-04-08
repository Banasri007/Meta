"""
FinOps Cloud Optimization Dashboard - Streamlit App for Hugging Face Spaces

Deploy to Hugging Face by:
1. Create a new Space on huggingface.co (choose Streamlit runtime)
2. Upload app.py + requirements.txt
3. Set environment variable: FINOPS_API_URL to your API endpoint
"""

import os
import json
import streamlit as st
import requests
from typing import Dict, List
from datetime import datetime

# Page config
st.set_page_config(
    page_title="FinOps Optimizer",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_URL = os.getenv("FINOPS_API_URL", "http://127.0.0.1:7860")

# Initialize session state
if "observation" not in st.session_state:
    st.session_state.observation = None
if "logs" not in st.session_state:
    st.session_state.logs = []

class FinOpsAPI:
    """Client for FinOps API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def add_log(self, message: str):
        """Add timestamped log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.logs.append(f"[{timestamp}] {message}")
    
    def reset(self) -> bool:
        """Reset environment."""
        try:
            self.add_log("🔄 Calling /reset")
            response = requests.post(f"{self.base_url}/reset", timeout=30)
            response.raise_for_status()
            st.session_state.observation = response.json()
            self.add_log(f"✅ Reset successful")
            return True
        except Exception as e:
            self.add_log(f"❌ Reset failed: {str(e)}")
            return False
    
    def get_state(self) -> bool:
        """Get current state."""
        try:
            self.add_log("🔄 Calling /state")
            response = requests.get(f"{self.base_url}/state", timeout=30)
            response.raise_for_status()
            st.session_state.observation = response.json()
            self.add_log(f"✅ State fetched")
            return True
        except Exception as e:
            self.add_log(f"❌ State fetch failed: {str(e)}")
            return False
    
    def step(self, action_type: str, **kwargs) -> bool:
        """Execute an action."""
        try:
            payload = {"action_type": action_type, **kwargs}
            self.add_log(f"🚀 Calling /step with action_type={action_type}")
            response = requests.post(f"{self.base_url}/step", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            st.session_state.observation = data.get('observation', {})
            reward = data.get('reward', 0)
            self.add_log(f"✅ Action executed, reward={reward:+.3f}")
            return True
        except Exception as e:
            self.add_log(f"❌ Action failed: {str(e)}")
            return False
    
    def get_score(self, task_id: str) -> float:
        """Get task score."""
        try:
            response = requests.get(f"{self.base_url}/tasks/{task_id}/score", timeout=30)
            response.raise_for_status()
            return response.json().get('score', 0)
        except Exception as e:
            self.add_log(f"❌ Score fetch failed: {str(e)}")
            return 0

# Initialize API client
api = FinOpsAPI(API_URL)

# Header
st.markdown("# ☁️ FinOps Cloud Optimizer")
st.markdown(f"**API URL:** `{API_URL}`")

# Sidebar - Quick connect
with st.sidebar:
    st.header("📡 Quick Connect")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Reset", use_container_width=True):
            api.reset()
            st.rerun()
    with col2:
        if st.button("📊 State", use_container_width=True):
            api.get_state()
            st.rerun()
    with col3:
        if st.button("🔃 Refresh", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Action types
    st.subheader("⚙️ Actions")
    action_type = st.selectbox(
        "Select Action",
        ["delete_resource", "modify_instance", "purchase_savings_plan"]
    )
    
    # Dynamic inputs based on action type
    if action_type == "delete_resource":
        resource_id = st.text_input("Resource ID")
        if st.button("Execute Delete", use_container_width=True, type="primary"):
            if resource_id:
                api.step("delete_resource", resource_id=resource_id)
                st.rerun()
    
    elif action_type == "modify_instance":
        instance_id = st.text_input("Instance ID")
        new_type = st.text_input("New Type", value="t3.small")
        if st.button("Execute Modify", use_container_width=True, type="primary"):
            if instance_id:
                api.step("modify_instance", instance_id=instance_id, new_type=new_type)
                st.rerun()
    
    elif action_type == "purchase_savings_plan":
        plan_type = st.selectbox("Plan Type", ["compute", "database"])
        duration = st.selectbox("Duration", ["1y", "3y"])
        if st.button("Execute Purchase", use_container_width=True, type="primary"):
            api.step("purchase_savings_plan", plan_type=plan_type, duration=duration)
            st.rerun()

# Main content
if st.session_state.observation:
    obs = st.session_state.observation
    cost_data = obs.get('cost_data', {})
    inventory = obs.get('inventory', [])
    
    # Status section
    st.header("📊 Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        bill = cost_data.get('projected_monthly_bill', 0)
        st.metric("💰 Monthly Bill", f"${bill:.2f}")
    
    with col2:
        latency = cost_data.get('p99_latency_ms', 0)
        st.metric("⏱️ P99 Latency", f"{latency:.0f}ms")
    
    with col3:
        throttle = cost_data.get('throttle_events', 0)
        st.metric("🚨 Throttle Events", f"{throttle}")
    
    with col4:
        downtime = cost_data.get('downtime_minutes', 0)
        st.metric("⏸️ Downtime", f"{downtime:.0f}min")
    
    # Task Scores
    st.header("🎯 Task Scores")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        score = api.get_score("cleanup_unattached")
        st.metric("Cleanup Unattached", f"{score:.1%}")
    
    with col2:
        score = api.get_score("rightsize_compute")
        st.metric("Rightsize Compute", f"{score:.1%}")
    
    with col3:
        score = api.get_score("fleet_strategy")
        st.metric("Fleet Strategy", f"{score:.1%}")
    
    # Inventory
    st.header("📦 Inventory")
    if inventory:
        inventory_data = []
        for res in inventory:
            inventory_data.append({
                "ID": res.get('id', '')[:12],
                "Type": res.get('resource_type', 'N/A'),
                "Category": res.get('category', 'N/A'),
                "CPU %": f"{res.get('cpu_usage_pct_30d', 0):.1f}",
                "Cost/hr": f"${res.get('hourly_cost', 0):.3f}"
            })
        st.dataframe(inventory_data, use_container_width=True)
    else:
        st.info("No inventory data. Click Reset to load resources.")
    
    # Raw JSON response
    st.header("📋 Raw Response")
    pretty_print = st.checkbox("Pretty print", value=True)
    
    if pretty_print:
        st.json(st.session_state.observation)
    else:
        st.code(json.dumps(st.session_state.observation), language="json")

else:
    st.info("👈 Click **Reset** in the sidebar to load the environment")

# Logs
st.header("📜 Logs")
if st.session_state.logs:
    log_text = "\n".join(reversed(st.session_state.logs))
    st.code(log_text, language="")
else:
    st.info("No logs yet")
