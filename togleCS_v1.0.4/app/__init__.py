from flask import Flask
from flask_session import Session
from datetime import datetime, timedelta
from app import config
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers import SchedulerNotRunningError
import logging
import atexit
import requests


def create_app():
    app = Flask(__name__)
    app.secret_key = "12345"

    # Flask-Session 설정
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = "./flask_session"
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)
    Session(app)

    # config 등록
    app.config.from_object(config)

    # Blueprint 등록
    from app.routes.index import index_bp
    from app.routes.togle import togle_bp
    from app.routes.review import review_bp
    from app.routes.talktalk import talktalk_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(togle_bp, url_prefix="/togle")
    app.register_blueprint(review_bp, url_prefix="/review")
    app.register_blueprint(talktalk_bp, url_prefix="/talktalk")

    # APScheduler 설정
    scheduler = start_scheduler()
    app.scheduler = scheduler

    # Flask 종료 시 스케줄러 안전 종료
    atexit.register(lambda: safe_shutdown_scheduler(app.scheduler))

    return app


# 🧹 안전한 스케줄러 종료
def safe_shutdown_scheduler(scheduler):
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            logging.info("Scheduler safely shut down.")
        else:
            logging.info("Scheduler already stopped.")
    except SchedulerNotRunningError:
        logging.warning("Scheduler was not running.")
    except Exception as e:
        logging.error(f"Error shutting down scheduler: {e}")


# 🚀 자동 실행: 미답변 페이지 이동 및 답변창 띄우기
def auto_open_togle_prompt():
    from app.drivers.chromedriver import set_chromedriver
    from app.services.togleService import togle_macro, search_element
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    driver = None
    try:
        print("🚀 자동 실행 시작:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        driver = set_chromedriver()

        # 1️⃣ Togle 접속 및 로그인
        togle_macro(driver)
        print("✅ Togle 로그인 완료")

        # 2️⃣ 미답변 문의 페이지 이동
        search_element(driver, By.XPATH, "//div[normalize-space(text())='미답변 문의']", "click")
        print("📥 미답변 문의 탭 클릭 완료")
        time.sleep(5)

        # 3️⃣ 미답변 리스트 확인
        try:
            list_div = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='ag-center-cols-container']"))
            )
            rows = list_div.find_elements(By.XPATH, ".//div[@role='row']")
        except Exception:
            rows = []

        # 4️⃣ 미답변 글이 없을 경우 → Flask 페이지로 이동
        if not rows:
            print("⚪ 미답변 글이 없습니다 → unansweredView 페이지로 이동합니다.")
            driver.get("http://127.0.0.1:5005/togle/unansweredView")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@id='get_unanswered']"))
            )
            print("✅ unansweredView 페이지로 이동 완료 및 버튼 로딩 완료.")
            while True:
                time.sleep(60)
            return

        # 5️⃣ 첫 번째 미답변 글 클릭
        rows[0].click()
        print("🟢 첫 번째 미답변 글 클릭 완료 → 답변창 열림")
        time.sleep(3)

        # 6️⃣ “답변제목” input이 보이면 성공
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='답변제목']"))
        )
        print("📝 답변 입력창이 정상적으로 열렸습니다 (프롬프트 표시 완료).")

        print("⏸️ 자동 입력/전송은 수행하지 않습니다. 브라우저를 닫지 않고 대기 중입니다.")
        while True:
            time.sleep(60)

    except Exception as e:
        print(f"❌ 자동화 중 오류 발생: {e}")

    finally:
        if driver:
            print("🧹 브라우저 종료 중...")
            driver.quit()


# 🕒 스케줄러 설정
def start_scheduler():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    scheduler = BackgroundScheduler()
    scheduler.add_listener(log_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # 하루마다 자동 실행 (테스트 시 minutes=1로 변경 가능)
    scheduler.add_job(
        auto_open_togle_prompt,
        trigger="interval",
        days=1,
        start_date=datetime.now() + timedelta(seconds=10),
        id="daily_prompt_open",
        replace_existing=True,
    )

    scheduler.start()
    logging.info("✅ Scheduler started successfully (daily prompt opener).")
    return scheduler


# 🪵 이벤트 로그
def log_event(event):
    if event.code == EVENT_JOB_EXECUTED:
        logging.info(f"Job {event.job_id} executed at {event.scheduled_run_time}")
    elif event.code == EVENT_JOB_ERROR:
        logging.error(f"Job {event.job_id} failed at {event.scheduled_run_time}")
