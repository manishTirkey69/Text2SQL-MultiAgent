"""
WebSocket handler for streaming reasoning traces.
"""
from typing import Dict, Any
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket connections for streaming."""
    
    def __init__(self, websocket: WebSocket):
        """
        Initialize WebSocket handler.
        
        Args:
            websocket: WebSocket connection
        """
        self.websocket = websocket
    
    async def send_trace_update(self, update: Dict[str, Any]):
        """
        Send trace update to client.
        
        Args:
            update: Update dictionary
        """
        try:
            await self.websocket.send_json(update)
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")
    
    async def send_error(self, error: str):
        """Send error message."""
        await self.send_trace_update({
            "type": "error",
            "message": error
        })
    
    async def send_success(self, result: Dict[str, Any]):
        """Send success result."""
        await self.send_trace_update({
            "type": "success",
            "result": result
        })
