/**
 * EventCard Component
 *
 * Formatted display of a single workflow event.
 */

import React, { useState } from 'react';
import { type WorkflowEvent } from '../../hooks/useWorkflowEvents';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface EventCardProps {
  event: WorkflowEvent;
}

const EventCard: React.FC<EventCardProps> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);

  const getEventTypeColor = (type: string) => {
    if (type.includes('started')) return 'bg-blue-900/30 text-blue-400 border-blue-800';
    if (type.includes('completed')) return 'bg-green-900/30 text-green-400 border-green-800';
    if (type.includes('failed')) return 'bg-red-900/30 text-red-400 border-red-800';
    if (type.includes('halted')) return 'bg-yellow-900/30 text-yellow-400 border-yellow-800';
    return 'bg-gray-900/30 text-gray-400 border-gray-800';
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString() + '.' + date.getMilliseconds().toString().padStart(3, '0');
  };

  const getKeyDetails = () => {
    const details: Array<{ label: string; value: any }> = [];

    if (event.node_id) details.push({ label: 'Node ID', value: event.node_id });
    if (event.node_name) details.push({ label: 'Node Name', value: event.node_name });
    if (event.node_category) details.push({ label: 'Category', value: event.node_category });
    if (event.duration_ms) details.push({ label: 'Duration', value: `${event.duration_ms.toFixed(2)}ms` });
    if (event.status) details.push({ label: 'Status', value: event.status });
    if (event.error) details.push({ label: 'Error', value: event.error });
    if (event.error_type) details.push({ label: 'Error Type', value: event.error_type });

    return details;
  };

  const keyDetails = getKeyDetails();

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden transition-all">
      {/* Event Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-800 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 flex-1">
            <span className={`px-2.5 py-1 rounded-md text-xs font-medium border ${getEventTypeColor(event.type)}`}>
              {event.type}
            </span>
            {keyDetails.length > 0 && (
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                {keyDetails.slice(0, 2).map((detail, idx) => (
                  <span key={idx}>
                    <span className="text-gray-500">{detail.label}:</span>{' '}
                    <span className="text-gray-300">{detail.value}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-xs text-gray-500 font-mono">
              {formatTimestamp(event.timestamp)}
            </span>
            {expanded ? (
              <ChevronUpIcon className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-4 h-4 text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 bg-gray-950">
          <div className="space-y-3">
            {/* IDs */}
            <div className="grid grid-cols-2 gap-4">
              {event.execution_id && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Execution ID</p>
                  <code className="text-xs text-blue-400 font-mono break-all">
                    {event.execution_id}
                  </code>
                </div>
              )}
              {event.workflow_id && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Workflow ID</p>
                  <code className="text-xs text-gray-300 font-mono">
                    {event.workflow_id}
                  </code>
                </div>
              )}
              {event.bot_id && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Bot ID</p>
                  <code className="text-xs text-gray-300 font-mono">
                    {event.bot_id}
                  </code>
                </div>
              )}
              {event.strategy_id && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Strategy ID</p>
                  <code className="text-xs text-gray-300 font-mono">
                    {event.strategy_id}
                  </code>
                </div>
              )}
            </div>

            {/* Key Details */}
            {keyDetails.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-2">Details</p>
                <div className="grid grid-cols-2 gap-2">
                  {keyDetails.map((detail, idx) => (
                    <div key={idx} className="text-xs">
                      <span className="text-gray-500">{detail.label}:</span>{' '}
                      <span className="text-gray-300">{detail.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Outputs */}
            {event.outputs && (
              <div>
                <p className="text-xs text-gray-500 mb-2">Outputs</p>
                <pre className="text-xs text-gray-300 bg-gray-900 p-2 rounded overflow-x-auto">
                  {JSON.stringify(event.outputs, null, 2)}
                </pre>
              </div>
            )}

            {/* Full JSON */}
            <details className="mt-3">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
                View Full JSON
              </summary>
              <pre className="text-xs text-gray-300 bg-gray-900 p-3 rounded mt-2 overflow-x-auto">
                {JSON.stringify(event, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      )}
    </div>
  );
};

export default EventCard;
