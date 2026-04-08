import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  PieChart, Pie, Cell,
  Tooltip, ResponsiveContainer
} from 'recharts';
import {
  Trash2, PlusCircle, RefreshCw, AlertCircle, CheckCircle,
  DollarSign, Zap, Database, HardDrive
} from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'https://mahekgupta312006-finops-optimizer.hf.space';

export default function App() {
  const [observation, setObservation] = useState(null);
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState(true);
  const [actionHistory, setActionHistory] = useState([]);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);

  const addLog = useCallback((message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${message}`;
    console.log(`[${type.toUpperCase()}]`, logMessage);
    setLogs(prev => [...prev, { message: logMessage, type, id: Date.now() }]);
  }, []);

  const resetEnvironment = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      addLog('🔄 Resetting environment...', 'info');
      const response = await axios.post(`${API_URL}/reset`);
      addLog(`✅ Environment reset. Bill: $${response.data.cost_data.projected_monthly_bill}`, 'success');
      setObservation(response.data);
      await fetchScores();
      setActionHistory([]);
    } catch (err) {
      const errMsg = `Failed to reset: ${err.message}`;
      addLog(errMsg, 'error');
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  }, [addLog]);

  useEffect(() => {
    resetEnvironment();
  }, [resetEnvironment]);

  const fetchScores = useCallback(async () => {
    try {
      addLog('📊 Fetching task scores...', 'info');
      const tasks = ['cleanup_unattached', 'rightsize_compute', 'fleet_strategy'];
      const newScores = {};
      for (const task of tasks) {
        const response = await axios.get(`${API_URL}/tasks/${task}/score`);
        newScores[task] = response.data.score;
        addLog(`  📈 ${task}: ${(response.data.score * 100).toFixed(1)}%`, 'info');
      }
      setScores(newScores);
      addLog('✅ Scores fetched successfully', 'success');
    } catch (err) {
      addLog(`Failed to fetch scores: ${err.message}`, 'error');
      console.error('Failed to fetch scores:', err);
    }
  }, [addLog]);

  const executeAction = useCallback(async (action) => {
    try {
      setError(null);
      addLog(`🚀 Executing: ${action.action_type}`, 'info');
      const response = await axios.post(`${API_URL}/step`, action);
      setObservation(response.data.observation);
      setActionHistory(prev => [
        ...prev,
        { action, reward: response.data.reward, timestamp: new Date() }
      ]);
      addLog(`  ✅ Reward: ${response.data.reward > 0 ? '+' : ''}${response.data.reward.toFixed(3)}`, 'success');
      addLog(`  💰 New bill: $${response.data.observation.cost_data.projected_monthly_bill.toFixed(2)}`, 'info');
      await fetchScores();
    } catch (err) {
      const errMsg = `Action failed: ${err.message}`;
      addLog(errMsg, 'error');
      setError(errMsg);
    }
  }, [addLog, fetchScores]);

  const deleteResource = useCallback((resourceId) => {
    executeAction({ action_type: 'delete_resource', resource_id: resourceId });
  }, [executeAction]);

  const modifyInstance = useCallback((instanceId, newType) => {
    executeAction({
      action_type: 'modify_instance',
      instance_id: instanceId,
      new_type: newType
    });
  }, [executeAction]);

  const purchaseSavingsPlan = useCallback((planType) => {
    executeAction({
      action_type: 'purchase_savings_plan',
      plan_type: planType,
      duration: '1y'
    });
  }, [executeAction]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin mb-4 inline-block">
            <RefreshCw size={48} />
          </div>
          <p className="text-xl">Loading FinOps Environment...</p>
        </div>
      </div>
    );
  }

  if (!observation) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <button
          onClick={resetEnvironment}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg"
        >
          Start Environment
        </button>
      </div>
    );
  }

  const compute = observation.inventory.filter(r => r.category === 'compute');
  const storage = observation.inventory.filter(r => r.category === 'storage');
  const database = observation.inventory.filter(r => r.category === 'database');

  const costData = [
    { name: 'Compute', value: compute.reduce((sum, r) => sum + r.monthly_cost, 0) },
    { name: 'Storage', value: storage.reduce((sum, r) => sum + r.monthly_cost, 0) },
    { name: 'Database', value: database.reduce((sum, r) => sum + r.monthly_cost, 0) }
  ];

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b'];

  const taskDescriptions = {
    cleanup_unattached: 'Delete unattached storage and idle test instances',
    rightsize_compute: 'Downsize underutilized VMs while maintaining performance',
    fleet_strategy: 'Achieve 40%+ cost reduction with positive ROI'
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">FinOps Cloud Optimizer</h1>
            <p className="text-gray-400">Optimize your cloud infrastructure costs</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2"
            >
              📋 Logs ({logs.length})
            </button>
            <button
              onClick={resetEnvironment}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
            >
              <RefreshCw size={20} />
              Reset Environment
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-900 border border-red-700 rounded-lg flex items-start gap-3">
            <AlertCircle size={24} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Error</p>
              <p className="text-sm text-red-100">{error}</p>
            </div>
          </div>
        )}

        {/* Logs Panel */}
        {showLogs && (
          <div className="mb-6 bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-bold">System Logs</h3>
              <button
                onClick={() => setLogs([])}
                className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded"
              >
                Clear
              </button>
            </div>
            <div className="bg-gray-900 rounded p-3 font-mono text-sm max-h-48 overflow-y-auto space-y-1">
              {logs.length === 0 ? (
                <p className="text-gray-500">No logs yet...</p>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className={`text-xs ${
                      log.type === 'error'
                        ? 'text-red-400'
                        : log.type === 'success'
                        ? 'text-green-400'
                        : 'text-blue-400'
                    }`}
                  >
                    {log.message}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Metrics Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <MetricCard
            icon={<DollarSign size={28} />}
            label="Monthly Bill"
            value={`$${observation.cost_data.projected_monthly_bill.toFixed(2)}`}
            color="from-blue-600 to-blue-800"
          />
          <MetricCard
            icon={<Zap size={28} />}
            label="System Latency"
            value={`${observation.health_status.system_latency_ms.toFixed(1)}ms`}
            color="from-yellow-600 to-yellow-800"
          />
          <MetricCard
            icon={<AlertCircle size={28} />}
            label="Throttle Events"
            value={observation.health_status.throttling_events}
            color="from-orange-600 to-orange-800"
          />
          <MetricCard
            icon={<CheckCircle size={28} />}
            label="Downtime Events"
            value={observation.health_status.downtime_events}
            color="from-red-600 to-red-800"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Cost Breakdown */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-6">Cost Breakdown</h2>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={costData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: $${value.toFixed(0)}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {costData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Task Scores */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-6">Task Scores</h2>
            <div className="space-y-4">
              {Object.entries(taskDescriptions).map(([taskId, description]) => (
                <div key={taskId} className="bg-gray-700 rounded p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold capitalize">
                        {taskId.replace(/_/g, ' ')}
                      </h3>
                      <p className="text-sm text-gray-300">{description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-green-400">
                        {(scores[taskId] * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-400">
                        {scores[taskId].toFixed(3)}
                      </div>
                    </div>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full"
                      style={{ width: `${scores[taskId] * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Inventory and Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Inventory */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4">Cloud Resources</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {observation.inventory.map((resource) => (
                <ResourceCard
                  key={resource.id}
                  resource={resource}
                  onDelete={() => deleteResource(resource.id)}
                  onModify={modifyInstance}
                />
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4">Quick Actions</h2>
            <div className="space-y-3">
              <ActionSection title="Compute Optimizations">
                {['t3.micro', 't3.small', 't3.medium', 't3.large'].map(type => (
                  <button
                    key={type}
                    onClick={() => {
                      const vm = compute.find(r => r.resource_type !== type);
                      if (vm) modifyInstance(vm.id, type);
                    }}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
                  >
                    Resize to {type}
                  </button>
                ))}
              </ActionSection>

              <ActionSection title="Resource Cleanup">
                <button
                  onClick={() => {
                    const vol = storage.find(r => !r.is_attached);
                    if (vol) deleteResource(vol.id);
                  }}
                  className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm flex items-center gap-2 justify-center"
                >
                  <Trash2 size={16} />
                  Delete Unattached Volume
                </button>
              </ActionSection>

              <ActionSection title="Savings Plans">
                <button
                  onClick={() => purchaseSavingsPlan('compute')}
                  className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm flex items-center gap-2 justify-center"
                >
                  <PlusCircle size={16} />
                  Buy Compute Savings Plan (1yr)
                </button>
                <button
                  onClick={() => purchaseSavingsPlan('database')}
                  className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm flex items-center gap-2 justify-center"
                >
                  <PlusCircle size={16} />
                  Buy Database Savings Plan (1yr)
                </button>
              </ActionSection>
            </div>
          </div>
        </div>

        {/* Action History */}
        {actionHistory.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4">Action History</h2>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {actionHistory.slice().reverse().map((entry, idx) => (
                <div key={idx} className="flex justify-between items-center p-3 bg-gray-700 rounded text-sm">
                  <div>
                    <p className="font-mono text-xs text-gray-300">
                      {entry.action.action_type}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${entry.reward > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {entry.reward > 0 ? '+' : ''}{entry.reward.toFixed(3)}
                    </p>
                    <p className="text-xs text-gray-400">
                      {entry.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, color }) {
  return (
    <div className={`bg-gradient-to-br ${color} rounded-lg p-6 text-white`}>
      <div className="flex items-start justify-between mb-4">
        <div className="opacity-75">{icon}</div>
      </div>
      <p className="text-gray-200 text-sm mb-1">{label}</p>
      <p className="text-3xl font-bold">{value}</p>
    </div>
  );
}

function ResourceCard({ resource, onDelete, onModify }) {
  const getCategoryColor = (category) => {
    switch (category) {
      case 'compute': return 'bg-blue-900 border-blue-700';
      case 'storage': return 'bg-green-900 border-green-700';
      case 'database': return 'bg-purple-900 border-purple-700';
      default: return 'bg-gray-700 border-gray-600';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'compute': return <Zap size={16} />;
      case 'storage': return <HardDrive size={16} />;
      case 'database': return <Database size={16} />;
      default: return null;
    }
  };

  return (
    <div className={`border rounded p-4 ${getCategoryColor(resource.category)}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {getCategoryIcon(resource.category)}
          <div>
            <p className="font-mono text-sm text-blue-300">{resource.id}</p>
            <p className="text-xs text-gray-400">{resource.resource_type}</p>
          </div>
        </div>
        <p className="font-bold text-green-400">${resource.monthly_cost.toFixed(2)}/mo</p>
      </div>

      <div className="text-xs text-gray-300 mb-2">
        CPU: {resource.cpu_usage_pct_30d.toFixed(1)}% | Memory: {resource.memory_usage_pct_30d.toFixed(1)}%
      </div>

      <div className="flex gap-2 mt-3">
        {resource.category === 'storage' && !resource.is_attached && (
          <button
            onClick={() => onDelete(resource.id)}
            className="flex-1 px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-xs flex items-center gap-1 justify-center"
          >
            <Trash2 size={12} /> Delete
          </button>
        )}
        {resource.category === 'compute' && resource.cpu_usage_pct_30d < 5 && (
          <button
            onClick={() => onModify(resource.id, 't3.small')}
            className="flex-1 px-2 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-xs"
          >
            Downsize
          </button>
        )}
      </div>
    </div>
  );
}

function ActionSection({ title, children }) {
  return (
    <div className="bg-gray-700 rounded p-4">
      <h3 className="font-semibold text-sm mb-3 text-gray-300">{title}</h3>
      <div className="space-y-2">
        {children}
      </div>
    </div>
  );
}
