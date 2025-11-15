"""
Models 패키지 초기화
모든 모델과 함수를 여기서 import하여 외부에서 쉽게 접근 가능하도록 함
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ✅ User 모델 import
from app.models.user_model import User

# ✅ UnansweredInquiry 모델 정의
class UnansweredInquiry(db.Model):
    """미답변 문의 테이블"""
    __tablename__ = 'unanswered_inquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    q_shopping_mall = db.Column(db.String(200))
    q_type = db.Column(db.String(100))
    q_date = db.Column(db.String(50))
    q_writer = db.Column(db.String(100))
    q_question = db.Column(db.Text)
    q_answer_title = db.Column(db.String(500))
    q_answer_content = db.Column(db.Text)
    is_submitted = db.Column(db.Boolean, default=False)  # 전송 여부
    created_at = db.Column(db.DateTime, default=datetime.now)  # 생성일
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)  # 수정일
    submitted_at = db.Column(db.DateTime, nullable=True)  # 전송일
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'q_shopping_mall': self.q_shopping_mall,
            'q_type': self.q_type,
            'q_date': self.q_date.strftime('%Y-%m-%d %H:%M:%S') if self.q_date else None,
            'q_writer': self.q_writer,
            'q_question': self.q_question,
            'q_answer_title': self.q_answer_title,
            'q_answer_content': self.q_answer_content,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'is_submitted': self.is_submitted
        }


# ✅ 데이터베이스 헬퍼 함수들
def save_unanswered_to_db(unanswered_list):
    """
    미답변 목록을 DB에 저장/업데이트
    - is_submitted=False인 항목은 모두 미답변으로 간주
    - 동일 문의는 최신 데이터로 통합 업데이트
    - 삭제 없이 상태 관리
    """
    try:
        updated_count = 0
        inserted_count = 0
        
        for item in unanswered_list:
            # 고유 식별: 쇼핑몰 + 작성자 + 질문 + 날짜로 동일 문의 판단
            inquiry = UnansweredInquiry.query.filter_by(
                q_shopping_mall=item.get('q_shopping_mall'),
                q_writer=item.get('q_writer'),
                q_question=item.get('q_question'),
                q_date=item.get('q_date')
            ).first()

            if inquiry:
                # ✅ 기존 문의 업데이트 (최신화)
                inquiry.q_type = item.get('q_type', inquiry.q_type)
                inquiry.q_answer_title = item.get('q_answer_title', inquiry.q_answer_title)
                inquiry.q_answer_content = item.get('q_answer_content', inquiry.q_answer_content)
                
                # 답변이 있으면 is_submitted를 유지, 없으면 False
                if item.get('q_answer_title') and item.get('q_answer_content'):
                    # 답변이 새로 추가된 경우에만 is_submitted 유지
                    pass  # 기존 상태 유지
                else:
                    inquiry.is_submitted = False  # 답변 없으면 미제출 상태
                
                if hasattr(inquiry, 'updated_at'):
                    inquiry.updated_at = datetime.now()
                
                updated_count += 1
                print(f"📝 업데이트: {inquiry.q_shopping_mall} - {inquiry.q_writer}")
            else:
                # ✅ 신규 문의 등록
                new_inquiry = UnansweredInquiry(
                    q_shopping_mall=item.get('q_shopping_mall'),
                    q_type=item.get('q_type'),
                    q_date=item.get('q_date'),
                    q_writer=item.get('q_writer'),
                    q_question=item.get('q_question'),
                    q_answer_title=item.get('q_answer_title', ''),
                    q_answer_content=item.get('q_answer_content', ''),
                    is_submitted=False  # 신규는 무조건 미제출
                )
                db.session.add(new_inquiry)
                inserted_count += 1
                print(f"➕ 신규 등록: {new_inquiry.q_shopping_mall} - {new_inquiry.q_writer}")

        db.session.commit()
        print(f"✅ DB 저장 완료 - 신규: {inserted_count}개, 업데이트: {updated_count}개")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ DB 저장 실패: {e}")
        return False


def mark_inquiries_as_submitted(inquiry_ids):
    """
    답변 전송 완료 후 is_submitted=True로 변경
    답변 날짜 갱신
    """
    try:
        for inquiry_id in inquiry_ids:
            inquiry = UnansweredInquiry.query.get(inquiry_id)
            if inquiry:
                inquiry.is_submitted = True
                inquiry.submitted_at = datetime.now()  # 답변 전송 날짜
                if hasattr(inquiry, 'updated_at'):
                    inquiry.updated_at = datetime.now()
        
        db.session.commit()
        print(f"✅ {len(inquiry_ids)}개 문의 전송 완료 처리")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ 전송 완료 처리 실패: {e}")
        return False

def get_all_unanswered_from_db():
    """
    is_submitted=False인 모든 문의 조회
    (미답변 또는 답변 작성 중)
    """
    try:
        # is_submitted가 False이거나 NULL인 항목 모두 조회
        inquiries = UnansweredInquiry.query.filter(
            (UnansweredInquiry.is_submitted == False) | 
            (UnansweredInquiry.is_submitted.is_(None))
        ).order_by(
            UnansweredInquiry.created_at.desc()
        ).all()
        
        result = []
        for inquiry in inquiries:
            result.append({
                'id': inquiry.id,
                'q_shopping_mall': inquiry.q_shopping_mall or '',
                'q_type': inquiry.q_type or '',
                'q_date': inquiry.q_date or '',
                'q_writer': inquiry.q_writer or '',
                'q_question': inquiry.q_question or '',
                'q_answer_title': inquiry.q_answer_title or '',
                'q_answer_content': inquiry.q_answer_content or '',
                'is_submitted': inquiry.is_submitted if inquiry.is_submitted is not None else False,
                'created_at': inquiry.created_at.strftime('%Y-%m-%d %H:%M:%S') if inquiry.created_at else None,
                'updated_at': inquiry.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(inquiry, 'updated_at') and inquiry.updated_at else None
            })
        
        print(f"✅ 미제출 문의 {len(result)}개 조회 완료 (is_submitted=False 또는 NULL)")
        return result
    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_unanswered_from_db():
    """미답변 목록 조회 (제출되지 않은 것만)"""
    try:
        inquiries = UnansweredInquiry.query.filter_by(is_submitted=False).order_by(UnansweredInquiry.q_date.desc()).all()
        return [inquiry.to_dict() for inquiry in inquiries]
    except Exception as e:
        print(f"❌ DB 조회 실패: {e}")
        return []


def update_answer_in_db(question_id, title, content):
    """답변 수정"""
    try:
        inquiry = UnansweredInquiry.query.get(question_id)
        if inquiry:
            inquiry.q_answer_title = title
            inquiry.q_answer_content = content
            inquiry.updated_at = datetime.now()
            db.session.commit()
            print(f"✅ ID {question_id} 답변 수정 완료")
            return True
        else:
            print(f"❌ ID {question_id} 찾을 수 없음")
            return False
    except Exception as e:
        db.session.rollback()
        print(f"❌ 답변 수정 실패: {e}")
        return False


def mark_as_submitted(question_ids):
    """답변 제출 완료 표시"""
    try:
        UnansweredInquiry.query.filter(UnansweredInquiry.id.in_(question_ids)).update(
            {UnansweredInquiry.is_submitted: True},
            synchronize_session=False
        )
        db.session.commit()
        print(f"✅ {len(question_ids)}개 항목 제출 완료 표시")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ 제출 완료 표시 실패: {e}")
        return False


def get_inquiry_by_question(question_text):
    """질문 내용으로 문의 조회 (매칭용)"""
    try:
        inquiry = UnansweredInquiry.query.filter_by(
            q_question=question_text,
            is_submitted=False
        ).first()
        return inquiry
    except Exception as e:
        print(f"❌ 문의 조회 실패: {e}")
        return None


# ✅ 외부에서 import 가능하도록 __all__ 정의
__all__ = [
    'db',
    'User',
    'UnansweredInquiry',
    'save_unanswered_to_db',
    'get_unanswered_from_db',
    'update_answer_in_db',
    'mark_as_submitted',
    'get_inquiry_by_question',
]