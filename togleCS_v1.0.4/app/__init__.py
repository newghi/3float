from flask import Flask
from flask_session import Session
from flask_cors import CORS
from datetime import datetime, timedelta
from app import config
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers import SchedulerNotRunningError
import logging
import atexit
from flask_login import LoginManager

# ✅ db는 models에서 import
from app.models import db

login_manager = LoginManager()
unanswered_data = []  # 기존 코드 호환용


def create_app():
    """Flask 앱 생성 및 초기화"""
    app = Flask(__name__)
    app.secret_key = "12345"
    
    print("=" * 60)
    print("🚀 Flask 앱 생성 시작...")
    print("=" * 60)

    # Flask-Session 설정
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = "./flask_session"
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)
    Session(app)
    print("✅ Flask-Session 설정 완료")

    # config 등록
    app.config.from_object(config)
    print("✅ Config 등록 완료")
    
    # ✅ CORS 설정 (외부 접속 허용)
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type"]
        }
    }, supports_credentials=True)  # ✅ 쿠키/세션 지원
    print("✅ CORS 설정 완료")
    
    # ✅ DB 설정
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///togle.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    print("✅ SQLAlchemy DB 설정 완료")
    
    # Flask-Login 초기화
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    print("✅ Flask-Login 초기화 완료")

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
    print("✅ 기존 Blueprint 등록 완료")
    
    # ✅ API Blueprint 등록
    try:
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
        print("✅ API Blueprint 등록 완료")
    except ImportError as e:
        print(f"⚠️ API Blueprint 없음: {e}")

    # DB 테이블 생성
    with app.app_context():
        db.create_all()
        print("✅ DB 테이블 생성 완료")

    # APScheduler 설정
    scheduler = start_scheduler()
    app.scheduler = scheduler
    atexit.register(lambda: safe_shutdown_scheduler(app.scheduler))
    print("✅ 스케줄러 시작 완료")
    
    print("=" * 60)
    print("✅ Flask 앱 생성 완료!")
    print("=" * 60)

    return app


# ✅ Flask-Login user_loader
from app.models.user_model import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def safe_shutdown_scheduler(scheduler):
    """스케줄러 안전 종료"""
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            logging.info("Scheduler safely shut down.")
    except SchedulerNotRunningError:
        logging.warning("Scheduler was not running.")
    except Exception as e:
        logging.error(f"Error shutting down scheduler: {e}")


def auto_open_togle_prompt():
    """미답변 문의 자동 수집"""
    global unanswered_data
    
    try:
        print("\n" + "=" * 60)
        print("🚀 자동 수집 시작:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 60)
        
        from app.services.togleService import get_unanswered_list
        unanswered_list = get_unanswered_list()
        
        # 전역 변수에 저장
        unanswered_data = unanswered_list
        print(f"✅ 전역 변수에 {len(unanswered_list)}개 저장 완료")
        
        # DB 저장 시도
        try:
            from app.models import save_unanswered_to_db
            save_unanswered_to_db(unanswered_list)
            print(f"✅ DB 저장 완료: {len(unanswered_list)}개")
        except Exception as e:
            print(f"⚠️ DB 저장 실패: {e}")
        
        print(f"✅ 총 {len(unanswered_list)}개 미답변 수집 완료")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"❌ 자동 수집 중 오류: {e}")
        import traceback
        traceback.print_exc()


def start_scheduler():
    """스케줄러 시작"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    scheduler = BackgroundScheduler()
    scheduler.add_listener(log_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # 매일 9시 자동 실행
    scheduler.add_job(
        auto_open_togle_prompt,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_unanswered_collection",
        replace_existing=True,
    )
    
    # 🧪 테스트용: 10초 후 1회 실행
    scheduler.add_job(
        auto_open_togle_prompt,
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=10),
        id="test_collection_once",
        replace_existing=True,
    )

    scheduler.start()
    logging.info("✅ Scheduler started (매일 9시 + 테스트 10초 후)")
    return scheduler


def log_event(event):
    """스케줄러 이벤트 로그"""
    if event.code == EVENT_JOB_EXECUTED:
        logging.info(f"Job {event.job_id} executed at {event.scheduled_run_time}")
    elif event.code == EVENT_JOB_ERROR:
        logging.error(f"Job {event.job_id} failed at {event.scheduled_run_time}")