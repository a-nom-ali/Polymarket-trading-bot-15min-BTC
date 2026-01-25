/**
 * RiskLimitMonitor Component
 *
 * Visual monitoring of risk limits with progress bars and color-coded warnings.
 */

import React from 'react';

export interface RiskLimit {
  name: string;
  current: number;
  limit: number;
  unit: string;
}

export interface RiskLimitMonitorProps {
  limits: RiskLimit[];
}

const RiskLimitMonitor: React.FC<RiskLimitMonitorProps> = ({ limits }) => {
  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 0.9) return 'bg-red-500';
    if (utilization >= 0.7) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getBarColor = (utilization: number) => {
    if (utilization >= 0.9) return 'bg-red-600';
    if (utilization >= 0.7) return 'bg-yellow-600';
    return 'bg-green-600';
  };

  if (limits.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 text-center">
        <p className="text-gray-400">No risk limits configured</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {limits.map((limit, index) => {
        const utilization = Math.min(Math.abs(limit.current) / Math.abs(limit.limit), 1);
        const percentage = (utilization * 100).toFixed(1);

        return (
          <div
            key={index}
            className="bg-gray-800 rounded-lg p-6 border border-gray-700"
          >
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="text-white font-medium">{limit.name}</h4>
                <p className="text-sm text-gray-400">
                  {limit.current.toFixed(2)} {limit.unit} / {Math.abs(limit.limit).toFixed(2)} {limit.unit} limit
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${getUtilizationColor(utilization)}`} />
                <span className="text-sm font-medium text-white">{percentage}%</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-gray-700 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-300 ${getBarColor(utilization)}`}
                style={{ width: `${Math.min(utilization * 100, 100)}%` }}
              />
            </div>

            {/* Warning Message */}
            {utilization >= 0.9 && (
              <div className="mt-3 p-3 bg-red-900/20 border border-red-800 rounded-lg">
                <p className="text-sm text-red-400 font-medium">
                  ⚠️ Critical: Auto-halt will trigger at 100% utilization
                </p>
              </div>
            )}
            {utilization >= 0.7 && utilization < 0.9 && (
              <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-800 rounded-lg">
                <p className="text-sm text-yellow-400 font-medium">
                  ⚡ Warning: Approaching risk limit
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default RiskLimitMonitor;
