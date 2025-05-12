# =============================================
# ✅ fastapi_service/app.py (개선판: Redis ping + 예외처리 추가)
# =============================================

import os
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

connected_users = set()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Realtime STT & Emotion Monitor</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
            #log { flex: 1; overflow-y: scroll; padding: 10px; border-bottom: 1px solid #ccc; }
            #stats { padding: 10px; background: #f2f2f2; position: sticky; bottom: 0; }
        </style>
    </head>
    <body>
        <div id="log"></div>
        <div id="stats">긍정: 0회 / 부정: 0회</div>

        <script>
            var ws = new WebSocket("ws://" + location.host + "/ws");
            var log = document.getElementById("log");
            var stats = document.getElementById("stats");
            var positive = 0, negative = 0;

            ws.onopen = function() {
                navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream) {
                    const mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.start(500);
                    mediaRecorder.ondataavailable = function(e) {
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send(e.data);
                        }
                    }
                });
            }

            ws.onmessage = function(event) {
                var data = event.data;
                var div = document.createElement("div");
                div.textContent = data;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;

                if (data.includes("긍정")) {
                    positive++;
                } else if (data.includes("부정")) {
                    negative++;
                }
                stats.textContent = `긍정: ${positive}회 / 부정: ${negative}회`;
            }

            ws.onclose = function() {
                var div = document.createElement("div");
                div.textContent = "[Disconnected]";
                div.style.color = "red";
                log.appendChild(div);
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
    try:
        # ✅ Redis 연결 확인 (없으면 종료)
        r.ping()
    except redis.ConnectionError:
        await websocket.close(code=1000)
        return

    if len(connected_users) >= 2:
        await websocket.close(code=1000)
        return

    await websocket.accept()
    connected_users.add(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            try:
                r.lpush("audio_queue", data)
                await websocket.send_text("✅ Audio chunk received")
            except redis.ConnectionError:
                await websocket.send_text("❌ Redis disconnected")
    except WebSocketDisconnect:
        connected_users.remove(websocket)