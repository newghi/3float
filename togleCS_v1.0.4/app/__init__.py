from flask import Flask
from flask_session import Session  # ✅ Flask-Session 추가
from datetime import timedelta
from app import config

def create_app():
    app = Flask(__name__)
    app.secret_key = '12345'  # ✅ 반드시 설정해야 함 (아무 문자열 가능)

    # ✅ Flask-Session 설정
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = './flask_session'
    app.config['SESSION_PERMANENT'] = True                   # ✅ 반드시 True로
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)  # ✅ 10분 유지

    Session(app)

    # config 등록
    app.config.from_object(config)

    # DB 연결
    
    # Blueprint 등록
    from app.routes.index import index_bp
    from app.routes.togle import togle_bp
    from app.routes.review import review_bp
    from app.routes.talktalk import talktalk_bp
    
    app.register_blueprint(index_bp) # 메인화면 페이지
    app.register_blueprint(togle_bp, url_prefix='/togle') # togle 관련 페이지
    app.register_blueprint(review_bp, url_prefix='/review')  # review 관련 페이지
    app.register_blueprint(talktalk_bp, url_prefix='/talktalk')  # 톡톡 관련 페이지
    
    return app
