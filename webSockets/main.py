from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict

app = FastAPI()

# Track connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[username] = websocket
        await self.broadcast_status(f"{username} is online")

    def disconnect(self, username: str):
        self.active_connections.pop(username, None)

    async def send_private_message(self, recipient: str, message: str, sender: str):
        if recipient in self.active_connections:
            await self.active_connections[recipient].send_json({
                "from": sender,
                "message": message
            })
            # Acknowledge delivery to sender
            await self.active_connections[sender].send_json({
                "system": f"Message delivered to {recipient}"
            })
        else:
            await self.active_connections[sender].send_json({
                "system": f"{recipient} is offline. Message not delivered."
            })

    async def broadcast_status(self, status_message: str):
        for conn in self.active_connections.values():
            await conn.send_json({"system": status_message})


manager = ConnectionManager()


@app.get("/")
async def get():
    with open("templates/chat2.html",encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            recipient = data["to"]
            message = data["message"]
            await manager.send_private_message(recipient, message, username)
    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.broadcast_status(f"{username} went offline")
