"""
사용자 모델
Flask-Login과 통합
"""

from flask_login import UserMixin
from app.models import db

class User(UserMixin, db.Model):
    """사용자 계정 테이블"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    # ✅ Flask-Login 필수 메서드들
    def get_id(self):
        """Flask-Login이 사용하는 ID 반환"""
        return str(self.id)
    
    @property
    def is_active(self):
        """계정 활성화 여부"""
        return True
    
    @property
    def is_authenticated(self):
        """인증 여부"""
        return True
    
    @property
    def is_anonymous(self):
        """익명 사용자 여부"""
        return False