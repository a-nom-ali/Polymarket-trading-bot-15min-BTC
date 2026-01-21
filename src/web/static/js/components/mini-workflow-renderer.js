// src/web/static/js/components/mini-workflow-renderer.js

/**
 * MiniWorkflowRenderer
 *
 * Renders a compact, read-only visualization of a workflow on a small canvas.
 * Used for workflow previews on bot cards in the dashboard.
 *
 * Features:
 * - Automatic layout and scaling
 * - Simplified block rendering
 * - Connection visualization
 * - Provider icons
 * - Fits any workflow in fixed canvas size
 */
class MiniWorkflowRenderer {
    constructor(canvasId, workflow, options = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas not found: ${canvasId}`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.workflow = workflow;

        // Options
        this.options = {
            width: options.width || 300,
            height: options.height || 150,
            padding: options.padding || 10,
            blockWidth: options.blockWidth || 40,
            blockHeight: options.blockHeight || 30,
            fontSize: options.fontSize || 10,
            showIcons: options.showIcons !== false,
            showConnections: options.showConnections !== false,
            backgroundColor: options.backgroundColor || '#0f172a',
            blockColor: options.blockColor || '#334155',
            providerColor: options.providerColor || '#1e3a8a',
            connectionColor: options.connectionColor || '#475569',
            textColor: options.textColor || '#e2e8f0'
        };

        // Set canvas size
        this.canvas.width = this.options.width;
        this.canvas.height = this.options.height;

        // Calculate layout
        this.layout = this.calculateLayout();

        this.render();
    }

    calculateLayout() {
        if (!this.workflow || !this.workflow.blocks || this.workflow.blocks.length === 0) {
            return { blocks: [], scale: 1 };
        }

        const blocks = this.workflow.blocks;
        const { width, height, padding, blockWidth, blockHeight } = this.options;

        // Find bounding box of all blocks
        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        blocks.forEach(block => {
            minX = Math.min(minX, block.x);
            minY = Math.min(minY, block.y);
            maxX = Math.max(maxX, block.x + (block.width || 150));
            maxY = Math.max(maxY, block.y + (block.height || 80));
        });

        const workflowWidth = maxX - minX;
        const workflowHeight = maxY - minY;

        // Calculate scale to fit canvas
        const scaleX = (width - padding * 2) / workflowWidth;
        const scaleY = (height - padding * 2) / workflowHeight;
        const scale = Math.min(scaleX, scaleY, 1); // Don't scale up, only down

        // Transform block positions
        const layoutBlocks = blocks.map(block => ({
            ...block,
            renderX: padding + (block.x - minX) * scale,
            renderY: padding + (block.y - minY) * scale,
            renderWidth: blockWidth,
            renderHeight: blockHeight
        }));

        return { blocks: layoutBlocks, scale, offsetX: minX, offsetY: minY };
    }

    render() {
        if (!this.ctx) return;

        // Clear canvas
        this.ctx.fillStyle = this.options.backgroundColor;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        if (!this.workflow || !this.workflow.blocks || this.workflow.blocks.length === 0) {
            this.renderEmpty();
            return;
        }

        // Draw connections first (behind blocks)
        if (this.options.showConnections && this.workflow.connections) {
            this.renderConnections();
        }

        // Draw blocks
        this.layout.blocks.forEach(block => {
            this.renderBlock(block);
        });
    }

    renderEmpty() {
        this.ctx.fillStyle = this.options.textColor;
        this.ctx.font = `${this.options.fontSize}px sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(
            'No workflow',
            this.canvas.width / 2,
            this.canvas.height / 2
        );
    }

    renderBlock(block) {
        const { ctx } = this;
        const { blockColor, providerColor, textColor, fontSize, showIcons } = this.options;
        const { renderX, renderY, renderWidth, renderHeight } = block;

        // Determine block color based on category
        const isProvider = block.category === 'providers';
        ctx.fillStyle = isProvider ? providerColor : blockColor;

        // Draw block rectangle
        ctx.fillRect(renderX, renderY, renderWidth, renderHeight);

        // Draw block border
        ctx.strokeStyle = isProvider ? '#60a5fa' : '#475569';
        ctx.lineWidth = 1;
        ctx.strokeRect(renderX, renderY, renderWidth, renderHeight);

        // Draw icon if enabled and available
        if (showIcons && block.icon) {
            ctx.font = `${fontSize + 2}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = textColor;
            ctx.fillText(
                block.icon,
                renderX + renderWidth / 2,
                renderY + renderHeight / 2
            );
        }
    }

    renderConnections() {
        if (!this.workflow.connections) return;

        const { ctx } = this;
        const { connectionColor } = this.options;

        this.workflow.connections.forEach(conn => {
            const fromBlock = this.layout.blocks.find(b => b.id === conn.from.blockId);
            const toBlock = this.layout.blocks.find(b => b.id === conn.to.blockId);

            if (!fromBlock || !toBlock) return;

            // Calculate connection points
            const fromX = fromBlock.renderX + fromBlock.renderWidth;
            const fromY = fromBlock.renderY + fromBlock.renderHeight / 2;
            const toX = toBlock.renderX;
            const toY = toBlock.renderY + toBlock.renderHeight / 2;

            // Draw connection line
            ctx.strokeStyle = connectionColor;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(fromX, fromY);

            // Use cubic bezier for smooth curves
            const midX = (fromX + toX) / 2;
            ctx.bezierCurveTo(midX, fromY, midX, toY, toX, toY);
            ctx.stroke();

            // Draw arrow
            this.drawArrow(ctx, toX, toY, Math.atan2(toY - fromY, toX - fromX));
        });
    }

    drawArrow(ctx, x, y, angle) {
        const arrowSize = 4;

        ctx.fillStyle = this.options.connectionColor;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(
            x - arrowSize * Math.cos(angle - Math.PI / 6),
            y - arrowSize * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
            x - arrowSize * Math.cos(angle + Math.PI / 6),
            y - arrowSize * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();
    }

    // Update workflow and re-render
    updateWorkflow(workflow) {
        this.workflow = workflow;
        this.layout = this.calculateLayout();
        this.render();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MiniWorkflowRenderer;
}
