# ✅ 개선 listener.py (최소 변경)
import redis
import os
import time

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CHANNELS = ["text_channel", "result_channel"]

def connect_redis():
    """Redis 연결 시도 (재시도 포함)"""
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
            r.ping()
            print(f"✅ Redis 연결 성공 → {REDIS_HOST}:{REDIS_PORT}")
            return r
        except redis.ConnectionError:
            print(f"❌ Redis 연결 실패... 3초 후 재시도 ({REDIS_HOST}:{REDIS_PORT})")
            time.sleep(3)

def listen_channels():
    """STT + 분석 결과 실시간 구독"""
    r = connect_redis()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(*CHANNELS)

    print(f"\n📢 [listener] {CHANNELS} 구독 대기 중...\n")

    try:
        for message in pubsub.listen():
            data = message['data']
            channel = message['channel'].decode()
            now = time.strftime('%Y-%m-%d %H:%M:%S')

            try:
                text = data.decode()
                # ✅ ✅ ✅ text_channel 결과는 눈에 띄게 + 즉시 확인 가능
                if channel == "text_channel":
                    print(f"\n📝 [STT] {now}\n{text}\n")
                elif channel == "result_channel":
                    print(f"🎯 [{now}] 감정 분석 → {text}")
            except Exception:
                print(f"⚠️ 디코딩 오류 ({channel}): {data}")

    except KeyboardInterrupt:
        print("\n🛑 listener 중단됨 (Ctrl+C)")
    except Exception as e:
        print(f"❌ listener 예외: {e}")

if __name__ == "__main__":
    listen_channels()
