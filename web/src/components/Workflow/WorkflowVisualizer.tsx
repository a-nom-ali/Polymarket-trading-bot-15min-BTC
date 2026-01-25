/**
 * WorkflowVisualizer Component
 *
 * Real-time workflow execution visualization using ReactFlow.
 * Shows workflow nodes and their execution status.
 */

import React, { useMemo } from 'react';
import {
  ReactFlow,
  type Node,
  type Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';

interface WorkflowVisualizerProps {
  workflowId?: string;
  botId?: string;
  strategyId?: string;
}

interface WorkflowNodeData extends Record<string, unknown> {
  label: string;
  status?: string;
  category?: string;
  duration_ms?: number;
}

// Custom node component with status indicator
const WorkflowNode: React.FC<NodeProps<WorkflowNodeData>> = ({ data }) => {
  const getStatusColor = () => {
    switch (data.status) {
      case 'running':
        return 'border-blue-500 bg-blue-900';
      case 'completed':
        return 'border-green-500 bg-green-900';
      case 'failed':
        return 'border-red-500 bg-red-900';
      case 'pending':
      default:
        return 'border-gray-500 bg-gray-800';
    }
  };

  const getStatusIcon = () => {
    switch (data.status) {
      case 'running':
        return '⚡';
      case 'completed':
        return '✓';
      case 'failed':
        return '✗';
      default:
        return '○';
    }
  };

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 ${getStatusColor()} transition-all duration-300 min-w-[150px]`}
    >
      <div className="flex items-center justify-between">
        <span className="text-white font-medium text-sm">{data.label}</span>
        <span className="text-lg ml-2">{getStatusIcon()}</span>
      </div>
      {data.category && (
        <div className="text-xs text-gray-400 mt-1">{data.category}</div>
      )}
      {data.duration_ms && (
        <div className="text-xs text-gray-400 mt-1">
          {data.duration_ms.toFixed(1)}ms
        </div>
      )}
    </div>
  );
};

const nodeTypes = {
  workflowNode: WorkflowNode,
};

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({
  workflowId,
  botId,
  strategyId,
}) => {
  const { events } = useWorkflowEvents({
    workflowId,
    botId,
    strategyId,
    maxEvents: 200,
  });

  // Initialize with empty nodes/edges
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<WorkflowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Build workflow graph from events
  React.useEffect(() => {
    if (events.length === 0) return;

    // Find the latest execution_started event
    const startedEvent = events.find((e) => e.type === 'execution_started');
    if (!startedEvent) return;

    // Track node statuses from events
    const nodeStatuses = new Map<string, any>();

    events.forEach((event) => {
      const nodeId = event.node_id;
      if (!nodeId) return;

      if (event.type === 'node_started') {
        nodeStatuses.set(nodeId, {
          status: 'running',
          name: event.node_name,
          category: event.node_category,
        });
      } else if (event.type === 'node_completed') {
        nodeStatuses.set(nodeId, {
          status: 'completed',
          name: event.node_name,
          category: event.node_category,
          duration_ms: event.duration_ms,
        });
      } else if (event.type === 'node_failed') {
        nodeStatuses.set(nodeId, {
          status: 'failed',
          name: event.node_name,
          category: event.node_category,
          error: event.error,
        });
      }
    });

    // Create nodes from statuses
    const newNodes: Node<WorkflowNodeData>[] = [];
    let yOffset = 0;

    nodeStatuses.forEach((data, nodeId) => {
      newNodes.push({
        id: nodeId,
        type: 'workflowNode',
        position: { x: 250, y: yOffset },
        data: {
          label: data.name || nodeId,
          status: data.status || 'pending',
          category: data.category,
          duration_ms: data.duration_ms,
        },
      });
      yOffset += 100;
    });

    setNodes(newNodes);

    // Create simple sequential edges
    const newEdges: Edge[] = [];
    for (let i = 0; i < newNodes.length - 1; i++) {
      newEdges.push({
        id: `e${i}`,
        source: newNodes[i].id,
        target: newNodes[i + 1].id,
        animated: true,
        style: { stroke: '#4B5563' },
      });
    }

    setEdges(newEdges);
  }, [events, setNodes, setEdges]);

  // Get current execution status
  const executionStatus = useMemo(() => {
    const latestEvent = events[0];
    if (!latestEvent) return 'No active execution';

    switch (latestEvent.type) {
      case 'execution_started':
        return 'Execution in progress...';
      case 'execution_completed':
        return 'Execution completed successfully';
      case 'execution_failed':
        return `Execution failed: ${latestEvent.error || 'Unknown error'}`;
      case 'execution_halted':
        return 'Execution halted (emergency)';
      default:
        return 'Execution in progress...';
    }
  }, [events]);

  return (
    <div className="flex flex-col h-full">
      {/* Status Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-400">Execution Status</p>
            <p className="text-white font-medium">{executionStatus}</p>
          </div>
          {workflowId && (
            <div className="text-right">
              <p className="text-xs text-gray-400">Workflow ID</p>
              <p className="text-sm text-white font-mono">{workflowId}</p>
            </div>
          )}
        </div>
      </div>

      {/* ReactFlow Canvas */}
      <div className="flex-1 bg-gray-900">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-900"
          >
            <Background color="#374151" gap={16} />
            <Controls className="bg-gray-800 border border-gray-700" />
            <MiniMap
              className="bg-gray-800 border border-gray-700"
              nodeColor={(node) => {
                switch (node.data.status) {
                  case 'running':
                    return '#3B82F6';
                  case 'completed':
                    return '#10B981';
                  case 'failed':
                    return '#EF4444';
                  default:
                    return '#6B7280';
                }
              }}
            />
          </ReactFlow>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-gray-400 text-lg">No workflow execution data</p>
              <p className="text-gray-500 text-sm mt-2">
                Start a workflow to see real-time visualization
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowVisualizer;
