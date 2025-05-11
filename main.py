import subprocess
import time
import sys
import os

def start_redis_container():
    """✅ Redis 컨테이너 실행 (없으면 새로 생성)"""
    try:
        print("✅ Redis 컨테이너 시작 시도...")
        subprocess.run(["docker", "start", "my-redis"], check=True)
        print("✅ 기존 Redis 컨테이너 실행됨.")
    except subprocess.CalledProcessError:
        print("⚠️ 기존 Redis 컨테이너 없음 → 새로 생성")
        try:
            subprocess.run([
                "docker", "run", "-d",
                "--name", "my-redis",
                "-p", "6379:6379",
                "redis:latest"
            ], check=True)
            print("✅ 새 Redis 컨테이너 생성 및 실행됨.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Redis 컨테이너 생성 실패: {e}")
            sys.exit(1)

def start_all_services():
    """✅ 전체 서비스 실행"""
    start_redis_container()
    time.sleep(3)  # Redis 부팅 대기

    # ✅ Windows / Linux 호환 처리
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_CONSOLE

    python_exe = sys.executable  # 현재 실행 중인 Python (venv 포함)

    try:
        # 🎙 recorder
        subprocess.Popen(
            [python_exe, os.path.join("recorder", "recorder.py")],
            creationflags=flags
        )
        print("✅ recorder 실행됨.")

        # 🎧 stt_worker 1 (concurrency=1, worker name = stt_worker1)
        subprocess.Popen(
            [python_exe, "-m", "celery", "-A", "stt_worker", "worker",
             "--loglevel=info", "--concurrency=1", "-n", "stt_worker1"],
            creationflags=flags
        )
        print("✅ stt_worker1 실행됨.")

        # 🎧 stt_worker 2 (concurrency=1, worker name = stt_worker2)
        subprocess.Popen(
            [python_exe, "-m", "celery", "-A", "stt_worker", "worker",
             "--loglevel=info", "--concurrency=1", "-n", "stt_worker2"],
            creationflags=flags
        )
        print("✅ stt_worker2 실행됨.")

        # 💡 analyzer_worker (celery worker)
        subprocess.Popen(
            [python_exe, "-m", "celery", "-A", "analyzer_worker", "worker",
             "--loglevel=info", "--concurrency=1", "-n", "analyzer_worker1"],
            creationflags=flags
        )
        print("✅ analyzer_worker 실행됨.")

        # 📢 listener
        subprocess.Popen(
            [python_exe, os.path.join("listener", "listener.py")],
            creationflags=flags
        )
        print("✅ result_listener 실행됨.")

        print("\n🎉 전체 시스템 정상 실행 완료.")
        print("🪄 각각의 콘솔에서 서비스 상태를 확인하세요.\n")

    except Exception as e:
        print(f"❌ 서비스 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_all_services()