import os
import asyncio
from contextlib import asynccontextmanager  # ✅ lifespan 구현용
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from prometheus_client import Counter, generate_latest
from fastapi import Response
from redis.asyncio import from_url as redis_from_url
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
celery = Celery("fastapi_service", broker=redis_url)

connected_users = {}
positive_count = 0
negative_count = 0
http_requests = Counter("http_requests_total", "Total HTTP Requests")

# Redis pubsub 전역 선언
pubsub = None


# FastAPI lifespan 함수 정의: 서버 시작/종료 타이밍에 실행되는 코드 정의
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pubsub
    # 서버 시작 시: Redis 연결 및 pubsub 구독 설정
    redis = await redis_from_url(redis_url, encoding="utf-8", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("result_channel")
    asyncio.create_task(redis_subscriber())  # ✅ 백그라운드로 Redis 수신 태스크 실행
    yield
    # 서버 종료 시: 구독 해제 및 리소스 정리
    await pubsub.unsubscribe("result_channel")
    await pubsub.close()
    print("[FastAPI] 🔒 Redis pubsub 정리 완료")


# lifespan 적용된 FastAPI 인스턴스 생성
app = FastAPI(lifespan=lifespan)


# 루트 엔드포인트 - 상태 확인용 HTML 응답
@app.get("/")
async def get():
    http_requests.inc()
    return HTMLResponse(html)


# 감정 분석 통계 API
@app.get("/status")
def status():
    return {"positive": positive_count, "negative": negative_count}


# Prometheus 메트릭 엔드포인트
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


# WebSocket 엔드포인트 정의 - 오디오 수신 및 STT 큐 전송
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Redis 연결 테스트
    redis = await redis_from_url(redis_url)
    try:
        await redis.ping()
    except Exception as e:
        print(f"❌Redis 연결 실패: {e}")
        await websocket.close()
        return

    # 클라이언트 WebSocket 연결 수락 및 등록
    await websocket.accept()
    connected_users[websocket] = {"buffer": bytearray(), "start_time": None}

    # 현재 연결 인원 브로드캐스트
    for user in connected_users:
        await user.send_text(f"PEOPLE:{len(connected_users)}")

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            print(f"[FastAPI] 🎧 청크 수신: {len(audio_chunk)} bytes")
            try:
                celery.send_task(
                    "stt_worker.transcribe_audio", args=[audio_chunk], queue="stt_queue"
                )
            except Exception as e:
                print(f"[FastAPI] ❌ Celery 전송 실패: {e}")
    except WebSocketDisconnect:
        # 연결 해제 시 유저 목록 정리 및 브로드캐스트 갱신
        connected_users.pop(websocket, None)
        for user in connected_users:
            await user.send_text(f"PEOPLE:{len(connected_users)}")


# Redis PubSub 수신 및 감정 통계 계산 루프
async def redis_subscriber():
    global positive_count, negative_count
    print("[FastAPI] ✅ Subscribed to result_channel")

    try:  # 개선된 이벤트 기반 처리 방식 (async for + listen)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            data = message.get("data", "")
            print(f"[FastAPI] 📩 메시지 수신: {data}")

            # 메시지를 모든 연결된 WebSocket 사용자에게 전송
            for user in list(connected_users):
                try:
                    await user.send_text(data)
                except Exception as e:
                    print(f"❌ WebSocket 전송 실패: {e}")
                    connected_users.pop(user, None)

            # 감정 분석 결과 카운팅
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
    except asyncio.CancelledError:
        print("[FastAPI] 🔴 redis_subscriber 종료됨")
    except Exception as e:
        print(f"[FastAPI] ❌ 예외 발생: {e}")


html = """
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

        #statsRow {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
            background: #f2f2f2;
            flex-wrap: wrap;
            gap: 6px;
        }

        #leftInfo {
            white-space: nowrap;
        }

        #centerStat {
            flex: 1;
            text-align: center;
            min-width: 160px;
        }

        #rightControl {
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }

        #thresholdSlider {
            width: 140px;
        }

        button { padding: 8px 16px; font-size: 1em; cursor: pointer; }

        @media (max-width: 480px) {
            #statsRow {
                flex-wrap: nowrap;
                flex-direction: column;
                align-items: stretch;
            }

            #rightControl {
                justify-content: center;
                margin-top: 6px;
            }

            #thresholdSlider {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div id="header">
        <div id="title">🎙️ 실시간 감정 분석</div>
        <button id="startButton">🎙️ Start</button>
        <div id="people">연결 인원:0</div>
    </div>
    <div id="log"></div>

    <div id="statsRow">                               <!-- 소음과 슬라이드로 감도 조절기능 추가 -->
        <div id="leftInfo">🔈 소음: <span id="currentEnergy">0</span></div>
        <div id="centerStat">👍0회 0%|0% 0회👎</div>
        <div id="rightControl">
            🎚️ <span>감도:</span>
            <input id="thresholdSlider" type="range" min="0" max="30" value="10">
            <span id="sensitivityLabel">10</span>        <!-- 슬라이더 뒤에 감도 표기 -->
        </div>
    </div>

    <script>
        let ws = null;
        let ctx = null;
        let stream = null;
        let worklet = null; 
        let audioBuffer = [];
        let lastSendTime = performance.now();

        const log = document.getElementById("log");
        const stats = document.getElementById("centerStat");
        const people = document.getElementById("people");
        const button = document.getElementById("startButton");
        const isMobile = /Mobi|Android|iPhone/i.test(navigator.userAgent);

        // 슬라이더와 관련된 DOM 요소들 정의
        const slider = document.getElementById("thresholdSlider");
        const energyDisplay = document.getElementById("currentEnergy");
        const sensitivityLabel = document.getElementById("sensitivityLabel");

        // threshold 설정 범위 정의 
        const minThreshold = 0;
        const thresholdStep = 0.001;
        const maxIndex = 30;  // 슬라이더 max 속성

        // 슬라이더 입력 이벤트: threshold 계산 및 Worklet 전송
        slider.oninput = () => {
            const index = parseInt(slider.value, 10);  // 슬라이더 값 정수로 변환
            const threshold = minThreshold + index * thresholdStep;  // 계산식 적용
            worklet?.port.postMessage({ type: "threshold", value: threshold });  // worklet에 threshold 값 전달
            sensitivityLabel.textContent = (threshold * 1000).toFixed(1);  // 감도 수치를 정수로 표시
        };

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
                            sampleRate: 16000,               // Whisper용 16kHz
                            channelCount: 1,                 // mono 고정
                            noiseSuppression: true,          // 배경 잡음 제거
                            echoCancellation: true           // 에코 제거
                        }
                    });
                    console.log("🎧 getUserMedia 성공");

                    ctx = new AudioContext({ sampleRate: 16000 });
                    const blob = new Blob([
                        document.querySelector('script[type="worklet"]').textContent
                    ], { type: 'application/javascript' });

                    const blobURL = URL.createObjectURL(blob);
                    await ctx.audioWorklet.addModule(blobURL);
                    const src = ctx.createMediaStreamSource(stream);
                    worklet = new AudioWorkletNode(ctx, 'audio-processor', {
                        processorOptions: { isMobile }
                    });

                    // 초기 threshold 설정 및 감도 수치 반영
                    const initIndex = parseInt(slider.value, 10);  // 문자열 슬라이더 값을 정수로 변환
                    const initialThreshold = minThreshold + initIndex * thresholdStep;
                    worklet?.port.postMessage({ type: "threshold", value: initialThreshold });
                    sensitivityLabel.textContent = (initialThreshold * 1000).toFixed(1);  // 정수형 감도 표기

                    // 오디오 처리 및 energy 수신 처리
                    worklet.port.onmessage = (e) => {
                        if (e.data?.type === "energy") {// 메시지를 받았을 때
                            energyDisplay.textContent = (e.data.value * 1000).toFixed(1);  // 소음 에너지를 정수화해서 표시
                        }// 그 메시지 객체의 type이 "energy"인 경우 실행되서 표기 

                        const now = performance.now();
                        if (e.data?.type !== "energy") { // 버퍼 넣기전에 energy타입인지 확인
                        const chunk = new Int16Array(e.data);
                        audioBuffer.push(...chunk); //전개 연산자(Spread operator) chunk가 128프레임 배열이라 각 원소를 하나씩 푸쉬
                            }

                        if (now - lastSendTime >= 4000) {   // 1초 단위로 녹음
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
                audioBuffer = [];
                button.textContent = "🎙️ Start";
                console.log("🛑 마이크/연결 종료");
            }
        };
    </script>

    <script type="worklet">
        class AudioProcessor extends AudioWorkletProcessor {
            constructor(options) {
                super();
                this.isMobile = options.processorOptions?.isMobile ?? false;
                this.energyThreshold = this.isMobile ? 0.001 : 0.01;
                this.port.onmessage = (e) => { // 객체타입이 맞을때 에너지값을 슬라이더값으로 받아옴
                    if (e.data?.type === "threshold") {
                        this.energyThreshold = e.data.value;
                    }
                };
            }

            process(inputs) {
                const input = inputs[0];
                if (input.length > 0) {
                    const channelData = input[0];

                    let energy = 0;
                    for (let i = 0; i < channelData.length; i++) {
                        energy += Math.abs(channelData[i]);
                    }
                    energy /= channelData.length;
                    this.port.postMessage({ type: "energy", value: energy }); // 화면에 에너지값 표기
                    if (energy < this.energyThreshold) return true;
                    
                    const int16Buffer = new Int16Array(channelData.length); // 오디오는 기본적으로Float32Array형으로 던져줌
                    for (let i = 0; i < channelData.length; i++) {          //클리핑(clipping) 오디오 데이터는 이론상 -1.0 ~ 1.0
                        let s = Math.max(-1, Math.min(1, channelData[i])); // 그래서 1보다 작은지 -1보다 큰지 체크
                        int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF; // Float32를 Int16로 변환 
                    }                                                     //-1.0 → -32768 (0x8000), 1.0 → 32767 (0x7FFF)
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
