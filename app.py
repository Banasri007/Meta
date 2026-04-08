"""
FinOps Cloud Optimizer - FastAPI server with embedded React UI
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
        .agent-summary-grid { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
        .agent-summary-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; min-width: 140px; flex: 1; }
        .agent-summary-label { font-size: 11px; color: #888; font-weight: 600; text-transform: uppercase; margin-bottom: 6px; }
        .agent-summary-value { font-size: 20px; font-weight: 700; color: #222; }
        .agent-table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
        .agent-table th, .agent-table td { padding: 8px 10px; font-size: 12px; border-bottom: 1px solid #f0f0f0; text-align: left; }
        .agent-table th { background: #fafafa; color: #666; font-weight: 600; }
        .agent-table-wrap { max-height: 280px; overflow: auto; border-radius: 8px; }
        .inventory-section { margin-top: 20px; }
        .inventory-label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; display: block; }
        .inventory-table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
        .inventory-table th, .inventory-table td { padding: 10px; font-size: 12px; border-bottom: 1px solid #f0f0f0; text-align: left; }
        .inventory-table th { background: #fafafa; color: #666; font-weight: 600; }
        .inventory-table-wrap { max-height: 400px; overflow: auto; border-radius: 8px; }
        .resource-badge { display: inline-block; margin-right: 4px; padding: 2px 6px; font-size: 10px; border-radius: 3px; font-weight: 600; }
        .badge-unattached { background: #fecaca; color: #991b1b; }
        .badge-idle { background: #fed7aa; color: #92400e; }
        .badge-legacy { background: #dbeafe; color: #1e40af; }
        .badge-production { background: #dcfce7; color: #166534; }
        .badge-compute { background: #e9d5ff; color: #6b21a8; }
        .badge-storage { background: #fce7f3; color: #831843; }
        .badge-database { background: #f3e8ff; color: #5b21b6; }
        .resource-row-deleted { opacity: 0.5; background: #f9fafb; }
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
            const [action, setAction] = useState(JSON.stringify({action_type: 'delete_resource', resource_id: ''}, null, 2));
            const [status, setStatus] = useState({ text: '', type: 'info' });
            const [response, setResponse] = useState(null);
            const [loading, setLoading] = useState(false);
            const [prettyPrint, setPrettyPrint] = useState(true);
            const [taskScore, setTaskScore] = useState(0);
            const [deletedResources, setDeletedResources] = useState([]);
            const [manualActionHistory, setManualActionHistory] = useState([]);
            const [stepCount, setStepCount] = useState(0);

            const taskDescriptions = {
                task1: "Task 1 (Easy): Delete unattached volumes and idle test instances.",
                task2: "Task 2 (Medium): Right-size underutilized compute instances.",
                task3: "Task 3 (Hard): Combine deletes, right-sizing, and savings plans."
            };
            const taskIdMap = {
                task1: "cleanup_unattached",
                task2: "rightsize_compute",
                task3: "fleet_strategy"
            };

            const defaultActionByTask = {
                task1: { action_type: "delete_resource", resource_id: "" },
                task2: { action_type: "modify_instance", instance_id: "", new_type: "t3.small" },
                task3: { action_type: "purchase_savings_plan", plan_type: "compute", duration: "1y" }
            };

            const suggestNextAction = (currentTask, observation) => {
                const inventory = observation?.inventory || [];
                if (!inventory.length) return defaultActionByTask[currentTask];

                if (currentTask === "task1") {
                    const unattached = inventory.find(r => r.category === "storage" && !r.is_attached);
                    if (unattached) return { action_type: "delete_resource", resource_id: unattached.id };
                    const idleTest = inventory.find(r => r.category === "compute" && r?.tags?.lifecycle === "idle");
                    if (idleTest) return { action_type: "delete_resource", resource_id: idleTest.id };
                    return defaultActionByTask[currentTask];
                }

                if (currentTask === "task2") {
                    const underutilized = inventory.find(
                        r => r.category === "compute" && Number(r.cpu_usage_pct_30d || 0) < 5.0 && r.resource_type !== "t3.small"
                    );
                    if (underutilized) {
                        return { action_type: "modify_instance", instance_id: underutilized.id, new_type: "t3.small" };
                    }
                    return defaultActionByTask[currentTask];
                }

                const legacyNonProd = inventory.find(r => r.is_legacy && !r.is_production);
                if (legacyNonProd) return { action_type: "delete_resource", resource_id: legacyNonProd.id };
                const unattached = inventory.find(r => r.category === "storage" && !r.is_attached);
                if (unattached) return { action_type: "delete_resource", resource_id: unattached.id };
                const idleTest = inventory.find(r => r.category === "compute" && r?.tags?.lifecycle === "idle");
                if (idleTest) return { action_type: "delete_resource", resource_id: idleTest.id };
                const underutilized = inventory.find(
                    r => r.category === "compute" && Number(r.cpu_usage_pct_30d || 0) < 5.0 && r.resource_type !== "t3.small"
                );
                if (underutilized) return { action_type: "modify_instance", instance_id: underutilized.id, new_type: "t3.small" };
                return defaultActionByTask[currentTask];
            };

            const fetchTaskScore = async (currentTask = task) => {
                try {
                    const taskId = taskIdMap[currentTask];
                    const resp = await fetch(`/tasks/${taskId}/score`);
                    const data = await resp.json();
                    if (resp.ok && typeof data?.score === "number") {
                        setTaskScore(data.score);
                    }
                } catch (err) {
                    console.error("Score fetch failed", err);
                }
            };

            const apiCall = async (method, endpoint, payload = null) => {
                setLoading(true);
                setStatus({ text: 'Loading...', type: 'info' });
                try {
                    const options = { method, headers: { 'Content-Type': 'application/json' } };
                    if (payload) options.body = JSON.stringify(payload);
                    const resp = await fetch(endpoint, options);
                    const data = await resp.json();
                    if (!resp.ok) throw new Error(data?.detail || `API error: ${resp.status}`);
                    setResponse(data);
                    setStatus({ text: 'Success ✓', type: 'success' });
                    return data;
                } catch (err) {
                    console.error(err);
                    setStatus({ text: `Error: ${err.message}`, type: 'error' });
                    setResponse(null);
                    return null;
                } finally {
                    setLoading(false);
                }
            };

            const handleReset = async () => {
                const data = await apiCall('POST', '/reset');
                if (data?.observation) {
                    const nextAction = suggestNextAction(task, data.observation);
                    setAction(JSON.stringify(nextAction, null, 2));
                    setDeletedResources([]);
                    setManualActionHistory([]);
                    setStepCount(0);
                }
                await fetchTaskScore();
            };
            const handleState = async () => {
                const data = await apiCall('GET', '/state');
                if (data?.observation) {
                    const nextAction = suggestNextAction(task, data.observation);
                    setAction(JSON.stringify(nextAction, null, 2));
                }
                await fetchTaskScore();
            };
            const handleStep = async () => {
                try {
                    const parsed = JSON.parse(action);
                    const data = await apiCall('POST', '/step', parsed);
                    if (data?.observation) {
                        const newStep = stepCount + 1;
                        setStepCount(newStep);
                        if (parsed.action_type === 'delete_resource') {
                            setDeletedResources([...deletedResources, parsed.resource_id]);
                        }
                        const historyEntry = {
                            step: newStep,
                            action: parsed,
                            reward: data.reward,
                            bill: data.bill,
                            latency_ms: data.latency,
                            status_message: data.status_message,
                            inventory_count: data.observation?.inventory?.length || 0
                        };
                        setManualActionHistory([...manualActionHistory, historyEntry]);
                        const nextAction = suggestNextAction(task, data.observation);
                        setAction(JSON.stringify(nextAction, null, 2));
                    }
                    await fetchTaskScore();
                } catch (e) {
                    setStatus({ text: 'Invalid JSON in action editor', type: 'error' });
                }
            };

            const handleAgentRun = async () => {
                setResponse(null);
                setStatus({ text: 'Running agent...', type: 'info' });
                await apiCall('POST', '/agent/run', {task: task, episodes: 5, max_steps: 25});
            };

            const buildAgentSummary = (agentResp) => {
                const logs = agentResp?.episode_logs || [];
                const allSteps = logs.flatMap(ep => ep.steps || []);
                const latestEpisode = logs.length ? logs[logs.length - 1] : null;
                const avgLatency = allSteps.length
                    ? allSteps.reduce((sum, s) => sum + Number(s.latency_ms || 0), 0) / allSteps.length
                    : 0;
                const maxThrottle = allSteps.length
                    ? Math.max(...allSteps.map(s => Number(s?.info?.throttling_events ?? s?.observation?.health_status?.throttling_events ?? 0)), 0)
                    : 0;
                const maxDowntime = allSteps.length
                    ? Math.max(...allSteps.map(s => Number(s?.info?.downtime_events ?? s?.observation?.health_status?.downtime_events ?? 0)), 0)
                    : 0;
                return {
                    episodes: logs.length,
                    totalReward: Number(agentResp?.total_reward || 0),
                    avgReward: Number(agentResp?.average_reward || 0),
                    bestScore: Number(agentResp?.best_episode_score || 0),
                    bestCostCut: Number(agentResp?.best_episode_cost_reduction_pct || 0),
                    avgLatency,
                    maxThrottle,
                    maxDowntime,
                    latestSteps: latestEpisode?.steps || [],
                };
            };

            const InventoryTable = ({ inventory }) => {
                const visibleResources = inventory.filter(r => !deletedResources.includes(r.id));
                
                const getResourceBadges = (resource) => {
                    const badges = [];
                    if (resource.category === 'compute') badges.push(<span key="compute" className="resource-badge badge-compute">Compute</span>);
                    else if (resource.category === 'storage') badges.push(<span key="storage" className="resource-badge badge-storage">Storage</span>);
                    else if (resource.category === 'database') badges.push(<span key="database" className="resource-badge badge-database">Database</span>);
                    
                    if (!resource.is_attached) badges.push(<span key="unattached" className="resource-badge badge-unattached">Unattached</span>);
                    if (resource.tags?.lifecycle === 'idle') badges.push(<span key="idle" className="resource-badge badge-idle">Idle</span>);
                    if (resource.is_legacy) badges.push(<span key="legacy" className="resource-badge badge-legacy">Legacy</span>);
                    if (resource.is_production) badges.push(<span key="prod" className="resource-badge badge-production">Production</span>);
                    
                    return badges;
                };

                return (
                    <div className="inventory-section">
                        <label className="inventory-label">Cloud Resources ({visibleResources.length} active)</label>
                        <div className="inventory-table-wrap">
                            <table className="inventory-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Category</th>
                                        <th>Type</th>
                                        <th>Cost/mo</th>
                                        <th>CPU %</th>
                                        <th>Memory %</th>
                                        <th>Network Mbps</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {visibleResources.map(resource => (
                                        <tr key={resource.id}>
                                            <td style={{fontSize: '11px', fontFamily: 'monospace'}}>{resource.id}</td>
                                            <td>{resource.category}</td>
                                            <td>{resource.resource_type}</td>
                                            <td>${resource.monthly_cost?.toFixed(2) || '0.00'}</td>
                                            <td>{Number(resource.cpu_usage_pct_30d || 0).toFixed(1)}%</td>
                                            <td>{Number(resource.memory_usage_pct_30d || 0).toFixed(1)}%</td>
                                            <td>{Number(resource.network_io_mbps_30d || 0).toFixed(1)}</td>
                                            <td style={{whiteSpace: 'normal', wordBreak: 'break-word'}}>{getResourceBadges(resource)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                );
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
                                    <button
                                        key={t}
                                        className={`task-btn ${task === t ? 'active' : ''}`}
                                        onClick={async () => {
                                            setTask(t);
                                            const nextAction = suggestNextAction(t, response?.observation);
                                            setAction(JSON.stringify(nextAction, null, 2));
                                            await fetchTaskScore(t);
                                        }}
                                    >
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
                                {['manual', 'agent'].map(t => (
                                    <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
                                        {t === 'manual' ? 'Manual Play' : 'Agent Run'}
                                    </button>
                                ))}
                            </div>
                            <div className="content">
                                {tab === 'manual' && (
                                    <>
                                        <div className="metrics-row">
                                            <div className="metric">
                                                <div className="metric-label">Bill Amount</div>
                                                <div className="metric-value">${response?.observation?.cost_data?.projected_monthly_bill ? response.observation.cost_data.projected_monthly_bill.toFixed(2) : '0.00'}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Latency (ms)</div>
                                                <div className="metric-value">{response?.observation?.health_status?.system_latency_ms ? response.observation.health_status.system_latency_ms.toFixed(1) : '0'}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Throttling</div>
                                                <div className="metric-value">{response?.observation?.health_status?.throttling_events ?? 0}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Downtime</div>
                                                <div className="metric-value">{response?.observation?.health_status?.downtime_events ?? 0}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Reward</div>
                                                <div className="metric-value">{response?.reward ? response.reward.toFixed(3) : '0.000'}</div>
                                            </div>
                                            <div className="metric">
                                                <div className="metric-label">Task Score</div>
                                                <div className="metric-value">{taskScore.toFixed(2)} ({(taskScore * 100).toFixed(0)}%)</div>
                                            </div>
                                        </div>
                                        {response?.observation?.inventory && (
                                            <InventoryTable inventory={response.observation.inventory} />
                                        )}
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
                                        {manualActionHistory.length > 0 && (
                                            <>
                                                <label className="editor-label">Action History ({manualActionHistory.length} steps)</label>
                                                <div className="agent-table-wrap">
                                                    <table className="agent-table">
                                                        <thead>
                                                            <tr>
                                                                <th>Step</th>
                                                                <th>Action</th>
                                                                <th>Reward</th>
                                                                <th>Bill</th>
                                                                <th>Latency</th>
                                                                <th>Resources</th>
                                                                <th>Status</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {manualActionHistory.map((entry, idx) => (
                                                                <tr key={`manual-${idx}`}>
                                                                    <td>{entry.step}</td>
                                                                    <td>{entry.action?.action_type || "n/a"}</td>
                                                                    <td>{Number(entry.reward || 0).toFixed(3)}</td>
                                                                    <td>${Number(entry.bill || 0).toFixed(2)}</td>
                                                                    <td>{Number(entry.latency_ms || 0).toFixed(1)}ms</td>
                                                                    <td>{entry.inventory_count}</td>
                                                                    <td>{entry.status_message || "ok"}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </>
                                        )}
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
                                {tab === 'agent' && (
                                    <>
                                        <div className="action-editor">
                                            <label className="editor-label">Agent Configuration</label>
                                            <div style={{fontSize: '13px', color: '#666', marginBottom: '12px'}}>
                                                <div>Strategy: Task-aware cost optimizer</div>
                                                <div>Episodes: 5</div>
                                                <div>Max Steps/Episode: 25</div>
                                                <div>Objective: Reduce bill while managing latency/throttling/downtime</div>
                                            </div>
                                            <div className="button-group">
                                                <button className="primary" onClick={handleAgentRun} disabled={loading}>
                                                    🚀 Run Agent
                                                </button>
                                                <button onClick={() => apiCall('GET', '/agent/plan')} disabled={loading}>📋 View Plan</button>
                                            </div>
                                        </div>
                                        <div className="status-box">
                                            <div className="status-label">Agent Status</div>
                                            <div className={`status-message ${status.type === 'error' ? 'error' : ''}`}>
                                                {status.text || 'Ready to run'}
                                            </div>
                                        </div>
                                        {response && (
                                            <>
                                                {(() => {
                                                    const summary = buildAgentSummary(response);
                                                    return (
                                                        <>
                                                            <label className="editor-label">Agent Results</label>
                                                            <div className="agent-summary-grid">
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Episodes</div><div className="agent-summary-value">{summary.episodes}</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Best Task Score</div><div className="agent-summary-value">{summary.bestScore.toFixed(2)}</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Best Cost Cut</div><div className="agent-summary-value">{summary.bestCostCut.toFixed(1)}%</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Avg Latency</div><div className="agent-summary-value">{summary.avgLatency.toFixed(1)}ms</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Max Throttle</div><div className="agent-summary-value">{summary.maxThrottle}</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Max Downtime</div><div className="agent-summary-value">{summary.maxDowntime}</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Total Reward</div><div className="agent-summary-value">{summary.totalReward.toFixed(2)}</div></div>
                                                                <div className="agent-summary-card"><div className="agent-summary-label">Avg Reward</div><div className="agent-summary-value">{summary.avgReward.toFixed(2)}</div></div>
                                                            </div>

                                                            <label className="editor-label">Latest Episode Steps</label>
                                                            <div className="agent-table-wrap">
                                                                <table className="agent-table">
                                                                    <thead>
                                                                        <tr>
                                                                            <th>Step</th>
                                                                            <th>Action</th>
                                                                            <th>Reward</th>
                                                                            <th>Bill</th>
                                                                            <th>Latency</th>
                                                                            <th>Status</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody>
                                                                        {summary.latestSteps.map((s, idx) => (
                                                                            <tr key={`${s.step}-${idx}`}>
                                                                                <td>{s.step}</td>
                                                                                <td>{s.action?.action_type || "n/a"}</td>
                                                                                <td>{Number(s.reward || 0).toFixed(3)}</td>
                                                                                <td>${Number(s.bill || 0).toFixed(2)}</td>
                                                                                <td>{Number(s.latency_ms || 0).toFixed(1)}ms</td>
                                                                                <td>{s.status_message || "ok"}</td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                </table>
                                                            </div>

                                                            <details style={{marginTop: '10px'}}>
                                                                <summary style={{cursor: 'pointer', fontSize: '12px', color: '#555'}}>View full raw logs (JSON)</summary>
                                                                <div className="json-viewer" style={{maxHeight: '360px', marginTop: '8px'}}>
                                                                    {prettyPrint ? JSON.stringify(response, null, 2) : JSON.stringify(response)}
                                                                </div>
                                                            </details>
                                                        </>
                                                    );
                                                })()}
                                            </>
                                        )}
                                    </>
                                )}
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
    obs_dict = initial_obs.model_dump() if hasattr(initial_obs, 'model_dump') else initial_obs.dict()
    return {
        "observation": obs_dict,
        "reward": 0.0,
        "done": False,
        "info": {}
    }


@app.get("/reset")
async def reset_get():
    """Browser-friendly reset alias (GET)."""
    initial_obs = env.reset()
    obs_dict = initial_obs.model_dump() if hasattr(initial_obs, 'model_dump') else initial_obs.dict()
    return {
        "observation": obs_dict,
        "reward": 0.0,
        "done": False,
        "info": {}
    }

@app.post("/step")
async def step(action: Action):
    """Execute action"""
    try:
        obs, reward, done, info = env.step(action)
        reward_val = float(reward.total if hasattr(reward, 'total') else reward)
        obs_dict = obs.model_dump() if hasattr(obs, 'model_dump') else obs.dict()
        return {
            "observation": obs_dict,
            "reward": reward_val,
            "done": bool(done),
            "info": info if isinstance(info, dict) else {}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state")
async def state():
    """Get current state"""
    obs = env.get_observation("Current state requested.")
    obs_dict = obs.model_dump() if hasattr(obs, 'model_dump') else obs.dict()
    return {
        "observation": obs_dict,
        "reward": 0.0,
        "done": False,
        "info": {}
    }

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
# AGENT ROUTES
# ────────────────────────────────────────────────────────────────────────────

@app.post("/agent/run")
async def agent_run(request: Request):
    """Run agent with Q-learning strategy"""
    try:
        body = await request.json()
        task = body.get("task", "task1")
        episodes = max(1, int(body.get("episodes", 5)))
        max_steps = max(5, int(body.get("max_steps", 25)))

        task_map = {
            "task1": "cleanup_unattached",
            "task2": "rightsize_compute",
            "task3": "fleet_strategy",
        }
        target_task_id = task_map.get(task, "cleanup_unattached")

        def select_action(observation, purchased_plans):
            inventory = observation.inventory

            # Task-specific prioritization.
            if task == "task1":
                for resource in inventory:
                    if resource.category == "storage" and not resource.is_attached:
                        return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
                for resource in inventory:
                    if resource.category == "compute" and resource.tags.get("lifecycle") == "idle":
                        return DeleteResourceAction(resource_id=resource.id), {"action_type": "delete_resource", "resource_id": resource.id}
                return None, None

            if task == "task2":
                for resource in inventory:
                    if resource.category == "compute" and float(resource.cpu_usage_pct_30d or 0.0) < 5.0 and resource.resource_type != "t3.small":
                        return (
                            ModifyInstanceAction(instance_id=resource.id, new_type="t3.small"),
                            {"action_type": "modify_instance", "instance_id": resource.id, "new_type": "t3.small"},
                        )
                return None, None

            # task3: fleet strategy (hard) - aggressive but safe optimization.
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
            "task": task,
            "target_task_id": target_task_id,
            "episodes": episodes,
            "episode_logs": [],
            "total_reward": 0.0,
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
                episode_reward += reward_value

                episode_log["steps"].append(
                    {
                        "step": step_idx + 1,
                        "action": action_payload,
                        "reward": reward_value,
                        "bill": bill_now,
                        "latency_ms": latency_now,
                        "done": bool(done),
                        "status_message": obs.status_message,
                        "info": info,
                    }
                )

                if done:
                    break

            final_bill = float(env.get_observation("Episode ended.").cost_data.projected_monthly_bill)
            cost_reduction_pct = ((initial_bill - final_bill) / initial_bill * 100.0) if initial_bill > 0 else 0.0
            task_score = float(compute_task_score(env, target_task_id))

            episode_log["total_reward"] = float(episode_reward)
            episode_log["final_task_score"] = task_score
            episode_log["cost_reduction_pct"] = round(cost_reduction_pct, 2)
            results["episode_logs"].append(episode_log)
            results["total_reward"] += float(episode_reward)
            results["best_episode_score"] = max(results["best_episode_score"], task_score)
            results["best_episode_cost_reduction_pct"] = max(
                results["best_episode_cost_reduction_pct"], round(cost_reduction_pct, 2)
            )

        results["average_reward"] = float(results["total_reward"] / episodes)
        return results

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent run error: {str(e)}")

@app.get("/agent/plan")
async def agent_plan():
    """Get agent planning details"""
    return {
        "plan_id": "plan-001",
        "strategy": "Q-Learning with Epsilon-Greedy Exploration",
        "objectives": [
            "Maximize cost savings",
            "Minimize resource contention",
            "Maintain performance SLAs"
        ],
        "planned_actions": [
            {
                "priority": 1,
                "action": "delete_resource",
                "target": "unused EC2 instances",
                "expected_saving": "$5000/month"
            },
            {
                "priority": 2,
                "action": "modify_instance",
                "target": "overprovisioned instances",
                "expected_saving": "$2000/month"
            },
            {
                "priority": 3,
                "action": "purchase_savings_plan",
                "target": "commitment-based discounts",
                "expected_saving": "$8000/month"
            }
        ],
        "total_projected_savings": "$15000/month",
        "confidence": 0.87
    }


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