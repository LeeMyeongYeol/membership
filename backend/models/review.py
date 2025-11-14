"""
리뷰 모델
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from database import Base


class Review(Base):
    """영화 리뷰 모델"""
    __tablename__ = 'reviews'
    
    # 게시글 번호 (PK)
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 영화 ID (TMDb ID)
    movie_id = Column(Integer, nullable=False, index=True)
    
    # 작성자 이름 (익명)
    author_name = Column(String(50), nullable=False)
    
    # 글 내용
    content = Column(Text, nullable=False)
    
    # 별점 (0.0 ~ 5.0)
    rating = Column(Float, nullable=False)
    
    # 작성일자
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'movie_id': self.movie_id,
            'author_name': self.author_name,
            'content': self.content,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }
