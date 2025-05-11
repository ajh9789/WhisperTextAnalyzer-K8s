# ✅ listener/result_listener.py : redis text_channel + result_channel → 실시간 출력

import redis
import os
import time

# =============================
# 🎯 환경 설정
# =============================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

def listen_channels():
    """
    📢 redis text_channel + result_channel 실시간 구독
    → STT 텍스트 + 감정 분석 결과 동시 출력
    """
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        pubsub = r.pubsub()
        pubsub.subscribe("text_channel", "result_channel")  # ✅ 두 채널 동시 구독
        print("\n📢 [listener] STT 텍스트 + 분석 결과 대기 중...\n")

        for message in pubsub.listen():
            if message['type'] != 'message':
                continue

            data = message['data']
            try:
                text = data.decode()
                channel = message['channel'].decode()
                now = time.strftime('%Y-%m-%d %H:%M:%S')

                if channel == "text_channel":
                    print(f"📝 [{now}] STT 텍스트 → {text}")
                elif channel == "result_channel":
                    print(f"🎯 [{now}] 감정 분석 → {text}")

            except Exception:
                print("⚠️ 디코딩 오류:", data)

    except redis.ConnectionError:
        print("❌ Redis 연결 실패! 서버 확인.")
    except KeyboardInterrupt:
        print("\n🛑 listener 중단됨 (Ctrl+C)")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

if __name__ == "__main__":
    listen_channels()
