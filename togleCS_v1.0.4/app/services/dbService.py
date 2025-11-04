'''
이젠오토 DB 관련된 함수들을 적어놓는 Service로직
'''

from app import db
from sqlalchemy import and_

# DB 삽입 함수.
def insert_DB(result_list, model_class):
    try:
        for data in result_list:
            instance = model_class(**data)
            db.session.add(instance)
        db.session.commit()
        print("✅ DB 저장 완료")
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB 저장 실패: {e}")

# DB 중복검사 및 정렬 함수.
def filter_dup(result_list, model_class, unique_fields):
    """
    result_list에서 DB에 존재하지 않는 항목만 필터링해서 반환
    :param result_list: [{...}, {...}, ...]
    :param model_class: SQLAlchemy 모델 클래스
    :param unique_fields: 중복 체크 기준 필드 이름 리스트 (예: ['q_question', 'q_date'])
    :return: DB에 없는 항목만 리스트로 반환
    """
    filtered = []

    for data in result_list:
        query = db.session.query(model_class)
        
        # 동적으로 filter 구성
        filters = [getattr(model_class, field) == data.get(field) for field in unique_fields]
        exists = query.filter(and_(*filters)).first()

        if not exists:
            filtered.append(data)

    return filtered
