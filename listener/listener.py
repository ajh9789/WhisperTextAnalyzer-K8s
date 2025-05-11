# ✅ 실전 디버깅 강화 listener.py
import redis
import os
import time
import traceback

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CHANNELS = ["text_channel", "result_channel"]

def connect_redis():
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_timeout=5)
            r.ping()
            print(f"✅ Redis 연결 성공 → {REDIS_HOST}:{REDIS_PORT}")
            return r
        except Exception as e:
            print(f"❌ Redis 연결 실패: {e}\n3초 후 재시도...")
            time.sleep(3)

def listen_channels():
    r = connect_redis()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(*CHANNELS)
    print(f"\n🎙️ 실시간 STT + 분석 결과 구독 시작 → {CHANNELS}\n")

    try:
        last_heartbeat = time.time()

        for message in pubsub.listen():
            # ✅ 5초마다 heartbeat 출력
            if time.time() - last_heartbeat > 5:
                print("💓 listener 동작 중...")
                last_heartbeat = time.time()

            try:
                if message['type'] != 'message':
                    continue

                channel = message['channel']
                data = message['data']

                # ✅ decode 방지 + debug 출력
                channel_name = channel.decode() if isinstance(channel, bytes) else str(channel)
                data_str = data.decode(errors='replace') if isinstance(data, bytes) else str(data)

                now = time.strftime('%Y-%m-%d %H:%M:%S')

                if channel_name == "text_channel":
                    print(f"\n📝 [STT 결과] {now}\n{data_str}\n")
                elif channel_name == "result_channel":
                    print(f"🎯 [감정 분석] {now} → {data_str}")
                else:
                    print(f"❔ [알 수 없는 채널] {channel_name}: {data_str}")

            except Exception as e:
                print("❌ 메시지 처리 중 예외 발생:")
                traceback.print_exc()

    except KeyboardInterrupt:
        print("\n🛑 listener 수동 종료됨 (Ctrl+C)")
    except Exception as e:
        print(f"❌ listener 전체 예외: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    listen_channels()