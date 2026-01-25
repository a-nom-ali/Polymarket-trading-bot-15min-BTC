/**
 * ExecutionTimelineChart Component
 *
 * Area chart showing execution activity over time with success/failure breakdown.
 */

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

export interface TimelineDataPoint {
  timestamp: number;
  executions: number;
  successes: number;
  failures: number;
}

interface ExecutionTimelineChartProps {
  data: TimelineDataPoint[];
  title?: string;
  height?: number;
}

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: number;
}> = ({ active, payload, label }) => {
  if (!active || !payload || !label) return null;

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
      <p className="text-gray-400 text-xs mb-2">{formatTime(label)}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
};

const ExecutionTimelineChart: React.FC<ExecutionTimelineChartProps> = ({
  data,
  title,
  height = 250,
}) => {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-800 rounded-lg border border-gray-700"
        style={{ height }}
      >
        <p className="text-gray-500">No timeline data available</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      {title && (
        <h4 className="text-white font-medium mb-4">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <defs>
            <linearGradient id="colorSuccesses" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorFailures" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTime}
            stroke="#6B7280"
            fontSize={12}
          />
          <YAxis stroke="#6B7280" fontSize={12} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Area
            type="monotone"
            dataKey="successes"
            name="Successes"
            stroke="#10B981"
            fill="url(#colorSuccesses)"
            stackId="1"
          />
          <Area
            type="monotone"
            dataKey="failures"
            name="Failures"
            stroke="#EF4444"
            fill="url(#colorFailures)"
            stackId="1"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ExecutionTimelineChart;
