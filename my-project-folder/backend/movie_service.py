"""
영화 저장 및 조회 서비스
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import Movie, Genre, Keyword
from tmdb_service import get_movie_full_info
from typing import Optional, Dict, Any
from tfidf_service import generate_and_save_vector


async def save_movie_to_db(movie_id: int, db: Session) -> Optional[Movie]:
    """
    TMDb에서 영화 정보를 가져와 DB에 저장합니다.

    Args:
        movie_id: TMDb 영화 ID
        db: SQLAlchemy 세션

    Returns:
        저장된 Movie 객체 또는 None (에러 시)
    """
    # 1. 이미 DB에 있는지 확인
    existing_movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if existing_movie:
        print(f"Movie ID {movie_id} already exists in database")
        return existing_movie

    # 2. TMDb에서 영화 정보 가져오기
    movie_info = await get_movie_full_info(movie_id)
    if not movie_info:
        print(f"Failed to fetch movie info for ID {movie_id}")
        return None

    details = movie_info["details"]
    keywords = movie_info["keywords"]

    # 3. 영화 객체 생성
    try:
        # 날짜 파싱
        release_date = None
        if details.get("release_date"):
            try:
                release_date = datetime.strptime(details["release_date"], "%Y-%m-%d").date()
            except ValueError:
                print(f"Invalid date format: {details['release_date']}")

        # Movie 객체 생성
        movie = Movie(
            id=details["id"],
            title=details.get("title"),
            original_title=details.get("original_title"),
            release_date=release_date,
            overview=details.get("overview"),
            original_language=details.get("original_language"),
            popularity=details.get("popularity"),
            vote_average=details.get("vote_average"),
            vote_count=details.get("vote_count"),
            poster_path=details.get("poster_path"),
            backdrop_path=details.get("backdrop_path")
        )

        # 4. 장르 연결
        if details.get("genres"):
            for genre_data in details["genres"]:
                genre = db.query(Genre).filter(Genre.id == genre_data["id"]).first()
                if genre:
                    movie.genres.append(genre)

        # 5. 키워드 저장 및 연결
        if keywords:
            for keyword_data in keywords:
                # 키워드가 이미 있는지 확인
                keyword = db.query(Keyword).filter(Keyword.id == keyword_data["id"]).first()

                if not keyword:
                    # 없으면 새로 생성
                    keyword = Keyword(
                        id=keyword_data["id"],
                        name=keyword_data["name"]
                    )
                    db.add(keyword)

                movie.keywords.append(keyword)

        # 6. DB에 저장
        db.add(movie)
        db.commit()
        db.refresh(movie)

        print(f"✓ Movie '{movie.title}' saved successfully (ID: {movie.id})")

        # 7. TF-IDF 벡터 자동 생성 (실패해도 영화는 저장됨)
        try:
            print(f"  Generating TF-IDF vector for movie {movie.id}...")
            if generate_and_save_vector(movie, db):
                print(f"  ✓ Vector generated and saved")
            else:
                print(f"  ⚠ Vector generation failed, but movie is saved")
        except Exception as e:
            print(f"  ⚠ Vector generation error: {e}")
            # 벡터 생성 실패는 무시하고 계속 진행

        return movie

    except IntegrityError as e:
        db.rollback()
        print(f"Database integrity error: {e}")
        return None
    except Exception as e:
        db.rollback()
        print(f"Error saving movie: {e}")
        return None


def get_movie_by_id(movie_id: int, db: Session) -> Optional[Movie]:
    """
    DB에서 영화를 ID로 조회합니다.

    Args:
        movie_id: 영화 ID
        db: SQLAlchemy 세션

    Returns:
        Movie 객체 또는 None
    """
    return db.query(Movie).filter(Movie.id == movie_id).first()


def get_all_movies(db: Session, skip: int = 0, limit: int = 100):
    """
    DB에 저장된 모든 영화를 조회합니다.

    Args:
        db: SQLAlchemy 세션
        skip: 건너뛸 개수 (페이지네이션)
        limit: 가져올 최대 개수

    Returns:
        Movie 객체 리스트
    """
    return db.query(Movie).offset(skip).limit(limit).all()


def delete_movie(movie_id: int, db: Session) -> bool:
    """
    DB에서 영화를 삭제합니다.
    CASCADE 설정으로 관련 데이터(movie_genres, movie_keywords, movie_vectors)도 자동 삭제됩니다.

    Args:
        movie_id: 영화 ID
        db: SQLAlchemy 세션

    Returns:
        성공 시 True, 실패 시 False
    """
    try:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()

        if not movie:
            print(f"Movie ID {movie_id} not found")
            return False

        movie_title = movie.title
        db.delete(movie)
        db.commit()

        print(f"✓ Movie '{movie_title}' (ID: {movie_id}) deleted successfully")
        return True

    except Exception as e:
        db.rollback()
        print(f"Error deleting movie: {e}")
        return False


def movie_to_dict(movie: Movie) -> Dict[str, Any]:
    """
    Movie 객체를 딕셔너리로 변환 (JSON 응답용)

    Args:
        movie: Movie 객체

    Returns:
        영화 정보 딕셔너리
    """
    return {
        "id": movie.id,
        "title": movie.title,
        "original_title": movie.original_title,
        "release_date": movie.release_date.isoformat() if movie.release_date else None,
        "overview": movie.overview,
        "original_language": movie.original_language,
        "popularity": movie.popularity,
        "vote_average": movie.vote_average,
        "vote_count": movie.vote_count,
        "poster_path": movie.poster_path,
        "backdrop_path": movie.backdrop_path,
        "genres": [{"id": g.id, "name": g.name} for g in movie.genres],
        "keywords": [{"id": k.id, "name": k.name} for k in movie.keywords]
    }
