/**
 * Workflows Page
 *
 * Workflow visualization and management.
 */

import React from 'react';
import WorkflowVisualizer from '../components/Workflow/WorkflowVisualizer';

const Workflows: React.FC = () => {
  return (
    <div className="flex flex-col h-full space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Workflows</h2>
        <p className="text-gray-400 mt-1">
          Real-time workflow execution visualization
        </p>
      </div>

      <div className="flex-1 bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <WorkflowVisualizer />
      </div>
    </div>
  );
};

export default Workflows;
