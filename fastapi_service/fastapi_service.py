# ✅ WhisperTextAnalyzer 완성본 (2025 최신버전)
# - connection별 buffer 누적 (2초)
# - 모바일 silence threshold 개선 (0.00001)
# - 원래 실시간 감정 분석 UI 복구

import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from celery import Celery
from redis import asyncio as aioredis

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
celery = Celery("fastapi_service", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
connected_users = set()
connection_buffers = {}

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Realtime STT & Emotion Monitor</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
            #header { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #333; color: white; font-size: 1.2em; flex-wrap: wrap; }
            #title { flex: 1; text-align: left; }
            #startButton { min-width: 120px; margin: 0 auto; display: block; padding: 8px 16px; font-size: 1em; cursor: pointer; }
            #people { flex: 1; text-align: right; }
            #log { flex: 1; overflow-y: scroll; padding: 10px; border-bottom: 1px solid #ccc; }
            #stats { padding: 10px; background: #f2f2f2; position: sticky; bottom: 0; display: flex; justify-content: center; font-size: 1.2em; }
        </style>
    </head>
    <body>
        <div id="header">
            <div id="title">🎙️ 실시간 감정 분석</div>
            <button id="startButton">🎙️ Start</button>
            <div id="people">연결 인원:0</div>
        </div>
        <div id="log"></div>
        <div id="stats">👍0회 0%|0% 0회👎</div>

        <script>
            let ws = null;
            let log = document.getElementById("log");
            let stats = document.getElementById("stats");
            let people = document.getElementById("people");
            document.getElementById("startButton").onclick = async function() {
                if (ws && ws.readyState === WebSocket.OPEN) return;
                ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
                ws.onmessage = function(event) {
                    var data = event.data;
                    if (data.startsWith("PEOPLE:")) { people.textContent = "연결 인원:" + data.replace("PEOPLE:", ""); return; }
                    if (data.startsWith("✅ Listener 통계 → ")) { stats.textContent = data.replace("✅ Listener 통계 → ", ""); return; }
                    var div = document.createElement("div"); div.textContent = data; log.appendChild(div); log.scrollTop = log.scrollHeight;
                };
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1, noiseSuppression: true, echoCancellation: true }});
                    const ctx = new AudioContext({ sampleRate: 16000 });
                    const blob = new Blob([document.querySelector('script[type="worklet"]').textContent], { type: 'application/javascript' });
                    const blobURL = URL.createObjectURL(blob);
                    await ctx.audioWorklet.addModule(blobURL);
                    const src = ctx.createMediaStreamSource(stream);
                    const worklet = new AudioWorkletNode(ctx, 'audio-processor');
                    worklet.port.onmessage = (e) => { if (ws.readyState === WebSocket.OPEN) ws.send(e.data); };
                    src.connect(worklet).connect(ctx.destination);
                } catch (error) { console.error("❌ Audio 처리 오류:", error); }
            };
        </script>

        <script type="worklet">
            class AudioProcessor extends AudioWorkletProcessor {
                process(inputs) {
                    const input = inputs[0];
                    if (input.length > 0) {
                        const channelData = input[0];
                        let energy = 0; for (let i = 0; i < channelData.length; i++) energy += Math.abs(channelData[i]);
                        energy /= channelData.length;
                        if (energy < 0.00001) return true; // ✅ 모바일 대응 silence skip
                        const int16Buffer = new Int16Array(channelData.length);
                        for (let i = 0; i < channelData.length; i++) {
                            let s = Math.max(-1, Math.min(1, channelData[i]));
                            int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        }
                        this.port.postMessage(int16Buffer.buffer, [int16Buffer.buffer]);
                    }
                    return true;
                }
            }
            registerProcessor('audio-processor', AudioProcessor);
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    redis = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
    try:
        await redis.ping()
    except Exception:
        await websocket.close()
        return

    await websocket.accept()
    connected_users.add(websocket)
    connection_buffers[websocket] = [bytearray(), None]

    for user in connected_users:
        await user.send_text(f"PEOPLE:{len(connected_users)}")

    try:
        while True:
            buffer, start_time = connection_buffers[websocket]
            chunk = await websocket.receive_bytes()
            if not start_time: start_time = asyncio.get_running_loop().time()
            buffer.extend(chunk)
            if asyncio.get_running_loop().time() - start_time >= 2.0:
                celery.send_task("stt_worker.transcribe_audio", args=[bytes(buffer)], queue="stt_queue")
                connection_buffers[websocket] = [bytearray(), None]
    except WebSocketDisconnect:
        connected_users.remove(websocket)
        connection_buffers.pop(websocket, None)
        for user in connected_users:
            await user.send_text(f"PEOPLE:{len(connected_users)}")

async def redis_subscriber():
    redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0", encoding="utf-8", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("final_stats", "result_messages")
    async for message in pubsub.listen():
        if message["type"] != "message": continue
        data = message["data"]
        for user in connected_users.copy():
            try: await user.send_text(data)
            except Exception:
                connected_users.remove(user)
                connection_buffers.pop(user, None)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())
