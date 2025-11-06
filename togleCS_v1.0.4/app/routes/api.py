from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import (
    get_unanswered_from_db, 
    update_answer_in_db, 
    mark_as_submitted,
    get_inquiry_by_question
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