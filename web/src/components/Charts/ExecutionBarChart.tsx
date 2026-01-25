/**
 * ExecutionBarChart Component
 *
 * Bar chart for execution statistics - successes, failures, and totals.
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

export interface ExecutionDataPoint {
  name: string;
  success: number;
  failed: number;
  total?: number;
}

interface ExecutionBarChartProps {
  data: ExecutionDataPoint[];
  title?: string;
  height?: number;
  stacked?: boolean;
}

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: Array<{ value: number; name: string; fill: string }>;
  label?: string;
}> = ({ active, payload, label }) => {
  if (!active || !payload) return null;

  const total = payload.reduce((sum, entry) => sum + entry.value, 0);
  const successRate = payload.find(p => p.name === 'Success')?.value || 0;
  const rate = total > 0 ? ((successRate / total) * 100).toFixed(1) : '0';

  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
      <p className="text-white font-medium text-sm mb-2">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-sm" style={{ color: entry.fill }}>
          {entry.name}: {entry.value}
        </p>
      ))}
      <p className="text-gray-400 text-xs mt-1 pt-1 border-t border-gray-600">
        Success Rate: {rate}%
      </p>
    </div>
  );
};

const ExecutionBarChart: React.FC<ExecutionBarChartProps> = ({
  data,
  title,
  height = 300,
  stacked = true,
}) => {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-800 rounded-lg border border-gray-700"
        style={{ height }}
      >
        <p className="text-gray-500">No execution data available</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      {title && (
        <h4 className="text-white font-medium mb-4">{title}</h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="name" stroke="#6B7280" fontSize={12} />
          <YAxis stroke="#6B7280" fontSize={12} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar
            dataKey="success"
            name="Success"
            fill="#10B981"
            stackId={stacked ? 'stack' : undefined}
            radius={stacked ? undefined : [4, 4, 0, 0]}
          />
          <Bar
            dataKey="failed"
            name="Failed"
            fill="#EF4444"
            stackId={stacked ? 'stack' : undefined}
            radius={stacked ? [4, 4, 0, 0] : [4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ExecutionBarChart;
