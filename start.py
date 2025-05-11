# ========================
# 🎯 Whisper Text Analyzer - 루트 실행 스크립트 (Local test 전용)
# 🎯 컨테이너 기반 서비스 전체를 순차적으로 실행
# ========================

import subprocess
import time
import sys
import os

def start_redis_container():
    """
    Docker로 Redis 컨테이너를 실행.
    (이미 있으면 재사용, 없으면 새로 생성)
    """
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
    """
    전체 Python 서비스 프로세스를 실행
    (recorder + STT worker 2개 + listener + analyzer)
    """
    start_redis_container()
    time.sleep(5)  # Redis 컨테이너 안정화 대기

    # Windows 환경이면 새 콘솔로 실행
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    python_exe = sys.executable

    try:
        # 🎙️ Recorder 서비스
        subprocess.Popen([python_exe, os.path.join("recorder", "recorder.py")], creationflags=flags)

        # 📝 STT Worker (2개 실행 → 다중 작업 처리)
        subprocess.Popen([
            python_exe, "-m", "celery", "-A", "stt_worker", "worker",
            "--loglevel=info", "--concurrency=1", "--pool=solo", "-n", "stt_worker1"
        ], creationflags=flags)

        subprocess.Popen([
            python_exe, "-m", "celery", "-A", "stt_worker", "worker",
            "--loglevel=info", "--concurrency=1", "--pool=solo", "-n", "stt_worker2"
        ], creationflags=flags)

        # 🖥️ Listener + Analyzer
        subprocess.Popen([python_exe, os.path.join("listener", "listener.py")], creationflags=flags)
        subprocess.Popen([python_exe, os.path.join("analyzer_worker", "analyzer_worker.py")], creationflags=flags)

        print("✅ 전체 시스템 정상 실행 완료.")

    except Exception as e:
        print(f"❌ 서비스 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_all_services()
