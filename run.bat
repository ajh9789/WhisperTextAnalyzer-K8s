# =============================================
# ✅ Windows 호환 최종 run_all.bat (celery version)
# =============================================

@echo off
echo ============================================
echo 🎙️ WhisperTextAnalyzer FINAL Celery System Start (Windows Safe)
echo ============================================

echo 🎙️ Starting Recorder
start cmd /k "python recorder/recorder.py"

echo 🎙️ Starting STT Worker 1 (celery)
start cmd /k "cd stt_worker && python -m celery -A stt_worker worker --loglevel=info --concurrency=1 --pool=solo"

echo 🎙️ Starting STT Worker 2 (celery)
start cmd /k "cd stt_worker && python -m celery -A stt_worker worker --loglevel=info --concurrency=1 --pool=solo"

echo 🎙️ Starting Analyzer Worker (celery)
start cmd /k "cd analyzer_worker && python -m celery -A analyzer_worker worker --loglevel=info --concurrency=1 --pool=solo"

echo 🎙️ Starting Listener
start cmd /k "python listener/listener.py"

echo ✅ All components launched. Ready for DEMO!
pause
