"""
Unified Strategy Graph Runtime

This module provides the runtime engine for executing node-based strategy graphs
across all domains (trading, GPU allocation, ad optimization, etc.).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Callable
from enum import Enum
from datetime import datetime
import asyncio
from collections import defaultdict, deque

from .asset import Asset
from .venue import Venue, ActionRequest, ActionResult
from .strategy import Opportunity, OpportunityType


class NodeCategory(Enum):
    """Categories of nodes in the strategy graph"""
    SOURCE = "source"              # Data sources (venues, APIs, feeds)
    TRANSFORM = "transform"        # Data transformation/calculation
    CONDITION = "condition"        # Decision/branching logic
    SCORER = "scorer"              # Opportunity scoring/ranking
    RISK = "risk"                  # Risk assessment/management
    OPTIMIZER = "optimizer"        # Optimization logic
    EXECUTOR = "executor"          # Action execution
    MONITOR = "monitor"            # Monitoring/alerting
    GATE = "gate"                  # Human approval gate
    CUSTOM = "custom"              # User-defined node types


class NodeStatus(Enum):
    """Execution status of a node"""
    PENDING = "pending"          # Not yet executed
    RUNNING = "running"          # Currently executing
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Execution failed
    SKIPPED = "skipped"          # Skipped due to conditions
    CANCELLED = "cancelled"      # Cancelled by user/system


@dataclass
class NodeInput:
    """Input specification for a node"""
    name: str
    data_type: str  # "number", "string", "asset", "venue", "opportunity", "any"
    required: bool = True
    default_value: Any = None


@dataclass
class NodeOutput:
    """Output specification for a node"""
    name: str
    data_type: str
    description: Optional[str] = None


@dataclass
class NodeConnection:
    """Connection between two nodes"""
    from_node_id: str
    from_output_index: int
    to_node_id: str
    to_input_index: int


@dataclass
class NodeExecutionContext:
    """Context available to a node during execution"""
    node_id: str
    graph_id: str
    execution_id: str

    # Input data from connected nodes
    inputs: Dict[str, Any] = field(default_factory=dict)

    # Shared state across all nodes in this execution
    shared_state: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    execution_started_at: datetime = field(default_factory=datetime.utcnow)
    node_started_at: Optional[datetime] = None


@dataclass
class NodeExecutionResult:
    """Result of executing a node"""
    node_id: str
    status: NodeStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Node:
    """
    Base class for all graph nodes.

    Each node represents a discrete operation in the strategy graph:
    - Data fetching (prices, metrics, signals)
    - Transformation (calculations, indicators)
    - Decision logic (if/then, compare, filter)
    - Risk checks (position size, stop loss)
    - Execution (place order, allocate budget)
    """

    def __init__(
        self,
        node_id: str,
        node_type: str,
        category: NodeCategory,
        inputs: List[NodeInput],
        outputs: List[NodeOutput],
        config: Dict[str, Any] = None
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.category = category
        self.inputs = inputs
        self.outputs = outputs
        self.config = config or {}

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """
        Execute this node with the given context.

        Override this method to implement node-specific logic.
        """
        raise NotImplementedError(f"Node {self.node_type} must implement execute()")

    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate that all required inputs are present"""
        for input_spec in self.inputs:
            if input_spec.required and input_spec.name not in inputs:
                if input_spec.default_value is None:
                    return False, f"Missing required input: {input_spec.name}"
        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to dictionary"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "category": self.category.value,
            "inputs": [{"name": i.name, "data_type": i.data_type, "required": i.required} for i in self.inputs],
            "outputs": [{"name": o.name, "data_type": o.data_type} for o in self.outputs],
            "config": self.config
        }


@dataclass
class StrategyGraph:
    """
    A complete strategy graph definition.

    The graph is a DAG (directed acyclic graph) where:
    - Nodes represent operations
    - Edges represent data flow
    - Execution follows topological order
    """

    graph_id: str
    name: str
    description: Optional[str] = None

    # Graph structure
    nodes: Dict[str, Node] = field(default_factory=dict)
    connections: List[NodeConnection] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node):
        """Add a node to the graph"""
        self.nodes[node.node_id] = node
        self.updated_at = datetime.utcnow()

    def add_connection(self, connection: NodeConnection):
        """Add a connection between nodes"""
        # Validate connection
        if connection.from_node_id not in self.nodes:
            raise ValueError(f"Source node {connection.from_node_id} not found")
        if connection.to_node_id not in self.nodes:
            raise ValueError(f"Target node {connection.to_node_id} not found")

        # Check for cycles
        if self._would_create_cycle(connection):
            raise ValueError("Connection would create a cycle")

        self.connections.append(connection)
        self.updated_at = datetime.utcnow()

    def _would_create_cycle(self, new_connection: NodeConnection) -> bool:
        """Check if adding a connection would create a cycle"""
        # Build adjacency list
        adj = defaultdict(list)
        for conn in self.connections:
            adj[conn.from_node_id].append(conn.to_node_id)

        # Add the new connection temporarily
        adj[new_connection.from_node_id].append(new_connection.to_node_id)

        # DFS to detect cycle
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in adj[node_id]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True

        return False

    def get_topological_order(self) -> List[str]:
        """
        Get nodes in topological order (dependencies first).

        Uses Kahn's algorithm.
        """
        # Build adjacency list and in-degree count
        adj = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize all nodes with in-degree 0
        for node_id in self.nodes:
            in_degree[node_id] = 0

        # Build graph
        for conn in self.connections:
            adj[conn.from_node_id].append(conn.to_node_id)
            in_degree[conn.to_node_id] += 1

        # Find all nodes with in-degree 0
        queue = deque([node_id for node_id in self.nodes if in_degree[node_id] == 0])
        order = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)

            # Reduce in-degree for neighbors
            for neighbor in adj[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.nodes):
            raise ValueError("Graph contains a cycle")

        return order

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary"""
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "connections": [
                {
                    "from": {"node_id": c.from_node_id, "output_index": c.from_output_index},
                    "to": {"node_id": c.to_node_id, "input_index": c.to_input_index}
                }
                for c in self.connections
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class GraphExecutionStatus(Enum):
    """Status of graph execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GraphExecutionResult:
    """Result of executing a strategy graph"""
    execution_id: str
    graph_id: str
    status: GraphExecutionStatus

    # Node results
    node_results: Dict[str, NodeExecutionResult] = field(default_factory=dict)

    # Final outputs (from terminal nodes)
    final_outputs: Dict[str, Any] = field(default_factory=dict)

    # Opportunities detected
    opportunities: List[Opportunity] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None

    # Error tracking
    error_message: Optional[str] = None
    failed_node_id: Optional[str] = None


class GraphRuntime:
    """
    Runtime engine for executing strategy graphs.

    This is the core execution engine that:
    1. Validates graph structure
    2. Determines execution order
    3. Executes nodes in dependency order
    4. Manages data flow between nodes
    5. Handles errors and retries
    """

    def __init__(self, graph: StrategyGraph):
        self.graph = graph
        self._execution_history: List[GraphExecutionResult] = []

    async def execute(
        self,
        initial_inputs: Optional[Dict[str, Any]] = None,
        shared_state: Optional[Dict[str, Any]] = None
    ) -> GraphExecutionResult:
        """
        Execute the strategy graph.

        Args:
            initial_inputs: Initial inputs for source nodes
            shared_state: Shared state accessible to all nodes

        Returns:
            Execution result
        """
        execution_id = f"exec_{datetime.utcnow().timestamp()}"
        result = GraphExecutionResult(
            execution_id=execution_id,
            graph_id=self.graph.graph_id,
            status=GraphExecutionStatus.RUNNING
        )

        try:
            # Get execution order
            execution_order = self.graph.get_topological_order()

            # Build data flow map
            node_outputs: Dict[str, Dict[str, Any]] = {}

            # Initialize shared state
            if shared_state is None:
                shared_state = {}

            # Execute nodes in order
            for node_id in execution_order:
                node = self.graph.nodes[node_id]

                # Prepare inputs from connected nodes
                node_inputs = self._prepare_node_inputs(node_id, node_outputs, initial_inputs or {})

                # Create execution context
                context = NodeExecutionContext(
                    node_id=node_id,
                    graph_id=self.graph.graph_id,
                    execution_id=execution_id,
                    inputs=node_inputs,
                    shared_state=shared_state,
                    node_started_at=datetime.utcnow()
                )

                # Execute node
                node_result = await node.execute(context)

                # Store result
                result.node_results[node_id] = node_result

                if node_result.status == NodeStatus.FAILED:
                    result.status = GraphExecutionStatus.FAILED
                    result.failed_node_id = node_id
                    result.error_message = node_result.error_message
                    break

                # Store outputs for downstream nodes
                node_outputs[node_id] = node_result.outputs

            # Mark as completed if not failed
            if result.status != GraphExecutionStatus.FAILED:
                result.status = GraphExecutionStatus.COMPLETED

                # Collect final outputs from terminal nodes
                terminal_nodes = self._get_terminal_nodes()
                for node_id in terminal_nodes:
                    if node_id in node_outputs:
                        result.final_outputs[node_id] = node_outputs[node_id]

        except Exception as e:
            result.status = GraphExecutionStatus.FAILED
            result.error_message = str(e)

        finally:
            result.completed_at = datetime.utcnow()
            result.execution_time_ms = (result.completed_at - result.started_at).total_seconds() * 1000
            self._execution_history.append(result)

        return result

    def _prepare_node_inputs(
        self,
        node_id: str,
        node_outputs: Dict[str, Dict[str, Any]],
        initial_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare inputs for a node from connected upstream nodes"""
        inputs = {}

        # Find all connections to this node
        for conn in self.graph.connections:
            if conn.to_node_id == node_id:
                # Get output from source node
                source_outputs = node_outputs.get(conn.from_node_id, {})
                source_node = self.graph.nodes[conn.from_node_id]

                if conn.from_output_index < len(source_node.outputs):
                    output_spec = source_node.outputs[conn.from_output_index]
                    output_name = output_spec.name

                    if output_name in source_outputs:
                        # Map to target input
                        target_node = self.graph.nodes[node_id]
                        if conn.to_input_index < len(target_node.inputs):
                            input_spec = target_node.inputs[conn.to_input_index]
                            inputs[input_spec.name] = source_outputs[output_name]

        # Add initial inputs for source nodes
        if not any(conn.to_node_id == node_id for conn in self.graph.connections):
            # This is a source node
            inputs.update(initial_inputs)

        return inputs

    def _get_terminal_nodes(self) -> List[str]:
        """Get nodes that have no outgoing connections"""
        nodes_with_outgoing = {conn.from_node_id for conn in self.graph.connections}
        return [node_id for node_id in self.graph.nodes if node_id not in nodes_with_outgoing]

    def get_execution_history(self) -> List[GraphExecutionResult]:
        """Get execution history"""
        return self._execution_history

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0
            }

        total = len(self._execution_history)
        successful = sum(1 for r in self._execution_history if r.status == GraphExecutionStatus.COMPLETED)

        return {
            "total_executions": total,
            "successful_executions": successful,
            "success_rate": successful / total,
            "avg_execution_time_ms": sum(r.execution_time_ms or 0 for r in self._execution_history) / total,
            "total_opportunities": sum(len(r.opportunities) for r in self._execution_history)
        }


# Node registry for dynamic node creation
_NODE_REGISTRY: Dict[str, type] = {}


def register_node_type(node_type: str):
    """Decorator to register a node type"""
    def decorator(cls):
        _NODE_REGISTRY[node_type] = cls
        return cls
    return decorator


def create_node(node_type: str, **kwargs) -> Node:
    """Factory function to create nodes by type"""
    if node_type not in _NODE_REGISTRY:
        raise ValueError(f"Unknown node type: {node_type}")
    return _NODE_REGISTRY[node_type](**kwargs)
