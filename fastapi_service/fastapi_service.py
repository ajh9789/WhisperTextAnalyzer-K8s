import os
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from celery import Celery

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
celery = Celery(broker=f"redis://{REDIS_HOST}:6379/0")

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
            <div id="people">연결 인원: 0/2</div>
        </div>
        <div id="log"></div>
        <div id="stats">👍 0% 0회 | 0회 0% 👎</div>

        <script>
            let ws = null;
            let log = document.getElementById("log");
            let stats = document.getElementById("stats");
            let people = document.getElementById("people");
            let positive = 0, negative = 0;

            document.getElementById("startButton").onclick = async function() {
                ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");

                ws.onopen = () => console.log("✅ WebSocket 연결 성공");
                ws.onclose = () => console.log("❌ WebSocket 연결 종료");

                ws.onmessage = function(event) {
                    var data = event.data;
                    if (data.startsWith("PEOPLE:")) {
                        people.textContent = "연결 인원: " + data.replace("PEOPLE:", "");
                        return;
                    }
                    var div = document.createElement("div");
                    div.textContent = data;
                    log.appendChild(div);
                    log.scrollTop = log.scrollHeight;

                    if (data.includes("긍정")) positive++;
                    else if (data.includes("부정")) negative++;

                    var total = positive + negative;
                    var pos = total ? Math.round((positive / total) * 100) : 0;
                    var neg = total ? Math.round((negative / total) * 100) : 0;
                    stats.textContent = `👍 ${pos}% ${positive}회 | ${negative}회 ${neg}% 👎`;
                };

                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    console.log("🎧 getUserMedia 성공");

                    const ctx = new AudioContext({ sampleRate: 16000 });
                    const blob = new Blob([document.querySelector('script[type="worklet"]').textContent], { type: 'application/javascript' });
                    const blobURL = URL.createObjectURL(blob);
                    await ctx.audioWorklet.addModule(blobURL);

                    const src = ctx.createMediaStreamSource(stream);
                    const worklet = new AudioWorkletNode(ctx, 'audio-processor');

                    worklet.port.onmessage = (e) => {
                        console.log("🎙️ Audio chunk 전달:", e.data.byteLength, "bytes");
                        console.log("ws.readyState:", ws.readyState);
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

                        // ✅ 잡음제거를 위해 energy filter 추가 (VAD)
                        let energy = 0;
                        for (let i = 0; i < channelData.length; i++) {
                            energy += Math.abs(channelData[i]);
                        }
                        energy = energy / channelData.length;

                        if (energy < 0.00005) {
                        // ✅ 무음 frame → 건너뜀
                            return true;
                        }

                        // ✅ 정상 frame → main thread로 전달
                        this.port.postMessage(channelData.buffer, [channelData.buffer]);
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
    try:
        print("✅ WebSocket 연결 요청")
        r.ping()
    except redis.ConnectionError:
        await websocket.close()
        print("❌ Redis 연결 실패 - WebSocket 종료")
        return

    await websocket.accept()
    print("✅ WebSocket 연결 수락")
    connected_users.add(websocket)

    try:
        while True:
            # ✅ 핵심 수정: receive_bytes로 바로 받기
            audio_chunk = await websocket.receive_bytes()
            print(f"🎧 WebSocket에서 binary data 수신: {len(audio_chunk)} bytes")
            celery.send_task("stt_worker.transcribe_audio", args=[audio_chunk])
            print("🎯 Redis audio_queue에 push, stt_worker 호출 완료")
    except WebSocketDisconnect:
        print("❌ WebSocket 연결 끊김")
    except Exception as e:
        print(f"❌ WebSocket receive error: {e}")
    finally:
        connected_users.remove(websocket)