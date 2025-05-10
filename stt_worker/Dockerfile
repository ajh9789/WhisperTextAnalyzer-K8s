# ✅ Python 3.9 base image
FROM python:3.9

# ✅ 컨테이너 작업 디렉토리
WORKDIR /app

# ✅ 프로젝트 코드 복사
COPY . .

# ✅ requirements.txt 복사 (상위 폴더에 requirements.txt 있을 경우)
COPY requirements.txt .

# ✅ pip 최신화 (버전 mismatch 방지)
RUN pip install --upgrade pip

# ✅ 일반 requirements 설치 + torch CUDA 12.1 wheel 추가 설치
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install torch==2.5.1+cu121 -f https://download.pytorch.org/whl/cu121

# ✅ 기본 실행 명령어
#    (각 폴더에 맞게 파일명만 바꿔줌)
CMD ["python", "stt_worker.py"]