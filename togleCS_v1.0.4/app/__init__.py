from flask import Flask, session, flash, redirect, url_for, request, abort
from flask_session import Session
from flask_cors import CORS
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers import SchedulerNotRunningError
from flask_login import LoginManager, logout_user, current_user
import logging
import atexit
import uuid
import os

# ✅ db는 models에서 import
from app.models import db
from app import config

# 프로젝트 최상위 폴더 기준
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
IP_BLOCK_FILE = os.path.join(LOG_DIR, "ip_blocks.txt")
os.makedirs(LOG_DIR, exist_ok=True)

login_manager = LoginManager()
unanswered_data = []  # 기존 코드 호환용

# ✅ 로거 기본 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ==========================
# Flask-Login user_loader
# ==========================
from app.models.user_model import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================
# IP 차단 로드
# ==========================
def load_blocked_ips():
    """IP 차단 목록 로드"""
    blocked = set()
    if os.path.exists(IP_BLOCK_FILE):
        with open(IP_BLOCK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        blocked.add(parts[1])
    return blocked


# ==========================
# 스케줄러 안전 종료
# ==========================
def safe_shutdown_scheduler(scheduler):
    """스케줄러 안전 종료"""
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler safely shut down.")
    except SchedulerNotRunningError:
        logger.warning("Scheduler was not running.")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")


# ==========================
# 자동 수집 함수
# ==========================
from app.drivers.chromedriver import set_chromedriver
from datetime import datetime
import threading
import time
import queue

# 전역 큐 - 진행 상황을 저장
progress_queue = queue.Queue()

# 전역 진행 상태
current_progress = {
    "step": "idle",
    "status": "idle",
    "message": "",
    "timestamp": ""
}

def send_progress(step, message, status="in_progress"):
    """진행 상황을 업데이트하고 큐에 추가"""
    global current_progress
    progress_data = {
        "step": step,
        "message": message,
        "status": status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    current_progress = progress_data
    progress_queue.put(progress_data)
    logger.info(f"📡 Progress: {message}")

def update_progress(step, message, status="in_progress"):
    print(f"[Progress] step={step}, status={status}, message={message}")
    send_progress(step, message, status)


def set_task_status(step, message, status='running'):
    global task_progress
    task_progress = {
        'step': step,
        'message': message,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }

def get_send():
    """현재 진행 상황 반환"""
    global current_progress
    return current_progress.copy()

import psutil

def kill_all_chrome():
    """백그라운드에서 실행되는 모든 Chrome / ChromeDriver 강제 종료"""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name'].lower()
            if 'chrome.exe' in name or 'chromedriver.exe' in name:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("🧹 모든 Chrome / ChromeDriver 프로세스 종료 완료")

from app.services.togleService import get_unanswered_list2, get_notebookAnswer, notebookLM_update, inquiries_crawling
from app.utils.paths import get_data_dir
from app.services.fileService import append_unique_to_excel, excel_to_pdf
from app.models import save_unanswered_to_db
import requests

def auto_open_togle_prompt(app):
    """답변 완료된 데이터만 크롤링하여 엑셀에 반영하고 PDF로 변환 후 노트북LM 업데이트"""
    with app.app_context():
        driver = None
        try:
            # 1. 드라이버 설정 (필요시 드라이버 설정)
            driver = set_chromedriver()

            # 2. 크롤링: 답변 완료된 미답변 데이터를 필터링
            update_progress("collect", "📥 답변 완료된 문의글을 수집하고 있습니다...", "in_progress")
            result_list = inquiries_crawling(driver)

            # 답변 완료된 데이터만 필터링
            answered_data = [item for item in result_list if item['q_answered']]
            print(f"✅ 답변 완료 {len(answered_data)}개 수집 완료")

            # 3. 엑셀 파일 업데이트
            update_progress("excel_pdf", "📝 엑셀 파일에 데이터를 작성하고 있습니다...", "in_progress")
            base_dir = get_data_dir()
            excel_path = os.path.join(base_dir, "app", "data", "togle_data.xlsx")
            pdf_path = os.path.join(base_dir, "app", "data", "togle_data.pdf")

            # 엑셀에 답변 완료된 데이터를 추가
            append_unique_to_excel(
                data_list=answered_data,
                filename="togle_data.xlsx",
                filepath=excel_path,
                col_mapping={
                    "q_shopping_mall": "쇼핑몰",
                    "q_type": "유형",
                    "q_date": "문의일",
                    "q_answered": "답변여부",
                    "q_writer": "작성자",
                    "q_question": "문의내용",
                    "q_answer": "답변"
                },
                sheetname="답변완료",
                key_fields=["q_date"],
                sort_by="q_date"
            )

            # 엑셀을 PDF로 변환
            excel_to_pdf(
                filepath=excel_path,
                output_path=pdf_path,
                source_sheet="답변완료",
                columns_order=["쇼핑몰", "유형", "문의일", "답변여부", "작성자", "문의내용", "답변"],
                small_headers=["쇼핑몰", "유형", "문의일", "답변여부", "작성자"],
                big_headers=("문의내용", "답변"),
                orientation="landscape",
                repeat_header=True
            )
            update_progress("excel_pdf_done", "✅ 엑셀 파일 및 PDF 생성 완료", "completed")
            time.sleep(1)

            # 4. 노트북LM 업데이트
            send_progress("notebooklm", "📚 노트북LM을 업데이트하고 있습니다...", "in_progress")
            notebookLM_update(filepath=pdf_path)
            send_progress("notebooklm", "✅ 노트북LM 업데이트 완료", "completed")

            # 5. DB 저장
            update_progress("db_save", "💾 데이터베이스에 저장하고 있습니다...", "in_progress")
            db_saved = save_unanswered_to_db(answered_data)

            if db_saved:
                logger.info(f"✅ DB 저장 완료 (답변 포함): {len(answered_data)}개")
                update_progress("db_save_done", f"✅ DB 저장 완료 ({len(answered_data)}개)", "completed")
            else:
                logger.warning("❌ DB 저장 실패")
                update_progress("db_save_error", "❌ DB 저장 실패", "error")
            
            time.sleep(1)

            # 6. 완료
            update_progress("done", "🎉 모든 작업이 완료되었습니다!", "completed")
            logger.info("✅ 자동 수집 작업 완료")

            # 상태 업데이트 (UI에서 마지막 업데이트 시간과 엑셀/PDF 상태를 갱신)
            requests.get('http://127.0.0.1:5005/api/update_status')

        except Exception as e:
            logger.error(f"❌ 자동 수집 중 오류: {e}", exc_info=True)
            update_progress("error", f"❌ 오류 발생: {str(e)}", "error")

        finally:
            # 7. 드라이버 종료
            if driver:
                try:
                    driver.quit()
                    logger.info("✅ 크롬 드라이버 종료 완료")
                except Exception as quit_error:
                    logger.error(f"⚠️ 드라이버 종료 실패: {quit_error}")
            
            # 8. 10초 후 idle 상태로 전환
            def reset_to_idle():
                time.sleep(10)
                if current_progress.get("step") in ["done", "error"]:
                    update_progress("idle", "", "idle")

            threading.Thread(target=reset_to_idle, daemon=True).start()

# def auto_open_togle_prompt(app):
#     """미답변 문의 자동 수집 (이벤트 기반)"""
#     global unanswered_data
    
#     with app.app_context():
#         driver = None
#         try:
#             # 1. 드라이버 설정
#             driver = set_chromedriver()
            
#             # 🚀 작업 시작
#             update_progress("start", "🚀 자동 수집 작업을 시작합니다...", "in_progress")
#             logger.info("🚀 자동 수집 시작: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

#             # 2. 미답변 문의글 수집
#             update_progress("collect", "📥 미답변 문의글을 수집하고 있습니다...", "in_progress")
#             unanswered_list = get_unanswered_list2(driver)
#             unanswered_data = unanswered_list
#             logger.info(f"✅ 미답변 {len(unanswered_list)}개 수집 완료")
#             update_progress("collect_done", f"✅ 미답변 문의 {len(unanswered_list)}개 수집 완료", "completed")
#             time.sleep(1)  # 이벤트 간 간격

#             # 3. 노트북LM 답변 생성
#             update_progress("notebook_answer", "🤖 노트북LM 답변을 생성하고 있습니다...", "in_progress")
#             notebookAnswer_list = get_notebookAnswer(unanswered_list)
#             logger.info(f"✅ 노트북LM 답변 생성 완료: {len(notebookAnswer_list)}개")
#             update_progress("notebook_answer_done", f"✅ 노트북LM 답변 {len(notebookAnswer_list)}개 생성 완료", "completed")
#             time.sleep(1)

#             # 4. 엑셀 업데이트 및 PDF 생성
#             update_progress("excel_pdf", "📝 엑셀 파일에 데이터를 작성하고 있습니다...", "in_progress")
#             base_dir = get_data_dir()
#             excel_path = os.path.join(base_dir, "app", "data", "togle_data.xlsx")
#             pdf_path = os.path.join(base_dir, "app", "data", "togle_data.pdf")

#             # 엑셀에 데이터를 추가
#             append_unique_to_excel(
#                 data_list=unanswered_list,
#                 filename="togle_data.xlsx",
#                 filepath=excel_path,
#                 col_mapping={
#                     "q_shopping_mall": "쇼핑몰",
#                     "q_type": "유형",
#                     "q_date": "문의일",
#                     "q_answered": "답변여부",
#                     "q_writer": "작성자",
#                     "q_question": "문의내용",
#                     "q_answer": "답변"
#                 },
#                 sheetname="전체",
#                 key_fields=["q_date"],
#                 sort_by="q_date"
#             )

#             # 엑셀을 PDF로 변환
#             excel_to_pdf(
#                 filepath=excel_path,
#                 output_path=pdf_path,
#                 source_sheet="전체",
#                 columns_order=["쇼핑몰","유형","문의일","답변여부","작성자","문의내용","답변"],
#                 small_headers=["쇼핑몰","유형","문의일","답변여부","작성자"],
#                 big_headers=("문의내용","답변"),
#                 orientation="landscape",
#                 repeat_header=True
#             )
#             update_progress("excel_pdf_done", "✅ 엑셀 파일 및 PDF 생성 완료", "completed")
#             time.sleep(1)

#             # 5. 노트북LM 업데이트
#             send_progress("notebooklm", "📚 노트북LM을 업데이트하고 있습니다...", "in_progress")
#             notebookLM_update(filepath=pdf_path)
#             send_progress("notebooklm", "✅ 노트북LM 업데이트 완료", "completed")

#             # 6. DB 저장
#             update_progress("db_save", "💾 데이터베이스에 저장하고 있습니다...", "in_progress")
#             db_saved = save_unanswered_to_db(notebookAnswer_list)
            
#             if db_saved:
#                 logger.info(f"✅ DB 저장 완료 (답변 포함): {len(notebookAnswer_list)}개")
#                 update_progress("db_save_done", f"✅ DB 저장 완료 ({len(notebookAnswer_list)}개)", "completed")
#             else:
#                 logger.warning("❌ DB 저장 실패")
#                 update_progress("db_save_error", "❌ DB 저장 실패", "error")
            
#             time.sleep(1)

#             # 7. 완료
#             update_progress("done", "🎉 모든 작업이 완료되었습니다!", "completed")
#             logger.info("✅ 자동 수집 작업 완료")

#         except Exception as e:
#             logger.error(f"❌ 자동 수집 중 오류: {e}", exc_info=True)
#             update_progress("error", f"❌ 오류 발생: {str(e)}", "error")
            
#         finally:
#             # 8. 드라이버 종료
#             if driver:
#                 try:
#                     driver.quit()
#                     logger.info("✅ 크롬 드라이버 종료 완료")
#                 except Exception as quit_error:
#                     logger.error(f"⚠️ 드라이버 종료 실패: {quit_error}")
            
#             # 9. 10초 후 idle 상태로 전환
#             def reset_to_idle():
#                 time.sleep(10)
#                 # 완료 또는 오류인 경우에만 idle로 변경
#                 if current_progress.get("step") in ["done", "error"]:
#                     update_progress("idle", "", "idle")

#             threading.Thread(target=reset_to_idle, daemon=True).start()


# def auto_open_togle_prompt(app):
#     """미답변 문의 자동 수집"""
#     global unanswered_data
#     with app.app_context():
#         try:
#             logger.info("🚀 자동 수집 시작: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#             from app.services.togleService import get_unanswered_list
#             unanswered_list = get_unanswered_list()
#             unanswered_data = unanswered_list
#             logger.info(f"✅ 미답변 {len(unanswered_list)}개 수집 완료")

#             try:
#                 from app.models import save_unanswered_to_db
#                 save_unanswered_to_db(unanswered_list)
#                 logger.info(f"✅ DB 저장 완료: {len(unanswered_list)}개")
#             except Exception as e:
#                 logger.warning(f"⚠️ DB 저장 실패: {e}")

#         except Exception as e:
#             logger.error(f"❌ 자동 수집 중 오류: {e}", exc_info=True)

# PC 서버 환경 속도 체크
import os
import subprocess
import speedtest
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 폴더 없으면 자동 생성
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로
LOG_FILE = os.path.join(LOG_DIR, "network_runtime_log.txt")


def write_log(message):
    """공통 로그 기록 함수"""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")

    # 콘솔에도 출력
    logger.info(message)


def check_network_detail():
    """PING + 속도 측정 결과 기록"""
    write_log("=== 📡 네트워크 상태 체크 시작 ===")

    # ------------------------------------
    # 1) Ping 테스트
    # ------------------------------------
    try:
        result = subprocess.run(
            ["ping", "-n", "4", "8.8.8.8"],   # Windows: 4회 Ping
            capture_output=True,
            text=True,
            timeout=10
        )
        ping_output = result.stdout

        write_log("📌 [PING 결과]\n" + ping_output.replace("\n", " | "))

        # 시간초과 확인
        if "시간 초과" in ping_output or "timed out" in ping_output:
            write_log("🚨 PING TIMEOUT 발생")
            ping_ok = False
        else:
            ping_ok = True

    except Exception as e:
        write_log(f"❌ Ping 테스트 오류: {e}")
        ping_ok = False

    # ------------------------------------
    # 2) Speedtest 속도 측정
    # ------------------------------------
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        ping = st.results.ping
        download = st.download() / 1_000_000   # Mbps 단위 변환
        upload = st.upload() / 1_000_000       # Mbps 단위 변환

        write_log(
            f"📊 [속도측정] Ping={ping}ms | Download={download:.2f}Mbps | Upload={upload:.2f}Mbps"
        )

        speed_ok = True

    except Exception as e:
        write_log(f"❌ Speedtest 오류 발생: {e}")
        speed_ok = False

    write_log("=== 📡 네트워크 체크 종료 ===")

    # 둘 중 하나라도 불안정하면 False
    return ping_ok and speed_ok

# ==========================
# 스케줄러 시작
# ==========================
import traceback

def start_scheduler(app):
    """스케줄러 시작"""
    scheduler = BackgroundScheduler()
    scheduler.add_listener(log_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    from app import auto_open_togle_prompt

    def scheduled_task():
        with app.app_context():

            write_log("🔔 스케줄러 작업 시작")
            
            # 0) 기존 백그라운드 크롬/크롬드라이버 종료
            kill_all_chrome()
            
            # 1) 네트워크 상태 체크
            network_ok = check_network_detail()

            if not network_ok:
                write_log("⚠️ 네트워크 불안정 상태에서 작업 실행됨 (원인 가능성 매우 높음)")

            # 2) 실제 작업 실행
            try:
                auto_open_togle_prompt(app)
                write_log("✅ auto_open_togle_prompt 실행 완료")

            except Exception as e:
                write_log("❌ auto_open_togle_prompt 실행 중 오류 발생")
                write_log(traceback.format_exc())

                # 스케줄러 이벤트 리스너에서도 기록되도록 다시 raise
                raise

    # 매일 9시 스케줄
    scheduler.add_job(
        scheduled_task,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_unanswered_collection",
        replace_existing=True,
        misfire_grace_time=300
    )

    # # 1시간마다 스케줄 실행
    # scheduler.add_job(
    #     scheduled_task,
    #     trigger="interval",
    #     minutes=30,
    #     id="hourly_unanswered_collection",
    #     replace_existing=True,
    #     misfire_grace_time=300
    # )

    # # 테스트용 10초 후 실행
    # scheduler.add_job(
    #     scheduled_task,
    #     trigger="date",
    #     run_date=datetime.now() + timedelta(seconds=10),
    #     id="test_collection_once",
    #     replace_existing=True,
    # )


    # # 자동으로 all_update 함수 호출 (매주 월요일 9시)
    # def scheduled_update():
    #     # 일주일 간격으로 필터 설정 (7일 전부터 오늘까지)
    #     end_date = datetime.now().strftime('%Y-%m-%d')
    #     start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    #     # 필터 데이터 준비
    #     form_data = {
    #         "mall": "전체",
    #         "q_type": "전체",
    #         "start_date": start_date,
    #         "end_date": end_date,
    #         "answer_filter": "전체",
    #         "include_deleted": "false",  # 삭제된 문의는 포함하지 않음
    #         "query": ""  # 쿼리 값은 공백으로 설정
    #     }

    #     # POST 요청을 통해 all_update 함수 호출
    #     try:
    #         response = requests.post("http://127.0.0.1:5005/togle/all_update", data=form_data)
    #         if response.status_code == 200:
    #             print("🗒️ 자동 업데이트가 성공적으로 완료되었습니다!")
    #         else:
    #             print(f"업데이트 요청 실패: {response.status_code}")
    #     except Exception as e:
    #         print(f"업데이트 요청 중 오류 발생: {str(e)}")

    # # 매주 월요일 9시에 자동으로 `scheduled_update` 함수 호출
    # scheduler.add_job(
    #     scheduled_update,
    #     trigger='cron',
    #     hour=9,
    #     minute=0,
    #     id='weekly_update',  # 작업 ID
    #     replace_existing=True,  # 기존 작업이 있을 경우 덮어쓰기
    #     misfire_grace_time=300  # 5분
    # )

    scheduler.start()
    logger.info("✅ Scheduler started (매일 9시)")
    return scheduler

def log_event(event):
    """스케줄러 이벤트 로그"""
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(f"✅ Job {event.job_id} executed at {event.scheduled_run_time}")
    elif event.code == EVENT_JOB_ERROR:
        logger.error(f"❌ Job {event.job_id} failed at {event.scheduled_run_time}")

def update_status_after_task():
    """작업 완료 후 상태 업데이트"""
    # 여기에서 엑셀과 PDF 업데이트 완료 상태를 설정
    # 이 함수는 auto_open_togle_prompt 작업 완료 후 호출됩니다.
    status = {
        'schedule_time': '매일 09:00',  # 자동 수집 시간
        'excel_update': '✅ 엑셀 업데이트 완료',  # 엑셀 업데이트 완료 표시
        'pdf_update': '✅ PDF 업데이트 완료'  # PDF 업데이트 완료 표시
    }
    return status  # 상태 업데이트 반환 (API로 반환할 수 있습니다)

# ==========================
# Flask 앱 생성
# ==========================
def create_app(init_scheduler=True):
    """Flask 앱 생성 및 초기화"""
    app = Flask(__name__)
    app.secret_key = "12345"

    print("=" * 60)
    print("🚀 Flask 앱 생성 시작...")
    print("=" * 60)

    # Flask-Session 설정
    app.config.update(
        SESSION_TYPE="filesystem",
        SESSION_FILE_DIR="./flask_session",
        SESSION_PERMANENT=False,
        SESSION_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),
    )
    Session(app)
    logger.info("✅ Flask-Session 설정 완료")

    # Config 등록
    app.config.from_object(config)
    logger.info("✅ Config 등록 완료")

    # CORS 설정
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    logger.info("✅ CORS 설정 완료")

    # DB 설정
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:1111@localhost:5432/togle_db'
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    logger.info("✅ SQLAlchemy DB 설정 완료")

    # Flask-Login 초기화
    login_manager.init_app(app)
    login_manager.login_view = "auth_bp.login"
    logger.info("✅ Flask-Login 초기화 완료")

    # 블락된 IP 로드
    blocked_ips = load_blocked_ips()

    @app.before_request
    def block_ips():
        ip = request.remote_addr
        if ip in blocked_ips:
            logger.warning(f"❌ 차단된 IP 요청: {ip}")
            abort(403, description="접속이 차단된 IP입니다.")

    @app.before_request
    def session_uid_check():
        if current_user.is_authenticated:
            now_ts = datetime.now().timestamp()
            last_checked = session.get("last_checked", now_ts)

            if "session_uid" not in session:
                session["session_uid"] = str(uuid.uuid4())
                session["last_checked"] = now_ts
            elif now_ts - last_checked > 10 * 60:
                logout_user()
                session.clear()
                flash("세션이 만료되어 로그아웃되었습니다.", "warning")
                return redirect(url_for("auth.login"))
            else:
                session["last_checked"] = now_ts

    # Blueprint 등록
    from app.routes.index import index_bp
    from app.routes.togle import togle_bp
    from app.routes.review import review_bp
    from app.routes.talktalk import talktalk_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(togle_bp, url_prefix="/togle")
    app.register_blueprint(review_bp, url_prefix="/review")
    app.register_blueprint(talktalk_bp, url_prefix="/talktalk")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    logger.info("✅ 기본 Blueprint 등록 완료")

    # API Blueprint (선택)
    try:
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
        logger.info("✅ API Blueprint 등록 완료")
    except ImportError:
        logger.warning("⚠️ API Blueprint 없음")

    # DB 테이블 생성
    with app.app_context():
        db.create_all()
        logger.info("✅ DB 테이블 생성 완료")

    # 스케줄러 시작 (옵션)
    if init_scheduler:
        scheduler = start_scheduler(app)
        app.scheduler = scheduler
        atexit.register(lambda: safe_shutdown_scheduler(app.scheduler))
        logger.info("✅ 스케줄러 시작 완료")
    else:
        app.scheduler = None
        logger.info("⚠️ 스케줄러 실행 생략 (init_scheduler=False)")

    print("=" * 60)
    print("✅ Flask 앱 생성 완료!")
    print("=" * 60)

    return app
