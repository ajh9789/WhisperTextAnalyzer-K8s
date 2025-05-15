import os
from redis import asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from celery import Celery
import asyncio

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
celery = Celery("fastapi_service", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
connected_users = set()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Realtime STT & Emotion Monitor</title>
        <style>
            body { font-family: Arial; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
            #header { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #333; color: white; font-size: 1.2em; flex-wrap: wrap; }
            #title { flex: 1; text-align: left; }
            #startButton {
                min-width: 120px;
                margin: 0 auto;
                display: block;
                padding: 8px 16px;
                font-size: 1em;
                cursor: pointer;
            }
            #people { flex: 1; text-align: right; }
            #log { flex: 1; overflow-y: scroll; padding: 10px; border-bottom: 1px solid #ccc; }
            #stats { padding: 10px; background: #f2f2f2; position: sticky; bottom: 0; display: flex; justify-content: center; font-size: 1.2em; }
            button { padding: 8px 16px; font-size: 1em; cursor: pointer; }
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
            if (ws && ws.readyState === WebSocket.OPEN) {
                console.warn("이미 WebSocket 연결 중입니다.");
                return;
                }
                ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");

                ws.onopen = () => console.log("✅ WebSocket 연결 성공");
                ws.onclose = () => console.log("❌ WebSocket 연결 종료");

                ws.onmessage = function(event) {
                    var data = event.data;
                    if (data.startsWith("PEOPLE:")) {
                        people.textContent = "연결 인원:" + data.replace("PEOPLE:", "");
                        return;
                    }
                    if (data.startsWith("✅ Listener 통계 → ")) {
                        stats.textContent = data.replace("✅ Listener 통계 → ", "");
                        return;
                    }
                    var div = document.createElement("div");
                    div.textContent = data;
                    log.appendChild(div);
                    log.scrollTop = log.scrollHeight;
                };

                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            sampleRate: 16000,               // 🎯 Whisper용 16kHz
                            channelCount: 1,                 // 🎯 mono 고정
                            noiseSuppression: true,          // 🎯 배경 잡음 제거
                            echoCancellation: true           // 🎯 에코 제거
                        }
                    });
                    console.log("🎧 getUserMedia 성공");

                    const ctx = new AudioContext({ sampleRate: 16000 });  // 🎯 downstream 16kHz 고정
                    const blob = new Blob([document.querySelector('script[type="worklet"]').textContent], { type: 'application/javascript' });
                    const blobURL = URL.createObjectURL(blob);
                    await ctx.audioWorklet.addModule(blobURL);

                    const src = ctx.createMediaStreamSource(stream);
                    const worklet = new AudioWorkletNode(ctx, 'audio-processor');

                    worklet.port.onmessage = (e) => {
                        console.log("🎙️ Audio chunk 전달:", e.data.byteLength, "bytes");
                        if (ws.readyState === WebSocket.OPEN) ws.send(e.data);
                    };

                    src.connect(worklet).connect(ctx.destination);
                } catch (error) {
                    console.error("❌ Audio 처리 중 오류 발생:", error);
                }
            };
        </script>

        <script type="worklet">
        class AudioProcessor extends AudioWorkletProcessor {
            process(inputs, outputs, parameters) {
                const input = inputs[0];
                if (input.length > 0) {
                    const channelData = input[0];

                    // ✅ VAD: energy filter
                    let energy = 0;
                    for (let i = 0; i < channelData.length; i++) {
                        energy += Math.abs(channelData[i]);
                    }
                    energy /= channelData.length;

                    if (energy < 0.0005) return true;  // ✅ silence skip

                    // ✅ Float32 → Int16 변환
                    const int16Buffer = new Int16Array(channelData.length);
                    for (let i = 0; i < channelData.length; i++) {
                        let s = Math.max(-1, Math.min(1, channelData[i]));
                        int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }

                    // ✅ Int16Array → ArrayBuffer 전달
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

    for user in connected_users:
        await user.send_text(f"PEOPLE:{len(connected_users)}")

    try:
        # ✅ 버퍼 accumulate 로직
        buffer = bytearray()
        start_time = None
        TIMEOUT_SECONDS = 2  # 🎯 버퍼 accumulate 시간 (5초)

        while True:
            audio_chunk = await websocket.receive_bytes()
            if not start_time:
                start_time = asyncio.get_event_loop().time()  # 🎯 시작 시간 기록
            buffer.extend(audio_chunk)

            # 🎯 5초 경과 시 STT task 전송
            if asyncio.get_event_loop().time() - start_time >= TIMEOUT_SECONDS:
                print(f"[FastAPI] 🎯 5초 버퍼 완료 → stt_worker 전달 (size: {len(buffer)})")
                celery.send_task("stt_worker.transcribe_audio", args=[bytes(buffer)], queue="stt_queue")
                buffer = bytearray()
                start_time = None

    except WebSocketDisconnect:
        connected_users.remove(websocket)
        for user in connected_users:
            await user.send_text(f"PEOPLE:{len(connected_users)}")


async def redis_subscriber():
    redis = await aioredis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}/0", encoding="utf-8", decode_responses=True
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe("final_stats", "result_messages")
    print("[fastapi] ✅ Subscribed to final_stats & result_messages")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        data = message["data"]
        for user in connected_users.copy():
            try:
                await user.send_text(data)
            except Exception:
                connected_users.remove(user)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())

