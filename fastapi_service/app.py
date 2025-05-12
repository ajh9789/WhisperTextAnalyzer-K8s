# =============================================
# ✅ fastapi_service/app.py (신규 FastAPI 서비스)
# =============================================

import os
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Voice Stream Test</title>
    </head>
    <body>
        <h1>Voice Stream Test</h1>
        <button onclick="startRecording()">🎙️ Start Recording</button>
        <script>
            var ws;
            function startRecording() {
                ws = new WebSocket("ws://localhost:8000/ws");
                ws.onopen = function() {
                    console.log("WebSocket Open");
                    navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream) {
                        const mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.start(250); // 250ms 단위로 chunk 전송
                        mediaRecorder.ondataavailable = function(e) {
                            if (ws.readyState === WebSocket.OPEN) {
                                ws.send(e.data);
                            }
                        }
                    });
                }
                ws.onmessage = function(event) {
                    console.log("Result: " + event.data);
                }
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            # ✅ Azure에서는 bytes (PCM or WAV)로 들어올 예정 → Redis push
            r.lpush("audio_queue", data)
            await websocket.send_text("✅ Audio chunk received")
    except WebSocketDisconnect:
        print("WebSocket disconnected")
