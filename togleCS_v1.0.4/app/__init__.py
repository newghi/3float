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
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"))
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def create_app():
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

    # ✅ CORS 설정
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    logger.info("✅ CORS 설정 완료")

    # ✅ DB 설정
    # app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///togle.db"
    # ✅ PostgreSQL 연결 문자열 (예시)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:1111@localhost:5432/togle_db'
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    logger.info("✅ SQLAlchemy DB 설정 완료")

    # ✅ Flask-Login 초기화
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    logger.info("✅ Flask-Login 초기화 완료")

    # ✅ 블락된 IP 로드
    blocked_ips = load_blocked_ips()

    @app.before_request
    def block_ips():
        ip = request.remote_addr
        if ip in blocked_ips:
            logger.warning(f"❌ 차단된 IP 요청: {ip}")
            abort(403, description="접속이 차단된 IP입니다.")

    # ✅ 세션 UID 체크 및 만료 관리
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

    # ✅ Blueprint 등록
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

    # ✅ API Blueprint (선택)
    try:
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
        logger.info("✅ API Blueprint 등록 완료")
    except ImportError:
        logger.warning("⚠️ API Blueprint 없음")

    # ✅ DB 테이블 생성
    with app.app_context():
        db.create_all()
        logger.info("✅ DB 테이블 생성 완료")

    # ✅ APScheduler 시작 (app 인스턴스 전달)
    scheduler = start_scheduler(app)
    app.scheduler = scheduler
    atexit.register(lambda: safe_shutdown_scheduler(app.scheduler))
    logger.info("✅ 스케줄러 시작 완료")

    print("=" * 60)
    print("✅ Flask 앱 생성 완료!")
    print("=" * 60)
    return app


# ✅ Flask-Login user_loader
from app.models.user_model import User


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


# ✅ 스케줄러 함수 (app 컨텍스트 사용)
def auto_open_togle_prompt(app):
    """미답변 문의 자동 수집"""
    global unanswered_data
    with app.app_context():
        try:
            logger.info("🚀 자동 수집 시작: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            from app.services.togleService import get_unanswered_list

            unanswered_list = get_unanswered_list()
            unanswered_data = unanswered_list

            logger.info(f"✅ 미답변 {len(unanswered_list)}개 수집 완료")

            try:
                from app.models import save_unanswered_to_db
                save_unanswered_to_db(unanswered_list)
                logger.info(f"✅ DB 저장 완료: {len(unanswered_list)}개")
            except Exception as e:
                logger.warning(f"⚠️ DB 저장 실패: {e}")

        except Exception as e:
            logger.error(f"❌ 자동 수집 중 오류: {e}", exc_info=True)


def start_scheduler(app):
    """스케줄러 시작 (app 인스턴스 컨텍스트 유지)"""
    scheduler = BackgroundScheduler()
    scheduler.add_listener(log_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # 매일 9시 실행
    scheduler.add_job(
        lambda: auto_open_togle_prompt(app),
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_unanswered_collection",
        replace_existing=True,
    )

    # 🧪 테스트용: 10초 후 1회 실행
    scheduler.add_job(
        lambda: auto_open_togle_prompt(app),
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=10),
        id="test_collection_once",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ Scheduler started (매일 9시 + 테스트 10초 후)")
    return scheduler


def log_event(event):
    """스케줄러 이벤트 로그"""
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(f"✅ Job {event.job_id} executed at {event.scheduled_run_time}")
    elif event.code == EVENT_JOB_ERROR:
        logger.error(f"❌ Job {event.job_id} failed at {event.scheduled_run_time}")
