from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, Table, TIMESTAMP
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()

# 영화-장르 매핑 테이블 (다대다 관계)
movie_genres = Table(
    'movie_genres',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True)
)

# 영화-키워드 매핑 테이블 (다대다 관계)
movie_keywords = Table(
    'movie_keywords',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True),
    Column('keyword_id', Integer, ForeignKey('keywords.id', ondelete='CASCADE'), primary_key=True)
)


class Movie(Base):
    """영화 메타데이터 모델"""
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)  # TMDb movie ID
    title = Column(String(500), nullable=False)
    original_title = Column(String(500))
    release_date = Column(Date)
    overview = Column(Text)  # 영화 줄거리
    original_language = Column(String(10))
    popularity = Column(Float)
    vote_average = Column(Float)
    vote_count = Column(Integer)
    poster_path = Column(String(200))
    backdrop_path = Column(String(200))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    genres = relationship('Genre', secondary=movie_genres, back_populates='movies')
    keywords = relationship('Keyword', secondary=movie_keywords, back_populates='movies')
    vector = relationship('MovieVector', back_populates='movie', uselist=False)

    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}', release_date={self.release_date})>"


class Genre(Base):
    """장르 모델"""
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)  # TMDb genre ID
    name = Column(String(100), nullable=False)

    # 관계 설정
    movies = relationship('Movie', secondary=movie_genres, back_populates='genres')

    def __repr__(self):
        return f"<Genre(id={self.id}, name='{self.name}')>"


class Keyword(Base):
    """키워드 모델"""
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)  # TMDb keyword ID
    name = Column(String(200), nullable=False, unique=True)

    # 관계 설정
    movies = relationship('Movie', secondary=movie_keywords, back_populates='keywords')

    def __repr__(self):
        return f"<Keyword(id={self.id}, name='{self.name}')>"


class MovieVector(Base):
    """영화 TF-IDF 벡터 모델"""
    __tablename__ = 'movie_vectors'

    movie_id = Column(Integer, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True)
    tfidf_vector = Column(Vector(512))  # TF-IDF 벡터 (차원: 512)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    movie = relationship('Movie', back_populates='vector')

    def __repr__(self):
        return f"<MovieVector(movie_id={self.movie_id})>"
