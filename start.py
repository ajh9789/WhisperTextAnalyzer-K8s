# ========================
# ✅ 루트/main.py 개선 버전
# ========================

import subprocess
import time
import sys
import os

def start_redis_container():
    try:
        print("Redis 컨테이너 시작 시도...")
        subprocess.run(["docker", "start", "my-redis"], check=True)
        print("기존 Redis 컨테이너 실행됨.")
    except subprocess.CalledProcessError:
        print("기존 Redis 컨테이너 없음 → 새로 생성")
        try:
            subprocess.run([
                "docker", "run", "-d",
                "--name", "my-redis",
                "-p", "6379:6379",
                "redis:latest"
            ], check=True)
            print("새 Redis 컨테이너 생성 및 실행됨.")
        except subprocess.CalledProcessError as e:
            print(f"Redis 컨테이너 생성 실패: {e}")
            sys.exit(1)

def start_all_services():
    start_redis_container()
    time.sleep(5)

    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    python_exe = sys.executable

    try:
        subprocess.Popen([python_exe, os.path.join("recorder", "recorder.py")], creationflags=flags)
        subprocess.Popen([
            python_exe, "-m", "celery", "-A", "stt_worker", "worker",
            "--loglevel=info", "--pool=solo", "-n", "stt_worker1"
        ], creationflags=flags)
        subprocess.Popen([
            python_exe, "-m", "celery", "-A", "stt_worker", "worker",
            "--loglevel=info", "--pool=solo", "-n", "stt_worker2"
        ], creationflags=flags)
        subprocess.Popen([python_exe, os.path.join("listener", "listener.py")], creationflags=flags)
        subprocess.Popen([python_exe, os.path.join("analyzer_worker", "analyzer_worker.py")], creationflags=flags)

        print("전체 시스템 정상 실행 완료.")

    except Exception as e:
        print(f"서비스 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_all_services()
