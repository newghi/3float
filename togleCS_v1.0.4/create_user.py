"""
초기 사용자 계정 생성 스크립트
실행: python create_user.py
"""

from app import create_app, db
from app.models.user_model import User
from werkzeug.security import generate_password_hash

def create_initial_users():
    """초기 사용자 계정 생성"""
    app = create_app()
    
    with app.app_context():
        # 기존 사용자 확인
        existing_count = User.query.count()
        
        if existing_count > 0:
            print(f"⚠️ 이미 {existing_count}명의 사용자가 존재합니다.")
            print("\n현재 사용자 목록:")
            users = User.query.all()
            for user in users:
                print(f"  - {user.username}")
            
            choice = input("\n모든 사용자를 삭제하고 다시 생성하시겠습니까? (y/n): ")
            if choice.lower() != 'y':
                print("취소되었습니다.")
                return
            
            # 모든 사용자 삭제
            User.query.delete()
            db.session.commit()
            print("✅ 기존 사용자 삭제 완료\n")
        
        # 새 사용자 생성
        users_to_create = [
            ('egenSecurity20250926', '123456789', '관리자'),
            ('egenauto', '0000', '외부 접속용')
            ]
        
        print("=" * 60)
        print("사용자 계정 생성 중...")
        print("=" * 60)
        
        for username, password, description in users_to_create:
            try:
                user = User(
                    username=username,
                    password=generate_password_hash(password)
                )
                db.session.add(user)
                print(f"✅ 생성 완료: {username} / {password} ({description})")
            except Exception as e:
                print(f"❌ {username} 생성 실패: {e}")
        
        try:
            db.session.commit()
            print("\n" + "=" * 60)
            print("✅ 모든 사용자 계정 생성 완료!")
            print("=" * 60)
            
            print("\n📋 생성된 계정 정보:")
            print("-" * 60)
            for username, password, description in users_to_create:
                print(f"  ID: {username:15} PW: {password:15} ({description})")
            print("-" * 60)
            
            print("\n🔒 보안을 위해 운영 환경에서는 비밀번호를 변경하세요!")
            print("\n🌐 외부 접속 URL:")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ 데이터베이스 커밋 실패: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    try:
        create_initial_users()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()