#!/usr/bin/env python3
"""
🎭 Parody Critics - WebSocket Manager
Real-time progress updates via WebSocket for media import operations
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from .logger import get_logger

logger = get_logger('websocket_manager')


class MessageType(str, Enum):
    """WebSocket message types"""
    IMPORT_STARTED = "import_started"
    IMPORT_PROGRESS = "import_progress"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_ERROR = "import_error"
    IMPORT_CANCELLED = "import_cancelled"
    PING = "ping"
    PONG = "pong"


@dataclass
class ImportProgress:
    """Progress data structure for media import"""
    session_id: str
    operation: str
    total_items: int = 0
    processed_items: int = 0
    new_items: int = 0
    updated_items: int = 0
    unchanged_items: int = 0
    errors: int = 0
    current_page: int = 0
    total_pages: int = 0
    current_item: str = ""
    items_per_second: float = 0.0
    percentage: float = 0.0
    estimated_completion: Optional[str] = None
    start_time: Optional[str] = None
    status: str = "running"  # running, completed, error, cancelled
    error_messages: List[str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

        # Calculate percentage
        if self.total_items > 0:
            self.percentage = (self.processed_items / self.total_items) * 100


class WebSocketConnection:
    """Individual WebSocket connection handler"""

    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected = False
        self.subscriptions: Set[str] = set()  # Session IDs this client is subscribed to

    async def connect(self):
        """Accept WebSocket connection"""
        await self.websocket.accept()
        self.connected = True
        logger.info(f"WebSocket client {self.client_id} connected")

    async def disconnect(self):
        """Disconnect WebSocket"""
        if self.connected:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket {self.client_id}: {e}")

        self.connected = False
        logger.info(f"WebSocket client {self.client_id} disconnected")

    async def send_message(self, message_type: MessageType, data: Dict[str, Any]):
        """Send message to WebSocket client"""
        if not self.connected:
            return False

        try:
            message = {
                "type": message_type.value,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }

            await self.websocket.send_text(json.dumps(message))
            return True

        except WebSocketDisconnect:
            logger.info(f"WebSocket {self.client_id} disconnected during send")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Error sending message to {self.client_id}: {e}")
            self.connected = False
            return False

    async def send_ping(self):
        """Send ping to check connection"""
        return await self.send_message(MessageType.PING, {"client_id": self.client_id})


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts progress updates

    Features:
    - Multiple client connections
    - Session-based subscriptions
    - Automatic connection cleanup
    - Real-time progress broadcasting
    - Ping/pong heartbeat
    """

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.import_sessions: Dict[str, ImportProgress] = {}
        self.active_imports: Set[str] = set()
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect_client(self, websocket: WebSocket) -> str:
        """Connect new WebSocket client"""
        client_id = str(uuid.uuid4())
        connection = WebSocketConnection(websocket, client_id)

        await connection.connect()
        self.connections[client_id] = connection

        # Send initial connection confirmation
        await connection.send_message(MessageType.PING, {
            "client_id": client_id,
            "message": "Connected to Parody Critics WebSocket"
        })

        logger.info(f"New WebSocket client connected: {client_id}")
        return client_id

    async def disconnect_client(self, client_id: str):
        """Disconnect WebSocket client"""
        if client_id in self.connections:
            connection = self.connections[client_id]
            await connection.disconnect()
            del self.connections[client_id]

            logger.info(f"WebSocket client disconnected: {client_id}")

    async def subscribe_to_session(self, client_id: str, session_id: str):
        """Subscribe client to import session updates"""
        if client_id in self.connections:
            connection = self.connections[client_id]
            connection.subscriptions.add(session_id)

            # Send current progress if session exists
            if session_id in self.import_sessions:
                progress = self.import_sessions[session_id]
                await connection.send_message(MessageType.IMPORT_PROGRESS, asdict(progress))

            logger.debug(f"Client {client_id} subscribed to session {session_id}")

    def start_import_session(self, session_id: str, operation: str) -> ImportProgress:
        """Start new import session"""
        progress = ImportProgress(
            session_id=session_id,
            operation=operation,
            start_time=datetime.now().isoformat(),
            status="running"
        )

        self.import_sessions[session_id] = progress
        self.active_imports.add(session_id)

        # Broadcast to all clients
        asyncio.create_task(self._broadcast_to_session(
            session_id,
            MessageType.IMPORT_STARTED,
            asdict(progress)
        ))

        logger.info(f"Started import session: {session_id} - {operation}")
        return progress

    async def update_import_progress(self, session_id: str, **updates):
        """Update import session progress"""
        if session_id not in self.import_sessions:
            logger.warning(f"Attempted to update non-existent session: {session_id}")
            return

        progress = self.import_sessions[session_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(progress, key):
                setattr(progress, key, value)

        # Recalculate percentage
        if progress.total_items > 0:
            progress.percentage = (progress.processed_items / progress.total_items) * 100

        # Broadcast update
        await self._broadcast_to_session(
            session_id,
            MessageType.IMPORT_PROGRESS,
            asdict(progress)
        )

    async def complete_import_session(self, session_id: str, success: bool = True, error_message: str = None):
        """Complete import session"""
        if session_id not in self.import_sessions:
            logger.warning(f"Attempted to complete non-existent session: {session_id}")
            return

        progress = self.import_sessions[session_id]
        progress.status = "completed" if success else "error"

        if error_message:
            progress.error_messages.append(error_message)
            progress.errors += 1

        # Remove from active imports
        self.active_imports.discard(session_id)

        # Broadcast completion
        message_type = MessageType.IMPORT_COMPLETED if success else MessageType.IMPORT_ERROR
        await self._broadcast_to_session(session_id, message_type, asdict(progress))

        logger.info(f"Completed import session: {session_id} - {'SUCCESS' if success else 'ERROR'}")

    async def cancel_import_session(self, session_id: str):
        """Cancel import session"""
        if session_id in self.import_sessions:
            progress = self.import_sessions[session_id]
            progress.status = "cancelled"

            self.active_imports.discard(session_id)

            await self._broadcast_to_session(
                session_id,
                MessageType.IMPORT_CANCELLED,
                asdict(progress)
            )

            logger.info(f"Cancelled import session: {session_id}")

    async def _broadcast_to_session(self, session_id: str, message_type: MessageType, data: Dict[str, Any]):
        """Broadcast message to all clients subscribed to a session"""
        if not self.connections:
            return

        tasks = []
        for client_id, connection in self.connections.items():
            if session_id in connection.subscriptions:
                task = connection.send_message(message_type, data)
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Clean up disconnected clients
            disconnected = []
            for i, (client_id, _) in enumerate(self.connections.items()):
                if isinstance(results[i], Exception) or results[i] is False:
                    disconnected.append(client_id)

            for client_id in disconnected:
                await self.disconnect_client(client_id)

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active import sessions"""
        return [
            asdict(progress)
            for session_id, progress in self.import_sessions.items()
            if session_id in self.active_imports
        ]

    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for specific session"""
        if session_id in self.import_sessions:
            return asdict(self.import_sessions[session_id])
        return None

    async def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old completed sessions"""
        now = datetime.now()
        to_remove = []

        for session_id, progress in self.import_sessions.items():
            if session_id not in self.active_imports and progress.start_time:
                start_time = datetime.fromisoformat(progress.start_time)
                age_hours = (now - start_time).total_seconds() / 3600

                if age_hours > max_age_hours:
                    to_remove.append(session_id)

        for session_id in to_remove:
            del self.import_sessions[session_id]
            logger.debug(f"Cleaned up old session: {session_id}")

    async def start_heartbeat(self, interval: int = 30):
        """Start heartbeat ping to all connections"""
        if self._heartbeat_task:
            return

        async def heartbeat():
            while True:
                await asyncio.sleep(interval)
                if self.connections:
                    tasks = [conn.send_ping() for conn in self.connections.values()]
                    await asyncio.gather(*tasks, return_exceptions=True)

        self._heartbeat_task = asyncio.create_task(heartbeat())

    async def stop_heartbeat(self):
        """Stop heartbeat task"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


class WebSocketProgressAdapter:
    """Adapter to bridge sync_progress with WebSocket updates"""

    def __init__(self, session_id: str, manager: WebSocketManager = None):
        self.session_id = session_id
        self.manager = manager or websocket_manager

    async def set_total_items(self, total: int, total_pages: int = 1):
        """Set total items for import"""
        await self.manager.update_import_progress(
            self.session_id,
            total_items=total,
            total_pages=total_pages
        )

    async def update_page_progress(self, current_page: int, total_pages: int, page_items: int):
        """Update page progress"""
        await self.manager.update_import_progress(
            self.session_id,
            current_page=current_page,
            total_pages=total_pages
        )

    async def record_new_item(self, item_name: str):
        """Record new item"""
        progress = self.manager.import_sessions.get(self.session_id)
        if progress:
            await self.manager.update_import_progress(
                self.session_id,
                new_items=progress.new_items + 1,
                processed_items=progress.processed_items + 1,
                current_item=item_name
            )

    async def record_updated_item(self, item_name: str):
        """Record updated item"""
        progress = self.manager.import_sessions.get(self.session_id)
        if progress:
            await self.manager.update_import_progress(
                self.session_id,
                updated_items=progress.updated_items + 1,
                processed_items=progress.processed_items + 1,
                current_item=item_name
            )

    async def record_unchanged_item(self, item_name: str):
        """Record unchanged item"""
        progress = self.manager.import_sessions.get(self.session_id)
        if progress:
            await self.manager.update_import_progress(
                self.session_id,
                unchanged_items=progress.unchanged_items + 1,
                processed_items=progress.processed_items + 1,
                current_item=item_name
            )

    async def record_error(self, error_message: str, item_name: str = ""):
        """Record error"""
        progress = self.manager.import_sessions.get(self.session_id)
        if progress:
            full_error = f"{error_message}"
            if item_name:
                full_error += f" (Item: {item_name})"

            new_errors = progress.error_messages + [full_error]
            await self.manager.update_import_progress(
                self.session_id,
                errors=progress.errors + 1,
                error_messages=new_errors
            )