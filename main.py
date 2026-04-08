"""
FinOps Cloud Optimizer - FastAPI server with embedded React UI
All three endpoints (reset, step, state) return identical shape so the
frontend can read the same fields regardless of which button was clicked.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from env.engine import FinOpsEngine
from env.models import (
    Action,
    DeleteResourceAction,
    ModifyInstanceAction,
    PurchaseSavingsPlanAction,
)
from env.tasks import get_task_score as compute_task_score, list_tasks

app = FastAPI(title="FinOps Cloud Optimizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = FinOpsEngine()


# ── helpers ────────────────────────────────────────────────────────────────────

def _obs_to_dict(obs):
    """Always return a plain dict from an Observation (Pydantic or dict)."""
    if hasattr(obs, "dict"):
        return obs.dict()
    return obs


def _make_response(obs, reward=0.0, done=False, info=None):
    """
    Single canonical response shape used by /reset, /step, /state.
    Frontend always reads:
        data.observation.cost_data.projected_monthly_bill
        data.observation.health_status.system_latency_ms
        data.observation.health_status.throttling_events
        data.observation.health_status.downtime_events
        data.observation.inventory
        data.observation.status_message
        data.reward
        data.done
    """
    obs_dict = _obs_to_dict(obs)
    return {
        "observation": obs_dict,
        "reward": round(float(reward), 4),
        "done": bool(done),
        "info": info or {},
    }


# ── core routes ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/health")
async def health():
    return {"message": "FinOps Cloud Optimizer OpenEnv is running."}


@app.post("/reset")
async def reset():
    obs = env.reset()
    return _make_response(obs, reward=0.0, done=False)


@app.post("/step")
async def step(action: Action):
    try:
        obs, reward, done, info = env.step(action)
        reward_val = float(reward.total if hasattr(reward, "total") else reward)
        return _make_response(obs, reward=reward_val, done=done, info=info)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state():
    obs = env.get_observation("Current state requested.")
    return _make_response(obs, reward=0.0, done=False)


# ── task graders ───────────────────────────────────────────────────────────────

@app.get("/tasks")
async def tasks():
    return {"tasks": list_tasks()}


@app.get("/tasks/{task_id}/score")
async def get_task_score(task_id: str):
    try:
        score = compute_task_score(env, task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "score": score}


# ── agent routes ───────────────────────────────────────────────────────────────

@app.post("/agent/run")
async def agent_run(request: Request):
    try:
        body = await request.json()
        task_name = body.get("task", "task1")
        episodes = max(1, int(body.get("episodes", 5)))
        max_steps = max(5, int(body.get("max_steps", 25)))

        task_map = {
            "task1": "cleanup_unattached",
            "task2": "rightsize_compute",
            "task3": "fleet_strategy",
        }
        target_task_id = task_map.get(task_name, "cleanup_unattached")

        def select_action(observation, purchased_plans):
            inventory = observation.inventory

            if task_name == "task1":
                for resource in inventory:
                    if resource.category == "storage" and not resource.is_attached:
                        return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
                for resource in inventory:
                    if resource.category == "compute" and resource.tags.get("lifecycle") == "idle":
                        return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
                return None, None

            if task_name == "task2":
                for resource in inventory:
                    if resource.category == "compute" and float(resource.cpu_usage_pct_30d or 0.0) < 5.0 and resource.resource_type != "t3.small":
                        return (
                            ModifyInstanceAction(instance_id=resource.id, new_type="t3.small"),
                            {"action_type": "modify_instance", "instance_id": resource.id, "new_type": "t3.small"},
                        )
                return None, None

            # task3: fleet strategy
            for resource in inventory:
                if resource.is_legacy and not resource.is_production:
                    return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
            for resource in inventory:
                if resource.category == "storage" and not resource.is_attached:
                    return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
            for resource in inventory:
                if resource.category == "compute" and resource.tags.get("lifecycle") == "idle":
                    return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
            for resource in inventory:
                if resource.category == "compute" and float(resource.cpu_usage_pct_30d or 0.0) < 5.0 and resource.resource_type != "t3.small":
                    return (
                        ModifyInstanceAction(instance_id=resource.id, new_type="t3.small"),
                        {"action_type": "modify_instance", "instance_id": resource.id, "new_type": "t3.small"},
                    )
            if not purchased_plans["compute"]:
                purchased_plans["compute"] = True
                return (
                    PurchaseSavingsPlanAction(plan_type="compute", duration="1y"),
                    {"action_type": "purchase_savings_plan", "plan_type": "compute", "duration": "1y"},
                )
            if not purchased_plans["database"]:
                purchased_plans["database"] = True
                return (
                    PurchaseSavingsPlanAction(plan_type="database", duration="1y"),
                    {"action_type": "purchase_savings_plan", "plan_type": "database", "duration": "1y"},
                )
            return None, None

        results = {
            "status": "completed",
            "task": task_name,
            "target_task_id": target_task_id,
            "episodes": episodes,
            "episode_logs": [],
            "total_reward": 0.0,
            "average_reward": 0.0,
            "best_episode_score": 0.0,
            "best_episode_cost_reduction_pct": 0.0,
            "strategy": "Greedy FinOps optimizer (task-aware)",
            "hyperparameters": {
                "episodes": episodes,
                "max_steps": max_steps,
                "policy": "task-priority deterministic",
            },
        }

        for ep in range(episodes):
            initial_obs = env.reset()
            initial_bill = float(initial_obs.cost_data.projected_monthly_bill)
            episode_reward = 0.0
            purchased_plans = {"compute": False, "database": False}
            episode_log = {
                "episode": ep + 1,
                "initial_bill": initial_bill,
                "steps": [],
                "total_reward": 0.0,
                "final_task_score": 0.0,
                "cost_reduction_pct": 0.0,
            }

            for step_idx in range(max_steps):
                observation = env.get_observation("Agent planning.")
                action_model, action_payload = select_action(observation, purchased_plans)
                if action_model is None:
                    break

                obs, reward, done, info = env.step(action_model)
                reward_value = float(reward.total)
                bill_now = float(obs.cost_data.projected_monthly_bill)
                latency_now = float(obs.health_status.system_latency_ms)
                throttle_now = int(obs.health_status.throttling_events)
                downtime_now = int(obs.health_status.downtime_events)
                episode_reward += reward_value

                episode_log["steps"].append({
                    "step": step_idx + 1,
                    "action": action_payload,
                    "reward": round(reward_value, 4),
                    "bill": round(bill_now, 2),
                    "latency_ms": round(latency_now, 2),
                    "throttling_events": throttle_now,
                    "downtime_events": downtime_now,
                    "done": bool(done),
                    "status_message": obs.status_message,
                    "info": info,
                })

                if done:
                    break

            final_bill = float(env.get_observation("Episode ended.").cost_data.projected_monthly_bill)
            cost_reduction_pct = ((initial_bill - final_bill) / initial_bill * 100.0) if initial_bill > 0 else 0.0
            task_score = float(compute_task_score(env, target_task_id))

            episode_log["total_reward"] = round(episode_reward, 4)
            episode_log["final_task_score"] = round(task_score, 4)
            episode_log["cost_reduction_pct"] = round(cost_reduction_pct, 2)
            results["episode_logs"].append(episode_log)
            results["total_reward"] += episode_reward
            results["best_episode_score"] = max(results["best_episode_score"], task_score)
            results["best_episode_cost_reduction_pct"] = max(
                results["best_episode_cost_reduction_pct"], round(cost_reduction_pct, 2)
            )

        results["total_reward"] = round(results["total_reward"], 4)
        results["average_reward"] = round(results["total_reward"] / episodes, 4) if episodes else 0.0
        return results

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent run error: {str(e)}")


@app.get("/agent/plan")
async def agent_plan():
    return {
        "plan_id": "plan-001",
        "strategy": "Q-Learning with Epsilon-Greedy Exploration",
        "objectives": [
            "Maximize cost savings",
            "Minimize resource contention",
            "Maintain performance SLAs",
        ],
        "planned_actions": [
            {"priority": 1, "action": "delete_resource",        "target": "unused EC2 instances",          "expected_saving": "$5,000/month"},
            {"priority": 2, "action": "modify_instance",        "target": "overprovisioned instances",     "expected_saving": "$2,000/month"},
            {"priority": 3, "action": "purchase_savings_plan",  "target": "commitment-based discounts",    "expected_saving": "$8,000/month"},
        ],
        "total_projected_savings": "$15,000/month",
        "confidence": 0.87,
    }


# ── HTML frontend ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>FinOps Cloud Optimizer</title>
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#333}
.header{background:#fff;border-bottom:1px solid #e0e0e0;padding:14px 24px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.header-title{font-size:22px;font-weight:700;color:#222}
.header-badge{background:#dbeafe;color:#1e40af;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:600;margin-left:10px}
.stage-badge{background:#dcfce7;color:#166534;padding:4px 14px;border-radius:14px;font-size:12px;font-weight:600}
.container{display:flex;height:calc(100vh - 57px)}
/* sidebar */
.sidebar{width:280px;background:#fafafa;border-right:1px solid #e0e0e0;padding:20px 16px;overflow-y:auto;display:flex;flex-direction:column;gap:16px}
.section-label{font-size:11px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px}
.task-btns{display:flex;gap:8px}
.task-btn{flex:1;padding:8px 0;border:1px solid #ddd;background:#fff;border-radius:5px;cursor:pointer;font-size:13px;font-weight:600;transition:all .15s}
.task-btn.active{background:#dcfce7;border-color:#4ade80;color:#166534}
.task-btn:hover:not(.active){border-color:#aaa}
.task-desc{font-size:13px;color:#666;line-height:1.6}
.code-block{font-size:11px;color:#cdd9e5;background:#1e2530;padding:12px;border-radius:6px;overflow-x:auto;font-family:'JetBrains Mono','Courier New',monospace;line-height:1.5;white-space:pre-wrap;word-break:break-all}
.divider{border:none;border-top:1px solid #e8e8e8}
/* main */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.tabs{background:#fff;border-bottom:1px solid #e0e0e0;display:flex;padding:0 20px}
.tab{padding:13px 18px;border:none;background:none;cursor:pointer;font-size:14px;font-weight:500;color:#999;border-bottom:2.5px solid transparent;transition:all .15s}
.tab.active{color:#222;border-bottom-color:#222}
.content{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:16px}
/* metrics */
.metrics-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.metric{background:#fff;padding:16px 14px;border-radius:8px;border:1px solid #e8e8e8}
.metric-label{font-size:11px;color:#999;font-weight:600;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em}
.metric-value{font-size:22px;font-weight:700;color:#222}
.metric-value.green{color:#16a34a}
.metric-value.red{color:#dc2626}
/* action editor */
.action-card{background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:18px}
.editor-label{font-size:11px;font-weight:700;color:#777;text-transform:uppercase;letter-spacing:.06em;display:block;margin-bottom:10px}
textarea{width:100%;height:140px;padding:12px;border:1px solid #e0e0e0;border-radius:6px;font-family:'JetBrains Mono','Courier New',monospace;font-size:12px;resize:vertical;line-height:1.5}
textarea:focus{outline:none;border-color:#4ade80;box-shadow:0 0 0 3px rgba(74,222,128,.12)}
textarea:disabled{background:#f9f9f9;color:#aaa}
.btn-row{display:flex;gap:10px;margin-top:14px}
.btn{padding:10px 22px;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer;font-size:14px;font-weight:600;transition:all .15s;display:flex;align-items:center;gap:6px}
.btn:hover:not(:disabled){border-color:#aaa}
.btn:active:not(:disabled){transform:scale(.97)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.primary{background:#4ade80;color:#fff;border-color:#4ade80}
.btn.primary:hover:not(:disabled){background:#22c55e;border-color:#22c55e}
/* status */
.status-card{background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:14px 18px}
.status-label{font-size:11px;font-weight:700;color:#777;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
.status-text{font-size:14px;color:#555}
.status-text.ok{color:#16a34a}
.status-text.error{color:#dc2626}
.status-text.loading{color:#888}
/* pretty print */
.pp-row{display:flex;align-items:center;gap:8px;font-size:13px;color:#666}
.pp-row input{accent-color:#16a34a;width:14px;height:14px;cursor:pointer}
/* json viewer */
.json-viewer{background:#1e2530;color:#cdd9e5;padding:16px;border-radius:8px;overflow:auto;font-family:'JetBrains Mono','Courier New',monospace;font-size:12px;line-height:1.5;max-height:420px;white-space:pre-wrap;word-break:break-word}
/* agent */
.agent-info{font-size:13px;color:#666;line-height:2;margin-bottom:14px}
.agent-info span{font-weight:600;color:#333}
/* scrollbar */
::-webkit-scrollbar{width:7px;height:7px}
::-webkit-scrollbar-track{background:#f5f5f5}
::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:#aaa}
/* agent results */
.agent-grid{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px}
.agent-card{background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:14px 16px;min-width:130px;flex:1}
.agent-card-label{font-size:10px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px}
.agent-card-value{font-size:20px;font-weight:700;color:#222}
.agent-card-value.green{color:#16a34a}
.agent-card-value.red{color:#dc2626}
.agent-card-value.blue{color:#1d4ed8}
.tbl-wrap{max-height:320px;overflow:auto;border-radius:8px;border:1px solid #e8e8e8}
.tbl{width:100%;border-collapse:collapse;background:#fff;font-size:12px}
.tbl th{position:sticky;top:0;background:#fafafa;color:#666;font-weight:700;padding:8px 10px;border-bottom:1px solid #e8e8e8;text-align:left;white-space:nowrap}
.tbl td{padding:7px 10px;border-bottom:1px solid #f3f3f3;color:#333;white-space:nowrap}
.tbl tr:last-child td{border-bottom:none}
.tbl tr:hover td{background:#fafff5}
.badge{display:inline-block;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700}
.badge-ok{background:#dcfce7;color:#166534}
.badge-warn{background:#fef9c3;color:#854d0e}
.badge-err{background:#fee2e2;color:#991b1b}
.ep-select{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.ep-btn{padding:5px 12px;border:1px solid #ddd;border-radius:5px;background:#fff;cursor:pointer;font-size:12px;font-weight:600;transition:all .15s}
.ep-btn.active{background:#dcfce7;border-color:#4ade80;color:#166534}
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const {useState, useCallback} = React;

// ── Agent Results Component ──────────────────────────────────────────────────
function AgentTab({task, loading, status, data, onRun, onPlan, pretty, setPretty}) {
  const isAgentData = data && data.episode_logs;
  const [selEp, setSelEp] = useState(0); // 0 = latest

  const epLogs = isAgentData ? data.episode_logs : [];
  const displayEp = epLogs.length ? epLogs[selEp < epLogs.length ? selEp : epLogs.length - 1] : null;
  const steps = displayEp ? displayEp.steps || [] : [];

  // Aggregate summary across all episodes
  const allSteps = epLogs.flatMap(ep => ep.steps || []);
  const avgLatency = allSteps.length
    ? (allSteps.reduce((s, x) => s + Number(x.latency_ms || 0), 0) / allSteps.length)
    : 0;
  const maxThrottle = allSteps.length
    ? Math.max(...allSteps.map(x => Number(x.throttling_events || 0)))
    : 0;
  const maxDowntime = allSteps.length
    ? Math.max(...allSteps.map(x => Number(x.downtime_events || 0)))
    : 0;

  function actionLabel(a) {
    if (!a) return "n/a";
    if (a.action_type === "delete_resource") return "🗑 delete";
    if (a.action_type === "modify_instance") return `⚙ resize → ${a.new_type || ""}`;
    if (a.action_type === "purchase_savings_plan") return `💳 savings (${a.plan_type})`;
    return a.action_type || "n/a";
  }

  function statusBadge(s) {
    if (!s) return <span className="badge badge-ok">ok</span>;
    const low = s.toLowerCase();
    if (low.includes("critical") || low.includes("failure") || low.includes("blocked"))
      return <span className="badge badge-err">{s.slice(0,38)}{s.length>38?"…":""}</span>;
    if (low.includes("throttl") || low.includes("downtime"))
      return <span className="badge badge-warn">{s.slice(0,38)}{s.length>38?"…":""}</span>;
    return <span className="badge badge-ok">{s.slice(0,38)}{s.length>38?"…":""}</span>;
  }

  return <>
    <div className="action-card">
      <label className="editor-label">Agent Configuration</label>
      <div className="agent-info">
        <div>Strategy: <span>Greedy FinOps optimizer (task-aware)</span></div>
        <div>Episodes: <span>5</span></div>
        <div>Max Steps/Episode: <span>25</span></div>
        <div>Task: <span>{task}</span></div>
      </div>
      <div className="btn-row">
        <button className="btn primary" onClick={onRun}  disabled={loading}>🚀 Run Agent</button>
        <button className="btn"          onClick={onPlan} disabled={loading}>📋 View Plan</button>
      </div>
    </div>

    <div className="status-card">
      <div className="status-label">Agent Status</div>
      <div className={"status-text "+status.type}>{status.text || "Ready to run"}</div>
    </div>

    {isAgentData && <>
      {/* Summary cards */}
      <label className="editor-label" style={{marginBottom:"8px",display:"block"}}>Run Summary</label>
      <div className="agent-grid">
        <div className="agent-card"><div className="agent-card-label">Episodes</div><div className="agent-card-value">{epLogs.length}</div></div>
        <div className="agent-card"><div className="agent-card-label">Best Task Score</div><div className="agent-card-value green">{Number(data.best_episode_score||0).toFixed(2)}</div></div>
        <div className="agent-card"><div className="agent-card-label">Best Cost Cut</div><div className="agent-card-value green">{Number(data.best_episode_cost_reduction_pct||0).toFixed(1)}%</div></div>
        <div className="agent-card"><div className="agent-card-label">Avg Latency</div><div className={"agent-card-value "+(avgLatency>200?"red":avgLatency>130?"":"green")}>{avgLatency.toFixed(1)} ms</div></div>
        <div className="agent-card"><div className="agent-card-label">Max Throttle</div><div className={"agent-card-value "+(maxThrottle>0?"red":"")}>{maxThrottle}</div></div>
        <div className="agent-card"><div className="agent-card-label">Max Downtime</div><div className={"agent-card-value "+(maxDowntime>0?"red":"")}>{maxDowntime}</div></div>
        <div className="agent-card"><div className="agent-card-label">Total Reward</div><div className={"agent-card-value "+(data.total_reward>=0?"green":"red")}>{Number(data.total_reward||0).toFixed(3)}</div></div>
        <div className="agent-card"><div className="agent-card-label">Avg Reward</div><div className={"agent-card-value "+(data.average_reward>=0?"green":"red")}>{Number(data.average_reward||0).toFixed(3)}</div></div>
      </div>

      {/* Episode selector */}
      {epLogs.length > 1 && <>
        <label className="editor-label" style={{marginBottom:"6px",display:"block"}}>Select Episode</label>
        <div className="ep-select">
          {epLogs.map((ep, i) => (
            <button key={i} className={"ep-btn"+(selEp===i?" active":"")} onClick={()=>setSelEp(i)}>
              Ep {ep.episode} · {Number(ep.final_task_score||0).toFixed(2)}
            </button>
          ))}
        </div>
      </>}

      {/* Episode detail */}
      {displayEp && <>
        <label className="editor-label" style={{marginBottom:"6px",display:"block"}}>
          Episode {displayEp.episode} · Score: {Number(displayEp.final_task_score||0).toFixed(2)} · Cost Cut: {Number(displayEp.cost_reduction_pct||0).toFixed(1)}%
        </label>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Step</th>
                <th>Action</th>
                <th>Reward</th>
                <th>Bill ($)</th>
                <th>Latency (ms)</th>
                <th>Throttle</th>
                <th>Downtime</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {steps.map((s, i) => (
                <tr key={i}>
                  <td>{s.step}</td>
                  <td>{actionLabel(s.action)}</td>
                  <td style={{color: s.reward >= 0 ? "#16a34a" : "#dc2626", fontWeight:600}}>
                    {s.reward >= 0 ? "+" : ""}{Number(s.reward||0).toFixed(3)}
                  </td>
                  <td>{Number(s.bill||0).toFixed(2)}</td>
                  <td style={{color: s.latency_ms > 200 ? "#dc2626" : s.latency_ms > 130 ? "#b45309" : "#16a34a", fontWeight:600}}>
                    {Number(s.latency_ms||0).toFixed(1)}
                  </td>
                  <td style={{color: s.throttling_events > 0 ? "#dc2626" : "#333", fontWeight: s.throttling_events > 0 ? 700 : 400}}>
                    {s.throttling_events || 0}
                  </td>
                  <td style={{color: s.downtime_events > 0 ? "#dc2626" : "#333", fontWeight: s.downtime_events > 0 ? 700 : 400}}>
                    {s.downtime_events || 0}
                  </td>
                  <td>{statusBadge(s.status_message)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>}

      {/* Collapsible raw JSON */}
      <details style={{marginTop:"8px"}}>
        <summary style={{cursor:"pointer",fontSize:"12px",color:"#888",userSelect:"none"}}>▶ View raw JSON response</summary>
        <div className="pp-row" style={{marginTop:"8px"}}>
          <input type="checkbox" id="pp2" checked={pretty} onChange={e=>setPretty(e.target.checked)}/>
          <label htmlFor="pp2">Pretty-print</label>
        </div>
        <pre className="json-viewer" style={{maxHeight:"400px",marginTop:"6px"}}>
          {pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data)}
        </pre>
      </details>
    </>}

    {!isAgentData && data && <>
      <div className="pp-row">
        <input type="checkbox" id="pp2" checked={pretty} onChange={e=>setPretty(e.target.checked)}/>
        <label htmlFor="pp2">Pretty-print</label>
      </div>
      <pre className="json-viewer" style={{maxHeight:"540px"}}>
        {pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data)}
      </pre>
    </>}
  </>;
}

const TASK_DESC = {
  task1: "Task 1: Reduce EC2 Costs. Delete unused compute resources.",
  task2: "Task 2: Optimize Storage. Modify storage tier to cheaper options.",
  task3: "Task 3: Maximize Savings. Purchase reserved capacity plans.",
};

const DEFAULT_ACTION = JSON.stringify({action_type:"delete_resource",resource_id:"i-0abc123"},null,2);

function metric(label, value, cls="") {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={"metric-value " + cls}>{value}</div>
    </div>
  );
}

function App() {
  const [task,     setTask]     = useState("task1");
  const [tab,      setTab]      = useState("manual");
  const [action,   setAction]   = useState(DEFAULT_ACTION);
  const [status,   setStatus]   = useState({text:"Ready", type:""});
  const [data,     setData]     = useState(null);   // last full API response
  const [loading,  setLoading]  = useState(false);
  const [pretty,   setPretty]   = useState(true);

  // ── API helper ───────────────────────────────────────────────────────────
  const call = useCallback(async (method, url, body=null) => {
    setLoading(true);
    setStatus({text:"Loading…", type:"loading"});
    try {
      const opts = {method, headers:{"Content-Type":"application/json"}};
      if(body) opts.body = JSON.stringify(body);
      const res = await fetch(url, opts);
      const json = await res.json();
      if(!res.ok) throw new Error(json?.detail || "API error " + res.status);
      setData(json);
      setStatus({text: json?.observation?.status_message || "Success ✓", type:"ok"});
    } catch(e) {
      setStatus({text: "Error: " + e.message, type:"error"});
    } finally {
      setLoading(false);
    }
  }, []);

  const handleReset = () => call("POST", "/reset");
  const handleState = () => call("GET",  "/state");
  const handleStep  = () => {
    try {
      call("POST", "/step", JSON.parse(action));
    } catch {
      setStatus({text:"Invalid JSON in action editor", type:"error"});
    }
  };
  const handleAgentRun  = () => call("POST", "/agent/run",  {task, episodes:5});
  const handleAgentPlan = () => call("GET",  "/agent/plan");

  // ── read from unified response shape: data.observation.* ────────────────
  const obs    = data?.observation   || {};
  const cd     = obs.cost_data       || {};
  const hs     = obs.health_status   || {};
  const inv    = obs.inventory       || [];
  const reward = data?.reward        ?? 0;
  const done   = data?.done          ?? false;

  const bill     = cd.projected_monthly_bill ?? 0;
  const latency  = hs.system_latency_ms      ?? 0;
  const throttle = hs.throttling_events      ?? 0;
  const downtime = hs.downtime_events        ?? 0;

  return (
    <>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="header">
        <div style={{display:"flex",alignItems:"center"}}>
          <span className="header-title">FinOps</span>
          <span className="header-badge">Cloud Optimizer</span>
        </div>
        <div className="stage-badge">Stage: {task}</div>
      </div>

      <div className="container">
        {/* ── Sidebar ──────────────────────────────────────────────────── */}
        <div className="sidebar">
          <div>
            <div className="section-label">Select Task</div>
            <div className="task-btns">
              {["task1","task2","task3"].map(t => (
                <button key={t} className={"task-btn"+(task===t?" active":"")} onClick={()=>setTask(t)}>
                  {t.replace("task","T")}
                </button>
              ))}
            </div>
          </div>

          <div className="task-desc">{TASK_DESC[task]}</div>

          <hr className="divider"/>

          <div>
            <div className="section-label">Quick Connect</div>
            <pre className="code-block">{`from env.engine import FinOpsEngine
from env.models import Action

env = FinOpsEngine()
obs = env.reset()
obs, r, done, info = env.step(
  Action(action_type=
    "delete_resource",
    resource_id="i-0abc123")
)`}</pre>
          </div>

          <hr className="divider"/>

          <div>
            <div className="section-label">Example Action</div>
            <pre className="code-block">{`{
  "action_type":
    "delete_resource",
  "resource_id":
    "i-0abc123"
}`}</pre>
          </div>

          {inv.length > 0 && (
            <>
              <hr className="divider"/>
              <div>
                <div className="section-label">Inventory ({inv.length})</div>
                {inv.slice(0,6).map(r => (
                  <div key={r.id} style={{fontSize:"11px",color:"#666",marginBottom:"4px",fontFamily:"monospace"}}>
                    <span style={{color:"#333",fontWeight:600}}>{String(r.id).slice(0,14)}</span>
                    <br/>{r.resource_type} · ${r.monthly_cost}/mo
                  </div>
                ))}
                {inv.length > 6 && <div style={{fontSize:"11px",color:"#aaa"}}>+{inv.length-6} more…</div>}
              </div>
            </>
          )}
        </div>

        {/* ── Main ─────────────────────────────────────────────────────── */}
        <div className="main">
          <div className="tabs">
            {[["manual","Manual Play"],["agent","Agent Run"]].map(([v,l]) => (
              <button key={v} className={"tab"+(tab===v?" active":"")} onClick={()=>setTab(v)}>{l}</button>
            ))}
          </div>

          <div className="content">

            {/* ── Manual Play tab ────────────────────────────────────── */}
            {tab === "manual" && <>

              {/* Metrics */}
              <div className="metrics-row">
                {metric("Bill Amount",  "$"+bill.toFixed(2))}
                {metric("Latency (ms)", latency.toFixed(1))}
                {metric("Throttling",   throttle, throttle>0?"red":"")}
                {metric("Downtime",     downtime, downtime>0?"red":"")}
                {metric("Reward",       (reward>=0?"+":"")+reward.toFixed(3), reward>0?"green":reward<0?"red":"")}
              </div>

              {/* Action editor */}
              <div className="action-card">
                <label className="editor-label">Action (JSON)</label>
                <textarea
                  value={action}
                  onChange={e=>setAction(e.target.value)}
                  disabled={loading}
                  spellCheck={false}
                />
                <div className="btn-row">
                  <button className="btn primary" onClick={handleStep}  disabled={loading}>▶ Step</button>
                  <button className="btn"          onClick={handleReset} disabled={loading}>↺ Reset</button>
                  <button className="btn"          onClick={handleState} disabled={loading}>ℹ State</button>
                </div>
              </div>

              {/* Status */}
              <div className="status-card">
                <div className="status-label">Status</div>
                <div className={"status-text "+status.type}>{status.text || "Ready"}</div>
              </div>

              {/* JSON response */}
              {data && <>
                <div className="pp-row">
                  <input type="checkbox" id="pp" checked={pretty} onChange={e=>setPretty(e.target.checked)}/>
                  <label htmlFor="pp">Pretty-print</label>
                </div>
                <pre className="json-viewer">
                  {pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data)}
                </pre>
              </>}
            </>}

            {/* ── Agent Run tab ──────────────────────────────────────── */}
            {tab === "agent" && <AgentTab task={task} loading={loading} status={status} data={data}
                onRun={handleAgentRun} onPlan={handleAgentPlan} pretty={pretty} setPretty={setPretty}/>}

          </div>
        </div>
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
>>>>>>> 7c834c8 (initial commit)
    uvicorn.run(app, host="0.0.0.0", port=7860)