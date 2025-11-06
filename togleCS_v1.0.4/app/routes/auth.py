from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.user_model import User
from datetime import datetime, timedelta
import os

# 전역 변수 또는 Redis/DB를 사용할 수 있음
login_attempts = {}  # { "ip주소": {"count": int, "last_attempt": datetime, "blocked_until": datetime} }
PERMANENT_BAN_THRESHOLD = 25
TEMP_BAN_THRESHOLD = 5
TEMP_BAN_MINUTES = 10

# 프로젝트 루트 기준 logs 폴더
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 현재 파일 기준 디렉토리
LOG_DIR = os.path.join(BASE_DIR, "logs")
IP_BLOCK_FILE = os.path.join(LOG_DIR, "ip_blocks.txt")
os.makedirs(LOG_DIR, exist_ok=True)

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

def log_permanent_ban(ip):
    now_str = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    with open(IP_BLOCK_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now_str} - PERMANENT BAN: {ip}\n")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    ip = request.remote_addr
    now = datetime.now()

    # IP 정보 초기화
    if ip not in login_attempts:
        login_attempts[ip] = {"count": 0, "last_attempt": now, "blocked_until": None}

    info = login_attempts[ip]

    # ✅ 영구 차단
    if info["count"] >= PERMANENT_BAN_THRESHOLD:
        log_permanent_ban(ip)
        flash("해당 IP가 영구 차단되었습니다.", "error")
        return render_template("login.html")

    # ✅ 임시 차단
    if info["blocked_until"] and now < info["blocked_until"]:
        flash(f"{TEMP_BAN_MINUTES}분 후 다시 시도해주세요.", "error")
        return render_template("login.html")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("아이디와 비밀번호를 입력해주세요.", "error")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            # 로그인 실패 카운트 증가
            info["count"] += 1
            info["last_attempt"] = now

            # 임시 차단 설정
            if info["count"] >= TEMP_BAN_THRESHOLD and info["count"] < PERMANENT_BAN_THRESHOLD:
                info["blocked_until"] = now + timedelta(minutes=TEMP_BAN_MINUTES)
                flash(f"5회 이상 로그인 실패, {TEMP_BAN_MINUTES}분 후 다시 시도해주세요.", "error")
            else:
                flash("아이디 또는 비밀번호가 잘못되었습니다.", "error")

            return render_template("login.html")

        # 로그인 성공 시 초기화
        login_user(user, remember=True)
        info["count"] = 0
        info["blocked_until"] = None
        flash(f"환영합니다, {user.username}님!", "success")

        if username == 'external':
            return redirect(url_for("togle.external_view"))
        else:
            return redirect(url_for("index.index"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("로그아웃 되었습니다.", "info")
    return redirect(url_for("auth.login"))
