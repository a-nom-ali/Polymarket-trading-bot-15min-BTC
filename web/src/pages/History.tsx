/**
 * History Page
 *
 * Execution history viewer with search and filtering.
 */

import React from 'react';
import ExecutionHistoryViewer from '../components/History/ExecutionHistoryViewer';

const History: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Execution History</h2>
        <p className="text-gray-400 mt-1">
          Search and view past workflow executions
        </p>
      </div>

      <ExecutionHistoryViewer />
    </div>
  );
};

export default History;
