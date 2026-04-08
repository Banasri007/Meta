"""
FinOps Cloud Optimizer - FastAPI server with embedded React UI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from env.engine import FinOpsEngine
from env.models import Action
from env.tasks import get_task_score as compute_task_score, list_tasks

# ────────────────────────────────────────────────────────────────────────────
# HTML TEMPLATE WITH EMBEDDED REACT UI
# ────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinOps Cloud Optimizer</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; background-color: #f5f5f5; color: #333; }
        .header { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .header-title { font-size: 24px; font-weight: 600; color: #333; }
        .header-badge { background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .header-right { display: flex; gap: 16px; align-items: center; }
        .stage-badge { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500; }
        .container { display: flex; height: calc(100vh - 64px); }
        .sidebar { width: 280px; background: #f9f9f9; border-right: 1px solid #e0e0e0; padding: 24px 16px; overflow-y: auto; }
        .task-label { font-size: 12px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
        .task-buttons { display: flex; gap: 8px; margin-bottom: 24px; }
        .task-btn { flex: 1; padding: 8px 12px; border: 1px solid #ddd; background: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
        .task-btn.active { background: #dcfce7; border-color: #4ade80; color: #166534; }
        .task-btn:hover { border-color: #999; }
        .task-desc { font-size: 13px; color: #666; line-height: 1.5; margin-bottom: 24px; }
        .sidebar-divider { border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }
        .code-snippet { font-size: 11px; color: #666; background: #f0f0f0; padding: 12px; border-radius: 4px; overflow: auto; max-height: 150px; font-family: 'Monaco', 'Courier New', monospace; line-height: 1.4; }
        .main-content { flex: 1; display: flex; flex-direction: column; }
        .tabs { background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; padding: 0 24px; }
        .tab { padding: 12px 16px; border: none; background: none; cursor: pointer; font-size: 14px; font-weight: 500; color: #999; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab.active { color: #333; border-bottom-color: #333; }
        .content { flex: 1; overflow-y: auto; padding: 24px; }
        .metrics-row { display: flex; gap: 16px; margin-bottom: 24px; }
        .metric { flex: 1; background: #fff; padding: 16px; border-radius: 8px; border: 1px solid #e0e0e0; }
        .metric-label { font-size: 12px; color: #999; font-weight: 500; margin-bottom: 8px; }
        .metric-value { font-size: 24px; font-weight: 600; color: #333; }
        .action-editor { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .editor-label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; display: block; }
        textarea { width: 100%; height: 150px; padding: 12px; border: 1px solid #e0e0e0; border-radius: 4px; font-family: 'Monaco', 'Courier New', monospace; font-size: 12px; resize: vertical; }
        textarea:focus { outline: none; border-color: #4ade80; box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.1); }
        textarea:disabled { background: #f5f5f5; color: #999; }
        .button-group { display: flex; gap: 12px; margin-top: 16px; }
        button { padding: 10px 20px; border: 1px solid #e0e0e0; border-radius: 4px; background: #fff; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; }
        button.primary { background: #4ade80; color: #fff; border-color: #4ade80; }
        button.primary:hover { background: #22c55e; }
        button:hover { border-color: #999; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .status-box { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .status-label { font-size: 12px; font-weight: 600; color: #666; margin-bottom: 8px; }
        .status-message { color: #4ade80; font-size: 14px; }
        .status-message.error { color: #ef4444; }
        .checkbox-group { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
        .checkbox-group label { font-size: 14px; cursor: pointer; }
        .json-viewer { background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; overflow: auto; font-family: 'Monaco', 'Courier New', monospace; font-size: 12px; line-height: 1.5; max-height: 400px; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #f5f5f5; }
        ::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #999; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const { useState } = React;
        function App() {
            const [task, setTask] = useState('task1');
            const [tab, setTab] = useState('manual');
            const [action, setAction] = useState(JSON.stringify({action_type: 'delete_resource', resource_id: 'i-0abc123'}, null, 2));
            const [status, setStatus] = useState({ text: '', type: 'info' });
            const [response, setResponse] = useState(null);
            const [loading, setLoading] = useState(false);
            const [prettyPrint, setPrettyPrint] = useState(true);

            const taskDescriptions = {
                task1: "Task 1: Reduce EC2 Costs. Delete unused compute resources.",
                task2: "Task 2: Optimize Storage. Modify storage tier to cheaper options.",
                task3: "Task 3: Maximize Savings. Purchase reserved capacity plans."
            };

            const apiCall = async (method, endpoint, payload = null) => {
                setLoading(true);
                try {
                    const options = { method, headers: { 'Content-Type': 'application/json' } };
                    if (payload) options.body = JSON.stringify(payload);
                    const resp = await fetch(endpoint, options);
                    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
                    const data = await resp.json();
                    setResponse(data);
                    setStatus({ text: 'Success', type: 'success' });
                    return data;
                } catch (err) {
                    setStatus({ text: `Error: ${err.message}`, type: 'error' });
                    setResponse(null);
                }
                setLoading(false);
            };

            const handleReset = async () => { setLoading(true); await apiCall('POST', '/reset'); setLoading(false); };
            const handleState = async () => { setLoading(true); await apiCall('GET', '/state'); setLoading(false); };
            const handleStep = async () => {
                try {
                    const parsed = JSON.parse(action);
                    setLoading(true);
                    await apiCall('POST', '/step', parsed);
                    setLoading(false);
                } catch {
                    setStatus({ text: 'Invalid JSON in action editor', type: 'error' });
                }
            };

            return (
                <>
                    <div className="header">
                        <div className="header-left">
                            <div className="header-title">FinOps</div>
                            <div className="header-badge">Cloud Optimizer</div>
                        </div>
                        <div className="header-right"><div className="stage-badge">Stage: {task}</div></div>
                    </div>
                    <div className="container">
                        <div className="sidebar">
                            <div className="task-label">Select Task</div>
                            <div className="task-buttons">
                                {['task1', 'task2', 'task3'].map(t => (
                                    <button key={t} className={`task-btn ${task === t ? 'active' : ''}`} onClick={() => setTask(t)}>
                                        {t.replace('task', 'T')}
                                    </button>
                                ))}
                            </div>
                            <div className="task-desc">{taskDescriptions[task]}</div>
                            <hr className="sidebar-divider" />
                            <div className="task-label">Example Action</div>
                            <div className="code-snippet">{`{\\n  "action_type": "delete_resource",\\n  "resource_id": "i-0abc123"\\n}`}</div>
                        </div>
                        <div className="main-content">
                            <div className="tabs">
                                {['manual', 'agent', 'supplier'].map(t => (
                                    <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
                                        {t === 'manual' ? 'Manual Play' : t === 'agent' ? 'Agent Run' : 'Play as Supplier'}
                                    </button>
                                ))}
                            </div>
                            <div className="content">
                                {tab === 'manual' && (
                                    <>
                                        <div className="metrics-row">
                                            <div className="metric">
                                                <div className="metric-label">Reward</div>
                                                <div className="metric-value">{response?.reward ?? 0}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Done</div>
                                                <div className="metric-value">{response?.done ? 'Yes' : 'No'}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Round</div>
                                                <div className="metric-value">{response?.observation?.round ?? 0}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Price</div>
                                                <div className="metric-value">${response?.observation?.market_price ?? 0}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Market</div>
                                                <div className="metric-value">{response?.observation?.market_condition ?? 'N/A'}</div>
                                            </div>
                                        </div>
                                        <div className="action-editor">
                                            <label className="editor-label">Action (JSON)</label>
                                            <textarea value={action} onChange={(e) => setAction(e.target.value)} disabled={loading} />
                                            <div className="button-group">
                                                <button className="primary" onClick={handleStep} disabled={loading}>▶ Step</button>
                                                <button onClick={handleReset} disabled={loading}>↺ Reset</button>
                                                <button onClick={handleState} disabled={loading}>ℹ State</button>
                                            </div>
                                        </div>
                                        <div className="status-box">
                                            <div className="status-label">Status</div>
                                            <div className={`status-message ${status.type === 'error' ? 'error' : ''}`}>
                                                {status.text || 'Ready'}
                                            </div>
                                        </div>
                                        {response && (
                                            <>
                                                <div className="checkbox-group">
                                                    <input type="checkbox" id="pretty" checked={prettyPrint} onChange={(e) => setPrettyPrint(e.target.checked)} />
                                                    <label htmlFor="pretty">Pretty Print</label>
                                                </div>
                                                <div className="json-viewer">
                                                    {prettyPrint ? JSON.stringify(response, null, 2) : JSON.stringify(response)}
                                                </div>
                                            </>
                                        )}
                                    </>
                                )}
                                {tab === 'agent' && <div style={{padding: '20px', textAlign: 'center', color: '#999'}}>Agent Run feature coming soon...</div>}
                                {tab === 'supplier' && <div style={{padding: '20px', textAlign: 'center', color: '#999'}}>Play as Supplier feature coming soon...</div>}
                            </div>
                        </div>
                    </div>
                </>
            );
        }
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
"""

# ────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="FinOps Cloud Optimizer")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engine
env = FinOpsEngine()

# ────────────────────────────────────────────────────────────────────────────
# API ROUTES
# ────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve React frontend"""
    return HTML_TEMPLATE

@app.post("/reset")
async def reset():
    """Reset environment"""
    initial_obs = env.reset()
    return initial_obs

@app.post("/step")
async def step(action: Action):
    """Execute action"""
    try:
        obs, reward, done, info = env.step(action)
        return {
            "observation": obs,
            "reward": reward.total if hasattr(reward, 'total') else reward,
            "reward_detail": reward,
            "done": done,
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
async def state():
    """Get current state"""
    return env.get_observation("Current state requested.")

@app.get("/tasks")
async def tasks():
    """List tasks"""
    return {"tasks": list_tasks()}

@app.get("/tasks/{task_id}/score")
async def get_task_score(task_id: str):
    """Get task score"""
    try:
        score = compute_task_score(env, task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "score": score}

# ────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "message": "FinOps Cloud Optimizer is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
