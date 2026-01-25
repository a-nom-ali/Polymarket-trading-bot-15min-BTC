/**
 * MetricCard Component
 *
 * Reusable card for displaying metrics with trend indicators.
 */

import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';

export interface MetricCardProps {
  title: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon?: React.ReactNode;
  color?: 'green' | 'blue' | 'yellow' | 'red' | 'gray';
  subtitle?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  trend,
  trendValue,
  icon,
  color = 'gray',
  subtitle,
}) => {
  const colorClasses = {
    green: 'text-green-400 bg-green-900/20 border-green-800',
    blue: 'text-blue-400 bg-blue-900/20 border-blue-800',
    yellow: 'text-yellow-400 bg-yellow-900/20 border-yellow-800',
    red: 'text-red-400 bg-red-900/20 border-red-800',
    gray: 'text-gray-400 bg-gray-800 border-gray-700',
  };

  const getTrendIcon = () => {
    if (trend === 'up') {
      return <ArrowUpIcon className="w-4 h-4 text-green-400" />;
    }
    if (trend === 'down') {
      return <ArrowDownIcon className="w-4 h-4 text-red-400" />;
    }
    return null;
  };

  return (
    <div className={`rounded-lg p-6 border ${colorClasses[color]} transition-all`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-gray-400">{title}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className={`text-3xl font-bold ${color !== 'gray' ? colorClasses[color].split(' ')[0] : 'text-white'}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>

        {trend && trendValue && (
          <div className="flex items-center space-x-1">
            {getTrendIcon()}
            <span className={`text-sm font-medium ${trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400'}`}>
              {trendValue}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
