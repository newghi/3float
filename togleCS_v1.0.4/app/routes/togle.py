from flask import Blueprint, render_template, request, redirect, send_file, current_app, jsonify, render_template_string, url_for, flash, session
from datetime import date, datetime
import os
from pathlib import Path

from app.services.togleService import (
    updateTogleData, append_category_id, notebookLM_update, get_unanswered_list,
    get_notebookAnswer, upload_togle_answer
)
from app.services.fileService import append_unique_to_excel, excel_to_pdf
from app.utils.paths import get_data_dir

togle_bp = Blueprint('togle', __name__)
#===================================================================================

# togle '문의내역 업데이트' 페이지 이동
@togle_bp.route('/updateView', methods=['GET'])
def updateView():
    today = date.today().isoformat()  # '2025-05-28' 형식
    return render_template('togle/togle_update.html', today=today)

# togle '미답변 자동답변' 페이지 이동
@togle_bp.route('/unansweredView', methods=['GET'])
def unansweredView():
    qa_list = session.get('qa_list', [])
    success_log = session.get('success_log', [])
    fail_log = session.get('fail_log', [])

    return render_template('togle/togle_unanswered.html',
                           qa_list=qa_list,
                           success_log=success_log,
                           fail_log=fail_log)

#===================================================================================

# 전체 문의 내역 업데이트
@togle_bp.route('/all_update', methods=['POST'])
def all_update():
    # form 데이터 추출
    formData = request.form
    print(f"🗒️ 넘어온 데이터 {formData}")

    # togle 리스트 추출 함수
    update_list = updateTogleData(formData)

    # ✅ base_dir 계산
    base_dir = get_data_dir()

    # 기존 엑셀파일에 덧붙이기 함수
    append_unique_to_excel(
        data_list = update_list,
        filename="togle_data.xlsx",
        filepath = os.path.join(base_dir, "app", "data", "togle_data.xlsx"),
        col_mapping={
            "q_shopping_mall": "쇼핑몰",
            "q_type": "유형",
            "q_date": "문의일",
            "q_answered": "답변여부",
            "q_writer": "작성자",
            "q_question": "문의내용",
            "q_answer": "답변"
        },
        sheetname="전체",
        key_fields=["q_date"],
        sort_by="q_date"
    )

    # 엑셀 파일을 pdf로 변환
    excel_to_pdf(
        filepath = os.path.join(base_dir, "app", "data", "togle_data.xlsx"), 
        output_path = os.path.join(base_dir, "app", "data", "togle_data.pdf"),
        source_sheet="전체",           # 원본 시트명
        columns_order=["쇼핑몰","유형","문의일","답변여부","작성자","문의내용","답변"],
        small_headers=["쇼핑몰","유형","문의일","답변여부","작성자"],
        big_headers=("문의내용","답변"),
        orientation="landscape",
        repeat_header=True            # 두 열 폭 동일(문자 기준)
    )

    # 노트푹LM 업데이트
    notebookLM_update(filepath = os.path.join(base_dir, "app", "data", "togle_data.pdf"))
    return render_template_string("""
    <script>
      alert("✅ 업데이트가 완료되었습니다!");
      window.location.href = "{{ url_for('index.index') }}";
    </script>
    """)

# 미답변 문의글 추출 + 노트북LM으로 답변 얻기
@togle_bp.route('/get_unanswered', methods=['GET'])
def get_unanswered():
    # 미답변 문의글 list
    unanswered_list = get_unanswered_list()
    print (f"📑 미답변 문의글 List : {unanswered_list[:1]}")

    # 노트북LM에게 답변 얻기
    notebookAnswer_list = get_notebookAnswer(unanswered_list)
    print(f"✅ 노트북LM 최종 결과값 : {notebookAnswer_list[:1]}")

     # ✅ 세션에 저장
    session['qa_list'] = notebookAnswer_list

    return jsonify({"qas": notebookAnswer_list})

# 미답변 답변 최종 전송
@togle_bp.route('/post_unanswered', methods=['POST'])
def post_unanswered():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    answers = []
    index_map = {}  # question → index 매핑용

    for item in data:
        question = item.get("question", "")
        title = item.get("q_answer_title", "")
        content = item.get("q_answer_content", "")
        index = item.get("index")

        full_answer = f"[제목] {title}\n[내용] {content}"

        answers.append({
            "q_question": question,
            "q_answer": full_answer,
            "q_answer_title": title,
            "q_answer_content": content
        })

        index_map[question] = index

    # 📤 togle에 전체 전송
    print(f"📑 최종 답변 전송 List : {answers}")
    unmatched_questions = upload_togle_answer(answers)

    # 🔍 실패한 질문들만 추출
    failed_items = []
    failed_indexes = set()
    for item in unmatched_questions:
        question = item["q_question"]
        failed_items.append({
            "q_question": question,
            "q_answer_title": item.get("q_answer_title", ""),
            "q_answer_content": item.get("q_answer_content", "")
        })
        idx = index_map.get(question)
        if idx is not None:
            failed_indexes.add(idx)

    # 성공 인덱스 계산
    all_indexes = set(index_map.values())
    success_indexes = list(all_indexes - failed_indexes)

    # ✅ 성공 리스트 만들기
    success_list = []
    for item in data:
        idx = item.get("index")
        if idx in success_indexes:
            success_list.append({
                "q_question": item.get("question"),
                "q_answer_title": item.get("q_answer_title", ""),
                "q_answer_content": item.get("q_answer_content", ""),
                "q_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    # ✅ 실패 리스트 만들기
    fail_list = []
    for fail_item in failed_items:
        fail_list.append({
            "q_question": fail_item["q_question"],
            "q_answer_title": fail_item["q_answer_title"],
            "q_answer_content": fail_item["q_answer_content"],
            "q_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    # ✅ 최종 세션 저장
    print(f"📑 성공한 질문들 : {success_list}")
    print(f"📑 실패한 질문들 : {fail_list}")
    session['success_log'] = success_list
    session['fail_log'] = fail_list

    # ✅ 성공한 질문들은 세션의 qa_list에서도 제거
    if 'qa_list' in session:
        before = session['qa_list']
        session['qa_list'] = [
            item for item in session['qa_list']
            if index_map.get(item['q_question']) not in success_indexes
        ]
        after = session['qa_list']

        print("🔍 QA 세션 정리 전 개수:", len(before))
        print("🔍 QA 세션 정리 후 개수:", len(after))
        print("🧾 남아있는 qa_list:", after)


    return jsonify({
        "success": True,
        "success_count": len(success_indexes),
        "fail_count": len(fail_list),
        "success_indexes": success_indexes,
        "success_list": success_list,
        "fail_list": fail_list
    })

# app/routes/togle.py에 추가할 코드

from flask_login import login_required, current_user
from flask import request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 현재 파일 위치
LOG_DIR = os.path.join(BASE_DIR, "logs")  # logs 폴더 생성
IP_BLOCK_FILE = os.path.join(LOG_DIR, "ip_blocks.txt")

@togle_bp.route('/external', methods=['GET'])
def external_view():
    # 디버깅용 출력
    print(f"현재 사용자: {current_user}")
    print(f"로그인 여부: {current_user.is_authenticated}")
    print(f"요청 IP: {request.remote_addr}")

    if not current_user.is_authenticated:
        print("❌ 로그인 안됨 → auth.login으로 리다이렉트")
        flash('로그인이 필요합니다.', 'warning')
        return redirect(url_for('auth.login'))

    # ✅ 로그인됨 → IP 기록
    now = datetime.now()
    year_month = now.strftime("%Y.%m")  # 파일명: 2025.11.txt
    log_file_path = os.path.join(LOG_DIR, f"{year_month}.txt")

    # 로그 디렉토리 없으면 생성
    os.makedirs(LOG_DIR, exist_ok=True)

    # 기록 내용: yyyy.mm.dd HH:MM:SS - IP - 사용자ID
    log_entry = f"{now.strftime('%Y.%m.%d %H:%M:%S')} - {request.remote_addr} - {current_user.username}\n"

    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"✅ IP 기록 완료: {log_file_path}")
    except Exception as e:
        print(f"❌ IP 기록 실패: {e}")

    return render_template('external_view.html', user=current_user)


@togle_bp.route('/external/logout', methods=['GET'])
@login_required
def external_logout():
    """로그아웃 (외부 페이지용)"""
    from flask_login import logout_user
    logout_user()
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('auth.login'))


# ✅ 외부에서 프롬프트 편집 페이지
@togle_bp.route('/external/edit_prompt', methods=['GET'])
@login_required
def external_edit_prompt():
    """외부에서 프롬프트 편집"""
    from app.utils.paths import get_data_dir
    import os
    
    base_dir = get_data_dir()
    prompt_path = os.path.join(base_dir, "app", "data", "prompt.txt")
    
    if not os.path.exists(prompt_path):
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write("")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    return render_template('external_edit_prompt.html', prompt_text=prompt, user=current_user)


# ✅ 외부에서 프롬프트 저장
@togle_bp.route('/external/save_prompt', methods=['POST'])
@login_required
def external_save_prompt():
    """외부에서 프롬프트 저장"""
    from app.utils.paths import get_data_dir
    import os, sys
    
    new_prompt = request.form.get('prompt_text', '')
    
    # 불필요한 빈 줄 제거
    lines = new_prompt.splitlines()
    cleaned = '\n'.join([line.rstrip() for line in lines if line.strip() != ''])
    
    # 경로 설정
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    prompt_path = os.path.abspath(os.path.join(base_dir, "app", "data", "prompt.txt"))
    
    # 저장
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    flash('✅ 프롬프트가 저장되었습니다.', 'success')
    return redirect(url_for('togle.external_edit_prompt'))