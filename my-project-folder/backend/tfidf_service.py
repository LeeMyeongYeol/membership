"""
TF-IDF 벡터 생성 및 관리 서비스
"""

import os
import pickle
import numpy as np
from typing import List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from konlpy.tag import Okt
from sqlalchemy.orm import Session
from models import Movie, MovieVector


# 벡터 차원 (pgvector 설정에 맞춤)
VECTOR_DIM = 512

# Vectorizer 저장 경로
VECTORIZER_PATH = '/app/data/tfidf_vectorizer.pkl'


class KoreanTokenizer:
    """한국어 형태소 분석기"""

    def __init__(self):
        self.okt = Okt()

    def __call__(self, text: str) -> List[str]:
        """
        텍스트를 형태소 단위로 토크나이징

        Args:
            text: 입력 텍스트

        Returns:
            형태소 리스트
        """
        if not text:
            return []

        # 명사, 동사, 형용사만 추출
        morphs = self.okt.pos(text, stem=True)
        return [word for word, pos in morphs if pos in ['Noun', 'Verb', 'Adjective']]


def create_movie_text(movie: Movie) -> str:
    """
    영화 객체로부터 TF-IDF 계산용 텍스트 생성

    Args:
        movie: Movie 객체

    Returns:
        장르 + 줄거리 + 키워드를 결합한 텍스트

    가중치 전략:
        - 장르: 5배 (영화 선택에 가장 중요한 요소)
        - 줄거리: 3배 (영화 내용과 분위기 파악)
        - 키워드: 2배 (보조적 특징)
    """
    parts = []

    # 장르 추가 (가중치 5: 영화 취향의 핵심)
    if movie.genres:
        genre_text = ' '.join([g.name for g in movie.genres])
        parts.extend([genre_text] * 5)

    # 줄거리 추가 (가중치 3: 영화 내용과 분위기)
    if movie.overview:
        parts.extend([movie.overview] * 3)

    # 키워드 추가 (가중치 2: 세부 특징)
    if movie.keywords:
        keyword_text = ' '.join([k.name for k in movie.keywords])
        parts.extend([keyword_text] * 2)

    return ' '.join(parts)


def pad_or_truncate_vector(vector: np.ndarray, target_dim: int) -> np.ndarray:
    """
    벡터를 목표 차원에 맞게 패딩 또는 잘라냄

    Args:
        vector: 입력 벡터
        target_dim: 목표 차원

    Returns:
        변환된 벡터
    """
    current_dim = vector.shape[0]

    if current_dim == target_dim:
        return vector
    elif current_dim > target_dim:
        # 잘라내기 (상위 중요도 유지)
        return vector[:target_dim]
    else:
        # 패딩 (0으로 채우기)
        return np.pad(vector, (0, target_dim - current_dim), mode='constant')


def create_and_train_vectorizer(movies: List[Movie]) -> TfidfVectorizer:
    """
    영화 데이터로 TfidfVectorizer 학습

    Args:
        movies: 영화 객체 리스트

    Returns:
        학습된 TfidfVectorizer
    """
    print(f"Creating TF-IDF vectorizer with {len(movies)} movies...")

    # 영화 텍스트 생성
    texts = [create_movie_text(movie) for movie in movies]

    # 한국어 토크나이저 생성
    tokenizer = KoreanTokenizer()

    # TfidfVectorizer 생성 및 학습
    vectorizer = TfidfVectorizer(
        tokenizer=tokenizer,
        max_features=VECTOR_DIM,  # 상위 512개 특징만 사용
        min_df=2,  # 최소 2개 문서에 등장 (너무 희귀한 단어 제거)
        max_df=0.7,  # 최대 70% 문서에 등장 (너무 흔한 단어 제거)
        sublinear_tf=True,  # TF에 로그 스케일 적용
        norm='l2',  # L2 정규화
        ngram_range=(1, 2)  # 1-gram과 2-gram 모두 사용 (문맥 파악)
    )

    vectorizer.fit(texts)

    print(f"Vectorizer trained with {len(vectorizer.vocabulary_)} features")

    return vectorizer


def save_vectorizer(vectorizer: TfidfVectorizer) -> None:
    """
    Vectorizer를 파일로 저장
    (Java 객체인 tokenizer는 저장할 수 없으므로 제거 후 저장)

    Args:
        vectorizer: TfidfVectorizer 객체
    """
    # 디렉토리 생성
    os.makedirs(os.path.dirname(VECTORIZER_PATH), exist_ok=True)

    # tokenizer를 임시로 제거 (Java 객체는 pickle 불가)
    original_tokenizer = vectorizer.tokenizer
    vectorizer.tokenizer = None

    try:
        with open(VECTORIZER_PATH, 'wb') as f:
            pickle.dump(vectorizer, f)
        print(f"Vectorizer saved to {VECTORIZER_PATH}")
    finally:
        # tokenizer 복구
        vectorizer.tokenizer = original_tokenizer


def load_vectorizer() -> Optional[TfidfVectorizer]:
    """
    저장된 Vectorizer 로드
    (저장 시 제거된 tokenizer를 다시 추가)

    Returns:
        TfidfVectorizer 객체 또는 None (파일이 없을 경우)
    """
    if not os.path.exists(VECTORIZER_PATH):
        print(f"Vectorizer file not found: {VECTORIZER_PATH}")
        return None

    with open(VECTORIZER_PATH, 'rb') as f:
        vectorizer = pickle.load(f)

    # 한국어 tokenizer 다시 추가
    vectorizer.tokenizer = KoreanTokenizer()

    print(f"Vectorizer loaded from {VECTORIZER_PATH}")
    return vectorizer


def generate_tfidf_vector(
    movie: Movie,
    vectorizer: Optional[TfidfVectorizer] = None
) -> np.ndarray:
    """
    단일 영화에 대한 TF-IDF 벡터 생성

    Args:
        movie: Movie 객체
        vectorizer: 사전 학습된 TfidfVectorizer (없으면 로드 시도)

    Returns:
        TF-IDF 벡터 (512차원)
    """
    if vectorizer is None:
        vectorizer = load_vectorizer()
        if vectorizer is None:
            raise ValueError("Vectorizer not found. Please run batch generation first.")

    # 텍스트 생성
    text = create_movie_text(movie)

    # TF-IDF 벡터 생성
    tfidf_vector = vectorizer.transform([text]).toarray()[0]

    # 512차원으로 맞추기
    vector_512 = pad_or_truncate_vector(tfidf_vector, VECTOR_DIM)

    return vector_512


def save_movie_vector(movie_id: int, vector: np.ndarray, db: Session) -> bool:
    """
    영화 벡터를 데이터베이스에 저장

    Args:
        movie_id: 영화 ID
        vector: TF-IDF 벡터
        db: SQLAlchemy 세션

    Returns:
        성공 여부
    """
    try:
        # 기존 벡터 확인
        existing = db.query(MovieVector).filter(MovieVector.movie_id == movie_id).first()

        if existing:
            # 업데이트
            existing.tfidf_vector = vector.tolist()
            print(f"Updated vector for movie ID {movie_id}")
        else:
            # 새로 생성
            movie_vector = MovieVector(
                movie_id=movie_id,
                tfidf_vector=vector.tolist()
            )
            db.add(movie_vector)
            print(f"Created vector for movie ID {movie_id}")

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        print(f"Error saving vector for movie {movie_id}: {e}")
        return False


def generate_and_save_vector(movie: Movie, db: Session) -> bool:
    """
    영화의 TF-IDF 벡터를 생성하고 저장

    Args:
        movie: Movie 객체
        db: SQLAlchemy 세션

    Returns:
        성공 여부
    """
    try:
        # 벡터 생성
        vector = generate_tfidf_vector(movie)

        # 저장
        return save_movie_vector(movie.id, vector, db)

    except Exception as e:
        print(f"Error generating vector for movie {movie.id}: {e}")
        return False
