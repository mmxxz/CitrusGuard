from fastapi import WebSocket
from typing import List, Dict

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        try:
            print(f"[WS-CONNECT] session={session_id}, total={len(self.active_connections[session_id])}")
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        try:
            print(f"[WS-DISCONNECT] session={session_id}")
        except Exception:
            pass

    async def broadcast_to_session(self, session_id: str, message: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    try:
                        print(f"[WS-SEND-ERROR] session={session_id} err={e}")
                    except Exception:
                        pass

manager = WebSocketManager()
