# =============================================
# ✅ fastapi_service/app.py (최종 심플 통계 개선판)
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
            #header { padding: 10px; background: #333; color: #fff; text-align: center; font-size: 1.2em; display: flex; justify-content: space-between; align-items: center; }
            #log { flex: 1; overflow-y: scroll; padding: 10px; border-bottom: 1px solid #ccc; }
            #stats { padding: 10px; background: #f2f2f2; position: sticky; bottom: 0; display: flex; justify-content: center; font-size: 1.2em; }
        </style>
    </head>
    <body>
        <div id="header">
            <span>🎙️ 실시간 감정 분석 모니터</span>
            <span id="people">현재 연결 인원: 0/2</span>
        </div>
        <div id="log"></div>
        <div id="stats">👍 0% 0회 | 0회 0% 👎</div>

        <script>
            var ws = new WebSocket("ws://" + location.host + "/ws");
            var log = document.getElementById("log");
            var stats = document.getElementById("stats");
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
                    people.textContent = "현재 연결 인원: " + data.replace("PEOPLE:", "");
                    return;
                }
                if (data.startsWith("ALERT:")) {
                    alert(data.replace("ALERT:", ""));
                    return;
                }
                var div = document.createElement("div");
                div.textContent = data;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;

                if (data.includes("긍정")) positive++;
                else if (data.includes("부정")) negative++;

                let total = positive + negative;
                let pos_ratio = total > 0 ? Math.round((positive / total) * 100) : 0;
                let neg_ratio = total > 0 ? Math.round((negative / total) * 100) : 0;

                stats.textContent = `👍 ${pos_ratio}% ${positive}회 | ${negative}회 ${neg_ratio}% 👎`;
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

    for ws in connected_users:
        await ws.send_text(f"PEOPLE:{len(connected_users)}/2")

    inactivity_timeout = 1800
    idle_timeout = 600
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
                    await websocket.send_text("ALERT:서버가 불안정해서 연결을 끊습니다.")
                    break
            except asyncio.TimeoutError:
                now = asyncio.get_event_loop().time()
                if now - last_active > inactivity_timeout:
                    await websocket.send_text("ALERT:30분이 지나서 연결을 끊습니다.")
                    break
                if now - last_active > idle_timeout:
                    await websocket.send_text("ALERT:10분 이상 말이 없어서 연결을 끊습니다.")
                    break
    except WebSocketDisconnect:
        pass
    finally:
        connected_users.remove(websocket)
        for ws in connected_users:
            await ws.send_text(f"PEOPLE:{len(connected_users)}/2")