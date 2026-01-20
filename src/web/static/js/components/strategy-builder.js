// src/web/static/js/components/strategy-builder.js

/**
 * Visual Strategy Builder Component
 *
 * Drag-and-drop interface for creating trading strategies without code.
 * Supports triggers, conditions, actions, and risk management blocks.
 */

class StrategyBuilder {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = null;
        this.blocks = [];
        this.connections = [];
        this.selectedBlock = null;
        this.draggedBlock = null;
        this.offset = { x: 0, y: 0 };
        this.connectionStart = null; // For drawing connections
        this.isDraggingBlock = false;
        this.tempConnection = null; // Temporary connection while dragging

        // History system for undo/redo
        this.history = [];
        this.historyIndex = -1;
        this.maxHistorySize = 50;

        // Block types library
        this.blockLibrary = {
            triggers: [
                { id: 'price_cross', name: 'Price Cross', icon: '📈', inputs: ['price', 'threshold'], outputs: ['signal'] },
                { id: 'volume_spike', name: 'Volume Spike', icon: '📊', inputs: ['volume', 'multiplier'], outputs: ['signal'] },
                { id: 'time_trigger', name: 'Time Trigger', icon: '⏰', inputs: ['schedule'], outputs: ['signal'] },
                { id: 'rsi_signal', name: 'RSI Signal', icon: '📉', inputs: ['period', 'overbought', 'oversold'], outputs: ['signal'] }
            ],
            conditions: [
                { id: 'and', name: 'AND Gate', icon: '&', inputs: ['input1', 'input2'], outputs: ['output'] },
                { id: 'or', name: 'OR Gate', icon: '|', inputs: ['input1', 'input2'], outputs: ['output'] },
                { id: 'compare', name: 'Compare', icon: '=', inputs: ['value1', 'operator', 'value2'], outputs: ['result'] },
                { id: 'threshold', name: 'Threshold', icon: '🎚', inputs: ['value', 'min', 'max'], outputs: ['pass'] }
            ],
            actions: [
                { id: 'buy', name: 'Buy Order', icon: '💰', inputs: ['signal', 'amount'], outputs: ['order'] },
                { id: 'sell', name: 'Sell Order', icon: '💵', inputs: ['signal', 'amount'], outputs: ['order'] },
                { id: 'cancel', name: 'Cancel Orders', icon: '❌', inputs: ['signal'], outputs: ['done'] },
                { id: 'notify', name: 'Send Alert', icon: '🔔', inputs: ['signal', 'message'], outputs: ['sent'] }
            ],
            risk: [
                { id: 'stop_loss', name: 'Stop Loss', icon: '🛑', inputs: ['price', 'percentage'], outputs: ['trigger'] },
                { id: 'take_profit', name: 'Take Profit', icon: '🎯', inputs: ['price', 'percentage'], outputs: ['trigger'] },
                { id: 'position_size', name: 'Position Size', icon: '📏', inputs: ['capital', 'risk_pct'], outputs: ['size'] },
                { id: 'max_trades', name: 'Max Trades', icon: '🔢', inputs: ['limit'], outputs: ['allowed'] }
            ]
        };

        this.init();
    }

    init() {
        this.render();
        this.attachEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="strategy-builder">
                <!-- Toolbar -->
                <div class="strategy-builder__toolbar">
                    <div class="toolbar__section">
                        <button class="toolbar__btn" onclick="strategyBuilder.newStrategy()" title="New Strategy">
                            📄 New
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.loadTemplate()" title="Load Template">
                            📋 Templates
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.save()" title="Save Strategy (Ctrl+S)">
                            💾 Save
                        </button>
                    </div>
                    <div class="toolbar__section">
                        <button class="toolbar__btn" onclick="strategyBuilder.undo()" title="Undo (Ctrl+Z)">
                            ↶ Undo
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.redo()" title="Redo (Ctrl+Y)">
                            ↷ Redo
                        </button>
                    </div>
                    <div class="toolbar__section">
                        <button class="toolbar__btn" onclick="strategyBuilder.validate()" title="Validate Strategy">
                            ✓ Validate
                        </button>
                        <button class="toolbar__btn" onclick="strategyBuilder.generateCode()" title="Generate Code">
                            🔧 Generate
                        </button>
                        <button class="toolbar__btn toolbar__btn--primary" onclick="strategyBuilder.deploy()" title="Deploy Strategy">
                            🚀 Deploy
                        </button>
                    </div>
                </div>

                <!-- Main Layout -->
                <div class="strategy-builder__main">
                    <!-- Block Library Sidebar -->
                    <div class="strategy-builder__sidebar">
                        <h3>Building Blocks</h3>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>📈 Triggers</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('triggers')}
                            </div>
                        </div>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>🔀 Conditions</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('conditions')}
                            </div>
                        </div>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>⚡ Actions</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('actions')}
                            </div>
                        </div>

                        <div class="block-category">
                            <div class="block-category__header" onclick="this.parentElement.classList.toggle('collapsed')">
                                <span>🛡️ Risk Management</span>
                                <span class="block-category__toggle">▼</span>
                            </div>
                            <div class="block-category__content">
                                ${this.renderBlockLibrary('risk')}
                            </div>
                        </div>
                    </div>

                    <!-- Canvas -->
                    <div class="strategy-builder__canvas-wrapper">
                        <div class="canvas__controls">
                            <button class="canvas__btn" onclick="strategyBuilder.zoomIn()" title="Zoom In">+</button>
                            <button class="canvas__btn" onclick="strategyBuilder.zoomOut()" title="Zoom Out">−</button>
                            <button class="canvas__btn" onclick="strategyBuilder.resetZoom()" title="Reset View">⊙</button>
                            <button class="canvas__btn" onclick="strategyBuilder.clearCanvas()" title="Clear All">🗑</button>
                        </div>
                        <canvas id="strategyCanvas" class="strategy-builder__canvas"></canvas>
                        <div class="canvas__hint">
                            Drag blocks from the sidebar to start building your strategy
                        </div>
                    </div>

                    <!-- Properties Panel -->
                    <div class="strategy-builder__properties">
                        <h3>Properties</h3>
                        <div id="propertiesPanel" class="properties__content">
                            <p class="properties__empty">Select a block to edit its properties</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.canvas = document.getElementById('strategyCanvas');
        this.setupCanvas();
    }

    renderBlockLibrary(category) {
        return this.blockLibrary[category].map(block => `
            <div class="block-library__item"
                 draggable="true"
                 data-block-type="${block.id}"
                 data-category="${category}">
                <span class="block__icon">${block.icon}</span>
                <span class="block__name">${block.name}</span>
            </div>
        `).join('');
    }

    setupCanvas() {
        const wrapper = this.canvas.parentElement;
        this.canvas.width = wrapper.clientWidth;
        this.canvas.height = wrapper.clientHeight;

        this.ctx = this.canvas.getContext('2d');
        this.drawGrid();
    }

    drawGrid() {
        const ctx = this.ctx;
        const gridSize = 20;

        ctx.strokeStyle = 'rgba(100, 116, 139, 0.1)';
        ctx.lineWidth = 1;

        // Vertical lines
        for (let x = 0; x < this.canvas.width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, this.canvas.height);
            ctx.stroke();
        }

        // Horizontal lines
        for (let y = 0; y < this.canvas.height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.canvas.width, y);
            ctx.stroke();
        }
    }

    attachEventListeners() {
        // Library item drag events
        const libraryItems = this.container.querySelectorAll('.block-library__item');
        libraryItems.forEach(item => {
            item.addEventListener('dragstart', (e) => this.handleDragStart(e));
            item.addEventListener('dragend', (e) => this.handleDragEnd(e));
        });

        // Canvas drop events
        this.canvas.addEventListener('dragover', (e) => e.preventDefault());
        this.canvas.addEventListener('drop', (e) => this.handleDrop(e));

        // Canvas click events
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('contextmenu', (e) => this.handleContextMenu(e));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));

        // Window resize
        window.addEventListener('resize', () => this.setupCanvas());
    }

    handleDragStart(e) {
        const blockType = e.target.dataset.blockType;
        const category = e.target.dataset.category;

        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('blockType', blockType);
        e.dataTransfer.setData('category', category);

        e.target.classList.add('dragging');
    }

    handleDragEnd(e) {
        e.target.classList.remove('dragging');
    }

    handleDrop(e) {
        e.preventDefault();

        const blockType = e.dataTransfer.getData('blockType');
        const category = e.dataTransfer.getData('category');

        if (!blockType || !category) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        this.addBlock(blockType, category, x, y);
    }

    addBlock(blockType, category, x, y) {
        const template = this.blockLibrary[category].find(b => b.id === blockType);
        if (!template) return;

        const block = {
            id: `block_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type: blockType,
            category: category,
            name: template.name,
            icon: template.icon,
            x: x,
            y: y,
            width: 150,
            height: 80,
            inputs: template.inputs.map(name => ({ name, connected: false })),
            outputs: template.outputs.map(name => ({ name, connected: false })),
            properties: {}
        };

        this.blocks.push(block);
        this.saveState();
        this.redraw();

        showNotification(`Added ${block.name}`, 'success');
    }

    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if clicked on a port
        const portInfo = this.getPortAt(x, y);
        if (portInfo) {
            this.connectionStart = portInfo;
            this.tempConnection = { from: portInfo, to: { x, y } };
            return;
        }

        // Check if clicked on a block
        const clickedBlock = this.blocks.find(block =>
            x >= block.x && x <= block.x + block.width &&
            y >= block.y && y <= block.y + block.height
        );

        if (clickedBlock) {
            this.isDraggingBlock = true;
            this.draggedBlock = clickedBlock;
            this.offset = {
                x: x - clickedBlock.x,
                y: y - clickedBlock.y
            };
        }
    }

    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Update temporary connection
        if (this.tempConnection) {
            this.tempConnection.to = { x, y };
            this.redraw();
            return;
        }

        // Drag block
        if (this.isDraggingBlock && this.draggedBlock) {
            this.draggedBlock.x = x - this.offset.x;
            this.draggedBlock.y = y - this.offset.y;
            this.redraw();
        }
    }

    handleMouseUp(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Complete connection
        if (this.connectionStart) {
            const portInfo = this.getPortAt(x, y);
            if (portInfo && this.canConnect(this.connectionStart, portInfo)) {
                this.addConnection(this.connectionStart, portInfo);
            }
            this.connectionStart = null;
            this.tempConnection = null;
            this.redraw();
            return;
        }

        // Stop dragging and save state if block was moved
        if (this.isDraggingBlock) {
            this.saveState();
            this.isDraggingBlock = false;
            this.draggedBlock = null;
        }
    }

    handleCanvasClick(e) {
        // Only handle selection if not dragging
        if (this.isDraggingBlock || this.connectionStart) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if clicked on a block
        const clickedBlock = this.blocks.find(block =>
            x >= block.x && x <= block.x + block.width &&
            y >= block.y && y <= block.y + block.height
        );

        if (clickedBlock) {
            this.selectBlock(clickedBlock);
        } else {
            this.deselectBlock();
        }
    }

    handleContextMenu(e) {
        e.preventDefault();

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if right-clicked on a connection
        const clickedConnection = this.getConnectionAt(x, y);
        if (clickedConnection) {
            if (confirm('Delete this connection?')) {
                this.deleteConnection(clickedConnection);
            }
        }
    }

    handleKeyboard(e) {
        // Only handle keyboard shortcuts when builder is active
        if (!this.canvas || document.activeElement.tagName === 'INPUT') return;

        // Ctrl+Z or Cmd+Z - Undo
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            this.undo();
        }

        // Ctrl+Y or Cmd+Shift+Z - Redo
        if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
            e.preventDefault();
            this.redo();
        }

        // Delete or Backspace - Delete selected block
        if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedBlock) {
            e.preventDefault();
            this.deleteBlock(this.selectedBlock.id);
        }

        // Ctrl+S or Cmd+S - Save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            this.save();
        }
    }

    getPortAt(x, y) {
        const portRadius = 5;

        for (const block of this.blocks) {
            // Check output ports
            for (let i = 0; i < block.outputs.length; i++) {
                const portY = block.y + 40 + (i * 20);
                const portX = block.x + block.width;

                const dist = Math.sqrt((x - portX) ** 2 + (y - portY) ** 2);
                if (dist <= portRadius + 5) {
                    return {
                        blockId: block.id,
                        type: 'output',
                        index: i,
                        x: portX,
                        y: portY,
                        name: block.outputs[i].name
                    };
                }
            }

            // Check input ports
            for (let i = 0; i < block.inputs.length; i++) {
                const portY = block.y + 40 + (i * 20);
                const portX = block.x;

                const dist = Math.sqrt((x - portX) ** 2 + (y - portY) ** 2);
                if (dist <= portRadius + 5) {
                    return {
                        blockId: block.id,
                        type: 'input',
                        index: i,
                        x: portX,
                        y: portY,
                        name: block.inputs[i].name
                    };
                }
            }
        }

        return null;
    }

    canConnect(from, to) {
        // Can only connect output to input
        if (from.type !== 'output' || to.type !== 'input') return false;

        // Can't connect to same block
        if (from.blockId === to.blockId) return false;

        // Check if input already has a connection
        const existingConnection = this.connections.find(c =>
            c.to.blockId === to.blockId && c.to.index === to.index
        );

        if (existingConnection) return false;

        return true;
    }

    addConnection(from, to) {
        const connection = {
            from: { blockId: from.blockId, index: from.index, x: from.x, y: from.y },
            to: { blockId: to.blockId, index: to.index, x: to.x, y: to.y }
        };

        this.connections.push(connection);

        // Update port connection status
        const fromBlock = this.blocks.find(b => b.id === from.blockId);
        const toBlock = this.blocks.find(b => b.id === to.blockId);

        if (fromBlock) fromBlock.outputs[from.index].connected = true;
        if (toBlock) toBlock.inputs[to.index].connected = true;

        this.saveState();
        showNotification('Connection created', 'success');
    }

    selectBlock(block) {
        this.selectedBlock = block;
        this.redraw();
        this.showProperties(block);
    }

    deselectBlock() {
        this.selectedBlock = null;
        this.redraw();
        this.hideProperties();
    }

    showProperties(block) {
        const panel = document.getElementById('propertiesPanel');

        panel.innerHTML = `
            <div class="property-group">
                <label>Block Type</label>
                <input type="text" value="${block.name}" readonly>
            </div>
            <div class="property-group">
                <label>Block ID</label>
                <input type="text" value="${block.id}" readonly>
            </div>
            <div class="property-group">
                <label>Category</label>
                <input type="text" value="${block.category}" readonly>
            </div>
            <hr>
            <h4>Settings</h4>
            ${this.renderBlockProperties(block)}
            <button class="btn btn--danger" onclick="strategyBuilder.deleteBlock('${block.id}')" style="width: 100%; margin-top: 10px;">
                Delete Block
            </button>
        `;
    }

    renderBlockProperties(block) {
        // Generate property inputs based on block type
        const inputs = block.inputs.map((input, i) => `
            <div class="property-group">
                <label>${input.name}</label>
                <input type="text"
                       placeholder="Enter ${input.name}"
                       value="${block.properties[input.name] || ''}"
                       onchange="strategyBuilder.updateProperty('${block.id}', '${input.name}', this.value)">
            </div>
        `).join('');

        return inputs || '<p class="properties__empty">No configurable properties</p>';
    }

    updateProperty(blockId, propertyName, value) {
        const block = this.blocks.find(b => b.id === blockId);
        if (block) {
            block.properties[propertyName] = value;
        }
    }

    hideProperties() {
        const panel = document.getElementById('propertiesPanel');
        panel.innerHTML = '<p class="properties__empty">Select a block to edit its properties</p>';
    }

    deleteBlock(blockId) {
        if (!confirm('Delete this block?')) return;

        this.blocks = this.blocks.filter(b => b.id !== blockId);
        this.connections = this.connections.filter(c =>
            c.from.blockId !== blockId && c.to.blockId !== blockId
        );

        this.deselectBlock();
        this.saveState();
        this.redraw();

        showNotification('Block deleted', 'info');
    }

    redraw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw grid
        this.drawGrid();

        // Update connection positions
        this.updateConnectionPositions();

        // Draw connections
        this.connections.forEach(conn => this.drawConnection(conn));

        // Draw temporary connection
        if (this.tempConnection) {
            this.drawConnection(this.tempConnection, true);
        }

        // Draw blocks
        this.blocks.forEach(block => this.drawBlock(block));
    }

    updateConnectionPositions() {
        this.connections.forEach(conn => {
            // Update from position
            const fromBlock = this.blocks.find(b => b.id === conn.from.blockId);
            if (fromBlock) {
                conn.from.x = fromBlock.x + fromBlock.width;
                conn.from.y = fromBlock.y + 40 + (conn.from.index * 20);
            }

            // Update to position
            const toBlock = this.blocks.find(b => b.id === conn.to.blockId);
            if (toBlock) {
                conn.to.x = toBlock.x;
                conn.to.y = toBlock.y + 40 + (conn.to.index * 20);
            }
        });
    }

    drawBlock(block) {
        const ctx = this.ctx;
        const isSelected = this.selectedBlock && this.selectedBlock.id === block.id;

        // Block shadow
        if (isSelected) {
            ctx.shadowColor = 'rgba(59, 130, 246, 0.5)';
            ctx.shadowBlur = 10;
        }

        // Block background
        ctx.fillStyle = isSelected ? '#1e40af' : '#334155';
        ctx.fillRect(block.x, block.y, block.width, block.height);

        // Block border
        ctx.strokeStyle = isSelected ? '#3b82f6' : '#475569';
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.strokeRect(block.x, block.y, block.width, block.height);

        ctx.shadowBlur = 0;

        // Block header
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(block.x, block.y, block.width, 30);

        // Block icon and name
        ctx.fillStyle = '#f1f5f9';
        ctx.font = '16px sans-serif';
        ctx.fillText(block.icon, block.x + 10, block.y + 20);

        ctx.font = '12px sans-serif';
        ctx.fillStyle = '#e2e8f0';
        ctx.fillText(block.name, block.x + 35, block.y + 20);

        // Input/Output ports
        this.drawPorts(block);
    }

    drawPorts(block) {
        const ctx = this.ctx;
        const portRadius = 5;

        // Input ports (left side)
        block.inputs.forEach((input, i) => {
            const y = block.y + 40 + (i * 20);

            ctx.fillStyle = input.connected ? '#10b981' : '#64748b';
            ctx.beginPath();
            ctx.arc(block.x, y, portRadius, 0, 2 * Math.PI);
            ctx.fill();

            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px sans-serif';
            ctx.fillText(input.name, block.x + 10, y + 4);
        });

        // Output ports (right side)
        block.outputs.forEach((output, i) => {
            const y = block.y + 40 + (i * 20);

            ctx.fillStyle = output.connected ? '#10b981' : '#64748b';
            ctx.beginPath();
            ctx.arc(block.x + block.width, y, portRadius, 0, 2 * Math.PI);
            ctx.fill();

            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px sans-serif';
            const text = output.name;
            const textWidth = ctx.measureText(text).width;
            ctx.fillText(text, block.x + block.width - textWidth - 10, y + 4);
        });
    }

    drawConnection(conn, isTemp = false) {
        const ctx = this.ctx;

        ctx.strokeStyle = isTemp ? '#64748b' : '#3b82f6';
        ctx.lineWidth = isTemp ? 2 : 3;
        ctx.setLineDash(isTemp ? [5, 5] : []);
        ctx.beginPath();
        ctx.moveTo(conn.from.x, conn.from.y);

        // Bezier curve for smooth connection
        const cp1x = conn.from.x + 50;
        const cp1y = conn.from.y;
        const cp2x = conn.to.x - 50;
        const cp2y = conn.to.y;

        ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, conn.to.x, conn.to.y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    getConnectionAt(x, y) {
        const threshold = 10; // Click detection threshold

        for (const conn of this.connections) {
            // Sample points along the Bezier curve
            for (let t = 0; t <= 1; t += 0.05) {
                const cp1x = conn.from.x + 50;
                const cp1y = conn.from.y;
                const cp2x = conn.to.x - 50;
                const cp2y = conn.to.y;

                // Cubic Bezier formula
                const px = Math.pow(1 - t, 3) * conn.from.x +
                          3 * Math.pow(1 - t, 2) * t * cp1x +
                          3 * (1 - t) * Math.pow(t, 2) * cp2x +
                          Math.pow(t, 3) * conn.to.x;

                const py = Math.pow(1 - t, 3) * conn.from.y +
                          3 * Math.pow(1 - t, 2) * t * cp1y +
                          3 * (1 - t) * Math.pow(t, 2) * cp2y +
                          Math.pow(t, 3) * conn.to.y;

                const dist = Math.sqrt((x - px) ** 2 + (y - py) ** 2);
                if (dist <= threshold) {
                    return conn;
                }
            }
        }

        return null;
    }

    deleteConnection(conn) {
        this.connections = this.connections.filter(c => c !== conn);

        // Update port connection status
        const fromBlock = this.blocks.find(b => b.id === conn.from.blockId);
        const toBlock = this.blocks.find(b => b.id === conn.to.blockId);

        if (fromBlock && fromBlock.outputs[conn.from.index]) {
            fromBlock.outputs[conn.from.index].connected = false;
        }
        if (toBlock && toBlock.inputs[conn.to.index]) {
            toBlock.inputs[conn.to.index].connected = false;
        }

        this.saveState();
        this.redraw();
        showNotification('Connection deleted', 'info');
    }

    // History Management
    saveState() {
        // Deep copy current state
        const state = {
            blocks: JSON.parse(JSON.stringify(this.blocks)),
            connections: JSON.parse(JSON.stringify(this.connections))
        };

        // Remove future history if we're not at the end
        if (this.historyIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.historyIndex + 1);
        }

        // Add new state
        this.history.push(state);

        // Limit history size
        if (this.history.length > this.maxHistorySize) {
            this.history.shift();
        } else {
            this.historyIndex++;
        }
    }

    undo() {
        if (this.historyIndex <= 0) {
            showNotification('Nothing to undo', 'info');
            return;
        }

        this.historyIndex--;
        this.restoreState(this.history[this.historyIndex]);
        showNotification('Undo', 'info');
    }

    redo() {
        if (this.historyIndex >= this.history.length - 1) {
            showNotification('Nothing to redo', 'info');
            return;
        }

        this.historyIndex++;
        this.restoreState(this.history[this.historyIndex]);
        showNotification('Redo', 'info');
    }

    restoreState(state) {
        this.blocks = JSON.parse(JSON.stringify(state.blocks));
        this.connections = JSON.parse(JSON.stringify(state.connections));
        this.deselectBlock();
        this.redraw();
    }

    // Toolbar actions
    newStrategy() {
        if (this.blocks.length > 0 && !confirm('Clear current strategy?')) return;

        this.blocks = [];
        this.connections = [];
        this.history = [];
        this.historyIndex = -1;
        this.deselectBlock();
        this.redraw();

        showNotification('New strategy canvas ready', 'info');
    }

    loadTemplate() {
        this.showTemplateSelector();
    }

    showTemplateSelector() {
        const templatesHTML = Object.keys(STRATEGY_TEMPLATES).map(key => {
            const template = STRATEGY_TEMPLATES[key];
            const difficultyColor = {
                'Beginner': 'var(--success)',
                'Intermediate': 'var(--warning)',
                'Advanced': 'var(--error)'
            }[template.difficulty];

            return `
                <div class="template-card" onclick="strategyBuilder.applyTemplate('${key}')">
                    <div class="template-card__header">
                        <h4>${template.name}</h4>
                        <span class="template-badge" style="background: ${difficultyColor}">${template.difficulty}</span>
                    </div>
                    <div class="template-card__category">${template.category}</div>
                    <p class="template-card__description">${template.description}</p>
                    <div class="template-card__stats">
                        <span>📦 ${template.blocks.length} blocks</span>
                        <span>🔗 ${template.connections.length} connections</span>
                    </div>
                </div>
            `;
        }).join('');

        const modal = document.createElement('div');
        modal.className = 'template-modal';
        modal.innerHTML = `
            <div class="template-modal__content">
                <div class="template-modal__header">
                    <h3>Strategy Templates</h3>
                    <button class="modal-close" onclick="this.closest('.template-modal').remove()">×</button>
                </div>
                <div class="template-modal__body">
                    <div class="template-grid">
                        ${templatesHTML}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    applyTemplate(templateKey) {
        const template = STRATEGY_TEMPLATES[templateKey];
        if (!template) return;

        if (this.blocks.length > 0 && !confirm('This will replace your current strategy. Continue?')) {
            return;
        }

        // Clear current strategy
        this.blocks = [];
        this.connections = [];

        // Add blocks from template
        template.blocks.forEach(blockData => {
            const templateDef = this.blockLibrary[blockData.category].find(b => b.id === blockData.type);
            if (!templateDef) return;

            const block = {
                id: `block_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                type: blockData.type,
                category: blockData.category,
                name: templateDef.name,
                icon: templateDef.icon,
                x: blockData.x,
                y: blockData.y,
                width: 150,
                height: 80,
                inputs: templateDef.inputs.map(name => ({ name, connected: false })),
                outputs: templateDef.outputs.map(name => ({ name, connected: false })),
                properties: blockData.properties || {}
            };

            this.blocks.push(block);
        });

        // Add connections from template
        template.connections.forEach(connData => {
            const fromBlock = this.blocks[connData.from.blockIndex];
            const toBlock = this.blocks[connData.to.blockIndex];

            if (!fromBlock || !toBlock) return;

            const fromY = fromBlock.y + 40 + (connData.from.outputIndex * 20);
            const toY = toBlock.y + 40 + (connData.to.inputIndex * 20);

            const connection = {
                from: {
                    blockId: fromBlock.id,
                    index: connData.from.outputIndex,
                    x: fromBlock.x + fromBlock.width,
                    y: fromY
                },
                to: {
                    blockId: toBlock.id,
                    index: connData.to.inputIndex,
                    x: toBlock.x,
                    y: toY
                }
            };

            this.connections.push(connection);

            // Mark ports as connected
            fromBlock.outputs[connData.from.outputIndex].connected = true;
            toBlock.inputs[connData.to.inputIndex].connected = true;
        });

        // Close template modal
        document.querySelector('.template-modal')?.remove();

        this.saveState();
        this.redraw();
        showNotification(`Loaded template: ${template.name}`, 'success');
    }

    save() {
        const strategy = {
            blocks: this.blocks,
            connections: this.connections,
            timestamp: new Date().toISOString()
        };

        const json = JSON.stringify(strategy, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `strategy_${Date.now()}.json`;
        a.click();

        showNotification('Strategy saved!', 'success');
    }

    validate() {
        const errors = [];

        // Check for triggers
        const hasTrigger = this.blocks.some(b => b.category === 'triggers');
        if (!hasTrigger) {
            errors.push('Strategy must have at least one trigger');
        }

        // Check for actions
        const hasAction = this.blocks.some(b => b.category === 'actions');
        if (!hasAction) {
            errors.push('Strategy must have at least one action');
        }

        // Check for disconnected blocks
        const disconnectedBlocks = this.blocks.filter(b =>
            b.outputs.every(o => !o.connected)
        );
        if (disconnectedBlocks.length > 0 && this.blocks.length > 1) {
            errors.push(`${disconnectedBlocks.length} block(s) are not connected`);
        }

        if (errors.length > 0) {
            showNotification(`Validation failed:\n${errors.join('\n')}`, 'error');
        } else {
            showNotification('✓ Strategy is valid!', 'success');
        }

        return errors.length === 0;
    }

    generateCode() {
        if (!this.validate()) return;

        showNotification('Code generation coming soon!', 'info');
        // TODO: Generate Python strategy code from blocks
    }

    deploy() {
        if (!this.validate()) return;

        if (!confirm('Deploy this strategy to production?')) return;

        showNotification('Strategy deployment coming soon!', 'info');
        // TODO: Deploy strategy to bot
    }

    // Canvas controls
    zoomIn() {
        showNotification('Zoom coming soon!', 'info');
    }

    zoomOut() {
        showNotification('Zoom coming soon!', 'info');
    }

    resetZoom() {
        this.redraw();
    }

    clearCanvas() {
        this.newStrategy();
    }
}

// Global instance will be created when modal opens
let strategyBuilder = null;
