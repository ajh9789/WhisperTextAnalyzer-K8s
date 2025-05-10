# ✅ Python 3.9 base image
FROM python:3.9

# ✅ 컨테이너 작업 디렉토리
WORKDIR /app

# ✅ 프로젝트 코드 복사
COPY . .

# ✅ requirements.txt 복사 (상위 폴더에 requirements.txt 있을 경우)
COPY requirements.txt .

# ✅ 필수 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 기본 실행 명령어
#    (각 폴더에 맞게 파일명만 바꿔줌)
CMD ["python", "analyer_worker.py"]