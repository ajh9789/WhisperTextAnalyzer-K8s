import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from prometheus_client import Counter, generate_latest
from fastapi import Response
from redis.asyncio import from_url as redis_from_url
from celery import Celery

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
celery = Celery("fastapi_service", broker=redis_url)

connected_users = {}
positive_count = 0
negative_count = 0
http_requests = Counter("http_requests_total", "Total HTTP Requests")

@app.get("/")
async def get():
    http_requests.inc()
    return HTMLResponse(html)

# api 만들기
# 부정 긍정 통계 카운트 반환
@app.get("/status")
def status():
    return {
        "positive": positive_count,
        "negative": negative_count
    }

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# 소켓연결 및 stt_worker에게 데이터 전달
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    redis = await redis_from_url(redis_url)
    try:
        await redis.ping()
    except Exception:
        await websocket.close()
        return

    await websocket.accept()
    connected_users[websocket] = {"buffer": bytearray(), "start_time": None}
    for user in connected_users:
        await user.send_text(f"PEOPLE:{len(connected_users)}")

    try:
        TIMEOUT_SECONDS = 1
        while True:
            audio_chunk = await websocket.receive_bytes()
            user_state = connected_users.get(websocket)
            if not user_state:
                break

            buffer = user_state["buffer"]
            if user_state["start_time"] is None:
                user_state["start_time"] = asyncio.get_event_loop().time()

            buffer.extend(audio_chunk)

            if asyncio.get_event_loop().time() - user_state["start_time"] >= TIMEOUT_SECONDS:
                try:
                    print(f"[FastAPI] 🎯 사용자 {id(websocket)} → stt_worker 전달 (size: {len(buffer)})")
                    celery.send_task(
                        "stt_worker.transcribe_audio",
                        args=[bytes(buffer)],
                        queue="stt_queue"
                    )
                except Exception as e:
                    print(f"[FastAPI] ❌ Celery 전송 실패: {e}")

                user_state["buffer"] = bytearray()
                user_state["start_time"] = None

    except WebSocketDisconnect:
        connected_users.pop(websocket, None)
        for user in connected_users:
            await user.send_text(f"PEOPLE:{len(connected_users)}")

# redis한테서 anyalyzer_worker한테 결과 받은거 출력 및 통계
async def redis_subscriber():
    global positive_count, negative_count
    redis = await redis_from_url(redis_url, encoding="utf-8", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("result_channel")
    print("[FastAPI] ✅ Subscribed to result_channel")

# 폴링 방식으로 받기
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
        if message and message.get("type") == "message":
            data = message["data"]
            print(f"[FastAPI] 📩 메시지 수신: {data}")

            for user in list(connected_users):
                try:
                    await user.send_text(data)
                except Exception:
                    connected_users.pop(user, None)

            if "긍정" in data:
                positive_count += 1
            elif "부정" in data:
                negative_count += 1

            total = positive_count + negative_count
            if total:
                pos_percent = (positive_count / total) * 100
                neg_percent = (negative_count / total) * 100
            else:
                pos_percent = neg_percent = 0

            stats = f"Listener 통계 → 👍{positive_count}회{pos_percent:.0f}%|{neg_percent:.0f}%{negative_count}회 👎"
            print(f"[FastAPI] 📊 {stats}")

            for user in list(connected_users):
                try:
                    await user.send_text(stats)
                except Exception:
                    connected_users.pop(user, None)

        await asyncio.sleep(0.1)

#
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())


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



