/**
 * EmergencyControlPanel Component
 *
 * Emergency halt controls with current state display and manual controls.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';
import RiskLimitMonitor, { type RiskLimit } from './RiskLimitMonitor';
import {
  ExclamationTriangleIcon,
  PlayIcon,
  StopIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';

type EmergencyState = 'NORMAL' | 'ALERT' | 'HALT' | 'SHUTDOWN';

const EmergencyControlPanel: React.FC = () => {
  const { events } = useWorkflowEvents({ maxEvents: 500 });
  const [currentState, setCurrentState] = useState<EmergencyState>('NORMAL');
  const [haltReason, setHaltReason] = useState<string>('');

  // Track emergency state changes from events
  useEffect(() => {
    const stateChangeEvent = events.find(e => e.type === 'emergency_state_changed');
    if (stateChangeEvent) {
      setCurrentState(stateChangeEvent.new_state || 'NORMAL');
      setHaltReason(stateChangeEvent.reason || '');
    }
  }, [events]);

  // Calculate risk limits from events (mock data for now)
  const riskLimits: RiskLimit[] = useMemo(() => {
    // In production, this would come from API or events
    return [
      {
        name: 'Daily Loss Limit',
        current: -125.50,
        limit: -500.0,
        unit: 'USD',
      },
      {
        name: 'Max Position Size',
        current: 12500.0,
        limit: 50000.0,
        unit: 'USD',
      },
      {
        name: 'Max Drawdown',
        current: 8.5,
        limit: 15.0,
        unit: '%',
      },
    ];
  }, []);

  // Handle manual controls (would call API in production)
  const handleHalt = () => {
    console.log('Emergency halt triggered');
    setCurrentState('HALT');
    setHaltReason('Manual halt by operator');
    // TODO: Call API to trigger halt
  };

  const handleResume = () => {
    console.log('Resuming normal operations');
    setCurrentState('NORMAL');
    setHaltReason('');
    // TODO: Call API to resume
  };

  const handleAlert = () => {
    console.log('Alert state set');
    setCurrentState('ALERT');
    setHaltReason('Manual alert by operator');
    // TODO: Call API to set alert
  };

  const getStateColor = () => {
    switch (currentState) {
      case 'NORMAL':
        return 'bg-green-900/30 text-green-400 border-green-800';
      case 'ALERT':
        return 'bg-yellow-900/30 text-yellow-400 border-yellow-800';
      case 'HALT':
        return 'bg-red-900/30 text-red-400 border-red-800';
      case 'SHUTDOWN':
        return 'bg-gray-900/30 text-gray-400 border-gray-800';
      default:
        return 'bg-gray-900/30 text-gray-400 border-gray-800';
    }
  };

  const getStateIcon = () => {
    switch (currentState) {
      case 'NORMAL':
        return <PlayIcon className="w-8 h-8 text-green-400" />;
      case 'ALERT':
        return <ExclamationTriangleIcon className="w-8 h-8 text-yellow-400" />;
      case 'HALT':
        return <StopIcon className="w-8 h-8 text-red-400" />;
      case 'SHUTDOWN':
        return <ShieldExclamationIcon className="w-8 h-8 text-gray-400" />;
    }
  };

  const canTrade = currentState === 'NORMAL' || currentState === 'ALERT';

  return (
    <div className="space-y-6">
      {/* Current State Display */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {getStateIcon()}
            <div>
              <p className="text-sm text-gray-400">Emergency State</p>
              <p className={`text-3xl font-bold mt-1 px-4 py-2 rounded-lg border inline-block ${getStateColor()}`}>
                {currentState}
              </p>
              {haltReason && (
                <p className="text-sm text-gray-400 mt-2">Reason: {haltReason}</p>
              )}
            </div>
          </div>

          {/* Status Indicators */}
          <div className="text-right space-y-2">
            <div className="flex items-center justify-end space-x-2">
              <span className="text-sm text-gray-400">Can Trade:</span>
              <span className={`font-medium ${canTrade ? 'text-green-400' : 'text-red-400'}`}>
                {canTrade ? 'Yes' : 'No'}
              </span>
            </div>
            <div className="flex items-center justify-end space-x-2">
              <span className="text-sm text-gray-400">Can Operate:</span>
              <span className={`font-medium ${currentState !== 'SHUTDOWN' ? 'text-green-400' : 'text-red-400'}`}>
                {currentState !== 'SHUTDOWN' ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </div>

        {/* Manual Controls */}
        <div className="mt-6 pt-6 border-t border-gray-700">
          <p className="text-sm text-gray-400 mb-3">Manual Controls</p>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleHalt}
              disabled={currentState === 'HALT' || currentState === 'SHUTDOWN'}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors font-medium"
            >
              Emergency Halt
            </button>
            <button
              onClick={handleAlert}
              disabled={currentState === 'ALERT' || currentState === 'HALT'}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors font-medium"
            >
              Set Alert
            </button>
            <button
              onClick={handleResume}
              disabled={currentState === 'NORMAL'}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors font-medium"
            >
              Resume Normal
            </button>
          </div>
        </div>
      </div>

      {/* Risk Limits */}
      <div>
        <h3 className="text-xl font-bold text-white mb-4">Risk Limits</h3>
        <RiskLimitMonitor limits={riskLimits} />
      </div>

      {/* Emergency Event History */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-xl font-bold text-white mb-4">Emergency Event History</h3>
        <div className="space-y-2">
          {events
            .filter(e => e.type === 'emergency_state_changed' || e.type === 'execution_halted')
            .slice(0, 5)
            .map((event, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-900 rounded-lg"
              >
                <div>
                  <p className="text-sm text-white font-medium">
                    {event.type === 'emergency_state_changed'
                      ? `State changed to ${event.new_state}`
                      : 'Execution halted'}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {event.reason || 'No reason provided'}
                  </p>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          {events.filter(e => e.type === 'emergency_state_changed' || e.type === 'execution_halted').length === 0 && (
            <p className="text-gray-400 text-center py-4">No emergency events recorded</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmergencyControlPanel;
