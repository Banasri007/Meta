"""
FinOps Cloud Optimizer - Streamlit Frontend for Hugging Face Spaces

Deploy steps:
1. Go to huggingface.co/spaces → New Space → choose Streamlit SDK
2. Upload this app.py + requirements.txt
3. Set Space secret: FINOPS_API_URL = https://mahekgupta312006-finops-optimizer.hf.space
"""

import os
import json
import streamlit as st
import requests
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinOps Optimizer",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — dark terminal aesthetic like the reference UI ─────────────────
st.markdown("""
<style>
/* ---------- global ---------- */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d0d0d;
    color: #e0e0e0;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #222;
}
/* ---------- headings ---------- */
h1, h2, h3 {
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: -0.02em;
}
/* ---------- metric cards ---------- */
[data-testid="stMetric"] {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 12px 16px !important;
}
[data-testid="stMetricValue"] { color: #4ade80; font-size: 1.4rem !important; }
[data-testid="stMetricLabel"] { color: #888; font-size: 0.72rem !important; }
/* ---------- buttons ---------- */
.stButton > button {
    background: #1a1a1a !important;
    color: #e0e0e0 !important;
    border: 1px solid #333 !important;
    border-radius: 5px !important;
    font-family: monospace !important;
    font-size: 13px !important;
    transition: all 0.15s;
}
.stButton > button:hover {
    border-color: #4ade80 !important;
    color: #4ade80 !important;
}
/* Primary button (Step) */
div[data-testid="column"]:first-child .stButton > button {
    background: #166534 !important;
    border-color: #4ade80 !important;
    color: #4ade80 !important;
}
div[data-testid="column"]:first-child .stButton > button:hover {
    background: #15803d !important;
}
/* ---------- code blocks ---------- */
[data-testid="stCodeBlock"] pre {
    background: #0a0a0a !important;
    border: 1px solid #222 !important;
    border-radius: 6px !important;
    font-size: 12px !important;
}
/* ---------- json viewer ---------- */
[data-testid="stJson"] {
    background: #0a0a0a !important;
    border: 1px solid #222 !important;
    border-radius: 6px !important;
}
/* ---------- selectbox / text_input ---------- */
[data-testid="stSelectbox"] select,
[data-testid="stTextInput"] input {
    background: #111 !important;
    color: #e0e0e0 !important;
    border-color: #333 !important;
    font-family: monospace !important;
    font-size: 13px !important;
}
/* ---------- status box ---------- */
.status-box {
    background: #0d1a0d;
    border: 1px solid #166534;
    border-radius: 6px;
    padding: 10px 16px;
    color: #4ade80;
    font-family: monospace;
    font-size: 14px;
    margin-bottom: 12px;
}
.status-box.error {
    background: #1a0d0d;
    border-color: #7f1d1d;
    color: #f87171;
}
.status-box.info {
    background: #0d0d1a;
    border-color: #1d3a7f;
    color: #93c5fd;
}
/* ---------- divider ---------- */
hr { border-color: #222 !important; }
/* ---------- tabs ---------- */
[data-testid="stTab"] {
    font-family: monospace !important;
    font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────────
API_URL = os.getenv(
    "FINOPS_API_URL",
    "https://mahekgupta312006-finops-optimizer.hf.space"
)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [
    ("observation", None),
    ("logs", []),
    ("status_msg", ""),
    ("status_type", "info"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── API helpers ────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")

def set_status(msg: str, kind: str = "info"):
    st.session_state.status_msg = msg
    st.session_state.status_type = kind

def api_reset():
    try:
        log("→ POST /reset")
        r = requests.post(f"{API_URL}/reset", timeout=30)
        r.raise_for_status()
        st.session_state.observation = r.json()
        set_status("✅  Reset successful — environment reloaded.", "ok")
        log("✅ Reset OK")
    except Exception as e:
        set_status(f"❌  Reset failed: {e}", "error")
        log(f"❌ Reset failed: {e}")

def api_state():
    try:
        log("→ GET /state")
        r = requests.get(f"{API_URL}/state", timeout=30)
        r.raise_for_status()
        st.session_state.observation = r.json()
        set_status("✅  State fetched.", "ok")
        log("✅ State fetched")
    except Exception as e:
        set_status(f"❌  State fetch failed: {e}", "error")
        log(f"❌ State failed: {e}")

def api_step(action_type: str, **kwargs):
    try:
        payload = {"action_type": action_type, **kwargs}
        log(f"→ POST /step  action={action_type}")
        r = requests.post(f"{API_URL}/step", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        st.session_state.observation = data.get("observation", data)
        reward = data.get("reward", "—")
        done   = data.get("done", False)
        reward_str = f"{reward:+.3f}" if isinstance(reward, float) else str(reward)
        status = f"✅  Step executed — reward={reward_str}"
        if done:
            status += "  |  🏁 Episode done"
        set_status(status, "ok")
        log(f"✅ Step OK  reward={reward_str}  done={done}")
    except Exception as e:
        set_status(f"❌  Step failed: {e}", "error")
        log(f"❌ Step failed: {e}")

def api_score(task_id: str) -> float:
    try:
        r = requests.get(f"{API_URL}/tasks/{task_id}/score", timeout=15)
        r.raise_for_status()
        return r.json().get("score", 0.0)
    except Exception:
        return 0.0

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## QUICK CONNECT")

    # Copy-paste snippet
    snippet = f"""from server.environment import FinOpsEnvironment
from models import OptimizationAction

env = FinOpsEnvironment(task_id=1)
obs = env.reset()
obs = env.step(OptimizationAction(
    action_type="delete_resource",
    resource_id="i-0abc123"
))"""
    st.code(snippet, language="python")

    st.markdown("---")
    st.markdown("## RUN INFERENCE")
    st.code("python inference.py", language="bash")
    st.code("TASK_ID=1 python inference.py", language="bash")

    st.markdown("---")
    st.markdown("## ACTIONS")

    action_type = st.selectbox(
        "Action type",
        ["delete_resource", "modify_instance", "purchase_savings_plan"],
        label_visibility="collapsed",
    )

    if action_type == "delete_resource":
        resource_id = st.text_input("Resource ID", placeholder="i-0abc123def456")
        if st.button("▶  Execute delete_resource", use_container_width=True):
            if resource_id:
                api_step("delete_resource", resource_id=resource_id)
                st.rerun()
            else:
                st.warning("Enter a resource ID first.")

    elif action_type == "modify_instance":
        instance_id = st.text_input("Instance ID", placeholder="i-0abc123def456")
        new_type    = st.text_input("New type", value="t3.small")
        if st.button("▶  Execute modify_instance", use_container_width=True):
            if instance_id:
                api_step("modify_instance", instance_id=instance_id, new_type=new_type)
                st.rerun()
            else:
                st.warning("Enter an instance ID first.")

    elif action_type == "purchase_savings_plan":
        plan_type = st.selectbox("Plan type", ["compute", "database"])
        duration  = st.selectbox("Duration",  ["1y", "3y"])
        if st.button("▶  Execute purchase_savings_plan", use_container_width=True):
            api_step("purchase_savings_plan", plan_type=plan_type, duration=duration)
            st.rerun()

    st.markdown("---")
    st.markdown("## SERVER")
    st.markdown(f"Base: `{API_URL}`")
    st.markdown(f"API docs: [{API_URL}/docs]({API_URL}/docs)")

# ── Main area ──────────────────────────────────────────────────────────────────
st.markdown("# ☁️  FinOps Cloud Optimizer")

# ── Top action bar (Step / Reset / State) ─────────────────────────────────────
col_step, col_reset, col_state, col_spacer = st.columns([1, 1, 1, 5])

with col_step:
    if st.button("▶  Step", use_container_width=True):
        # Generic step with no-op action to advance environment
        api_step("noop")
        st.rerun()

with col_reset:
    if st.button("↺  Reset", use_container_width=True):
        api_reset()
        st.rerun()

with col_state:
    if st.button("ℹ  State", use_container_width=True):
        api_state()
        st.rerun()

# ── Status bar ─────────────────────────────────────────────────────────────────
if st.session_state.status_msg:
    css_class = {
        "ok":    "status-box",
        "error": "status-box error",
        "info":  "status-box info",
    }.get(st.session_state.status_type, "status-box info")
    st.markdown(
        f'<div class="{css_class}">{st.session_state.status_msg}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Observation panels ─────────────────────────────────────────────────────────
if st.session_state.observation:
    obs       = st.session_state.observation
    cost_data = obs.get("cost_data", {})
    inventory = obs.get("inventory", [])

    # Metrics row
    st.markdown("### Status")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Episode",      obs.get("episode_id", "—")[:10] if obs.get("episode_id") else "—")
    m2.metric("Step count",   obs.get("step_count", 0))
    m3.metric("Monthly bill", f"${cost_data.get('projected_monthly_bill', 0):,.2f}")
    m4.metric("P99 latency",  f"{cost_data.get('p99_latency_ms', 0):.0f} ms")
    m5.metric("Throttle events", cost_data.get("throttle_events", 0))

    st.markdown("---")

    # Task scores row
    st.markdown("### Task scores")
    t1, t2, t3 = st.columns(3)
    t1.metric("Cleanup unattached",  f"{api_score('cleanup_unattached'):.1%}")
    t2.metric("Rightsize compute",   f"{api_score('rightsize_compute'):.1%}")
    t3.metric("Fleet strategy",      f"{api_score('fleet_strategy'):.1%}")

    st.markdown("---")

    # Inventory table
    st.markdown("### Inventory")
    if inventory:
        rows = [
            {
                "ID":       r.get("id", "")[:14],
                "Type":     r.get("resource_type", "—"),
                "Category": r.get("category", "—"),
                "CPU %":    round(r.get("cpu_usage_pct_30d", 0), 1),
                "Cost/hr":  f"${r.get('hourly_cost', 0):.3f}",
                "Region":   r.get("region", "—"),
                "State":    r.get("state", "—"),
            }
            for r in inventory
        ]
        st.dataframe(rows, use_container_width=True, height=280)
    else:
        st.info("No inventory data. Click **Reset** to load resources.")

    st.markdown("---")

    # Raw JSON
    st.markdown("### Raw JSON response")
    pretty = st.checkbox("Pretty-print", value=True)
    if pretty:
        st.json(obs)
    else:
        st.code(json.dumps(obs), language="json")

else:
    # Nothing loaded yet — show hint matching reference UI
    st.markdown(
        '<div class="status-box info">👈  Click <strong>Reset</strong> to load the environment, '
        'or <strong>State</strong> to fetch current state.</div>',
        unsafe_allow_html=True,
    )

    # Show placeholder pretty-print checkbox (matches reference)
    pretty = st.checkbox("Pretty-print", value=True)

st.markdown("---")

# ── Logs ───────────────────────────────────────────────────────────────────────
st.markdown("### Logs")
if st.session_state.logs:
    st.code("\n".join(st.session_state.logs[:40]), language="")
else:
    st.info("No logs yet — actions will appear here.")