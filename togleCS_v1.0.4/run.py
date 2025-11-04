import sys
import os
import threading
import time
import webbrowser
import signal

# app 모듈 import
from app import create_app

# 👉 PyInstaller 실행 시 _MEIPASS 경로 대응 (배포용 필수)
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

# Flask 앱 생성
app = create_app()

# Flask 서버 실행 함수
def run_flask():
    app.run(host="0.0.0.0", port=5005, debug=False, use_reloader=False)

# 종료 핸들러 (Ctrl+C)
def signal_handler(sig, frame):
    print("\n[종료] Ctrl+C 로 서버를 종료합니다.")
    sys.exit(0)

if __name__ == "__main__":
    # Ctrl+C 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    # Flask 서버 백그라운드 실행
    threading.Thread(target=run_flask, daemon=True).start()

    # 브라우저 자동 오픈
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5005/")

    # 콘솔 유지 (배포용)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
