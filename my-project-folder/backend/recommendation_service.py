"""
영화 추천 서비스

사용자의 취향을 분석하여 유사한 영화를 추천합니다.
pgvector의 코사인 유사도를 활용합니다.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import Movie, MovieVector
from tfidf_service import generate_and_save_vector


def get_user_preference_vector(movie_ids: List[int], db: Session) -> Optional[np.ndarray]:
    """
    사용자가 선택한 영화들의 벡터를 평균내어 취향 벡터를 생성

    Args:
        movie_ids: 사용자가 좋아하는 영화 ID 리스트
        db: SQLAlchemy 세션

    Returns:
        취향 벡터 (512차원) 또는 None
    """
    if not movie_ids:
        print("No movie IDs provided")
        return None

    # 선택한 영화들의 벡터 가져오기
    vectors = []
    for movie_id in movie_ids:
        movie_vector = db.query(MovieVector).filter(MovieVector.movie_id == movie_id).first()

        if movie_vector is not None and movie_vector.tfidf_vector is not None:
            vectors.append(np.array(movie_vector.tfidf_vector))
        else:
            print(f"Warning: No vector found for movie ID {movie_id}")

    if not vectors:
        print("No vectors found for selected movies")
        return None

    # 벡터들의 평균 계산
    preference_vector = np.mean(vectors, axis=0)

    # L2 정규화 (코사인 유사도 계산을 위해)
    norm = np.linalg.norm(preference_vector)
    if norm > 0:
        preference_vector = preference_vector / norm

    print(f"Created preference vector from {len(vectors)} movies")
    return preference_vector


def recommend_movies(
    user_movie_ids: List[int],
    db: Session,
    limit: int = 10,
    exclude_selected: bool = True
) -> List[Dict[str, Any]]:
    """
    사용자 취향 기반 영화 추천

    Args:
        user_movie_ids: 사용자가 좋아하는 영화 ID 리스트
        db: SQLAlchemy 세션
        limit: 추천할 영화 개수
        exclude_selected: 선택한 영화를 추천에서 제외할지 여부

    Returns:
        추천 영화 리스트 (유사도 점수 포함)
    """
    # 1. 취향 벡터 생성
    preference_vector = get_user_preference_vector(user_movie_ids, db)

    if preference_vector is None:
        return []

    # 2. pgvector를 사용한 코사인 유사도 검색
    # pgvector는 <=> 연산자로 코사인 거리를 계산 (1 - 코사인 유사도)
    # 따라서 거리가 작을수록 유사함

    vector_str = '[' + ','.join(map(str, preference_vector)) + ']'

    if exclude_selected:
        # 선택한 영화 제외
        excluded_ids = ','.join(map(str, user_movie_ids))
        query = text(f"""
            SELECT
                m.id,
                m.title,
                m.original_title,
                m.release_date,
                m.overview,
                m.vote_average,
                m.poster_path,
                1 - (mv.tfidf_vector <=> '{vector_str}'::vector) as similarity
            FROM movies m
            JOIN movie_vectors mv ON m.id = mv.movie_id
            WHERE m.id NOT IN ({excluded_ids})
            ORDER BY mv.tfidf_vector <=> '{vector_str}'::vector
            LIMIT :limit
        """)
    else:
        query = text(f"""
            SELECT
                m.id,
                m.title,
                m.original_title,
                m.release_date,
                m.overview,
                m.vote_average,
                m.poster_path,
                1 - (mv.tfidf_vector <=> '{vector_str}'::vector) as similarity
            FROM movies m
            JOIN movie_vectors mv ON m.id = mv.movie_id
            ORDER BY mv.tfidf_vector <=> '{vector_str}'::vector
            LIMIT :limit
        """)

    try:
        result = db.execute(query, {"limit": limit})
        rows = result.fetchall()

        recommendations = []
        for row in rows:
            # 장르와 키워드는 별도로 로드
            movie = db.query(Movie).filter(Movie.id == row.id).first()

            recommendations.append({
                "id": row.id,
                "title": row.title,
                "original_title": row.original_title,
                "release_date": row.release_date.isoformat() if row.release_date else None,
                "overview": row.overview,
                "vote_average": float(row.vote_average) if row.vote_average else None,
                "poster_path": row.poster_path,
                "similarity": float(row.similarity),
                "similarity_percent": round(float(row.similarity) * 100, 1),
                "genres": [{"id": g.id, "name": g.name} for g in movie.genres] if movie else [],
                "keywords": [{"id": k.id, "name": k.name} for k in movie.keywords] if movie else []
            })

        print(f"Found {len(recommendations)} recommendations")
        return recommendations

    except Exception as e:
        print(f"Error during recommendation: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_similar_movies(
    movie_id: int,
    db: Session,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    특정 영화와 유사한 영화 추천

    Args:
        movie_id: 기준 영화 ID
        db: SQLAlchemy 세션
        limit: 추천할 영화 개수

    Returns:
        유사 영화 리스트
    """
    # 기준 영화의 벡터 가져오기
    movie_vector = db.query(MovieVector).filter(MovieVector.movie_id == movie_id).first()

    if movie_vector is None or movie_vector.tfidf_vector is None:
        print(f"No vector found for movie ID {movie_id}")
        return []

    vector = np.array(movie_vector.tfidf_vector)
    vector_str = '[' + ','.join(map(str, vector)) + ']'

    # 유사한 영화 검색 (자기 자신 제외)
    query = text(f"""
        SELECT
            m.id,
            m.title,
            m.original_title,
            m.release_date,
            m.overview,
            m.vote_average,
            m.poster_path,
            1 - (mv.tfidf_vector <=> '{vector_str}'::vector) as similarity
        FROM movies m
        JOIN movie_vectors mv ON m.id = mv.movie_id
        WHERE m.id != :movie_id
        ORDER BY mv.tfidf_vector <=> '{vector_str}'::vector
        LIMIT :limit
    """)

    try:
        result = db.execute(query, {"movie_id": movie_id, "limit": limit})
        rows = result.fetchall()

        similar_movies = []
        for row in rows:
            movie = db.query(Movie).filter(Movie.id == row.id).first()

            similar_movies.append({
                "id": row.id,
                "title": row.title,
                "original_title": row.original_title,
                "release_date": row.release_date.isoformat() if row.release_date else None,
                "overview": row.overview,
                "vote_average": float(row.vote_average) if row.vote_average else None,
                "poster_path": row.poster_path,
                "similarity": float(row.similarity),
                "similarity_percent": round(float(row.similarity) * 100, 1),
                "genres": [{"id": g.id, "name": g.name} for g in movie.genres] if movie else [],
                "keywords": [{"id": k.id, "name": k.name} for k in movie.keywords] if movie else []
            })

        print(f"Found {len(similar_movies)} similar movies to ID {movie_id}")
        return similar_movies

    except Exception as e:
        print(f"Error finding similar movies: {e}")
        import traceback
        traceback.print_exc()
        return []


def ensure_vectors_exist(movie_ids: List[int], db: Session) -> Dict[str, Any]:
    """
    영화들의 벡터가 존재하는지 확인하고, 없으면 생성

    Args:
        movie_ids: 확인할 영화 ID 리스트
        db: SQLAlchemy 세션

    Returns:
        생성 결과 정보
    """
    result = {
        "total": len(movie_ids),
        "already_exists": 0,
        "newly_created": 0,
        "failed": 0,
        "failed_ids": []
    }

    for movie_id in movie_ids:
        # 벡터 존재 여부 확인
        existing_vector = db.query(MovieVector).filter(MovieVector.movie_id == movie_id).first()

        if existing_vector is not None:
            result["already_exists"] += 1
            print(f"Vector already exists for movie ID {movie_id}")
            continue

        # 벡터가 없으면 생성
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            print(f"Movie ID {movie_id} not found in database")
            result["failed"] += 1
            result["failed_ids"].append(movie_id)
            continue

        print(f"Generating vector for movie: {movie.title} (ID: {movie_id})")
        try:
            success = generate_and_save_vector(movie, db)
            if success:
                result["newly_created"] += 1
                print(f"  ✓ Vector created successfully")
            else:
                result["failed"] += 1
                result["failed_ids"].append(movie_id)
                print(f"  ✗ Failed to create vector")
        except Exception as e:
            result["failed"] += 1
            result["failed_ids"].append(movie_id)
            print(f"  ✗ Error creating vector: {e}")

    return result


def get_recommendation_stats(db: Session) -> Dict[str, int]:
    """
    추천 시스템 통계 정보

    Args:
        db: SQLAlchemy 세션

    Returns:
        통계 정보 딕셔너리
    """
    total_movies = db.query(Movie).count()
    vectorized_movies = db.query(MovieVector).count()

    return {
        "total_movies": total_movies,
        "vectorized_movies": vectorized_movies,
        "ready_for_recommendation": vectorized_movies > 0,
        "coverage_percent": round((vectorized_movies / total_movies * 100), 1) if total_movies > 0 else 0
    }
