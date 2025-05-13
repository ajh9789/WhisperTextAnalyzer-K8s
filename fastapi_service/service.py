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
            var ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
            var log = document.getElementById("log");
            var stats = document.getElementById("stats");
            var people = document.getElementById("people");
            var positive = 0, negative = 0;

            document.getElementById("startButton").onclick = function() {
                navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream) {
                    const audioContext = new AudioContext();
                    const source = audioContext.createMediaStreamSource(stream);
                    const processor = audioContext.createScriptProcessor(4096, 1, 1);

                    source.connect(processor);
                    processor.connect(audioContext.destination);

                    processor.onaudioprocess = function(e) {
                        var input = e.inputBuffer.getChannelData(0);
                        var buffer = encodeWAV(input, audioContext.sampleRate);
                        if (ws.readyState === WebSocket.OPEN) ws.send(buffer);
                    };
                });
            };

            function encodeWAV(samples, rate) {
                var buffer = new ArrayBuffer(44 + samples.length * 2);
                var view = new DataView(buffer);

                function writeStr(v, o, s) { for (var i = 0; i < s.length; i++) v.setUint8(o+i, s.charCodeAt(i)); }

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

                var offset = 44;
                for (var i = 0; i < samples.length; i++, offset += 2) {
                    var s = Math.max(-1, Math.min(1, samples[i]));
                    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                }

                return buffer;
            }

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

            ws.onclose = function() {
                var div = document.createElement("div");
                div.textContent = "[Disconnected]";
                div.style.color = "red";
                log.appendChild(div);
            };
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
            await websocket.send_text(f"Audio chunk size: {len(data)} bytes")
    except WebSocketDisconnect:
        pass
    finally:
        connected_users.remove(websocket)