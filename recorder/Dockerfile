FROM python:3.9

WORKDIR /app

# ✅ 서비스 코드만 복사
COPY . .

# ✅ 루트 requirements.txt 복사 (루트 build 시에는 안 해도 됨. 폴더 build 시 필수)
COPY requirements.txt .

# ✅ pip 최신화
RUN pip install --upgrade pip

# ✅ whisper + torch 고정 설치
RUN pip install torch==2.5.1 -f https://download.pytorch.org/whl/cu121 \
 && pip install openai-whisper==20240930

# ✅ 나머지 requirements 설치
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 기본 실행 명령어 (서비스마다 파일명만 다르게)
CMD ["python", "recorder.py"]