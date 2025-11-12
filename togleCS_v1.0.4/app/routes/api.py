from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import (
    get_unanswered_from_db, 
    update_answer_in_db, 
    mark_as_submitted,
    get_inquiry_by_question,
    save_unanswered_to_db, UnansweredInquiry
)

api_bp = Blueprint('api', __name__)


@api_bp.route('/unanswered', methods=['GET'])
@login_required  # ✅ Flask-Login 데코레이터
def get_unanswered():
    """
    외부에서 미답변 목록 조회
    GET /api/unanswered
    """
    try:
        data = get_unanswered_from_db()
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/update_prompt', methods=['POST'])
@login_required  # ✅ 로그인 체크 추가
def update_prompt():
    """
    외부에서 프롬프트(답변) 수정
    POST /api/update_prompt
    Body: {
        "id": 1,
        "title": "답변 제목",
        "content": "답변 내용"
    }
    """
    try:
        data = request.json
        question_id = data.get('id')
        new_title = data.get('title', '')
        new_content = data.get('content', '')
        
        if not question_id:
            return jsonify({
                'success': False,
                'error': 'ID가 필요합니다'
            }), 400
        
        success = update_answer_in_db(question_id, new_title, new_content)
        
        return jsonify({
            'success': success,
            'message': '수정 완료' if success else '수정 실패'
        }), 200 if success else 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/update_batch', methods=['POST'])
@login_required  # ✅ 로그인 체크 추가
def update_batch():
    """
    여러 답변 일괄 수정
    POST /api/update_batch
    Body: {
        "updates": [
            {"id": 1, "title": "제목1", "content": "내용1"},
            {"id": 2, "title": "제목2", "content": "내용2"}
        ]
    }
    """
    try:
        data = request.json
        updates = data.get('updates', [])
        
        success_count = 0
        for item in updates:
            if update_answer_in_db(item.get('id'), item.get('title', ''), item.get('content', '')):
                success_count += 1
        
        return jsonify({
            'success': True,
            'updated': success_count,
            'total': len(updates)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/submit_answers', methods=['POST'])
@login_required  # ✅ 로그인 체크 추가
def submit_answers():
    """
    ✅ 외부에서 답변 일괄 전송 → 서버 PC에서 자동으로 Togle에 업로드
    POST /api/submit_answers
    Body: {
        "answers": [
            {
                "q_question": "질문 내용",
                "q_answer_title": "답변 제목",
                "q_answer_content": "답변 내용"
            }
        ]
    }
    
    ⚠️ 주의: 이 API는 서버 PC에서 Selenium을 실행합니다 (시간 소요)
    """
    try:
        # ✅ 서버 PC에서 백그라운드로 실행
        import threading
        from app.services.togleService import upload_togle_answer
        
        answers = request.json.get('answers', [])
        
        if not answers:
            return jsonify({
                'success': False,
                'error': '전송할 답변이 없습니다'
            }), 400
        
        print(f"📤 외부 요청으로 {len(answers)}개 답변 전송 시작...")
        
        # ✅ 별도 스레드에서 실행 (API 응답 속도 개선)
        def background_upload():
            try:
                unmatched = upload_togle_answer(answers)
                
                # 성공한 항목들을 DB에서 제출 완료 표시
                if len(unmatched) < len(answers):
                    submitted_questions = [
                        ans['q_question'] for ans in answers 
                        if ans not in unmatched
                    ]
                    
                    # 제출 완료된 항목의 ID 찾기
                    submitted_ids = []
                    for q_text in submitted_questions:
                        inquiry = get_inquiry_by_question(q_text)
                        if inquiry:
                            submitted_ids.append(inquiry.id)
                    
                    if submitted_ids:
                        mark_as_submitted(submitted_ids)
                
                print(f"✅ 전송 완료: {len(answers) - len(unmatched)}/{len(answers)}개 성공")
                
            except Exception as e:
                print(f"❌ 백그라운드 전송 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 백그라운드 실행
        thread = threading.Thread(target=background_upload, daemon=True)
        thread.start()
        
        # 즉시 응답 (실제 전송은 백그라운드에서 진행)
        return jsonify({
            'success': True,
            'message': f'{len(answers)}개 답변 전송을 시작했습니다. 서버에서 처리 중입니다.',
            'total': len(answers)
        }), 202  # 202 Accepted
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/submit_status', methods=['GET'])
@login_required  # ✅ 로그인 체크 추가
def submit_status():
    """
    ✅ 전송 상태 확인
    GET /api/submit_status
    """
    try:
        # 미제출 항목 개수 확인
        from app.models import UnansweredInquiry
        pending_count = UnansweredInquiry.query.filter_by(is_submitted=False).count()
        
        return jsonify({
            'success': True,
            'pending_count': pending_count,
            'message': f'{pending_count}개 항목이 아직 미전송 상태입니다.'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/generate_answers', methods=['POST'])
@login_required  # ✅ 로그인 체크 추가
def generate_answers():
    """
    NotebookLM으로 답변 생성
    POST /api/generate_answers
    Body: {
        "questions": [
            {"id": 1, "q_question": "질문 내용"}
        ]
    }
    
    ⚠️ 주의: 이 API는 서버 PC에서 Selenium을 실행합니다 (시간 소요)
    """
    try:
        from app.services.togleService import get_notebookAnswer
        
        questions = request.json.get('questions', [])
        
        if not questions:
            return jsonify({
                'success': False,
                'error': '질문이 없습니다'
            }), 400
        
        print(f"🤖 NotebookLM 답변 생성 시작: {len(questions)}개")
        
        # NotebookLM으로 답변 생성
        results = get_notebookAnswer(questions)
        
        # DB 업데이트
        updated_count = 0
        for result in results:
            # id가 있으면 DB 업데이트
            if 'id' in result:
                if update_answer_in_db(
                    result['id'],
                    result.get('q_answer_title', ''),
                    result.get('q_answer_content', '')
                ):
                    updated_count += 1
        
        print(f"✅ NotebookLM 답변 생성 완료: {updated_count}개")
        
        return jsonify({
            'success': True,
            'generated': len(results),
            'updated': updated_count,
            'results': results
        }), 200
        
    except Exception as e:
        print(f"❌ NotebookLM 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'status': 'ok',
        'message': 'API server is running'
    }), 200


# ✅ 엑셀 정보 조회
@api_bp.route('/excel_info', methods=['GET'])
@login_required
def excel_info():
    """엑셀 파일 최종 수정 날짜 조회"""
    try:
        from app.utils.paths import get_data_dir
        import os
        from datetime import datetime
        
        base_dir = get_data_dir()
        excel_path = os.path.join(base_dir, "app", "data", "togle_data.xlsx")
        
        if os.path.exists(excel_path):
            modified_time = os.path.getmtime(excel_path)
            last_updated = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_updated = "파일 없음"
        
        return jsonify({
            'success': True,
            'last_updated': last_updated
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ✅ 엑셀 다운로드
@api_bp.route('/download_excel', methods=['GET'])
@login_required
def download_excel():
    """엑셀 파일 다운로드"""
    from flask import send_file, jsonify
    from app.utils.paths import get_data_dir
    import os
    import traceback
    from datetime import datetime

    try:
        # 1️⃣ 기본 데이터 디렉토리 가져오기
        base_dir = get_data_dir()
        print(f"DEBUG: base_dir = {base_dir}")  # 경로 확인용

        # 2️⃣ 엑셀 파일 경로 구성
        excel_path = os.path.join(base_dir, "app", "data", "togle_data.xlsx")
        print(f"DEBUG: excel_path = {excel_path}")  # 경로 확인용

        # 3️⃣ 파일 존재 여부 확인
        if not os.path.exists(excel_path):
            return jsonify({
                'success': False,
                'error': f'엑셀 파일이 존재하지 않습니다: {excel_path}'
            }), 404

        # 4️⃣ send_file로 전송
        return send_file(
            excel_path,
            as_attachment=True,
            download_name=f'togle_data_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )

    except Exception as e:
        traceback.print_exc()  # 상세 오류 로그 출력
        return jsonify({
            'success': False,
            'error': f"서버 오류 발생: {str(e)}"
        }), 500


# ✅ 스케줄 정보 조회
@api_bp.route('/schedule_info', methods=['GET'])
@login_required
def schedule_info():
    """자동 수집 스케줄 정보 조회"""
    try:
        from flask import current_app
        
        scheduler = current_app.scheduler
        job = scheduler.get_job('daily_unanswered_collection')
        
        if job:
            trigger = job.trigger
            return jsonify({
                'success': True,
                'hour': trigger.fields[5].expressions[0].first,  # hour
                'minute': trigger.fields[6].expressions[0].first  # minute
            }), 200
        else:
            return jsonify({
                'success': True,
                'hour': 9,
                'minute': 0
            }), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ✅ 스케줄 업데이트
@api_bp.route('/update_schedule', methods=['POST'])
@login_required
def update_schedule():
    """자동 수집 시간 변경"""
    try:
        from flask import current_app
        
        data = request.json
        hour = data.get('hour', 9)
        minute = data.get('minute', 0)
        
        scheduler = current_app.scheduler
        
        # 기존 작업 제거
        try:
            scheduler.remove_job('daily_unanswered_collection')
        except:
            pass
        
        # 새 작업 추가
        from app import auto_open_togle_prompt
        scheduler.add_job(
            lambda: auto_open_togle_prompt(current_app),
            trigger="cron",
            hour=hour,
            minute=minute,
            id="daily_unanswered_collection",
            replace_existing=True,
        )
        
        return jsonify({
            'success': True,
            'message': f'스케줄이 {hour:02d}:{minute:02d}로 변경되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ✅ 미답변 문의 가져오기 (수동 크롤링)
@api_bp.route('/fetch_unanswered', methods=['POST'])
@login_required
def fetch_unanswered():
    """서버에서 미답변 문의 크롤링"""
    try:
        import threading
        from app.services.togleService import get_unanswered_list
        from app.models import save_unanswered_to_db
        from flask import current_app
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        def background_fetch():
            try:
                # 현재 앱 컨텍스트 사용
                with current_app.app_context():
                    unanswered_list = get_unanswered_list()
                    
                    safe_list = []
                    for idx, item in enumerate(unanswered_list, start=1):
                        try:
                            # Selenium 페이지 이동 안전하게 처리
                            WebDriverWait(item['driver'], 10).until(
                                EC.presence_of_element_located((By.XPATH, f".//span[@class='block' and text()='{idx}']"))
                            )
                            safe_list.append(item)
                        except TimeoutException:
                            print(f"❌ 페이지 {idx} 이동 실패, 해당 문의는 스킵합니다.")

                    # 안전하게 DB 저장
                    save_unanswered_to_db(safe_list)
                    print(f"✅ 수동 크롤링 완료: {len(safe_list)}개")
            except Exception as e:
                print(f"❌ 수동 크롤링 실패: {e}")

        # 백그라운드 스레드 실행
        thread = threading.Thread(target=background_fetch, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': '미답변 문의 수집을 시작했습니다. 잠시 후 새로고침하세요.'
        }), 202

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ✅ 프로그램 업데이트
@api_bp.route('/update_program', methods=['POST'])
@login_required
def update_program():
    """프로그램 업데이트 (Git Pull 등)"""
    try:
        import subprocess
        import threading
        
        def background_update():
            try:
                # Git Pull 실행
                result = subprocess.run(
                    ['git', 'pull'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                print(f"Git Pull 결과: {result.stdout}")
                
                # 서버 재시작 (운영 환경에 따라 수정 필요)
                import sys
                import os
                os.execv(sys.executable, ['python'] + sys.argv)
                
            except Exception as e:
                print(f"❌ 업데이트 실패: {e}")
        
        # 백그라운드 실행
        thread = threading.Thread(target=background_update, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '프로그램 업데이트를 시작했습니다. 잠시 후 재접속하세요.'
        }), 202
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# save_unanswered API
@api_bp.route('/save_unanswered', methods=['POST'])
def save_unanswered():
    try:
        # 요청으로부터 unanswered_list를 가져옵니다.
        unanswered_list = request.json.get('unanswered_list', [])
        
        if not unanswered_list:
            return jsonify({'success': False, 'error': '빈 목록입니다.'}), 400

        # 수정된 항목만 저장
        success = save_unanswered_to_db(unanswered_list)
        
        if success:
            return jsonify({'success': True, 'message': f'{len(unanswered_list)}개 항목 수정 완료'}), 200
        else:
            return jsonify({'success': False, 'error': '수정된 항목이 없습니다.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# get_unanswered_from_db API
@api_bp.route('/get_unanswered_from_db', methods=['GET'])
def get_unanswered_from_db():
    try:
        unanswered_inquiries = UnansweredInquiry.query.filter_by(is_submitted=False).all()
        unanswered_list = [{
            'q_shopping_mall': item.q_shopping_mall,
            'q_type': item.q_type,
            'q_date': item.q_date,
            'q_writer': item.q_writer,
            'q_question': item.q_question,
            'q_answer_title': item.q_answer_title,
            'q_answer_content': item.q_answer_content
        } for item in unanswered_inquiries]
        
        if not unanswered_list:
            return jsonify({'success': True, 'message': '미답변 목록이 없습니다.'}), 200
        
        return jsonify({'success': True, 'qas': unanswered_list}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500