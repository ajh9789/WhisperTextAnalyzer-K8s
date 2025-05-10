FROM python:3.9

WORKDIR /app

# ✅ 프로젝트 코드 복사
COPY . .

# ✅ pip 최신화 (버전 mismatch 방지)
RUN pip install --upgrade pip

# ✅ 반드시 whisper + torch를 먼저 고정 설치 (openai-whisper가 자동으로 최신 torch 설치 막기)
RUN pip install torch==2.5.1 -f https://download.pytorch.org/whl/cu121 \
 && pip install openai-whisper==20240930

# ✅ 나머지 requirements 설치 (torch 제외, 주석 처리 상태로)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 기본 실행 명령어
#    (각 폴더에 맞게 파일명만 바꿔줌)
CMD ["python", "analyzer_worker.py"]