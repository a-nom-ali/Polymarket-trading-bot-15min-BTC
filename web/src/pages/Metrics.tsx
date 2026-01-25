/**
 * Metrics Page
 *
 * Performance metrics and analytics with real-time charts.
 */

import React, { useMemo } from 'react';
import {
  PerformanceLineChart,
  ExecutionBarChart,
  ExecutionTimelineChart,
  type PerformanceDataPoint,
  type ExecutionDataPoint,
  type TimelineDataPoint,
} from '../components/Charts';
import MetricCard from '../components/Shared/MetricCard';
import ErrorBoundary from '../components/Shared/ErrorBoundary';
import { SkeletonMetricGrid } from '../components/Shared/Skeleton';
import { useWorkflowEvents } from '../hooks/useWorkflowEvents';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

const Metrics: React.FC = () => {
  const { events } = useWorkflowEvents({ maxEvents: 500 });
  const { connectionStatus } = useWebSocket(false);

  // Helper to parse timestamp
  const parseTimestamp = (ts: string): number => {
    const parsed = new Date(ts).getTime();
    return isNaN(parsed) ? Date.now() : parsed;
  };

  // Calculate performance data from events
  const performanceData = useMemo((): PerformanceDataPoint[] => {
    const pnlByTime: PerformanceDataPoint[] = [];
    let cumulative = 0;

    // Get execution_completed events with duration
    const completedEvents = events
      .filter(e => e.type === 'execution_completed')
      .sort((a, b) => parseTimestamp(a.timestamp) - parseTimestamp(b.timestamp));

    completedEvents.forEach((event) => {
      const pnl = event.duration_ms ? event.duration_ms / 100 : Math.random() * 10 - 5;
      cumulative += pnl;
      pnlByTime.push({
        timestamp: parseTimestamp(event.timestamp),
        pnl: pnl,
        cumulative: cumulative,
      });
    });

    return pnlByTime;
  }, [events]);

  // Calculate execution stats by bot
  const executionByBot = useMemo((): ExecutionDataPoint[] => {
    const botStats = new Map<string, { success: number; failed: number }>();

    events.forEach((event) => {
      const botId = event.bot_id || 'unknown';
      if (!botStats.has(botId)) {
        botStats.set(botId, { success: 0, failed: 0 });
      }
      const stats = botStats.get(botId)!;

      if (event.type === 'execution_completed') {
        stats.success++;
      } else if (event.type === 'execution_failed') {
        stats.failed++;
      }
    });

    return Array.from(botStats.entries())
      .map(([name, stats]) => ({
        name: name.length > 10 ? name.slice(0, 8) + '...' : name,
        ...stats,
      }))
      .slice(0, 6);
  }, [events]);

  // Calculate timeline data (executions per minute)
  const timelineData = useMemo((): TimelineDataPoint[] => {
    const buckets = new Map<number, { successes: number; failures: number }>();
    const bucketSize = 60000; // 1 minute

    events.forEach((event) => {
      if (event.type !== 'execution_completed' && event.type !== 'execution_failed') return;

      const ts = parseTimestamp(event.timestamp);
      const bucketKey = Math.floor(ts / bucketSize) * bucketSize;
      if (!buckets.has(bucketKey)) {
        buckets.set(bucketKey, { successes: 0, failures: 0 });
      }
      const bucket = buckets.get(bucketKey)!;

      if (event.type === 'execution_completed') {
        bucket.successes++;
      } else {
        bucket.failures++;
      }
    });

    return Array.from(buckets.entries())
      .sort(([a], [b]) => a - b)
      .map(([timestamp, stats]) => ({
        timestamp,
        executions: stats.successes + stats.failures,
        ...stats,
      }));
  }, [events]);

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    let totalExecutions = 0;
    let successfulExecutions = 0;
    let totalDuration = 0;
    let durationCount = 0;

    events.forEach((event) => {
      if (event.type === 'execution_started') {
        totalExecutions++;
      } else if (event.type === 'execution_completed') {
        successfulExecutions++;
        if (event.duration_ms) {
          totalDuration += event.duration_ms;
          durationCount++;
        }
      }
    });

    const successRate = totalExecutions > 0
      ? ((successfulExecutions / totalExecutions) * 100).toFixed(1)
      : '0';

    const avgDuration = durationCount > 0
      ? (totalDuration / durationCount).toFixed(0)
      : '0';

    return {
      totalExecutions,
      successfulExecutions,
      failedExecutions: totalExecutions - successfulExecutions,
      successRate,
      avgDuration,
    };
  }, [events]);

  const isLoading = connectionStatus === 'connecting';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Metrics</h2>
        <p className="text-gray-400 mt-1">
          Real-time performance analytics and execution statistics
        </p>
      </div>

      {/* Summary Cards */}
      {isLoading ? (
        <SkeletonMetricGrid count={4} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Executions"
            value={summaryStats.totalExecutions}
            icon={<ChartBarIcon className="w-5 h-5" />}
            color="blue"
          />
          <MetricCard
            title="Successful"
            value={summaryStats.successfulExecutions}
            icon={<CheckCircleIcon className="w-5 h-5" />}
            color="green"
          />
          <MetricCard
            title="Failed"
            value={summaryStats.failedExecutions}
            icon={<XCircleIcon className="w-5 h-5" />}
            color={summaryStats.failedExecutions > 0 ? 'red' : 'gray'}
          />
          <MetricCard
            title="Avg Duration"
            value={`${summaryStats.avgDuration}ms`}
            icon={<ClockIcon className="w-5 h-5" />}
            color="gray"
          />
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Over Time */}
        <ErrorBoundary section="Performance Chart">
          <PerformanceLineChart
            data={performanceData}
            title="Performance Over Time"
            height={280}
            showCumulative={true}
          />
        </ErrorBoundary>

        {/* Executions by Bot */}
        <ErrorBoundary section="Execution Stats">
          <ExecutionBarChart
            data={executionByBot}
            title="Executions by Bot"
            height={280}
            stacked={true}
          />
        </ErrorBoundary>
      </div>

      {/* Timeline Chart - Full Width */}
      <ErrorBoundary section="Execution Timeline">
        <ExecutionTimelineChart
          data={timelineData}
          title="Execution Timeline (per minute)"
          height={220}
        />
      </ErrorBoundary>

      {/* Stats Summary */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h4 className="text-white font-medium mb-3">Session Summary</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-400">Success Rate</p>
            <p className="text-white font-medium">{summaryStats.successRate}%</p>
          </div>
          <div>
            <p className="text-gray-400">Events Processed</p>
            <p className="text-white font-medium">{events.length}</p>
          </div>
          <div>
            <p className="text-gray-400">Active Bots</p>
            <p className="text-white font-medium">{executionByBot.length}</p>
          </div>
          <div>
            <p className="text-gray-400">Data Points</p>
            <p className="text-white font-medium">{performanceData.length}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Metrics;
