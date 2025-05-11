# ========================
# 🎙️ Whisper Text Analyzer - STT Worker Dockerfile
# ========================

FROM python:3.9

WORKDIR /app

# ✅ 서비스 코드 복사
COPY . .

COPY requirements.txt .

# ✅ pip 최신화
RUN pip install --upgrade pip

# ✅ whisper + torch 고정 설치 (GPU 사용 가능 버전)
RUN pip install torch==2.5.1 -f https://download.pytorch.org/whl/cu121 \
 && pip install openai-whisper==20240930

# ✅ 나머지 requirements 설치
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 기본 실행 명령어는 compose에서 지정
