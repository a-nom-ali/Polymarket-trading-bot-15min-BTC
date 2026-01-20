// src/web/static/js/components/workflow-executor.js

/**
 * Workflow Execution Engine
 *
 * n8n-inspired execution system that runs visual trading strategies.
 * Handles node execution, data flow, conditional branching, and error handling.
 */

class WorkflowExecutor {
    constructor() {
        this.isRunning = false;
        this.executionQueue = [];
        this.executionHistory = [];
        this.nodeOutputs = new Map(); // Store outputs from each node
        this.variables = new Map(); // Workflow-scoped variables
        this.maxExecutionTime = 30000; // 30 seconds max per workflow
        this.debugMode = false;
    }

    /**
     * Execute a complete workflow
     * @param {Object} workflow - { blocks, connections }
     * @param {Object} triggerData - Initial data from trigger
     */
    async execute(workflow, triggerData = {}) {
        if (this.isRunning) {
            throw new Error('Workflow is already running');
        }

        this.isRunning = true;
        this.nodeOutputs.clear();
        this.variables.clear();

        const execution = {
            id: `exec_${Date.now()}`,
            startTime: Date.now(),
            status: 'running',
            triggerData: triggerData,
            results: [],
            errors: []
        };

        try {
            // Find trigger nodes
            const triggerNodes = workflow.blocks.filter(b => b.category === 'triggers');

            if (triggerNodes.length === 0) {
                throw new Error('No trigger nodes found in workflow');
            }

            // Execute from each trigger
            for (const trigger of triggerNodes) {
                await this.executeNode(trigger, triggerData, workflow, execution);
            }

            execution.status = 'completed';
            execution.endTime = Date.now();
            execution.duration = execution.endTime - execution.startTime;

            this.log('success', `Workflow completed in ${execution.duration}ms`);

        } catch (error) {
            execution.status = 'error';
            execution.error = error.message;
            execution.endTime = Date.now();
            execution.duration = execution.endTime - execution.startTime;

            this.log('error', `Workflow failed: ${error.message}`);
        } finally {
            this.isRunning = false;
            this.executionHistory.push(execution);

            // Keep only last 50 executions
            if (this.executionHistory.length > 50) {
                this.executionHistory.shift();
            }
        }

        return execution;
    }

    /**
     * Execute a single node and its downstream nodes
     */
    async executeNode(node, inputData, workflow, execution) {
        const startTime = Date.now();

        try {
            this.log('info', `Executing node: ${node.name} (${node.type})`);

            // Visual feedback: highlight active node
            if (workflow.visualizer) {
                workflow.visualizer.activeNodes.add(node.id);
                workflow.visualizer.redraw();

                // Small delay for visual effect
                await new Promise(resolve => setTimeout(resolve, 200));
            }

            // Get node executor
            const executor = this.getNodeExecutor(node.type, node.category);

            // Execute node with input data
            const output = await executor(node, inputData, this);

            // Store output
            this.nodeOutputs.set(node.id, output);

            // Record execution
            execution.results.push({
                nodeId: node.id,
                nodeName: node.name,
                nodeType: node.type,
                input: inputData,
                output: output,
                duration: Date.now() - startTime,
                timestamp: Date.now()
            });

            // Visual feedback: animate data flow
            if (workflow.visualizer) {
                const connections = workflow.connections.filter(c => c.from.blockId === node.id);
                for (const conn of connections) {
                    workflow.visualizer.addDataFlowParticle(conn, '#10b981');
                }
            }

            // Find and execute connected nodes
            // For branching nodes (if/switch), only execute the appropriate branch
            if (node.type === 'if') {
                const branch = output.branch; // 'true' or 'false'
                const branchNodes = this.getBranchNodes(node, branch, workflow);

                for (const branchNode of branchNodes) {
                    const branchData = branch === 'true' ? output.trueOutput : output.falseOutput;
                    await this.executeNode(branchNode, branchData || output, workflow, execution);
                }
            } else if (node.type === 'switch') {
                const branch = output.branch; // 'case1', 'case2', 'case3', 'default'
                const branchNodes = this.getBranchNodes(node, branch, workflow);

                for (const branchNode of branchNodes) {
                    await this.executeNode(branchNode, output.output, workflow, execution);
                }
            } else {
                // Normal execution - all connected nodes
                const connectedNodes = this.getConnectedNodes(node, workflow);

                for (const connectedNode of connectedNodes) {
                    await this.executeNode(connectedNode, output, workflow, execution);
                }
            }

            // Visual feedback: remove active highlight
            if (workflow.visualizer) {
                workflow.visualizer.activeNodes.delete(node.id);
                workflow.visualizer.redraw();
            }

        } catch (error) {
            this.log('error', `Node execution failed: ${node.name} - ${error.message}`);

            execution.errors.push({
                nodeId: node.id,
                nodeName: node.name,
                error: error.message,
                timestamp: Date.now()
            });

            throw error; // Propagate error to stop workflow
        }
    }

    /**
     * Get nodes connected to this node's outputs
     */
    getConnectedNodes(node, workflow) {
        const connectedNodes = [];

        for (const connection of workflow.connections) {
            if (connection.from.blockId === node.id) {
                const targetNode = workflow.blocks.find(b => b.id === connection.to.blockId);
                if (targetNode) {
                    connectedNodes.push(targetNode);
                }
            }
        }

        return connectedNodes;
    }

    /**
     * Get nodes connected to a specific branch output
     */
    getBranchNodes(node, branchName, workflow) {
        const branchNodes = [];

        // Map branch names to output indices
        const outputMap = {
            'true': 0,
            'false': 1,
            'case1': 0,
            'case2': 1,
            'case3': 2,
            'default': 3
        };

        const outputIndex = outputMap[branchName];

        if (outputIndex === undefined) {
            return branchNodes;
        }

        for (const connection of workflow.connections) {
            if (connection.from.blockId === node.id && connection.from.index === outputIndex) {
                const targetNode = workflow.blocks.find(b => b.id === connection.to.blockId);
                if (targetNode) {
                    branchNodes.push(targetNode);
                }
            }
        }

        return branchNodes;
    }

    /**
     * Get executor function for a node type
     */
    getNodeExecutor(type, category) {
        // Trigger executors
        if (category === 'triggers') {
            switch (type) {
                case 'price_cross':
                    return this.executePriceCross.bind(this);
                case 'volume_spike':
                    return this.executeVolumeSpike.bind(this);
                case 'time_trigger':
                    return this.executeTimeTrigger.bind(this);
                case 'rsi_signal':
                    return this.executeRSISignal.bind(this);
                case 'webhook':
                    return this.executeWebhook.bind(this);
                case 'event_listener':
                    return this.executeEventListener.bind(this);
                case 'manual_trigger':
                    return this.executeManualTrigger.bind(this);
                default:
                    throw new Error(`Unknown trigger type: ${type}`);
            }
        }

        // Condition executors
        if (category === 'conditions') {
            switch (type) {
                case 'and':
                    return this.executeAND.bind(this);
                case 'or':
                    return this.executeOR.bind(this);
                case 'compare':
                    return this.executeCompare.bind(this);
                case 'threshold':
                    return this.executeThreshold.bind(this);
                case 'if':
                    return this.executeIf.bind(this);
                case 'switch':
                    return this.executeSwitch.bind(this);
                default:
                    throw new Error(`Unknown condition type: ${type}`);
            }
        }

        // Action executors
        if (category === 'actions') {
            switch (type) {
                case 'buy':
                    return this.executeBuy.bind(this);
                case 'sell':
                    return this.executeSell.bind(this);
                case 'cancel':
                    return this.executeCancel.bind(this);
                case 'notify':
                    return this.executeNotify.bind(this);
                default:
                    throw new Error(`Unknown action type: ${type}`);
            }
        }

        // Risk management executors
        if (category === 'risk') {
            switch (type) {
                case 'stop_loss':
                    return this.executeStopLoss.bind(this);
                case 'take_profit':
                    return this.executeTakeProfit.bind(this);
                case 'position_size':
                    return this.executePositionSize.bind(this);
                case 'max_trades':
                    return this.executeMaxTrades.bind(this);
                default:
                    throw new Error(`Unknown risk type: ${type}`);
            }
        }

        throw new Error(`Unknown node category: ${category}`);
    }

    // ============================================================================
    // TRIGGER EXECUTORS
    // ============================================================================

    async executePriceCross(node, input) {
        const threshold = parseFloat(node.properties.threshold || 0);
        const currentPrice = input.price || 0;
        const previousPrice = input.previousPrice || currentPrice;

        const priceChange = ((currentPrice - previousPrice) / previousPrice) * 100;
        const crossed = Math.abs(priceChange) >= threshold;

        return {
            triggered: crossed,
            price: currentPrice,
            previousPrice: previousPrice,
            change: priceChange,
            threshold: threshold,
            direction: priceChange > 0 ? 'up' : 'down'
        };
    }

    async executeVolumeSpike(node, input) {
        const multiplier = parseFloat(node.properties.multiplier || 1.5);
        const currentVolume = input.volume || 0;
        const avgVolume = input.avgVolume || currentVolume;

        const spiked = currentVolume >= (avgVolume * multiplier);

        return {
            triggered: spiked,
            volume: currentVolume,
            avgVolume: avgVolume,
            multiplier: multiplier,
            ratio: currentVolume / avgVolume
        };
    }

    async executeTimeTrigger(node, input) {
        const schedule = node.properties.schedule || '';
        const currentTime = new Date();
        const currentHM = `${currentTime.getHours()}:${currentTime.getMinutes().toString().padStart(2, '0')}`;

        const scheduledTimes = schedule.split(',').map(t => t.trim());
        const triggered = scheduledTimes.includes(currentHM);

        return {
            triggered: triggered,
            currentTime: currentTime.toISOString(),
            schedule: scheduledTimes,
            matched: currentHM
        };
    }

    async executeRSISignal(node, input) {
        const period = parseInt(node.properties.period || 14);
        const overbought = parseFloat(node.properties.overbought || 70);
        const oversold = parseFloat(node.properties.oversold || 30);
        const rsi = input.rsi || 50; // RSI would come from market data

        const signal = rsi >= overbought ? 'sell' : rsi <= oversold ? 'buy' : 'hold';

        return {
            triggered: signal !== 'hold',
            rsi: rsi,
            signal: signal,
            period: period,
            overbought: overbought,
            oversold: oversold
        };
    }

    async executeWebhook(node, input) {
        const url = node.properties.url || '';

        this.log('info', `WEBHOOK: Listening on ${url}`);

        // In real implementation, register webhook endpoint
        // For demo, return trigger data as webhook payload
        return {
            triggered: true,
            webhookUrl: url,
            payload: input,
            timestamp: Date.now(),
            method: 'POST'
        };
    }

    async executeEventListener(node, input) {
        const eventType = node.properties.event_type || 'price_update';

        this.log('info', `EVENT LISTENER: Waiting for '${eventType}' events`);

        // In real implementation, subscribe to event bus
        return {
            triggered: true,
            eventType: eventType,
            eventData: input,
            timestamp: Date.now()
        };
    }

    async executeManualTrigger(node, input) {
        this.log('success', 'MANUAL TRIGGER: Workflow started manually');

        return {
            triggered: true,
            manual: true,
            data: input,
            timestamp: Date.now(),
            initiator: 'user'
        };
    }

    // ============================================================================
    // CONDITION EXECUTORS
    // ============================================================================

    async executeAND(node, input) {
        // Check if all inputs are truthy
        const result = input.input1 && input.input2;

        return {
            passed: result,
            input1: input.input1,
            input2: input.input2
        };
    }

    async executeOR(node, input) {
        // Check if any input is truthy
        const result = input.input1 || input.input2;

        return {
            passed: result,
            input1: input.input1,
            input2: input.input2
        };
    }

    async executeCompare(node, input) {
        const value1 = input.value1 || 0;
        const value2 = input.value2 || 0;
        const operator = node.properties.operator || '==';

        let result = false;
        switch (operator) {
            case '==': result = value1 == value2; break;
            case '!=': result = value1 != value2; break;
            case '>': result = value1 > value2; break;
            case '<': result = value1 < value2; break;
            case '>=': result = value1 >= value2; break;
            case '<=': result = value1 <= value2; break;
        }

        return {
            passed: result,
            value1: value1,
            value2: value2,
            operator: operator
        };
    }

    async executeThreshold(node, input) {
        const value = input.value || 0;
        const min = parseFloat(node.properties.min || -Infinity);
        const max = parseFloat(node.properties.max || Infinity);

        const passed = value >= min && value <= max;

        return {
            passed: passed,
            value: value,
            min: min,
            max: max
        };
    }

    async executeIf(node, input) {
        // Evaluate condition from input
        const condition = input.condition || input.triggered || input.passed || false;

        this.log('info', `IF: Condition evaluated to ${condition}`);

        return {
            branch: condition ? 'true' : 'false',
            condition: condition,
            trueOutput: condition ? input : null,
            falseOutput: condition ? null : input
        };
    }

    async executeSwitch(node, input) {
        const value = input.value || input.signal || '';
        const case1 = node.properties.case1 || '';
        const case2 = node.properties.case2 || '';
        const case3 = node.properties.case3 || '';

        let branch = 'default';
        if (value === case1) branch = 'case1';
        else if (value === case2) branch = 'case2';
        else if (value === case3) branch = 'case3';

        this.log('info', `SWITCH: Value '${value}' matched '${branch}'`);

        return {
            branch: branch,
            value: value,
            matched: branch !== 'default',
            output: input
        };
    }

    // ============================================================================
    // ACTION EXECUTORS
    // ============================================================================

    async executeBuy(node, input) {
        const amount = parseFloat(node.properties.amount || 0);

        this.log('success', `BUY ORDER: ${amount} units`);

        // In real implementation, this would call the trading API
        return {
            action: 'buy',
            amount: amount,
            executed: true,
            timestamp: Date.now(),
            price: input.price || 0,
            orderId: `order_${Date.now()}`
        };
    }

    async executeSell(node, input) {
        const amount = parseFloat(node.properties.amount || 0);

        this.log('warning', `SELL ORDER: ${amount} units`);

        return {
            action: 'sell',
            amount: amount,
            executed: true,
            timestamp: Date.now(),
            price: input.price || 0,
            orderId: `order_${Date.now()}`
        };
    }

    async executeCancel(node, input) {
        this.log('info', 'CANCEL: All open orders');

        return {
            action: 'cancel',
            executed: true,
            timestamp: Date.now(),
            cancelledOrders: []
        };
    }

    async executeNotify(node, input) {
        const message = node.properties.message || 'Alert!';

        this.log('info', `NOTIFICATION: ${message}`);

        // In real implementation, send to notification service
        if (typeof showNotification === 'function') {
            showNotification(message, 'info');
        }

        return {
            action: 'notify',
            message: message,
            sent: true,
            timestamp: Date.now()
        };
    }

    // ============================================================================
    // RISK MANAGEMENT EXECUTORS
    // ============================================================================

    async executeStopLoss(node, input) {
        const percentage = parseFloat(node.properties.percentage || 2);
        const entryPrice = input.price || 0;
        const stopPrice = entryPrice * (1 - percentage / 100);

        this.log('info', `STOP LOSS: Set at ${stopPrice.toFixed(2)} (${percentage}% below ${entryPrice})`);

        return {
            type: 'stop_loss',
            percentage: percentage,
            entryPrice: entryPrice,
            stopPrice: stopPrice,
            active: true
        };
    }

    async executeTakeProfit(node, input) {
        const percentage = parseFloat(node.properties.percentage || 5);
        const entryPrice = input.price || 0;
        const targetPrice = entryPrice * (1 + percentage / 100);

        this.log('success', `TAKE PROFIT: Set at ${targetPrice.toFixed(2)} (${percentage}% above ${entryPrice})`);

        return {
            type: 'take_profit',
            percentage: percentage,
            entryPrice: entryPrice,
            targetPrice: targetPrice,
            active: true
        };
    }

    async executePositionSize(node, input) {
        const capital = parseFloat(node.properties.capital || 1000);
        const riskPct = parseFloat(node.properties.risk_pct || 2);
        const positionSize = (capital * riskPct) / 100;

        this.log('info', `POSITION SIZE: $${positionSize.toFixed(2)} (${riskPct}% of $${capital})`);

        return {
            type: 'position_size',
            capital: capital,
            riskPercentage: riskPct,
            positionSize: positionSize,
            maxLoss: positionSize
        };
    }

    async executeMaxTrades(node, input) {
        const limit = parseInt(node.properties.limit || 3);
        const currentTrades = this.variables.get('tradeCount') || 0;
        const allowed = currentTrades < limit;

        if (allowed) {
            this.variables.set('tradeCount', currentTrades + 1);
        }

        this.log('info', `MAX TRADES: ${currentTrades}/${limit} trades used`);

        return {
            type: 'max_trades',
            limit: limit,
            currentTrades: currentTrades,
            allowed: allowed,
            remaining: limit - currentTrades
        };
    }

    // ============================================================================
    // UTILITY METHODS
    // ============================================================================

    log(level, message) {
        if (this.debugMode) {
            console.log(`[WorkflowExecutor ${level.toUpperCase()}]`, message);
        }

        // Send to event feed if available
        if (typeof eventFeed !== 'undefined' && eventFeed) {
            eventFeed.addEvent(level, message);
        }
    }

    stop() {
        this.isRunning = false;
        this.log('warning', 'Workflow execution stopped');
    }

    getExecutionHistory() {
        return this.executionHistory;
    }

    clearHistory() {
        this.executionHistory = [];
    }

    setDebugMode(enabled) {
        this.debugMode = enabled;
    }
}

// Global instance
const workflowExecutor = new WorkflowExecutor();
