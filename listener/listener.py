# =============================================
# ✅ listener/listener.py
# =============================================

import redis
import os
import time

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
CHANNELS = ["text_channel", "result_channel"]

def listen_channels():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    pubsub = r.pubsub()
    pubsub.subscribe(*CHANNELS)

    while True:
        message = pubsub.get_message(timeout=1)
        if message and message['type'] == 'message':
            channel = message['channel']
            data = message['data']
            channel_name = channel.decode() if isinstance(channel, bytes) else str(channel)
            data_str = data.decode(errors='replace') if isinstance(data, bytes) else str(data)

            if channel_name == "text_channel":
                print(f"[STT 결과] {data_str}")
            elif channel_name == "result_channel":
                print(f"[분석 결과] {data_str}")
        time.sleep(0.01)

if __name__ == "__main__":
    listen_channels()