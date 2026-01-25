/**
 * Bots Page
 *
 * Bot management and details.
 */

import React from 'react';

const Bots: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Bots</h2>
        <p className="text-gray-400 mt-1">
          Manage and monitor your trading bots
        </p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <p className="text-gray-400">Bot list and details will be displayed here</p>
      </div>
    </div>
  );
};

export default Bots;
