# ========================
# 🎙️ Whisper Text Analyzer - Listener 서비스
# 🎙️ text_channel + result_channel 실시간 구독 + 콘솔 출력
# ========================

import redis
import os
import time
import traceback

# ========================
# 🎯 Redis 연결 설정
# ========================

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# 구독할 Redis PubSub 채널 목록
CHANNELS = ["text_channel", "result_channel"]

def connect_redis():
    """
    Redis 연결 및 client 반환
    """
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    print(f"✅ listener 연결 Redis host: {REDIS_HOST}")
    return r

def listen_channels():
    """
    Redis PubSub listener: text_channel + result_channel 구독
    """
    r = connect_redis()
    pubsub = r.pubsub()
    pubsub.subscribe(*CHANNELS)  # ⭐ 2개 채널 동시 구독

    try:
        while True:
            # PubSub 메시지 polling
            message = pubsub.get_message(timeout=1)
            if message and message['type'] == 'message':
                channel = message['channel']
                data = message['data']

                # bytes → str 변환
                channel_name = channel.decode() if isinstance(channel, bytes) else str(channel)
                data_str = data.decode(errors='replace') if isinstance(data, bytes) else str(data)

                # 결과 구분 출력
                if channel_name == "text_channel":
                    print(f"🎙️ [STT 결과] {data_str}")
                elif channel_name == "result_channel":
                    print(f"📊 [분석 결과] {data_str}")

            time.sleep(0.01)  # CPU 부하 방지

    except Exception as e:
        print(f"❌ listener 예외: {e}\n{traceback.format_exc()}")

# ========================
# 🎯 Entry Point
# ========================

if __name__ == "__main__":
    listen_channels()
