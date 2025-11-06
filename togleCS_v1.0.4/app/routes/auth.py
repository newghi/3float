from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.user_model import User

# ✅ Blueprint 이름이 'auth'여야 함
auth_bp = Blueprint("auth", __name__, template_folder="../templates")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # ✅ 이미 로그인된 경우 리다이렉트
    if current_user.is_authenticated:
        return redirect(url_for("index.index"))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("아이디와 비밀번호를 입력해주세요.", "error")
            return render_template("login.html")
        
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash("아이디 또는 비밀번호가 잘못되었습니다.", "error")
            return redirect(url_for("auth.login"))

        # 로그인 처리
        login_user(user, remember=True)
        flash(f"환영합니다, {user.username}님!", "success")
        
        # ✅ 외부 사용자는 external 페이지로, 나머지는 메인으로
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