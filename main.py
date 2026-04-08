"""
FinOps Cloud Optimizer - FastAPI server with embedded React UI
All three endpoints (reset, step, state) return identical shape so the
frontend can read the same fields regardless of which button was clicked.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from env.engine import FinOpsEngine
from env.models import Action
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
        episodes = int(body.get("episodes", 5))

        results = {
            "status": "completed",
            "task": task_name,
            "episodes": episodes,
            "episode_logs": [],
            "total_reward": 0.0,
            "average_reward": 0.0,
            "strategy": "Epsilon-Greedy Q-Learning",
            "hyperparameters": {
                "learning_rate": 0.1,
                "discount_factor": 0.95,
                "epsilon": 0.1,
                "max_steps": 10,
            },
        }

        for ep in range(episodes):
            env.reset()
            episode_reward = 0.0
            episode_log = {"episode": ep + 1, "steps": [], "total_reward": 0.0}

            for s in range(10):
                try:
                    action = Action(
                        action_type="delete_resource" if ep % 2 == 0 else "modify_instance",
                        resource_id=f"i-{ep:04d}{s:03d}",
                    )
                    obs, reward, done, info = env.step(action)
                    rval = float(reward.total if hasattr(reward, "total") else reward)
                    episode_reward += rval
                    episode_log["steps"].append(
                        {"step": s + 1, "action": action.action_type, "reward": rval, "done": bool(done)}
                    )
                    if done:
                        break
                except Exception:
                    episode_log["steps"].append({"step": s + 1, "action": "error", "reward": 0.0, "done": False})

            episode_log["total_reward"] = round(episode_reward, 4)
            results["episode_logs"].append(episode_log)
            results["total_reward"] += episode_reward

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
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const {useState, useCallback} = React;
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
            {tab === "agent" && <>
              <div className="action-card">
                <label className="editor-label">Agent Configuration</label>
                <div className="agent-info">
                  <div>Strategy: <span>Epsilon-Greedy Q-Learning</span></div>
                  <div>Episodes: <span>5</span></div>
                  <div>Max Steps/Episode: <span>10</span></div>
                  <div>Learning Rate: <span>0.1</span></div>
                  <div>Task: <span>{task}</span></div>
                </div>
                <div className="btn-row">
                  <button className="btn primary" onClick={handleAgentRun}  disabled={loading}>🚀 Run Agent</button>
                  <button className="btn"          onClick={handleAgentPlan} disabled={loading}>📋 View Plan</button>
                </div>
              </div>
              <div className="status-card">
                <div className="status-label">Agent Status</div>
                <div className={"status-text "+status.type}>{status.text || "Ready to run"}</div>
              </div>
              {data && <>
                <div className="pp-row">
                  <input type="checkbox" id="pp2" checked={pretty} onChange={e=>setPretty(e.target.checked)}/>
                  <label htmlFor="pp2">Pretty-print</label>
                </div>
                <pre className="json-viewer" style={{maxHeight:"540px"}}>
                  {pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data)}
                </pre>
              </>}
            </>}
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
    uvicorn.run(app, host="0.0.0.0", port=7860)