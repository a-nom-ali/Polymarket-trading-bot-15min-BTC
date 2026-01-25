/**
 * useWorkflowEvents Hook
 *
 * React hook for subscribing to and filtering workflow events from WebSocket.
 */

import { useState, useEffect, useCallback } from 'react';
import { websocketService } from '../services/websocket';

export interface WorkflowEvent {
  type: string;
  execution_id?: string;
  workflow_id?: string;
  bot_id?: string;
  strategy_id?: string;
  node_id?: string;
  node_name?: string;
  node_category?: string;
  timestamp: string;
  duration_ms?: number;
  status?: string;
  outputs?: any;
  error?: string;
  error_type?: string;
  [key: string]: any;
}

export interface UseWorkflowEventsOptions {
  workflowId?: string;
  botId?: string;
  strategyId?: string;
  eventTypes?: string[];
  maxEvents?: number;
}

/**
 * Custom hook for subscribing to workflow events
 *
 * @param options - Filtering options for events
 * @returns Array of filtered workflow events
 */
export function useWorkflowEvents(options: UseWorkflowEventsOptions = {}) {
  const {
    workflowId,
    botId,
    strategyId,
    eventTypes,
    maxEvents = 100,
  } = options;

  const [events, setEvents] = useState<WorkflowEvent[]>([]);

  // Handle incoming workflow event
  const handleWorkflowEvent = useCallback((event: WorkflowEvent) => {
    // Apply filters
    if (workflowId && event.workflow_id !== workflowId) return;
    if (botId && event.bot_id !== botId) return;
    if (strategyId && event.strategy_id !== strategyId) return;
    if (eventTypes && !eventTypes.includes(event.type)) return;

    setEvents(prev => {
      const newEvents = [event, ...prev];
      // Limit to maxEvents
      return newEvents.slice(0, maxEvents);
    });
  }, [workflowId, botId, strategyId, eventTypes, maxEvents]);

  // Clear events
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  useEffect(() => {
    // Subscribe to workflow_event
    websocketService.on('workflow_event', handleWorkflowEvent);

    // Cleanup on unmount
    return () => {
      websocketService.off('workflow_event', handleWorkflowEvent);
    };
  }, [handleWorkflowEvent]);

  return {
    events,
    clearEvents,
  };
}

export default useWorkflowEvents;
