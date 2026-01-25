/**
 * Metrics Page
 *
 * Performance metrics and charts.
 */

import React from 'react';

const Metrics: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Metrics</h2>
        <p className="text-gray-400 mt-1">
          Performance metrics and analytics
        </p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <p className="text-gray-400">Performance charts will be displayed here</p>
      </div>
    </div>
  );
};

export default Metrics;
