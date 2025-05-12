# =============================================
# ✅ fastapi_service/app.py (최종 통합 개선판)
# =============================================

import os
import redis
import asyncio
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
            #header { padding: 10px; background: #333; color: #fff; text-align: center; font-size: 1.2em; }
            #log { flex: 1; overflow-y: scroll; padding: 10px; border-bottom: 1px solid #ccc; }
            #stats { padding: 10px; background: #f2f2f2; position: sticky; bottom: 0; display: flex; justify-content: space-between; font-size: 1.1em; }
        </style>
    </head>
    <body>
        <div id="header">🎙️ 실시간 감정 분석 모니터</div>
        <div id="log"></div>
        <div id="stats"><span id="people">0/2 연결됨</span> <span id="result">긍정: 0회 / 부정: 0회</span></div>

        <script>
            var ws = new WebSocket("ws://" + location.host + "/ws");
            var log = document.getElementById("log");
            var stats = document.getElementById("result");
            var people = document.getElementById("people");
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
                if (data.startsWith("PEOPLE:")) {
                    people.textContent = data.replace("PEOPLE:", "") + " 연결됨";
                    return;
                }
                var div = document.createElement("div");
                div.textContent = data;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;

                if (data.includes("긍정")) positive++;
                else if (data.includes("부정")) negative++;
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
        r.ping()
    except redis.ConnectionError:
        await websocket.close(code=1000)
        return

    if len(connected_users) >= 2:
        await websocket.close(code=1000)
        return

    await websocket.accept()
    connected_users.add(websocket)

    # ✅ 연결 인원수 update broadcast
    for ws in connected_users:
        await ws.send_text(f"PEOPLE:{len(connected_users)}/2")

    inactivity_timeout = 1800  # 30분
    idle_timeout = 600         # 10분
    last_active = asyncio.get_event_loop().time()

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=10)
                last_active = asyncio.get_event_loop().time()
                try:
                    r.lpush("audio_queue", data)
                    await websocket.send_text("✅ Audio chunk received")
                except redis.ConnectionError:
                    await websocket.send_text("❌ Redis disconnected")
            except asyncio.TimeoutError:
                now = asyncio.get_event_loop().time()
                if now - last_active > inactivity_timeout:
                    await websocket.send_text("⏳ 30분 inactivity → 연결 종료")
                    break
                if now - last_active > idle_timeout:
                    await websocket.send_text("⏳ 10분 idle → 연결 종료")
                    break
    except WebSocketDisconnect:
        pass
    finally:
        connected_users.remove(websocket)
        # ✅ 연결 인원수 update broadcast
        for ws in connected_users:
            await ws.send_text(f"PEOPLE:{len(connected_users)}/2")
