from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from app.utils.paths import get_data_dir

import os, threading, signal, sys

index_bp = Blueprint('index', __name__)

from flask_login import login_required, current_user
from ipaddress import ip_address

def is_private_ip(ip):
    """사설망 IP인지 확인"""
    try:
        return ip_address(ip).is_private
    except ValueError:
        return False

@index_bp.route('/', methods=['GET'])
@login_required
def index():
    ip = request.remote_addr

    # 외부 IP면 external_view.html
    # if not is_private_ip(ip):
    #     # 필요하면 로그 기록도 여기서 추가 가능
    #     return render_template('external_view.html', user=current_user)

    # 내부 IP면 기존 index.html
    return render_template('index.html', user=current_user)

@index_bp.route('/home', methods=['GET'])
@login_required
def foreign_index():
    # 외부 페이지인 external_view.html을 내부에서도 접근할 수 있도록 함
    return render_template('index.html', user=current_user)

@index_bp.route('/external-view', methods=['GET'])
@login_required
def proto_index():
    # 외부 페이지인 external_view.html을 내부에서도 접근할 수 있도록 함
    return render_template('external_view.html', user=current_user)

# 프롬프트 편집 페이지
@index_bp.route('/edit_prompt', methods=['GET'])
def edit_prompt():
    # ✅ base_dir 계산
    base_dir = get_data_dir()

    # ✅ app/data/prompt.txt 경로
    prompt_path = os.path.join(base_dir, "app", "data", "prompt.txt")
    print("💾 프롬프트 불러오는 경로:", prompt_path)

    # 파일 없으면 빈 파일 생성
    if not os.path.exists(prompt_path):
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write("")

    # 프롬프트 불러오기 (있는 그대로)
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()

    return render_template('edit_prompt.html', prompt_text=prompt)

# 프롬프트 저장
@index_bp.route('/save_prompt', methods=['POST'])
def save_prompt():
    new_prompt = request.form.get('prompt_text', '')

    # ✅ 불필요한 빈 줄 제거
    lines = new_prompt.splitlines()
    cleaned = '\n'.join([line.rstrip() for line in lines if line.strip() != ''])

    # ✅ 실행 환경에 따라 base_dir 설정
    if getattr(sys, 'frozen', False):
        # PyInstaller로 실행된 경우 (run.exe)
        base_dir = os.path.dirname(sys.executable)
    else:
        # 개발용 run.py로 실행 중
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # data/prompt.txt 경로 구성 (base_dir 기준으로 상위 ../data)
    prompt_path = os.path.abspath(os.path.join(base_dir, "app", "data", "prompt.txt"))

    print("💾 프롬프트 저장 경로:", prompt_path)

    # 저장
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    flash("✅ 프롬프트가 저장되었습니다.")
    return redirect(url_for('index.edit_prompt'))


# 종료버튼 클릭시
@index_bp.route('/shutdown', methods=['POST'])
def shutdown():
    def shutdown_async():
        os.kill(os.getpid(), signal.SIGTERM)  # 프로세스 종료

    threading.Thread(target=shutdown_async).start()
    return '서버 종료 중...'


from flask import request, redirect, url_for
from flask_login import current_user

def login_or_internal_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        client_ip = request.remote_addr
        # 서버 내부 IP 체크
        internal_ips = ["127.0.0.1", "192.168.0.100"]  # 서버 IP 추가
        if client_ip in internal_ips:
            return f(*args, **kwargs)
        # 외부 IP이면 로그인 체크
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated
