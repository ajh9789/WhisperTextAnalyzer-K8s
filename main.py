import subprocess
import time
import sys

def start_redis_container():
    """
    ✅ Redis 컨테이너를 실행하는 함수
    - 이미 존재하는 경우 docker start
    - 없으면 docker run으로 새로 생성
    """
    try:
        print("✅ Redis 컨테이너 시작 시도...")
        subprocess.run(["docker", "start", "my-redis"], check=True)
        print("✅ 기존 Redis 컨테이너 실행됨.")
    except subprocess.CalledProcessError:
        # 컨테이너가 없을 경우 새로 생성
        print("⚠️ 기존 Redis 컨테이너 없음 → 새로 생성")
        try:
            subprocess.run([
                "docker", "run", "-d",
                "--name", "my-redis",
                "-p", "6379:6379",
                "redis:latest"
            ], check=True)
            print("✅ 새 Redis 컨테이너가 생성 및 실행됨.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Redis 컨테이너 생성 실패: {e}")
            print("👉 Docker Desktop이 실행 중인지 확인하세요.")
            sys.exit(1)

def start_all_services():
    """
    ✅ 전체 서비스 실행 함수
    - Redis → celery workers → listener → recorder 순서로 실행
    - Windows에서는 각각을 새 콘솔 창으로 실행
    """
    start_redis_container()
    # Redis 초기화 대기
    time.sleep(3)

    flags = subprocess.CREATE_NEW_CONSOLE  # Windows: 새 콘솔 창으로 실행

    try:
        subprocess.Popen(
            ["celery", "-A","stt_worker", "worker", "--loglevel=info", "--concurrency=2"],
            creationflags=flags
        )
        print("✅ stt_worker 실행됨.")

        subprocess.Popen(
            ["celery", "-A", "analyzer_worker", "worker", "--loglevel=info"],
            creationflags=flags
        )
        print("✅ analyzer_worker 실행됨.")

        subprocess.Popen(
            ["python", "analyzer_worker/result_listener.py"],
            creationflags=flags
        )
        print("✅ result_listener 실행됨.")

        subprocess.Popen(
            ["python", "recorder/recorder.py"],
            creationflags=flags
        )
        print("✅ recorder 실행됨.")

        print("\n🎉 전체 시스템 정상 실행 완료.")
        print("🪄 각각의 독립 콘솔에서 서비스 상태를 모니터링하세요.\n")

    except Exception as e:
        print(f"❌ 서비스 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    """
    ✅ 프로그램 진입점
    - main.py를 직접 실행했을 때만 start_all_services() 호출
    """
    start_all_services()