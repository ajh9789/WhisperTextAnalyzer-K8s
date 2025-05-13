import os
import redis
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

service = FastAPI()

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
        body { font-family: Arial; display: flex; flex-direction: column; height: 100vh; margin: 0; }
        #header { background: #333; color: white; padding: 10px; display: flex; justify-content: space-between; }
        #log { flex: 1; overflow-y: auto; padding: 10px; }
        #stats { background: #f2f2f2; padding: 10px; text-align: center; }
        button { padding: 8px 16px; cursor: pointer; }
    </style>
</head>
<body>
<div id="header">
    <div>🎙️ 실시간 감정 분석</div>
    <button onclick="startRecording()">Start</button>
</div>
<div id="log"></div>
<div id="stats">👍 0% 0회 | 0회 0% 👎</div>
<script>
let ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
let log = document.getElementById("log");
let stats = document.getElementById("stats");
let positive = 0, negative = 0;

ws.onmessage = e => {
    let data = e.data;
    let div = document.createElement("div");
    div.textContent = data;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;

    if (data.includes("긍정")) positive++;
    else if (data.includes("부정")) negative++;

    let total = positive + negative;
    let pos = total ? Math.round((positive / total) * 100) : 0;
    let neg = total ? Math.round((negative / total) * 100) : 0;
    stats.textContent = `👍 ${pos}% ${positive}회 | ${negative}회 ${neg}% 👎`;
};

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        let ctx = new AudioContext();
        let source = ctx.createMediaStreamSource(stream);
        let processor = ctx.createScriptProcessor(4096, 1, 1);

        source.connect(processor);
        processor.connect(ctx.destination);

        processor.onaudioprocess = e => {
            let input = e.inputBuffer.getChannelData(0);
            let buffer = encodeWAV(input, ctx.sampleRate);
            if (ws.readyState === WebSocket.OPEN) ws.send(buffer);
        };
    });
}
<!-- webm형식 데이터를 wav로 변환 -->
function encodeWAV(samples, rate) {
    let buffer = new ArrayBuffer(44 + samples.length * 2);
    let view = new DataView(buffer);

    function writeStr(v, o, s) { for (let i = 0; i < s.length; i++) v.setUint8(o+i, s.charCodeAt(i)); }

    writeStr(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(view, 8, 'WAVEfmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, rate, true);
    view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return buffer;
}
</script>
</body>
</html>
"""

@service.get("/")
async def get():
    return HTMLResponse(html)

@service.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        r.ping()
    except redis.ConnectionError:
        await websocket.close()
        return

    await websocket.accept()
    connected_users.add(websocket)

    try:
        while True:
            data = await websocket.receive_bytes()
            r.lpush("audio_queue", data)
            await websocket.send_text(f"chunk: {len(data)} bytes")
    except WebSocketDisconnect:
        pass
    finally:
        connected_users.remove(websocket)
