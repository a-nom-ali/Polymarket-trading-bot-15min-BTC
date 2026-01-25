/**
 * Dashboard Page
 *
 * Main dashboard view with bot metrics and global statistics.
 */

import React, { useMemo } from 'react';
import BotMetricsDashboard from '../components/Dashboard/BotMetricsDashboard';
import MetricCard from '../components/Shared/MetricCard';
import { useWorkflowEvents } from '../hooks/useWorkflowEvents';
import { CpuChipIcon, BoltIcon, CheckCircleIcon, ChartBarIcon } from '@heroicons/react/24/outline';

const Dashboard: React.FC = () => {
  const { events } = useWorkflowEvents({ maxEvents: 1000 });

  // Calculate global stats from events
  const globalStats = useMemo(() => {
    const uniqueBots = new Set<string>();
    let totalExecutions = 0;
    let successfulExecutions = 0;
    let runningExecutions = 0;

    events.forEach((event) => {
      if (event.bot_id) {
        uniqueBots.add(event.bot_id);
      }
      if (event.type === 'execution_started') {
        totalExecutions++;
        runningExecutions++;
      } else if (event.type === 'execution_completed') {
        successfulExecutions++;
        runningExecutions--;
      } else if (event.type === 'execution_failed' || event.type === 'execution_halted') {
        runningExecutions--;
      }
    });

    const successRate = totalExecutions > 0
      ? ((successfulExecutions / totalExecutions) * 100).toFixed(1)
      : '0';

    return {
      activeBots: uniqueBots.size,
      runningWorkflows: Math.max(0, runningExecutions),
      successRate,
      totalExecutions,
    };
  }, [events]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Dashboard</h2>
        <p className="text-gray-400 mt-1">
          Overview of all trading bots and strategies
        </p>
      </div>

      {/* Global Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Bots"
          value={globalStats.activeBots}
          icon={<CpuChipIcon className="w-5 h-5" />}
          color="blue"
        />
        <MetricCard
          title="Running Workflows"
          value={globalStats.runningWorkflows}
          icon={<BoltIcon className="w-5 h-5" />}
          color={globalStats.runningWorkflows > 0 ? 'yellow' : 'gray'}
        />
        <MetricCard
          title="Success Rate"
          value={`${globalStats.successRate}%`}
          icon={<CheckCircleIcon className="w-5 h-5" />}
          color="green"
        />
        <MetricCard
          title="Total Executions"
          value={globalStats.totalExecutions}
          icon={<ChartBarIcon className="w-5 h-5" />}
          color="gray"
        />
      </div>

      {/* Bot Metrics Section */}
      <div>
        <h3 className="text-xl font-bold text-white mb-4">Bot Metrics</h3>
        <BotMetricsDashboard />
      </div>
    </div>
  );
};

export default Dashboard;
