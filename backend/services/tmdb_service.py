"""
TMDb API 호출 서비스
"""
from typing import Dict, Any, List
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

import requests
from config import Config


# TMDb 장르 ID 매핑
GENRE_MAP = {
    "Action": 28, "액션": 28,
    "Adventure": 12, "모험": 12,
    "Animation": 16, "애니메이션": 16,
    "Comedy": 35, "코미디": 35,
    "Crime": 80, "범죄": 80,
    "Drama": 18, "드라마": 18,
    "Fantasy": 14, "판타지": 14,
    "Historical": 36, "사극": 36, "역사": 36,
    "Horror": 27, "공포": 27,
    "Musical": 10402, "뮤지컬": 10402,
    "Mystery": 9648, "미스터리": 9648,
    "Romance": 10749, "로맨스": 10749,
    "Sci-Fi": 878, "SF": 878, "공상과학": 878,
    "Thriller": 53, "스릴러": 53,
    "War": 10752, "전쟁": 10752,
    "Western": 37, "서부극": 37,
    "Documentary": 99, "다큐멘터리": 99,
    "Family": 10751, "가족": 10751,
    "Biography": 18, "전기": 18,
    "Sport": 18, "스포츠": 18
}

# 테마 → TMDb 파라미터 매핑
THEME_MAP = {
    "Now Playing": {"endpoint": "now_playing"},
    "현재 상영작": {"endpoint": "now_playing"},
    "Upcoming": {"endpoint": "upcoming"},
    "개봉 예정작": {"endpoint": "upcoming"},
    "Top Rated": {"endpoint": "top_rated"},
    "평점 높은 순": {"endpoint": "top_rated"},
    "Popular": {"endpoint": "popular"},
    "인기순": {"endpoint": "popular"},
    "Classic": {"sort_by": "vote_average.desc", "vote_count.gte": "1000", "primary_release_date.lte": "2000-12-31"},
    "고전 명작": {"sort_by": "vote_average.desc", "vote_count.gte": "1000", "primary_release_date.lte": "2000-12-31"},
}


class TMDbService:
    """TMDb API 서비스 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.base_url = Config.TMDB_BASE_URL
        self.image_base_url = Config.TMDB_IMAGE_BASE_URL
        self.api_key = Config.TMDB_API_KEY
    
    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """TMDb API GET 요청"""
        params = {"api_key": self.api_key, **params}
        response = self.session.get(
            f"{self.base_url}{path}", 
            params=params, 
            timeout=Config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    
    @lru_cache(maxsize=4096)
    def search_movie(self, title: str, lang: str = "ko-KR") -> Dict[str, Any]:
        """
        영화 제목으로 검색하여 가장 적합한 영화 반환
        
        Args:
            title: 검색할 영화 제목
            lang: 언어 코드 (기본값: ko-KR)
            
        Returns:
            영화 정보 딕셔너리 (없으면 빈 딕셔너리)
        """
        if not title.strip():
            return {}
        
        # 한국어로 검색
        data = self._get("/search/movie", {
            "query": title,
            "language": lang,
            "include_adult": False
        })
        results = data.get("results", [])
        
        # 결과가 없으면 영어로 재시도
        if not results:
            data = self._get("/search/movie", {
                "query": title,
                "language": "en-US",
                "include_adult": False
            })
            results = data.get("results", [])
            
            if not results:
                return {}
        
        # 인기도와 제목 유사도로 정렬
        title_lower = title.lower()
        for movie in results:
            movie["_popularity"] = movie.get("popularity", 0)
            name = (movie.get("title") or movie.get("original_title") or "").lower()
            if title_lower in name:
                movie["_popularity"] += 100
        
        best_match = sorted(results, key=lambda x: x["_popularity"], reverse=True)[0]
        return best_match
    
    @lru_cache(maxsize=8192)
    def get_movie_details(self, movie_id: int, lang: str = "ko-KR") -> Dict[str, Any]:
        """
        영화 상세 정보 조회 (키워드, 크레딧, 추천 영화 등 포함)
        
        Args:
            movie_id: TMDb 영화 ID
            lang: 언어 코드
            
        Returns:
            영화 프로필 딕셔너리
        """
        detail = self._get(f"/movie/{movie_id}", {
            "language": lang,
            "append_to_response": "keywords,credits,recommendations,external_ids,similar"
        })
        
        # 데이터 정규화
        genres = [g.get("name") for g in (detail.get("genres") or [])]
        keywords = [k.get("name") for k in ((detail.get("keywords") or {}).get("keywords") or [])]
        cast = [c.get("name") for c in ((detail.get("credits") or {}).get("cast") or [])[:10]]
        
        crew = (detail.get("credits") or {}).get("crew") or []
        directors = [c.get("name") for c in crew if c.get("job") == "Director"]
        writers = [c.get("name") for c in crew if c.get("job") in ("Writer", "Screenplay")]
        
        recommendations = ((detail.get("recommendations") or {}).get("results") or [])
        similars = ((detail.get("similar") or {}).get("results") or [])
        
        profile = {
            "id": detail.get("id"),
            "title": detail.get("title") or detail.get("original_title"),
            "overview": detail.get("overview") or "",
            "genres": genres,
            "keywords": keywords,
            "cast": cast,
            "directors": directors,
            "writers": writers,
            "poster": (
                self.image_base_url + detail.get("poster_path")
                if detail.get("poster_path") else None
            ),
            "vote_average": detail.get("vote_average"),
            "vote_count": detail.get("vote_count"),
            "release_date": detail.get("release_date"),
            "runtime": detail.get("runtime"),
            "lang": lang,
            "external_ids": detail.get("external_ids") or {},
            "candidate_ids": [
                m.get("id") 
                for m in recommendations[:30] + similars[:30] 
                if m.get("id")
            ],
        }
        return profile
    
    def get_bulk_movie_details(self, movie_ids: List[int], lang: str = "ko-KR") -> List[Dict[str, Any]]:
        """
        여러 영화의 상세 정보를 병렬로 조회
        
        Args:
            movie_ids: 영화 ID 리스트
            lang: 언어 코드
            
        Returns:
            영화 프로필 리스트
        """
        # 중복 제거하면서 순서 유지
        seen = set()
        unique_ids = []
        for movie_id in movie_ids:
            if movie_id not in seen:
                seen.add(movie_id)
                unique_ids.append(movie_id)
        
        results = []
        
        def fetch_movie(movie_id: int):
            try:
                return self.get_movie_details(movie_id, lang)
            except Exception:
                return None
        
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            for profile in executor.map(fetch_movie, unique_ids):
                if profile:
                    results.append(profile)
        
        return results
    
    def discover_movies(
        self,
        genres: List[str] = None,
        themes: List[str] = None,
        lang: str = "ko-KR",
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        장르, 테마 등으로 영화 발견
        
        Args:
            genres: 장르 리스트 (예: ["Action", "Comedy"])
            themes: 테마 리스트 (예: ["Popular", "Top Rated"])
            lang: 언어 코드
            page: 페이지 번호
            
        Returns:
            영화 리스트
        """
        print(f"[DEBUG] discover_movies called with genres={genres}, themes={themes}, lang={lang}, page={page}")
        
        # 장르 ID 변환
        genre_ids = []
        if genres:
            for genre in genres:
                # 괄호 안의 한글 제거 (예: "Action (액션)" -> "Action")
                genre_clean = genre.split("(")[0].strip()
                if genre_clean in GENRE_MAP:
                    genre_ids.append(GENRE_MAP[genre_clean])
                    print(f"[DEBUG] Genre '{genre_clean}' mapped to ID {GENRE_MAP[genre_clean]}")
        
        # 테마 처리
        endpoint = "discover/movie"
        params = {
            "language": lang,
            "page": page,
            "include_adult": False,
            "sort_by": "popularity.desc"
        }
        
        # 특별한 엔드포인트가 있는 테마 처리
        if themes:
            for theme in themes:
                theme_clean = theme.split("(")[0].strip()
                if theme_clean in THEME_MAP:
                    theme_config = THEME_MAP[theme_clean]
                    if "endpoint" in theme_config:
                        endpoint = f"movie/{theme_config['endpoint']}"
                        print(f"[DEBUG] Theme '{theme_clean}' changed endpoint to '{endpoint}'")
                        break
                    else:
                        params.update(theme_config)
                        print(f"[DEBUG] Theme '{theme_clean}' added params: {theme_config}")
        
        # 장르 ID 추가
        if genre_ids:
            params["with_genres"] = ",".join(map(str, genre_ids))
        
        print(f"[DEBUG] Final endpoint: {endpoint}, params: {params}")
        
        # API 호출
        try:
            data = self._get(f"/{endpoint}", params)
            results = data.get("results", [])
            print(f"[DEBUG] Got {len(results)} results from TMDb")
        except Exception as e:
            print(f"[ERROR] TMDb API call failed: {e}")
            raise
        
        # 결과 정규화
        movies = []
        for movie in results:
            movies.append({
                "id": movie.get("id"),
                "title": movie.get("title") or movie.get("original_title"),
                "year": (movie.get("release_date") or "")[:4],
                "poster": (
                    self.image_base_url + movie.get("poster_path")
                    if movie.get("poster_path") else None
                ),
                "source": "TMDb",
                "vote_average": movie.get("vote_average"),
                "vote_count": movie.get("vote_count"),
                "overview": movie.get("overview") or ""
            })
        
        return movies


# 싱글톤 인스턴스
tmdb_service = TMDbService()
