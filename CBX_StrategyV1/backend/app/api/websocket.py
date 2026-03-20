import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.utils.security import decode_token
from jose import JWTError

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections using a dictionary for targeted messaging.
    """
    def __init__(self):
        # client_id (UUID string) -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """Accept connection and store in dict."""
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket: Client {client_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """Remove connection from dict."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket: Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to a specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return
            
        logger.debug(f"Broadcasting message: {message.get('type')}")
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Cleanup any failed connections
        for client_id in disconnected_clients:
            self.disconnect(client_id)

# Global instances
connection_manager = ConnectionManager()

async def _ping_loop(websocket: WebSocket, client_id: str, manager: ConnectionManager):
    """
    Background loop to send pings every 30 seconds.
    If no pong/response (handled by main loop), connection will eventually timeout or fail.
    """
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception:
        # Loop will terminate on disconnect or error
        pass

async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    client_id: str = Query(...)
):
    """
    WebSocket endpoint with JWT validation and keep-alive.
    URL: /ws?token=<jwt>&client_id=<uuid>
    """
    # 1. JWT Validation
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            logger.warning(f"WS Auth Failed: Invalid token type for client {client_id}")
            await websocket.close(code=4001)
            return
    except JWTError:
        logger.warning(f"WS Auth Failed: Malformed token for client {client_id}")
        await websocket.close(code=4001)
        return
    except Exception as e:
        logger.error(f"WS Auth Error: {e}")
        await websocket.close(code=4001)
        return

    # 2. Accept connection
    await websocket.accept()
    await connection_manager.connect(client_id, websocket)
    
    # 3. Start keep-alive loop
    ping_task = asyncio.create_task(_ping_loop(websocket, client_id, connection_manager))
    
    try:
        # Main communication loop (wait for client messages/keep connection open)
        while True:
            data = await websocket.receive_json()
            # Handle pong or other client messages if needed
            if data.get("type") == "pong":
                logger.debug(f"Received PONG from {client_id}")
            else:
                logger.debug(f"Received message from client {client_id}: {data}")
    except WebSocketDisconnect:
        logger.info(f"WebSocketDisconnect: Client {client_id}")
    except Exception as e:
        logger.error(f"WebSocket Error for {client_id}: {e}")
    finally:
        ping_task.cancel()
        connection_manager.disconnect(client_id)
        # Ensure connection is closed if not already
        try:
            await websocket.close()
        except:
            pass
