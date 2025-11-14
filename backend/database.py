"""
데이터베이스 설정
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 환경 변수에서 데이터베이스 URL 가져오기
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@db:5432/movie_reviews'
)

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL, echo=True)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()


def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 테이블 초기화"""
    from models.review import Review
    Base.metadata.create_all(bind=engine)
