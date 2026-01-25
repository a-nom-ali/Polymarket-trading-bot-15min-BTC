"""
WebSocket Server for Real-Time Workflow Events

Broadcasts workflow execution events to connected UI clients using Socket.IO.
"""

import socketio
from aiohttp import web
from typing import Optional, Dict, Set
import time
from datetime import datetime
from src.infrastructure.factory import Infrastructure
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class WorkflowWebSocketServer:
    """
    WebSocket server that broadcasts workflow events to UI clients.

    Features:
    - Real-time event broadcasting
    - Client subscription by workflow/bot/strategy ID
    - Automatic reconnection support
    - Event replay for new clients

    Usage:
        # Create server
        infra = await Infrastructure.create("development")
        server = WorkflowWebSocketServer(infra)

        # Start server
        await server.run(host='0.0.0.0', port=8001)

        # Clients connect via Socket.IO:
        # const socket = io('http://localhost:8001')
        # socket.on('workflow_event', (event) => { ... })
    """

    def __init__(
        self,
        infra: Infrastructure,
        auth_token: Optional[str] = None,
        require_auth: bool = False
    ):
        """
        Initialize WebSocket server.

        Args:
            infra: Infrastructure instance
            auth_token: Optional authentication token for client connections
            require_auth: Whether to require authentication
        """
        self.infra = infra
        self.auth_token = auth_token
        self.require_auth = require_auth

        # Create Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',  # Allow all origins for development
            logger=False,
            engineio_logger=False
        )

        # Create aiohttp web app
        self.app = web.Application()
        self.sio.attach(self.app)

        # Track client subscriptions
        # sid -> {'workflow_ids': set(), 'bot_ids': set(), 'strategy_ids': set(), 'authenticated': bool}
        self.client_subscriptions: Dict[str, Dict[str, any]] = {}

        # Recent events buffer (for replay to new clients)
        self.recent_events: list = []
        self.max_recent_events = 100

        # Server metrics
        self.start_time = time.time()
        self.total_events_received = 0
        self.total_events_sent = 0
        self.total_connections = 0

        # Register event handlers
        self._register_handlers()
        self._register_http_routes()

        logger.info(
            "websocket_server_initialized",
            cors_allowed=True,
            auth_required=require_auth
        )

    def _register_handlers(self):
        """Register Socket.IO event handlers."""

        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection."""
            self.total_connections += 1
            logger.info("client_connected", sid=sid, total_connections=self.total_connections)

            # Initialize subscription tracking
            self.client_subscriptions[sid] = {
                'workflow_ids': set(),
                'bot_ids': set(),
                'strategy_ids': set(),
                'authenticated': not self.require_auth,  # Auto-auth if not required
                'connected_at': time.time()
            }

            # Send connection confirmation
            await self.sio.emit('connected', {
                'sid': sid,
                'message': 'Connected to workflow events',
                'auth_required': self.require_auth,
                'server_time': datetime.utcnow().isoformat()
            }, to=sid)

        @self.sio.event
        async def authenticate(sid, data):
            """
            Authenticate client connection.

            Client sends: { token: 'auth_token' }
            """
            if not self.require_auth:
                await self.sio.emit('auth_response', {
                    'success': True,
                    'message': 'Authentication not required'
                }, to=sid)
                return

            token = data.get('token')

            if token == self.auth_token:
                self.client_subscriptions[sid]['authenticated'] = True
                logger.info("client_authenticated", sid=sid)

                await self.sio.emit('auth_response', {
                    'success': True,
                    'message': 'Authentication successful'
                }, to=sid)
            else:
                logger.warning("client_auth_failed", sid=sid)

                await self.sio.emit('auth_response', {
                    'success': False,
                    'message': 'Invalid authentication token'
                }, to=sid)

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            logger.info("client_disconnected", sid=sid)

            # Clean up subscriptions
            if sid in self.client_subscriptions:
                del self.client_subscriptions[sid]

        @self.sio.event
        async def subscribe_workflow(sid, data):
            """
            Subscribe to workflow-specific events.

            Client sends: { workflow_id: 'arb_btc_001' }
            """
            # Check authentication
            if self.require_auth and not self.client_subscriptions[sid]['authenticated']:
                await self.sio.emit('error', {
                    'message': 'Authentication required'
                }, to=sid)
                return

            workflow_id = data.get('workflow_id')

            if not workflow_id:
                await self.sio.emit('error', {
                    'message': 'workflow_id required'
                }, to=sid)
                return

            # Add to subscriptions
            self.client_subscriptions[sid]['workflow_ids'].add(workflow_id)

            logger.info(
                "client_subscribed_workflow",
                sid=sid,
                workflow_id=workflow_id
            )

            # Send recent events for this workflow
            await self._send_recent_events(sid, workflow_id=workflow_id)

            # Confirm subscription
            await self.sio.emit('subscribed', {
                'type': 'workflow',
                'workflow_id': workflow_id
            }, to=sid)

        @self.sio.event
        async def subscribe_bot(sid, data):
            """
            Subscribe to bot-specific events.

            Client sends: { bot_id: 'bot_001' }
            """
            # Check authentication
            if self.require_auth and not self.client_subscriptions[sid]['authenticated']:
                await self.sio.emit('error', {
                    'message': 'Authentication required'
                }, to=sid)
                return

            bot_id = data.get('bot_id')

            if not bot_id:
                await self.sio.emit('error', {
                    'message': 'bot_id required'
                }, to=sid)
                return

            # Add to subscriptions
            self.client_subscriptions[sid]['bot_ids'].add(bot_id)

            logger.info("client_subscribed_bot", sid=sid, bot_id=bot_id)

            # Send recent events for this bot
            await self._send_recent_events(sid, bot_id=bot_id)

            # Confirm subscription
            await self.sio.emit('subscribed', {
                'type': 'bot',
                'bot_id': bot_id
            }, to=sid)

        @self.sio.event
        async def subscribe_strategy(sid, data):
            """
            Subscribe to strategy-specific events.

            Client sends: { strategy_id: 'arb_btc' }
            """
            # Check authentication
            if self.require_auth and not self.client_subscriptions[sid]['authenticated']:
                await self.sio.emit('error', {
                    'message': 'Authentication required'
                }, to=sid)
                return

            strategy_id = data.get('strategy_id')

            if not strategy_id:
                await self.sio.emit('error', {
                    'message': 'strategy_id required'
                }, to=sid)
                return

            # Add to subscriptions
            self.client_subscriptions[sid]['strategy_ids'].add(strategy_id)

            logger.info(
                "client_subscribed_strategy",
                sid=sid,
                strategy_id=strategy_id
            )

            # Send recent events for this strategy
            await self._send_recent_events(sid, strategy_id=strategy_id)

            # Confirm subscription
            await self.sio.emit('subscribed', {
                'type': 'strategy',
                'strategy_id': strategy_id
            }, to=sid)

        @self.sio.event
        async def unsubscribe(sid, data):
            """
            Unsubscribe from events.

            Client sends: { type: 'workflow', workflow_id: 'arb_btc_001' }
            """
            sub_type = data.get('type')
            sub_id = data.get(f'{sub_type}_id')

            if not sub_type or not sub_id:
                return

            # Remove from subscriptions
            subs = self.client_subscriptions.get(sid, {})
            sub_set = subs.get(f'{sub_type}_ids', set())
            sub_set.discard(sub_id)

            logger.info(
                "client_unsubscribed",
                sid=sid,
                type=sub_type,
                id=sub_id
            )

            # Confirm unsubscription
            await self.sio.emit('unsubscribed', {
                'type': sub_type,
                f'{sub_type}_id': sub_id
            }, to=sid)

    def _register_http_routes(self):
        """Register HTTP routes for health checks and metrics."""

        async def health_check(request):
            """
            Health check endpoint.

            GET /health
            """
            # Check infrastructure health
            infra_health = await self.infra.health_check()

            # Build response
            health_status = {
                'status': 'healthy' if infra_health['status'] == 'healthy' else 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'websocket': {
                    'connected_clients': len(self.client_subscriptions),
                    'total_connections': self.total_connections
                },
                'infrastructure': infra_health
            }

            status_code = 200 if health_status['status'] == 'healthy' else 503

            return web.json_response(health_status, status=status_code)

        async def metrics(request):
            """
            Metrics endpoint.

            GET /metrics
            """
            stats = self.get_stats()

            metrics_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - self.start_time,
                'connections': {
                    'current': stats['connected_clients'],
                    'total': self.total_connections
                },
                'subscriptions': {
                    'total': stats['total_subscriptions'],
                    'by_client': stats['clients']
                },
                'events': {
                    'received': self.total_events_received,
                    'sent': self.total_events_sent,
                    'recent_buffer': stats['recent_events_count']
                }
            }

            return web.json_response(metrics_data)

        async def status(request):
            """
            Simple status endpoint.

            GET /status
            """
            return web.json_response({
                'status': 'ok',
                'server': 'workflow-websocket-server',
                'timestamp': datetime.utcnow().isoformat()
            })

        # Register routes
        self.app.router.add_get('/health', health_check)
        self.app.router.add_get('/metrics', metrics)
        self.app.router.add_get('/status', status)

        logger.info("http_routes_registered", routes=['/health', '/metrics', '/status'])

    async def setup(self):
        """Set up event bus subscription."""
        # Subscribe to workflow events from infrastructure
        await self.infra.events.subscribe(
            "workflow_events",
            self.handle_workflow_event
        )

        logger.info("websocket_server_subscribed_to_events")

    async def handle_workflow_event(self, event: dict):
        """
        Handle workflow event from event bus.

        Forwards event to subscribed clients.

        Args:
            event: Workflow event
        """
        self.total_events_received += 1

        # Store in recent events buffer
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

        # Log event
        logger.debug(
            "workflow_event_received",
            event_type=event.get('type'),
            workflow_id=event.get('workflow_id'),
            node_id=event.get('node_id')
        )

        # Broadcast to subscribed clients
        await self._broadcast_event(event)

    async def _broadcast_event(self, event: dict):
        """
        Broadcast event to subscribed clients.

        Args:
            event: Event to broadcast
        """
        workflow_id = event.get('workflow_id')
        bot_id = event.get('bot_id')
        strategy_id = event.get('strategy_id')

        # Find matching clients
        for sid, subs in self.client_subscriptions.items():
            should_send = False

            # Check if client is subscribed to this workflow
            if workflow_id and workflow_id in subs['workflow_ids']:
                should_send = True

            # Check if client is subscribed to this bot
            if bot_id and bot_id in subs['bot_ids']:
                should_send = True

            # Check if client is subscribed to this strategy
            if strategy_id and strategy_id in subs['strategy_ids']:
                should_send = True

            # Send event to client
            if should_send:
                await self.sio.emit('workflow_event', event, to=sid)
                self.total_events_sent += 1

    async def _send_recent_events(
        self,
        sid: str,
        workflow_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        strategy_id: Optional[str] = None
    ):
        """
        Send recent events to newly subscribed client.

        Args:
            sid: Client session ID
            workflow_id: Optional workflow filter
            bot_id: Optional bot filter
            strategy_id: Optional strategy filter
        """
        filtered_events = []

        for event in self.recent_events:
            match = False

            if workflow_id and event.get('workflow_id') == workflow_id:
                match = True
            if bot_id and event.get('bot_id') == bot_id:
                match = True
            if strategy_id and event.get('strategy_id') == strategy_id:
                match = True

            if match:
                filtered_events.append(event)

        # Send events
        if filtered_events:
            await self.sio.emit('recent_events', {
                'events': filtered_events,
                'count': len(filtered_events)
            }, to=sid)

            logger.info(
                "recent_events_sent",
                sid=sid,
                event_count=len(filtered_events)
            )

    async def run(self, host: str = '0.0.0.0', port: int = 8001):
        """
        Start WebSocket server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        logger.info("websocket_server_starting", host=host, port=port)

        # Set up event subscription
        await self.setup()

        # Create and start app runner (works inside existing async context)
        runner = web.AppRunner(self.app)
        await runner.setup()

        try:
            site = web.TCPSite(runner, host, port)
            await site.start()
            logger.info("websocket_server_started", host=host, port=port)

            # Keep server running until interrupted
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour, will be interrupted by signals

        except asyncio.CancelledError:
            logger.info("websocket_server_cancelled")
        finally:
            await runner.cleanup()

    def get_stats(self) -> dict:
        """
        Get server statistics.

        Returns:
            Dictionary with server stats
        """
        total_subscriptions = sum(
            len(subs['workflow_ids']) +
            len(subs['bot_ids']) +
            len(subs['strategy_ids'])
            for subs in self.client_subscriptions.values()
        )

        return {
            'connected_clients': len(self.client_subscriptions),
            'total_subscriptions': total_subscriptions,
            'recent_events_count': len(self.recent_events),
            'clients': [
                {
                    'sid': sid,
                    'workflow_count': len(subs['workflow_ids']),
                    'bot_count': len(subs['bot_ids']),
                    'strategy_count': len(subs['strategy_ids'])
                }
                for sid, subs in self.client_subscriptions.items()
            ]
        }
