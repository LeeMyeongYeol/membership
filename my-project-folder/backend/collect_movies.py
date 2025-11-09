#!/usr/bin/env python3
"""
TMDb API에서 영화를 대량으로 수집하는 스크립트

다양한 카테고리에서 영화를 수집하여 데이터베이스에 저장합니다:
- 인기 영화 (popular)
- 평점 높은 영화 (top_rated)
- 현재 상영 중 (now_playing)
- 개봉 예정 (upcoming)
- 장르별 영화 (discover)

Usage:
    python collect_movies.py --limit 500
    python collect_movies.py --categories popular top_rated --limit 200
"""

import os
import sys
import asyncio
import argparse
import httpx
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Movie
from movie_service import save_movie_to_db


TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# 수집 가능한 카테고리
CATEGORIES = {
    "popular": "인기 영화",
    "top_rated": "평점 높은 영화",
    "now_playing": "현재 상영 중",
    "upcoming": "개봉 예정"
}

# TMDb 장르 ID
GENRE_IDS = {
    28: "액션",
    12: "모험",
    16: "애니메이션",
    35: "코미디",
    80: "범죄",
    99: "다큐멘터리",
    18: "드라마",
    10751: "가족",
    14: "판타지",
    36: "역사",
    27: "공포",
    10402: "음악",
    9648: "미스터리",
    10749: "로맨스",
    878: "SF",
    10770: "TV 영화",
    53: "스릴러",
    10752: "전쟁",
    37: "서부"
}


async def fetch_movies_from_category(
    category: str,
    page: int = 1,
    language: str = "ko-KR"
) -> List[Dict[str, Any]]:
    """
    특정 카테고리에서 영화 목록 가져오기

    Args:
        category: 카테고리 (popular, top_rated, now_playing, upcoming)
        page: 페이지 번호 (1-500)
        language: 언어 코드

    Returns:
        영화 정보 리스트
    """
    if not TMDB_API_KEY:
        print("Error: TMDB_API_KEY is not set")
        return []

    url = f"{TMDB_BASE_URL}/movie/{category}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": language,
        "page": page
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            print(f"  ✗ Error fetching {category} page {page}: {e}")
            return []


async def fetch_movies_by_genre(
    genre_id: int,
    page: int = 1,
    language: str = "ko-KR"
) -> List[Dict[str, Any]]:
    """
    특정 장르의 영화 목록 가져오기

    Args:
        genre_id: 장르 ID
        page: 페이지 번호
        language: 언어 코드

    Returns:
        영화 정보 리스트
    """
    if not TMDB_API_KEY:
        print("Error: TMDB_API_KEY is not set")
        return []

    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "language": language,
        "page": page,
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "vote_count.gte": 100  # 최소 100표 이상
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            print(f"  ✗ Error fetching genre {genre_id} page {page}: {e}")
            return []


async def collect_movies_from_categories(
    categories: List[str],
    max_per_category: int = 100
) -> Set[int]:
    """
    여러 카테고리에서 영화 ID 수집

    Args:
        categories: 수집할 카테고리 리스트
        max_per_category: 카테고리당 최대 수집 개수

    Returns:
        수집된 영화 ID 집합
    """
    movie_ids = set()
    pages_per_category = (max_per_category + 19) // 20  # 페이지당 20개

    for category in categories:
        print(f"\n[Category: {CATEGORIES.get(category, category)}]")

        for page in range(1, pages_per_category + 1):
            movies = await fetch_movies_from_category(category, page)

            if not movies:
                break

            for movie in movies:
                movie_ids.add(movie["id"])

            print(f"  Page {page}: {len(movies)} movies fetched (Total unique: {len(movie_ids)})")

            # API 호출 제한 방지 (작은 지연)
            await asyncio.sleep(0.25)

    return movie_ids


async def collect_movies_from_genres(
    max_per_genre: int = 20
) -> Set[int]:
    """
    다양한 장르에서 영화 ID 수집

    Args:
        max_per_genre: 장르당 최대 수집 개수

    Returns:
        수집된 영화 ID 집합
    """
    movie_ids = set()
    pages_per_genre = (max_per_genre + 19) // 20  # 페이지당 20개

    print(f"\n[Collecting from {len(GENRE_IDS)} genres]")

    for genre_id, genre_name in GENRE_IDS.items():
        print(f"  Genre: {genre_name} (ID: {genre_id})")

        for page in range(1, pages_per_genre + 1):
            movies = await fetch_movies_by_genre(genre_id, page)

            if not movies:
                break

            for movie in movies:
                movie_ids.add(movie["id"])

            # API 호출 제한 방지
            await asyncio.sleep(0.25)

        print(f"    → Added {len(movies)} movies (Total unique: {len(movie_ids)})")

    return movie_ids


async def save_collected_movies(movie_ids: Set[int], db: Session):
    """
    수집된 영화 ID를 데이터베이스에 저장

    Args:
        movie_ids: 영화 ID 집합
        db: SQLAlchemy 세션
    """
    print(f"\n{'='*60}")
    print(f"Saving {len(movie_ids)} movies to database")
    print(f"{'='*60}")

    success_count = 0
    skip_count = 0
    error_count = 0

    for i, movie_id in enumerate(sorted(movie_ids), 1):
        print(f"\n[{i}/{len(movie_ids)}] Movie ID: {movie_id}")

        # 이미 저장된 영화인지 확인
        existing = db.query(Movie).filter(Movie.id == movie_id).first()
        if existing:
            print(f"  ⊘ Already exists: {existing.title}")
            skip_count += 1
            continue

        # 영화 저장
        try:
            movie = await save_movie_to_db(movie_id, db)
            if movie:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"  ✗ Error saving movie: {e}")
            error_count += 1

        # API 호출 제한 방지
        await asyncio.sleep(0.3)

    # 결과 요약
    print(f"\n{'='*60}")
    print("Collection Summary")
    print(f"{'='*60}")
    print(f"Total unique IDs:  {len(movie_ids)}")
    print(f"Successfully saved: {success_count}")
    print(f"Already existed:    {skip_count}")
    print(f"Errors:             {error_count}")
    print(f"{'='*60}")


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Collect movies from TMDb API")
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Total number of movies to collect (default: 500)"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
        help="Categories to collect from (default: all)"
    )
    parser.add_argument(
        "--include-genres",
        action="store_true",
        help="Also collect from different genres"
    )

    args = parser.parse_args()

    print("="*60)
    print("TMDb Movie Collection Script")
    print("="*60)
    print(f"Target: {args.limit} movies")
    print(f"Categories: {', '.join([CATEGORIES[c] for c in args.categories])}")
    print(f"Include genres: {args.include_genres}")
    print("="*60)

    # 영화 ID 수집
    movie_ids = set()

    # 카테고리에서 수집
    max_per_category = args.limit // len(args.categories)
    category_ids = await collect_movies_from_categories(args.categories, max_per_category)
    movie_ids.update(category_ids)

    # 장르에서 추가 수집 (옵션)
    if args.include_genres:
        remaining = args.limit - len(movie_ids)
        if remaining > 0:
            max_per_genre = max(10, remaining // len(GENRE_IDS))
            genre_ids = await collect_movies_from_genres(max_per_genre)
            movie_ids.update(genre_ids)

    print(f"\nCollected {len(movie_ids)} unique movie IDs")

    # 제한 수만큼만 저장
    if len(movie_ids) > args.limit:
        movie_ids = set(list(movie_ids)[:args.limit])
        print(f"Limiting to {args.limit} movies")

    # 데이터베이스에 저장
    db = SessionLocal()
    try:
        await save_collected_movies(movie_ids, db)
    finally:
        db.close()

    print("\n✓ Collection completed!")


if __name__ == "__main__":
    asyncio.run(main())
