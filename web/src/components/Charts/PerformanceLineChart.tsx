/**
 * PerformanceLineChart Component
 *
 * Real-time line chart for PnL and performance metrics over time.
 * Uses Recharts for visualization.
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

export interface PerformanceDataPoint {
  timestamp: number;
  pnl: number;
  cumulative?: number;
  label?: string;
}

interface PerformanceLineChartProps {
  data: PerformanceDataPoint[];
  title?: string;
  height?: number;
  showCumulative?: boolean;
  color?: string;
}

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatValue = (value: number): string => {
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}k`;
  }
  return `$${value.toFixed(2)}`;
};

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: number;
}> = ({ active, payload, label }) => {
  if (!active || !payload || !label) return null;

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
      <p className="text-gray-400 text-xs mb-1">{formatTime(label)}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatValue(entry.value)}
        </p>
      ))}
    </div>
  );
};

const PerformanceLineChart: React.FC<PerformanceLineChartProps> = ({
  data,
  title,
  height = 300,
  showCumulative = false,
  color = '#10B981',
}) => {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-800 rounded-lg border border-gray-700"
        style={{ height }}
      >
        <p className="text-gray-500">No performance data available</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      {title && (
        <h4 className="text-white font-medium mb-4">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTime}
            stroke="#6B7280"
            fontSize={12}
          />
          <YAxis
            tickFormatter={formatValue}
            stroke="#6B7280"
            fontSize={12}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line
            type="monotone"
            dataKey="pnl"
            name="PnL"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: color }}
          />
          {showCumulative && (
            <Line
              type="monotone"
              dataKey="cumulative"
              name="Cumulative"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              strokeDasharray="5 5"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceLineChart;
