"""
FinOps Cloud Optimizer — Frontend App
--------------------------------------
Run this file directly:  python app.py
It serves a rich single-page dashboard that talks to the FastAPI server
(server.py, default http://localhost:7860).

The frontend is a self-contained HTML page served via a tiny Python HTTP
server so there are zero extra dependencies beyond the stdlib.

If you prefer to host the HTML separately, copy the HTML string to a file
and open it in a browser — just update API_BASE at the top of the <script>.
"""

import http.server
import webbrowser
import os

# ── configuration ────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8080
API_BASE = os.getenv("FINOPS_API_URL", "http://localhost:7860")  # FastAPI server

# ── HTML ─────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>FinOps Cloud Optimizer</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Syne:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0d0f14; --surface: #161922; --surface2: #1e2330; --border: #2a3045;
    --accent: #3ef0a0; --accent2: #3ea8f0; --warn: #f0a83e; --danger: #f05a3e;
    --text: #e8edf5; --muted: #6b7898; --mono: 'IBM Plex Mono', monospace;
    --sans: 'Syne', sans-serif; --radius: 8px;
  }
  html { font-size: 14px; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; display: flex; flex-direction: column; }
  header { display: flex; align-items: center; justify-content: space-between; padding: 18px 28px; border-bottom: 1px solid var(--border); background: var(--surface); }
  .logo { font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }
  .logo span { color: var(--accent); }
  .status-pill { font-family: var(--mono); font-size: 11px; padding: 4px 10px; border-radius: 20px; border: 1px solid var(--border); display: flex; align-items: center; gap: 6px; }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
  .dot.ok { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
  main { flex: 1; display: grid; grid-template-columns: 240px 1fr; grid-template-rows: auto 1fr; }
  aside { grid-row: 1/3; background: var(--surface); border-right: 1px solid var(--border); padding: 20px 16px; display: flex; flex-direction: column; gap: 8px; }
  .aside-label { font-size: 10px; font-family: var(--mono); color: var(--muted); letter-spacing: 1px; text-transform: uppercase; padding: 0 8px 6px; }
  .nav-btn { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: var(--radius); background: transparent; border: none; color: var(--muted); font-family: var(--sans); font-size: 13px; cursor: pointer; text-align: left; width: 100%; transition: all .15s; }
  .nav-btn:hover { background: var(--surface2); color: var(--text); }
  .nav-btn.active { background: var(--surface2); color: var(--accent); }
  .nav-icon { font-size: 15px; width: 18px; text-align: center; }
  .divider { height: 1px; background: var(--border); margin: 8px 0; }
  .metrics-bar { grid-column: 2; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--border); border-bottom: 1px solid var(--border); }
  .metric-card { background: var(--surface); padding: 16px 20px; display: flex; flex-direction: column; gap: 4px; }
  .metric-label { font-size: 11px; font-family: var(--mono); color: var(--muted); }
  .metric-value { font-size: 24px; font-weight: 700; font-family: var(--mono); }
  .metric-sub { font-size: 11px; color: var(--muted); }
  .val-green { color: var(--accent); }
  .val-blue { color: var(--accent2); }
  .val-amber { color: var(--warn); }
  .val-red { color: var(--danger); }
  .content { grid-column: 2; padding: 24px 28px; overflow-y: auto; display: flex; flex-direction: column; gap: 20px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .card-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--border); }
  .card-header h3 { font-size: 13px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; }
  thead th { padding: 9px 14px; font-family: var(--mono); font-size: 10px; letter-spacing: .8px; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--border); text-align: left; background: var(--surface2); }
  tbody tr { border-bottom: 1px solid var(--border); transition: background .1s; }
  tbody tr:hover { background: var(--surface2); }
  td { padding: 9px 14px; font-size: 12px; font-family: var(--mono); }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-family: var(--mono); }
  .badge-compute { background: #1a2a3a; color: var(--accent2); }
  .badge-storage { background: #2a2a1a; color: var(--warn); }
  .badge-database { background: #2a1a2a; color: #d88cf0; }
  .badge-prod { background: #1a2a1a; color: var(--accent); }
  .badge-dev { background: #1e2330; color: var(--muted); }
  .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .action-form { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
  .action-form h4 { font-size: 12px; font-weight: 600; margin-bottom: 12px; color: var(--accent2); }
  label { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; font-family: var(--mono); }
  input[type=text], select { width: 100%; padding: 8px 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 5px; color: var(--text); font-family: var(--mono); font-size: 12px; margin-bottom: 10px; outline: none; }
  input[type=text]:focus, select:focus { border-color: var(--accent2); }
  select option { background: var(--bg); }
  .btn { padding: 8px 16px; border-radius: 5px; font-family: var(--sans); font-size: 12px; font-weight: 600; cursor: pointer; border: none; transition: all .15s; }
  .btn-primary { background: var(--accent); color: #0d0f14; }
  .btn-primary:hover { background: #5af4b4; }
  .btn-outline { background: transparent; color: var(--accent2); border: 1px solid var(--accent2); }
  .btn-outline:hover { background: var(--accent2); color: #0d0f14; }
  .btn-danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); }
  .btn-danger:hover { background: var(--danger); color: #fff; }
  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .agent-config { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px; }
  .log-box { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; font-family: var(--mono); font-size: 11px; line-height: 1.7; max-height: 320px; overflow-y: auto; color: var(--muted); }
  .log-line-action { color: var(--accent2); }
  .log-line-reward { color: var(--accent); }
  .log-line-episode { color: var(--text); font-weight: 600; }
  .task-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .task-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
  .task-card h4 { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
  .task-diff { font-size: 10px; font-family: var(--mono); padding: 2px 7px; border-radius: 4px; margin-bottom: 12px; display: inline-block; }
  .diff-easy { background: #1a2a1a; color: var(--accent); }
  .diff-medium { background: #2a2a1a; color: var(--warn); }
  .diff-hard { background: #2a1a1a; color: var(--danger); }
  .score-bar-wrap { height: 5px; background: var(--border); border-radius: 3px; margin: 10px 0 6px; }
  .score-bar { height: 5px; border-radius: 3px; background: var(--accent); transition: width .5s; }
  .score-label { font-family: var(--mono); font-size: 12px; }
  #toast { position: fixed; bottom: 24px; right: 24px; background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 16px; font-size: 12px; font-family: var(--mono); opacity: 0; transform: translateY(8px); transition: all .25s; pointer-events: none; }
  #toast.show { opacity: 1; transform: translateY(0); }
  .spin { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty { padding: 40px; text-align: center; color: var(--muted); font-size: 13px; }
  .tab-pane { display: none; }
  .tab-pane.active { display: block; }
</style>
</head>
<body>

<header>
  <div class="logo">Fin<span>Ops</span> Cloud Optimizer</div>
  <div id="server-status" class="status-pill">
    <span class="dot" id="dot"></span>
    <span id="status-text" style="font-family:var(--mono)">connecting…</span>
  </div>
</header>

<main>
  <aside>
    <div class="aside-label">Navigation</div>
    <button class="nav-btn active" onclick="switchTab('dashboard')"><span class="nav-icon">◈</span> Dashboard</button>
    <button class="nav-btn" onclick="switchTab('inventory')"><span class="nav-icon">◫</span> Inventory</button>
    <button class="nav-btn" onclick="switchTab('actions')"><span class="nav-icon">◎</span> Actions</button>
    <button class="nav-btn" onclick="switchTab('agent')"><span class="nav-icon">◆</span> Agent Runner</button>
    <button class="nav-btn" onclick="switchTab('tasks')"><span class="nav-icon">◉</span> Tasks & Scores</button>
    <div class="divider"></div>
    <div class="aside-label">Controls</div>
    <button class="nav-btn" onclick="doReset()"><span class="nav-icon">↺</span> Reset Env</button>
    <button class="nav-btn" onclick="doRefresh()"><span class="nav-icon">⟳</span> Refresh State</button>
  </aside>

  <div class="metrics-bar">
    <div class="metric-card"><div class="metric-label">Monthly Bill</div><div class="metric-value val-amber" id="m-bill">—</div><div class="metric-sub">projected</div></div>
    <div class="metric-card"><div class="metric-label">Daily Burn</div><div class="metric-value val-blue" id="m-burn">—</div><div class="metric-sub">per day</div></div>
    <div class="metric-card"><div class="metric-label">Resources</div><div class="metric-value val-green" id="m-res">—</div><div class="metric-sub">in inventory</div></div>
    <div class="metric-card"><div class="metric-label">Latency</div><div class="metric-value" id="m-lat">—</div><div class="metric-sub">system ms</div></div>
  </div>

  <div class="content">
    <div id="tab-dashboard" class="tab-pane active"><div class="card"><div class="card-header"><h3>Environment Overview</h3><button class="btn btn-outline" onclick="doRefresh()">Refresh</button></div><div id="dash-content" style="padding:16px; font-family:var(--mono); font-size:12px; line-height:1.9;">Loading…</div></div></div>

    <div id="tab-inventory" class="tab-pane"><div class="card"><div class="card-header"><h3>Resource Inventory</h3><span id="res-count" style="font-size:11px;font-family:var(--mono)"></span></div><div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>Category</th><th>Type</th><th>Monthly $</th><th>CPU %</th><th>Mem %</th><th>Attached</th><th>Prod</th><th>Tags</th></tr></thead><tbody id="inv-body"><tr><td colspan="9" class="empty">No data</td></tr></tbody></table></div></div></div>

    <div id="tab-actions" class="tab-pane"><div class="action-grid"><div class="action-form"><h4>Delete Resource</h4><label>Resource ID</label><input type="text" id="del-id" placeholder="res-12345" /><button class="btn btn-danger" onclick="doDelete()">Delete</button></div><div class="action-form"><h4>Modify Instance</h4><label>Instance ID</label><input type="text" id="mod-id" placeholder="res-12345" /><label>New Type</label><select id="mod-type"><option>m5.xlarge</option><option>m5.large</option><option>t3.medium</option><option>t3.small</option><option>t3.micro</option></select><button class="btn btn-primary" onclick="doModify()">Apply Change</button></div><div class="action-form"><h4>Purchase Savings Plan</h4><label>Plan Type</label><select id="sp-type"><option>compute</option><option>database</option></select><label>Duration</label><select id="sp-dur"><option>1y</option><option>3y</option></select><button class="btn btn-primary" onclick="doPurchasePlan()">Purchase</button></div><div class="action-form"><h4>Tag Resource</h4><label>Resource ID</label><input type="text" id="tag-id" placeholder="res-12345" /><label>Tag Key</label><input type="text" id="tag-key" placeholder="env" /><label>Tag Value</label><input type="text" id="tag-val" placeholder="prod" /><button class="btn btn-primary" onclick="doTag()">Apply Tag</button></div></div><div class="card" style="margin-top:16px"><div class="card-header"><h3>Action Log</h3></div><div class="log-box" id="action-log">No actions yet.</div></div></div>

    <div id="tab-agent" class="tab-pane"><div class="card"><div class="card-header"><h3>Agent Configuration</h3></div><div style="padding:16px"><div class="agent-config"><div><label>Task</label><select id="ag-task"><option value="task1">Task 1 — Clean Up</option><option value="task2">Task 2 — Right-Size</option><option value="task3">Task 3 — Fleet</option></select></div><div><label>Episodes</label><input type="text" id="ag-ep" value="3" /></div><div><label>Max Steps</label><input type="text" id="ag-steps" value="20" /></div></div><div class="btn-row"><button class="btn btn-primary" id="run-btn" onclick="doAgentRun()">Run Agent</button></div></div></div><div class="card" style="margin-top:16px"><div class="card-header"><h3>Run Output</h3><div id="agent-summary" style="font-size:11px;font-family:var(--mono)"></div></div><div class="log-box" id="agent-log">Ready.</div></div></div>

    <div id="tab-tasks" class="tab-pane"><div class="task-cards" id="task-cards"><div class="empty">Loading…</div></div></div>
  </div>
</main>

<div id="toast"></div>

<script>
const API = "API_BASE_PLACEHOLDER";
let state = null;

function toast(msg, color) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.borderColor = color || 'var(--border)';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

async function apiFetch(path, opts) {
  try {
    const r = await fetch(API + path, opts);
    if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || r.statusText);
    return r.json();
  } catch(e) {
    toast('API error: ' + e.message, 'var(--danger)');
    throw e;
  }
}

function fmt$(n) { return '$' + parseFloat(n).toFixed(2); }
function fmtPct(n) { return parseFloat(n).toFixed(1) + '%'; }

function switchTab(id) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  event.currentTarget.classList.add('active');
  if (id === 'inventory') renderInventory();
  if (id === 'tasks') loadTasks();
}

async function checkHealth() {
  try {
    await apiFetch('/health');
    document.getElementById('dot').className = 'dot ok';
    document.getElementById('status-text').textContent = 'server online';
  } catch {
    document.getElementById('dot').className = 'dot';
    document.getElementById('status-text').textContent = 'server offline';
  }
}

async function loadState() {
  const data = await apiFetch('/state');
  state = data.observation;
  updateMetrics();
  updateDash();
}

function updateMetrics() {
  if (!state) return;
  const b = state.cost_data.projected_monthly_bill;
  const d = state.cost_data.daily_burn_rate;
  const l = state.health_status.system_latency_ms;
  document.getElementById('m-bill').textContent = fmt$(b);
  document.getElementById('m-burn').textContent = fmt$(d);
  document.getElementById('m-res').textContent = state.inventory.length;
  const latEl = document.getElementById('m-lat');
  latEl.textContent = parseFloat(l).toFixed(1) + ' ms';
  latEl.className = 'metric-value ' + (l > 200 ? 'val-red' : l > 100 ? 'val-amber' : 'val-green');
}

function updateDash() {
  if (!state) return;
  const inv = state.inventory;
  const cats = {compute:0, storage:0, database:0};
  let unattached = 0, prod = 0, legacy = 0;
  inv.forEach(r => { cats[r.category] = (cats[r.category]||0)+1; if (!r.is_attached) unattached++; if (r.is_production) prod++; if (r.is_legacy) legacy++; });
  const bill = state.cost_data.projected_monthly_bill;
  document.getElementById('dash-content').innerHTML = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><div><strong>Cost Summary</strong><br/>Bill: ${fmt$(bill)}<br/>Burn: ${fmt$(state.cost_data.daily_burn_rate)}<br/>Latency: ${parseFloat(state.health_status.system_latency_ms).toFixed(1)}ms<br/>Throttles: ${state.health_status.throttling_events}</div><div><strong>Inventory</strong><br/>Compute: ${cats.compute || 0}<br/>Storage: ${cats.storage || 0}<br/>Database: ${cats.database || 0}<br/>Unattached: ${unattached}</div></div>`;
}

function renderInventory() {
  if (!state) { loadState().then(renderInventory); return; }
  const inv = state.inventory;
  document.getElementById('res-count').textContent = inv.length + ' resources';
  const rows = inv.map(r => {
    const catBadge = `<span class="badge badge-${r.category}">${r.category}</span>`;
    const envTag = r.tags.env || '—';
    const envBadge = `<span class="badge ${r.tags.env === 'prod' ? 'badge-prod' : 'badge-dev'}">${envTag}</span>`;
    return `<tr><td>${r.id}</td><td>${catBadge}</td><td>${r.resource_type}</td><td>${fmt$(r.monthly_cost)}</td><td>${fmtPct(r.cpu_usage_pct_30d)}</td><td>${fmtPct(r.memory_usage_pct_30d)}</td><td>${r.is_attached?'yes':'no'}</td><td>${r.is_production?'yes':'—'}</td><td>${envBadge}</td></tr>`;
  }).join('');
  document.getElementById('inv-body').innerHTML = rows || '<tr><td colspan="9">Empty</td></tr>';
}

function logAction(msg, cls) {
  const box = document.getElementById('action-log');
  const line = document.createElement('div');
  line.className = 'log-line-' + (cls||'action');
  line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
  if (box.textContent === 'No actions yet.') box.textContent = '';
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

async function stepAction(payload) {
  const data = await apiFetch('/step', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  state = data.observation;
  updateMetrics();
  updateDash();
  logAction(`reward ${data.reward.toFixed(2)} | bill ${fmt$(state.cost_data.projected_monthly_bill)}`, 'reward');
  toast('Action: ' + data.reward.toFixed(2), 'var(--accent)');
}

async function doDelete() {
  const id = document.getElementById('del-id').value.trim();
  if (!id) { toast('Enter resource ID', 'var(--warn)'); return; }
  logAction(`delete_resource id=${id}`);
  await stepAction({ action_type: 'delete_resource', resource_id: id });
}

async function doModify() {
  const id = document.getElementById('mod-id').value.trim();
  const type = document.getElementById('mod-type').value;
  if (!id) { toast('Enter instance ID', 'var(--warn)'); return; }
  logAction(`modify id=${id} type=${type}`);
  await stepAction({ action_type: 'modify_instance', instance_id: id, new_type: type });
}

async function doPurchasePlan() {
  const pt = document.getElementById('sp-type').value;
  const dur = document.getElementById('sp-dur').value;
  logAction(`savings_plan type=${pt} dur=${dur}`);
  await stepAction({ action_type: 'purchase_savings_plan', plan_type: pt, duration: dur });
}

async function doTag() {
  const id = document.getElementById('tag-id').value.trim();
  const key = document.getElementById('tag-key').value.trim();
  const val = document.getElementById('tag-val').value.trim();
  if (!id||!key||!val) { toast('Fill all fields', 'var(--warn)'); return; }
  logAction(`tag id=${id} ${key}=${val}`);
  await stepAction({ action_type: 'tag_resource', resource_id: id, tag_key: key, tag_value: val });
}

async function doReset() {
  await apiFetch('/reset', { method: 'POST' });
  await loadState();
  toast('Reset', 'var(--accent)');
}

async function doRefresh() {
  await loadState();
  if (document.getElementById('tab-inventory').classList.contains('active')) renderInventory();
  toast('Refreshed', 'var(--accent2)');
}

async function doAgentRun() {
  const btn = document.getElementById('run-btn');
  btn.innerHTML = '<span class="spin"></span> Running…';
  btn.disabled = true;
  const box = document.getElementById('agent-log');
  box.textContent = '';
  const task = document.getElementById('ag-task').value;
  const ep = parseInt(document.getElementById('ag-ep').value) || 3;
  const steps = parseInt(document.getElementById('ag-steps').value) || 20;
  try {
    const data = await apiFetch('/agent/run', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ task, episodes: ep, max_steps: steps }) });
    appendLog(box, `Strategy: ${data.strategy}`, 'episode');
    appendLog(box, `Task: ${data.target_task_id}`, 'episode');
    (data.episode_logs || []).forEach(e => {
      appendLog(box, `Ep ${e.episode}: score=${(e.final_task_score*100).toFixed(1)}% cost_reduction=${e.cost_reduction_pct}%`, 'reward');
    });
    appendLog(box, `Best: ${(data.best_episode_score*100).toFixed(1)}% avg_reward: ${data.average_reward.toFixed(2)}`, 'episode');
    document.getElementById('agent-summary').textContent = `${(data.best_episode_score*100).toFixed(1)}% · ${data.average_reward.toFixed(2)}`;
    await loadState();
    toast('Agent done', 'var(--accent)');
  } finally {
    btn.textContent = 'Run Agent';
    btn.disabled = false;
  }
}

function appendLog(box, text, cls) {
  const div = document.createElement('div');
  div.className = 'log-line-' + cls;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function loadTasks() {
  const data = await apiFetch('/tasks');
  const tasks = data.tasks || [];
  const scores = await Promise.all(tasks.map(t => apiFetch('/tasks/' + t.id + '/score').catch(() => ({ score: 0 }))));
  const cards = tasks.map((t, i) => {
    const pct = (scores[i].score * 100).toFixed(1);
    return `<div class="task-card"><h4>${t.name}</h4><span class="task-diff diff-${t.difficulty}">${t.difficulty}</span><div class="score-label">Score: ${pct}%</div><div class="score-bar-wrap"><div class="score-bar" style="width:${pct}%"></div></div><button class="btn btn-outline" style="font-size:11px;padding:5px 12px;margin-top:12px" onclick="refreshScore('${t.id}', this)">Refresh</button></div>`;
  }).join('');
  document.getElementById('task-cards').innerHTML = cards || '<div class="empty">No tasks</div>';
}

async function refreshScore(taskId, btn) {
  btn.textContent = '…';
  try {
    const data = await apiFetch('/tasks/' + taskId + '/score');
    const pct = (data.score * 100).toFixed(1);
    const card = btn.closest('.task-card');
    card.querySelector('.score-label').textContent = 'Score: ' + pct + '%';
    card.querySelector('.score-bar').style.width = pct + '%';
    toast('Score: ' + pct + '%', 'var(--accent)');
  } finally {
    btn.textContent = 'Refresh';
  }
}

(async function init() {
  await checkHealth();
  await loadState();
  setInterval(checkHealth, 15000);
})();
</script>
</body>
</html>
""".replace("API_BASE_PLACEHOLDER", API_BASE)


# ── HTTP server  ───────────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def log_message(self, fmt, *args):
        pass


def serve():
    server = http.server.HTTPServer((HOST, PORT), Handler)
    print(f"\n  FinOps Dashboard  →  http://{HOST}:{PORT}")
    print(f"  FastAPI server    →  {API_BASE}")
    print("  Press Ctrl+C to stop.\n")
    webbrowser.open(f"http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
