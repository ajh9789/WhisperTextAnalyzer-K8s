# ========================
# 🎙️ Whisper Text Analyzer - Recorder Dockerfile
# ========================

FROM python:3.9

WORKDIR /app

# ✅ 서비스 코드 복사
COPY . .

COPY requirements.txt .

# ✅ pip 최신화
RUN pip install --upgrade pip

# ✅ 필수 requirements 설치
RUN pip install --no-cache-dir -r requirements.txt
