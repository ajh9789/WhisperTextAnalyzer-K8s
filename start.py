# =============================================
# ✅ start/main.py (local test 전용)
# =============================================

import subprocess
import time
import sys
import os

def start_redis_container():
    try:
        subprocess.run(["docker", "start", "my-redis"], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["docker", "run", "-d", "--name", "my-redis", "-p", "6379:6379", "redis:latest"], check=True)

def start_all_services():
    start_redis_container()
    time.sleep(5)
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    python_exe = sys.executable

    subprocess.Popen([python_exe, os.path.join("recorder", "recorder.py")], creationflags=flags)
    subprocess.Popen([python_exe, "-m", "celery", "-A", "stt_worker", "worker", "--loglevel=info", "--concurrency=1", "--pool=solo", "-n", "stt_worker1"], creationflags=flags)
    subprocess.Popen([python_exe, "-m", "celery", "-A", "stt_worker", "worker", "--loglevel=info", "--concurrency=1", "--pool=solo", "-n", "stt_worker2"], creationflags=flags)
    subprocess.Popen([python_exe, "-m", "celery", "-A", "analyzer_worker", "worker", "--loglevel=info", "--concurrency=1", "--pool=solo", "-n", "analyzer_worker1"], creationflags=flags)
    subprocess.Popen([python_exe, os.path.join("listener", "listener.py")], creationflags=flags)

if __name__ == "__main__":
    start_all_services()