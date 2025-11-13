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
    q_shopping_mall = db.Column(db.String(100))
    q_type = db.Column(db.String(50))
    q_date = db.Column(db.DateTime)
    q_writer = db.Column(db.String(100))
    q_question = db.Column(db.Text, nullable=False)
    q_answer_title = db.Column(db.String(200), default='')
    q_answer_content = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_submitted = db.Column(db.Boolean, default=False)
    
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
    미답변 목록을 DB에 저장
    기존 데이터가 있으면 UPDATE, 없으면 INSERT
    """
    try:
        for item in unanswered_list:
            # 고유 식별 기준 설정 (id가 있다면 id로 조회)
            question_id = item.get('id') or item.get('q_id') or item.get('question_id')

            if question_id:
                inquiry = UnansweredInquiry.query.get(question_id)
            else:
                # id가 없으면 고유 조건으로 검색
                inquiry = UnansweredInquiry.query.filter_by(
                    q_shopping_mall=item.get('q_shopping_mall'),
                    q_writer=item.get('q_writer'),
                    q_question=item.get('q_question'),
                    q_date=item.get('q_date')
                ).first()

            # ① 이미 존재하면 UPDATE
            if inquiry:
                inquiry.q_answer_title = item.get('q_answer_title', '')
                inquiry.q_answer_content = item.get('q_answer_content', '')
                inquiry.q_type = item.get('q_type', inquiry.q_type)
                inquiry.is_submitted = False
                if hasattr(inquiry, 'updated_at'):
                    inquiry.updated_at = datetime.now()

            # ② 존재하지 않으면 INSERT
            else:
                new_inquiry = UnansweredInquiry(
                    q_shopping_mall=item.get('q_shopping_mall'),
                    q_type=item.get('q_type'),
                    q_date=item.get('q_date'),
                    q_writer=item.get('q_writer'),
                    q_question=item.get('q_question'),
                    q_answer_title=item.get('q_answer_title', ''),
                    q_answer_content=item.get('q_answer_content', ''),
                    is_submitted=False
                )
                db.session.add(new_inquiry)

        db.session.commit()
        print(f"✅ {len(unanswered_list)}개 항목 DB 저장 완료 (업데이트 포함)")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ DB 저장 실패: {e}")
        return False


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