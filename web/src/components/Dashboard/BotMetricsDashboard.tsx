/**
 * BotMetricsDashboard Component
 *
 * Grid display of bot performance metrics with real-time updates.
 */

import React, { useState, useEffect } from 'react';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';
import MetricCard from '../Shared/MetricCard';
import { CpuChipIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';

interface BotMetrics {
  botId: string;
  executionCount: number;
  successCount: number;
  failureCount: number;
  avgDuration: number;
  lastExecution?: string;
  status: 'active' | 'paused' | 'halted';
}

const BotMetricsDashboard: React.FC = () => {
  const { events } = useWorkflowEvents({ maxEvents: 500 });
  const [botMetrics, setBotMetrics] = useState<Map<string, BotMetrics>>(new Map());

  // Calculate metrics from events
  useEffect(() => {
    const metrics = new Map<string, BotMetrics>();

    events.forEach((event) => {
      const botId = event.bot_id || 'unknown';
      if (!metrics.has(botId)) {
        metrics.set(botId, {
          botId,
          executionCount: 0,
          successCount: 0,
          failureCount: 0,
          avgDuration: 0,
          status: 'active',
        });
      }

      const botMetric = metrics.get(botId)!;

      if (event.type === 'execution_started') {
        botMetric.executionCount++;
        botMetric.lastExecution = event.timestamp;
      } else if (event.type === 'execution_completed') {
        botMetric.successCount++;
        if (event.duration_ms) {
          const totalDuration = botMetric.avgDuration * (botMetric.executionCount - 1);
          botMetric.avgDuration = (totalDuration + event.duration_ms) / botMetric.executionCount;
        }
      } else if (event.type === 'execution_failed') {
        botMetric.failureCount++;
      } else if (event.type === 'execution_halted') {
        botMetric.status = 'halted';
      }
    });

    setBotMetrics(metrics);
  }, [events]);

  const botList = Array.from(botMetrics.values());

  if (botList.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-12 border border-gray-700 text-center">
        <CpuChipIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400 text-lg">No bot activity detected</p>
        <p className="text-gray-500 text-sm mt-2">
          Start a workflow with bot_id to see metrics here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {botList.map((bot) => {
        const successRate = bot.executionCount > 0
          ? ((bot.successCount / bot.executionCount) * 100).toFixed(1)
          : '0';

        return (
          <div key={bot.botId} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            {/* Bot Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <CpuChipIcon className="w-8 h-8 text-blue-400" />
                <div>
                  <h3 className="text-xl font-bold text-white">{bot.botId}</h3>
                  <p className="text-sm text-gray-400">Trading Bot</p>
                </div>
              </div>
              <div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    bot.status === 'active'
                      ? 'bg-green-900/30 text-green-400 border border-green-800'
                      : bot.status === 'halted'
                      ? 'bg-red-900/30 text-red-400 border border-red-800'
                      : 'bg-yellow-900/30 text-yellow-400 border border-yellow-800'
                  }`}
                >
                  {bot.status.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Total Executions"
                value={bot.executionCount}
                icon={<ClockIcon className="w-5 h-5" />}
                color="blue"
              />
              <MetricCard
                title="Success Rate"
                value={`${successRate}%`}
                icon={<CheckCircleIcon className="w-5 h-5" />}
                color="green"
                subtitle={`${bot.successCount} successful`}
              />
              <MetricCard
                title="Failures"
                value={bot.failureCount}
                icon={<XCircleIcon className="w-5 h-5" />}
                color={bot.failureCount > 0 ? 'red' : 'gray'}
              />
              <MetricCard
                title="Avg Duration"
                value={`${bot.avgDuration.toFixed(0)}ms`}
                icon={<ClockIcon className="w-5 h-5" />}
                color="gray"
              />
            </div>

            {/* Last Execution */}
            {bot.lastExecution && (
              <div className="mt-4 pt-4 border-t border-gray-700">
                <p className="text-xs text-gray-500">
                  Last execution: {new Date(bot.lastExecution).toLocaleString()}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default BotMetricsDashboard;
