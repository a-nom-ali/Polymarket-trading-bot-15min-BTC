/**
 * ExecutionHistoryViewer Component
 *
 * Searchable table of past workflow executions with filtering.
 */

import React, { useState, useMemo } from 'react';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

interface ExecutionRecord {
  execution_id: string;
  workflow_id?: string;
  bot_id?: string;
  strategy_id?: string;
  status: 'completed' | 'failed' | 'halted';
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

const ExecutionHistoryViewer: React.FC = () => {
  const { events } = useWorkflowEvents({ maxEvents: 1000 });
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Build execution records from events
  const executions = useMemo(() => {
    const executionMap = new Map<string, ExecutionRecord>();

    events.forEach((event) => {
      const execId = event.execution_id;
      if (!execId) return;

      if (event.type === 'execution_started') {
        executionMap.set(execId, {
          execution_id: execId,
          workflow_id: event.workflow_id,
          bot_id: event.bot_id,
          strategy_id: event.strategy_id,
          status: 'completed', // Default, will be updated
          started_at: event.timestamp,
        });
      } else if (event.type === 'execution_completed') {
        const record = executionMap.get(execId);
        if (record) {
          record.status = 'completed';
          record.completed_at = event.timestamp;
          record.duration_ms = event.duration_ms;
        }
      } else if (event.type === 'execution_failed') {
        const record = executionMap.get(execId);
        if (record) {
          record.status = 'failed';
          record.completed_at = event.timestamp;
          record.error = event.error;
        }
      } else if (event.type === 'execution_halted') {
        const record = executionMap.get(execId);
        if (record) {
          record.status = 'halted';
          record.completed_at = event.timestamp;
          record.error = event.error || 'Emergency halt';
        }
      }
    });

    return Array.from(executionMap.values()).sort(
      (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
    );
  }, [events]);

  // Filter executions
  const filteredExecutions = useMemo(() => {
    return executions.filter((exec) => {
      const matchesSearch =
        searchTerm === '' ||
        exec.execution_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exec.workflow_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exec.bot_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exec.strategy_id?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus =
        statusFilter === 'all' || exec.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [executions, searchTerm, statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-900/30 text-green-400 border border-green-800">
            <CheckCircleIcon className="w-3 h-3 mr-1" />
            Completed
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-900/30 text-red-400 border border-red-800">
            <XCircleIcon className="w-3 h-3 mr-1" />
            Failed
          </span>
        );
      case 'halted':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-900/30 text-yellow-400 border border-yellow-800">
            <XCircleIcon className="w-3 h-3 mr-1" />
            Halted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-900/30 text-gray-400 border border-gray-800">
            Unknown
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by execution ID, workflow ID, bot ID, strategy ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-gray-900 text-white pl-10 pr-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-900 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="halted">Halted</option>
          </select>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          Showing {filteredExecutions.length} of {executions.length} executions
        </p>
      </div>

      {/* Execution Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Execution ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Workflow / Bot
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Started At
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredExecutions.length > 0 ? (
                filteredExecutions.slice(0, 50).map((exec) => (
                  <tr
                    key={exec.execution_id}
                    className="hover:bg-gray-900 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <code className="text-sm text-blue-400 font-mono">
                        {exec.execution_id.substring(0, 24)}...
                      </code>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-white">
                        {exec.workflow_id || 'N/A'}
                      </div>
                      <div className="text-xs text-gray-400">
                        {exec.bot_id ? `Bot: ${exec.bot_id}` : 'No bot'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(exec.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-300">
                        <ClockIcon className="w-4 h-4 mr-1 text-gray-400" />
                        {exec.duration_ms
                          ? `${exec.duration_ms.toFixed(0)}ms`
                          : 'N/A'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {new Date(exec.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <p className="text-gray-400">No executions found</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {filteredExecutions.length > 50 && (
        <div className="text-center">
          <p className="text-sm text-gray-400">
            Showing first 50 results. Refine your search to see more.
          </p>
        </div>
      )}
    </div>
  );
};

export default ExecutionHistoryViewer;
