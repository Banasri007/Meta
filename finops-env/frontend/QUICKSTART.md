# FinOps Frontend - Quick Start Guide

## What is this?

A modern, interactive web dashboard for the FinOps Cloud Optimizer. It provides:

- **Real-time visualization** of cloud resources and costs
- **Interactive task scoring** for cloud optimization challenges
- **One-click actions** for common cost-saving operations
- **Cost breakdown charts** showing where your money is spent
- **Action history** tracking all optimizations performed

## Quick Start (3 steps)

### Step 1: Install Dependencies

```powershell
cd finops-env/frontend
npm install
```

**Takes ~2 minutes**

### Step 2: Configure Backend Connection

**Option A: Local Backend** (Recommended for development)

```powershell
# Terminal 1: Start the backend API
cd finops-env
python -m uvicorn main:app --host 127.0.0.1 --port 7860

# Terminal 2: Set environment variable
$env:REACT_APP_API_URL = "http://127.0.0.1:7860"

# Terminal 2: Start frontend
cd frontend
npm start
```

**Option B: Remote Backend** (Hugging Face Space)

```powershell
cd frontend
npm start
```

(Uses default remote URL)

### Step 3: Open Dashboard

Visit `http://localhost:3000` in your browser

---

## Dashboard Walkthrough

### 1. Top Metrics
Shows your key cloud metrics:
- **Monthly Bill**: Total projected cloud costs
- **System Latency**: Current system response time
- **Throttle/Downtime Events**: System health indicators

### 2. Cost Breakdown Chart
Pie chart showing cost distribution:
- Compute (blue) - EC2 instances
- Storage (green) - S3, EBS volumes
- Database (yellow) - RDS, managed databases

### 3. Task Scores & Progress
Three optimization challenges with difficulty:

1. **Cleanup Unattached** ⭐ (Easy)
   - Goal: Delete 5 unattached volumes + 2 idle test instances
   - Scoring: 0.7×(volumes deleted) + 0.3×(tests deleted)

2. **Rightsize Compute** ⭐⭐ (Medium)
   - Goal: Downsize underutilized VMs to smaller types
   - Constraint: Keep latency < 200ms
   - Scoring: Based on cost savings vs maximum theoretical savings

3. **Fleet Strategy** ⭐⭐⭐ (Hard)
   - Goal: Achieve 40%+ cost reduction with positive ROI
   - Constraint: Zero downtime on production
   - Scoring: Combination of cost reduction, ROI, and reliability

### 4. Cloud Resources List
View all your resources:
- **Compute**: EC2 instances with CPU/memory usage
- **Storage**: Volumes, their attachment status  
- **Database**: RDS instances and other managed databases

Click action buttons for quick optimizations:
- `Delete` - Remove unattached or idle resources
- `Downsize` - Resize underutilized instances

### 5. Quick Actions Panel
Common optimization operations:
- Resize instances (t3.micro → t3.large)
- Delete unattached volumes
- Buy savings plans (1-year compute/database)

### 6. Action History
Running log of everything you've done:
- Shows the action type and exact parameters
- Displays the immediate reward (positive = good)
- Timestamps for tracking your work

---

## Features Explained

### Real-Time Updates
Every action you take immediately updates:
- Cloud costs
- Resource inventory
- System metrics
- Task scores

### Reward System
Each action has an immediate reward:
- **Positive rewards** (green): Good moves (deleted waste, optimized RIs)
- **Negative rewards** (red): Risky moves (deleted wrong resource, SLA violation)
- **Bill change rewards**: Automatic bonus for cost reduction

### Scoring Algorithm
Task scores 0.0 (fail) to 1.0 (perfect):
- Calculated based on task-specific requirements
- Automatically saved and displayed
- Progress bars show visual progress toward 100%

### Cost Tracking
Real-time cost calculation:
- Compute costs: Based on instance type and CPU utilization
- Storage costs: Based on volume type and attachment status
- Database costs: Based on instance type and usage

---

## Troubleshooting

### Frontend won't load (blank page)
```
✓ Check if npm start is running
✓ Check browser console (F12) for errors
✓ Try: Ctrl+Shift+R (hard refresh)
✓ Clear cache: npm start --reset-cache
```

### "Cannot connect to API" error
```
✓ Check local API is running (Terminal 1)
✓ Verify REACT_APP_API_URL is set correctly
✓ Check if port 7860 is available
✓ For remote: Verify internet connection
```

### Actions not working
```
✓ Check browser console for error details
✓ Verify API backend is still running
✓ Check for network requests in Network tab
✓ Try resetting environment (Refresh button)
```

### Charts not showing
```
✓ Check browser console for errors
✓ Ensure JavaScript is enabled
✓ Try refreshing the page
✓ Check if data is being returned from API
```

---

## Common Tasks

### Optimize for Cost (Easy Task)
1. Go to **Cloud Resources** section
2. Find resources with `Delete` button (unattached volumes, idle instances)
3. Click `Delete` on each
4. Watch score go up in **Task Scores** section
5. Monitor cost reduction in **Metrics Overview**

### Optimize for Performance (Medium Task)
1. Look for instances with **low CPU usage** (< 5%)
2. Click `Downsize` button or use **Quick Actions**
3. Select smaller instance type (t3.small, t3.medium)
4. Watch latency metric - should stay < 200ms
5. Score increases as you resize more instances

### Optimize for ROI (Hard Task)
1. Delete waste (unattached volumes, idle instances)
2. Downsize underutilized compute
3. Purchase savings plans for remaining resources
4. Aim for ~40% cost reduction
5. Keep latency < 200ms and zero downtime

---

## Tips & Tricks

💡 **Start Easy**: Begin with cleanup (delete obvious waste)

💡 **Monitor Metrics**: Watch latency before aggressive downsizing

💡 **Read Tooltips**: Hover over resources to see what they do

💡 **Action History**: Review past actions to understand impact

💡 **Reset Often**: Use "Reset Environment" to try different strategies

💡 **Savings Plans**: Most impactful for hard task (40%+ savings)

---

## API Documentation

The frontend calls these endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/reset` | Reset environment to initial state |
| POST | `/step` | Execute an action (delete, modify, purchase) |
| GET | `/state` | Get current cloud state |
| GET | `/tasks/{id}/score` | Get task completion score |

Full API docs: See [../main.py](../main.py)

---

## Next Steps

1. ✅ Install dependencies (`npm install`)
2. ✅ Start backend API (`python -m uvicorn main:app ...`)
3. ✅ Start frontend (`npm start`)
4. ✅ Open browser to `http://localhost:3000`
5. ✅ Click "Reset Environment" to begin
6. ✅ Start optimizing!

---

Enjoy optimizing your cloud infrastructure! 🚀
