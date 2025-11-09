"""
TMDb API 서비스
영화 상세 정보, 키워드, 장르 등을 가져오는 함수들
"""

import os
import httpx
from typing import Optional, Dict, Any

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


async def get_movie_details(movie_id: int) -> Optional[Dict[str, Any]]:
    """
    TMDb API에서 영화 상세 정보를 가져옵니다.

    Args:
        movie_id: TMDb 영화 ID

    Returns:
        영화 상세 정보 딕셔너리 또는 None (에러 시)
    """
    if not TMDB_API_KEY:
        print("Error: TMDB_API_KEY is not set")
        return None

    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ko-KR"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching movie details for ID {movie_id}: {e}")
            return None


async def get_movie_keywords(movie_id: int) -> Optional[list]:
    """
    TMDb API에서 영화 키워드를 가져옵니다.

    Args:
        movie_id: TMDb 영화 ID

    Returns:
        키워드 리스트 또는 None (에러 시)
    """
    if not TMDB_API_KEY:
        print("Error: TMDB_API_KEY is not set")
        return None

    url = f"{TMDB_BASE_URL}/movie/{movie_id}/keywords"
    params = {
        "api_key": TMDB_API_KEY
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("keywords", [])
        except httpx.HTTPError as e:
            print(f"Error fetching keywords for movie ID {movie_id}: {e}")
            return None


async def get_movie_full_info(movie_id: int) -> Optional[Dict[str, Any]]:
    """
    영화의 모든 정보를 한 번에 가져옵니다.
    (상세 정보 + 키워드)

    Args:
        movie_id: TMDb 영화 ID

    Returns:
        {
            "details": {...},  # 영화 상세 정보
            "keywords": [...]  # 키워드 리스트
        }
    """
    details = await get_movie_details(movie_id)
    keywords = await get_movie_keywords(movie_id)

    if details is None:
        return None

    return {
        "details": details,
        "keywords": keywords or []
    }
