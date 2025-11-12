"""
Flask API 라우트
"""
from typing import List
from flask import Blueprint, request, jsonify

from config import Config
from services.tmdb_service import tmdb_service
from services.omdb_service import omdb_service
from services.recommendation import recommendation_service

api_bp = Blueprint('api', __name__)


@api_bp.route('/')
def health_check():
    """API 헬스 체크"""
    return jsonify({
        "status": "ok",
        "message": "Movie Recommendation API",
        "version": "2.0",
        "endpoints": {
            "analyze": "/api/analyze",
            "discover": "/api/discover"
        },
        "config": {
            "tmdb_configured": bool(Config.TMDB_API_KEY),
            "omdb_configured": bool(Config.OMDB_API_KEY)
        }
    })


@api_bp.route('/api/analyze', methods=['POST'])
def analyze():
    """
    영화 취향 분석 및 추천 API
    
    Request Body:
        titles: List[str] - 좋아하는 영화 제목 리스트
        language: str - 언어 코드 (기본값: ko-KR)
    
    Response:
        favorites: 입력한 영화 정보
        top_features: TF-IDF 상위 특징
        top_genres: 상위 장르
        top_directors: 상위 감독
        top_actors: 상위 배우
        recommendations: 추천 영화 리스트
    """
    try:
        data = request.get_json(force=True)
        titles: List[str] = data.get("titles", [])
        lang: str = data.get("language", "ko-KR")
        
        # 1. 영화 제목 → TMDb ID 변환
        resolved_ids = []
        for title in titles:
            try:
                movie = tmdb_service.search_movie(title, lang)
                if movie:
                    movie_id = movie.get("id")
                    if movie_id:
                        resolved_ids.append(movie_id)
            except Exception:
                continue
        
        if not resolved_ids:
            return jsonify({
                "error": "입력한 제목으로 TMDb에서 영화를 찾을 수 없습니다."
            }), 400
        
        # 2. 좋아하는 영화들의 프로필 조회
        favorite_profiles = tmdb_service.get_bulk_movie_details(resolved_ids, lang)
        
        # 3. TF-IDF 프로필 생성
        try:
            vectorizer, user_vector, top_features = recommendation_service.create_tfidf_profile(
                favorite_profiles
            )
        except Exception as e:
            return jsonify({"error": f"TF-IDF 분석 실패: {str(e)}"}), 500
        
        # 4. 후보 영화 풀 생성 (추천/유사 영화들)
        candidate_ids = []
        for profile in favorite_profiles:
            candidate_ids.extend(profile.get("candidate_ids") or [])
        
        # 중복 제거 및 제한
        candidate_ids = list(dict.fromkeys(candidate_ids))[:Config.CANDIDATE_LIMIT]
        candidates = tmdb_service.get_bulk_movie_details(candidate_ids, lang)
        
        # 5. 추천 점수 계산
        exclude_ids = {p.get("id") for p in favorite_profiles}
        scored_movies = recommendation_service.score_candidates(
            vectorizer,
            user_vector,
            candidates,
            exclude_ids
        )
        
        # 6. 상위 N개 선택 및 OMDb 정보 보강
        top_movies = scored_movies[:Config.TOP_N]
        recommendations = []
        
        for idx, (score, profile) in enumerate(top_movies, start=1):
            # 상위 일부만 OMDb 정보 추가 (API 호출 절약)
            if idx <= Config.ENRICH_TOP:
                profile = omdb_service.enrich_movie_profile(profile)
            
            recommendations.append({
                "score": float(score),
                "id": profile.get("id"),
                "title": profile.get("title"),
                "overview": profile.get("overview"),
                "poster": profile.get("poster"),
                "genres": profile.get("genres"),
                "vote_average": profile.get("vote_average"),
                "vote_count": profile.get("vote_count"),
                "release_date": profile.get("release_date"),
                "runtime": profile.get("runtime"),
                "omdb": profile.get("omdb"),
            })
        
        # 7. 패턴 분석
        patterns = recommendation_service.analyze_patterns(favorite_profiles)
        
        # 8. 응답 구성
        response = {
            "favorites": [
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "poster": p.get("poster")
                }
                for p in favorite_profiles
            ],
            "top_features": top_features,
            "top_genres": patterns["top_genres"],
            "top_directors": patterns["top_directors"],
            "top_actors": patterns["top_actors"],
            "recommendations": recommendations,
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500


@api_bp.route('/api/discover', methods=['POST'])
def discover():
    """
    장르, 테마 기반 영화 발견 API
    
    Request Body:
        genres: List[str] - 장르 리스트 (예: ["Action", "Comedy"])
        themes: List[str] - 테마 리스트 (예: ["Popular", "Top Rated"])
        language: str - 언어 코드 (기본값: ko-KR)
        page: int - 페이지 번호 (기본값: 1)
    
    Response:
        items: 영화 리스트
        total: 총 영화 수
        page: 현재 페이지
    """
    try:
        data = request.get_json(force=True)
        genres = data.get("genres", [])
        themes = data.get("themes", [])
        lang = data.get("language", "ko-KR")
        page = data.get("page", 1)
        
        # TMDb discover API 호출
        movies = tmdb_service.discover_movies(
            genres=genres,
            themes=themes,
            lang=lang,
            page=page
        )
        
        return jsonify({
            "items": movies,
            "total": len(movies),
            "page": page
        })
    
    except Exception as e:
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500
