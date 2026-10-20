import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API Gateway Anomaly Detection is running"}

from pydantic import BaseModel
from pipeline import handle_incoming_request

class RequestData(BaseModel):
    ip: str
    url: str
    status: int
    size: int
    user_agent: str
    referrer: str
    extra: str
    protocol: str
    method: str

@app.post("/check-request")
async def check_request(data: RequestData):
    result = handle_incoming_request(
        ip=data.ip, url=data.url, status=data.status, size=data.size,
        user_agent=data.user_agent, referrer=data.referrer, extra=data.extra,
        protocol=data.protocol, method=data.method
    )
    await broadcast_to_dashboard(result)
    return result


from fastapi import WebSocket


connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Connected successfully!")
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_clients.remove(websocket)

async def broadcast_to_dashboard(message: dict):
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            pass