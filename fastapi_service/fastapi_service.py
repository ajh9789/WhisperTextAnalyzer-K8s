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
    # ✅ Redis 연결
    redis = await redis_from_url(redis_url)
    try:
        await redis.ping()
    except Exception as e:
        print(f"❌Redis 연결 실패: {e}")
        await websocket.close()
        return

    # ✅ WebSocket 연결 수락 및 유저 목록 등록
    await websocket.accept()
    connected_users[websocket] = {"buffer": bytearray(), "start_time": None}

    # ✅ 전체 유저 수 broadcast
    for user in connected_users:
        await user.send_text(f"PEOPLE:{len(connected_users)}")

    try:
        # ✅ 실시간 오디오 수신 및 STT로 바로 전송 (버퍼 없이 처리)
        while True:
            audio_chunk = await websocket.receive_bytes()
            print(f"[FastAPI] 🎧 청크 수신: {len(audio_chunk)} bytes")
            try:
                celery.send_task(
                    "stt_worker.transcribe_audio",
                    args=[audio_chunk],
                    queue="stt_queue"
                )
            except Exception as e:
                print(f"[FastAPI] ❌ Celery 전송 실패: {e}")

        # 🔽 기존 0.5초 누적 버퍼 방식 (지금은 비활성화, 주석처리)
        # TIMEOUT_SECONDS = 0.5
        # while True:
        #     audio_chunk = await websocket.receive_bytes()
        #     user_state = connected_users.get(websocket)
        #     if not user_state:
        #         break
        #
        #     buffer = user_state["buffer"]
        #     if user_state["start_time"] is None:
        #         user_state["start_time"] = asyncio.get_event_loop().time()
        #
        #     buffer.extend(audio_chunk)
        #
        #     if asyncio.get_event_loop().time() - user_state["start_time"] >= TIMEOUT_SECONDS:
        #         try:
        #             print(f"[FastAPI] 🎯 사용자 {id(websocket)} → stt_worker 전달 (size: {len(buffer)})")
        #             celery.send_task(
        #                 "stt_worker.transcribe_audio",
        #                 args=[bytes(buffer)],
        #                 queue="stt_queue"
        #             )
        #         except Exception as e:
        #             print(f"[FastAPI] ❌ Celery 전송 실패: {e}")
        #
        #         user_state["buffer"] = bytearray()
        #         user_state["start_time"] = None

    except WebSocketDisconnect:
        # ✅ 연결 종료 시 유저 목록에서 제거 및 사람 수 갱신
        connected_users.pop(websocket, None)
        for user in connected_users:
            await user.send_text(f"PEOPLE:{len(connected_users)}")

# ✅ Redis에서 analyzer_worker 결과 수신 및 감정 통계 처리
async def redis_subscriber():
    global positive_count, negative_count
    redis = await redis_from_url(redis_url, encoding="utf-8", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("result_channel")
    print("[FastAPI] ✅ Subscribed to result_channel")

    # ✅ 개선된 이벤트 기반 처리 방식 (async for + listen)
    async for message in pubsub.listen():
        if message.get("type") != "message":
            continue

        data = message.get("data", "")
        print(f"[FastAPI] 📩 메시지 수신: {data}")

        # 전체 유저에게 메시지 전달
        for user in list(connected_users):
            try:
                await user.send_text(data)
            except Exception as e:
                print(f"❌ WebSocket 전송 실패: {e}")
                connected_users.pop(user, None)

        # 감정 통계 계산
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

# ✅ FastAPI 서버 시작 시 Redis 수신 루프 실행
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
        let ctx = null;
        let stream = null;
        let audioBuffer = [];  // ✅ 0.5초 버퍼링용
        let lastSendTime = performance.now();

        const log = document.getElementById("log");
        const stats = document.getElementById("stats");
        const people = document.getElementById("people");
        const button = document.getElementById("startButton");
        
        function resolveWebSocketURL(path = "/ws") {
            const loc = window.location;
            const protocol = loc.protocol === "https:" ? "wss://" : "ws://";
            const port = loc.port ? `:${loc.port}` : "";
            return `${protocol}${loc.hostname}${port}${path}`;
        }

        button.onclick = async function () {
            if (button.textContent.includes("Start")) {
                ws = new WebSocket(resolveWebSocketURL("/ws"));
                ws.onopen = () => console.log("✅ WebSocket 연결 성공");
                ws.onclose = () => console.log("❌ WebSocket 연결 종료");
                ws.onerror = (e) => console.error("❌ WebSocket 오류 발생:", e);

                ws.onmessage = function (event) {
                    const data = event.data;
                    if (data.startsWith("PEOPLE:")) {
                        people.textContent = "연결 인원:" + data.replace("PEOPLE:", "");
                        return;
                    }
                    if (data.startsWith("✅ Listener 통계 → ")) {
                        stats.textContent = data.replace("✅ Listener 통계 → ", "");
                        return;
                    }
                    const div = document.createElement("div");
                    div.textContent = data;
                    log.appendChild(div);
                    log.scrollTop = log.scrollHeight;
                };

                try {
                    stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            sampleRate: 16000,               // 🎯 Whisper용 16kHz
                            channelCount: 1,                 // 🎯 mono 고정
                            noiseSuppression: true,          // 🎯 배경 잡음 제거
                            echoCancellation: true           // 🎯 에코 제거
                        }
                    });
                    console.log("🎧 getUserMedia 성공");

                    ctx = new AudioContext({ sampleRate: 16000 });
                    const blob = new Blob([document.querySelector('script[type="worklet"]').textContent], { type: 'application/javascript' });
                    const blobURL = URL.createObjectURL(blob);
                    await ctx.audioWorklet.addModule(blobURL);

                    const src = ctx.createMediaStreamSource(stream);
                    const worklet = new AudioWorkletNode(ctx, 'audio-processor');

                    // ✅ 0.5초 단위로 audio chunk 전송
                    worklet.port.onmessage = (e) => {
                        const now = performance.now();
                        const chunk = new Int16Array(e.data);
                        audioBuffer.push(...chunk);

                        if (now - lastSendTime >= 500) {
                            if (ws.readyState === WebSocket.OPEN) {
                                const final = new Int16Array(audioBuffer);
                                ws.send(final.buffer);
                                audioBuffer = [];
                                lastSendTime = now;
                            }
                        }
                    };

                    src.connect(worklet).connect(ctx.destination);
                    button.textContent = "⏹️ Stop";
                } catch (error) {
                    console.error("❌ Audio 처리 중 오류 발생:", error);
                }
            } else {
                if (audioBuffer.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    const final = new Int16Array(audioBuffer);
                    ws.send(final.buffer);
                    console.log("🧹 남은 오디오 버퍼 전송 후 종료");
                }
                if (ws) {
                    ws.close();
                    ws = null;
                }
                if (ctx) {
                    ctx.close();
                    ctx = null;
                }
                if (stream) {
                    stream.getTracks().forEach(t => t.stop());
                    stream = null;
                }
                audioBuffer = [];  // ✅ 잔여 데이터 정리
                button.textContent = "🎙️ Start";
                console.log("🛑 마이크/연결 종료");
            }
        };
    </script>

    <script type="worklet">
        class AudioProcessor extends AudioWorkletProcessor {
            constructor() {
                super();
                // ✅ 모바일과 PC 구분 후 에너지 기준치 설정
                this.isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(globalThis.navigator.userAgent);
                this.energyThreshold = this.isMobile ? 0.0001 : 0.001;
            }

            process(inputs, outputs, parameters) {
                const input = inputs[0];
                if (input.length > 0) {
                    const channelData = input[0];

                    // ✅ VAD energy filter
                    let energy = 0;
                    for (let i = 0; i < channelData.length; i++) {
                        energy += Math.abs(channelData[i]);
                    }
                    energy /= channelData.length;

                    if (energy < this.energyThreshold) return true;  // ✅ silence skip

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



