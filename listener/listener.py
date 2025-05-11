# ========================
# ✅ listener/listener.py 개선 버전
# ========================

import redis
import os
import time
import traceback

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CHANNELS = ["text_channel", "result_channel"]

def connect_redis():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    print(f"listener 연결 Redis host: {REDIS_HOST}")
    return r

def listen_channels():
    r = connect_redis()
    pubsub = r.pubsub()
    pubsub.subscribe(*CHANNELS)

    try:
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

    except Exception as e:
        print(f"listener 예외: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    listen_channels()