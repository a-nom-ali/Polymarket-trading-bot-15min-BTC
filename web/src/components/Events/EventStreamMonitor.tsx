/**
 * EventStreamMonitor Component
 *
 * Live scrolling event feed with filtering and search.
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';
import EventCard from './EventCard';

const EVENT_TYPES = [
  'all',
  'execution_started',
  'execution_completed',
  'execution_failed',
  'execution_halted',
  'node_started',
  'node_completed',
  'node_failed',
  'emergency_state_changed',
];

const EventStreamMonitor: React.FC = () => {
  const { events, clearEvents } = useWorkflowEvents({ maxEvents: 200 });
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const matchesType =
        eventTypeFilter === 'all' || event.type === eventTypeFilter;

      const matchesSearch =
        searchTerm === '' ||
        JSON.stringify(event).toLowerCase().includes(searchTerm.toLowerCase());

      return matchesType && matchesSearch;
    });
  }, [events, eventTypeFilter, searchTerm]);

  const handleExport = () => {
    const dataStr = JSON.stringify(filteredEvents, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `workflow-events-${new Date().toISOString()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Controls */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center space-x-4 mb-3">
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="bg-gray-900 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
          >
            {EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type === 'all' ? 'All Event Types' : type}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Search events..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-gray-900 text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={clearEvents}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Clear
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Export JSON
          </button>
        </div>
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-400">
            {filteredEvents.length} events
            {eventTypeFilter !== 'all' && ` (filtered by ${eventTypeFilter})`}
          </p>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="form-checkbox h-4 w-4 text-blue-600 bg-gray-900 border-gray-700 rounded"
            />
            <span className="text-sm text-gray-400">Auto-scroll</span>
          </label>
        </div>
      </div>

      {/* Event Stream */}
      <div
        ref={scrollRef}
        className="flex-1 bg-gray-800 rounded-lg border border-gray-700 overflow-y-auto p-4 space-y-3"
      >
        {filteredEvents.length > 0 ? (
          filteredEvents.map((event, index) => (
            <EventCard key={index} event={event} />
          ))
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-400 text-lg">No events to display</p>
              <p className="text-gray-500 text-sm mt-2">
                {events.length === 0
                  ? 'Waiting for workflow events...'
                  : 'No events match your filters'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EventStreamMonitor;
