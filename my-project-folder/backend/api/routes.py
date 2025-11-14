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
            "discover": "/api/discover",
            "streaming_single": "/api/streaming/<movie_id>",
            "streaming_bulk": "/api/streaming/bulk"
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


@api_bp.route('/api/streaming/<int:movie_id>', methods=['GET'])
def get_streaming(movie_id: int):
    """
    특정 영화의 스트리밍 제공 정보 조회 API
    
    Path Parameters:
        movie_id: int - TMDb 영화 ID
    
    Query Parameters:
        region: str - 국가 코드 (기본값: KR)
                     KR(한국), US(미국), JP(일본), GB(영국), CN(중국) 등
    
    Response:
        movie_id: 영화 ID
        region: 국가 코드
        link: TMDb Watch 페이지 URL
        flatrate: 구독형 OTT 리스트 (Netflix, Disney+ 등)
        rent: 대여 가능 플랫폼 리스트
        buy: 구매 가능 플랫폼 리스트
        free: 무료 스트리밍 플랫폼 리스트
        ads: 광고 포함 무료 플랫폼 리스트
    
    Example:
        GET /api/streaming/550?region=KR
        GET /api/streaming/550?region=US
    """
    try:
        region = request.args.get('region', 'KR').upper()
        
        streaming_info = tmdb_service.get_streaming_providers(movie_id, region)
        
        # 결과가 비어있는지 확인
        has_providers = any([
            streaming_info.get('flatrate'),
            streaming_info.get('rent'),
            streaming_info.get('buy'),
            streaming_info.get('free'),
            streaming_info.get('ads')
        ])
        
        if not has_providers and not streaming_info.get('error'):
            return jsonify({
                **streaming_info,
                "message": f"{region} 지역에서 사용 가능한 스트리밍 정보가 없습니다."
            })
        
        return jsonify(streaming_info)
    
    except Exception as e:
        return jsonify({
            "error": f"스트리밍 정보 조회 실패: {str(e)}"
        }), 500


@api_bp.route('/api/streaming/bulk', methods=['POST'])
def get_streaming_bulk():
    """
    여러 영화의 스트리밍 제공 정보를 한 번에 조회하는 API
    
    Request Body:
        movie_ids: List[int] - 영화 ID 리스트
        region: str - 국가 코드 (기본값: KR)
    
    Response:
        items: 스트리밍 정보 리스트
        total: 총 개수
        region: 조회한 국가 코드
    
    Example:
        POST /api/streaming/bulk
        Body: {
            "movie_ids": [550, 680, 155],
            "region": "KR"
        }
    """
    try:
        data = request.get_json(force=True)
        movie_ids = data.get('movie_ids', [])
        region = data.get('region', 'KR').upper()
        
        if not movie_ids:
            return jsonify({"error": "movie_ids는 필수 필드입니다."}), 400
        
        if not isinstance(movie_ids, list):
            return jsonify({"error": "movie_ids는 리스트여야 합니다."}), 400
        
        # 최대 50개로 제한
        if len(movie_ids) > 50:
            movie_ids = movie_ids[:50]
        
        streaming_infos = tmdb_service.get_bulk_streaming_providers(movie_ids, region)
        
        return jsonify({
            "items": streaming_infos,
            "total": len(streaming_infos),
            "region": region
        })
    
    except Exception as e:
        return jsonify({
            "error": f"대량 스트리밍 정보 조회 실패: {str(e)}"
        }), 500


@api_bp.route('/api/search', methods=['GET'])
def search_movies():
    """
    영화 제목으로 검색하는 API (자동완성용)
    
    Query Parameters:
        q: str - 검색어
        language: str - 언어 코드 (기본값: ko-KR)
    
    Response:
        results: 영화 리스트 (최대 10개)
    
    Example:
        GET /api/search?q=기생충&language=ko-KR
    """
    try:
        query = request.args.get('q', '').strip()
        lang = request.args.get('language', 'ko-KR')
        
        if not query:
            return jsonify({"results": []})
        
        if len(query) < 1:
            return jsonify({"results": []})
        
        # TMDb 검색 API 호출 (여러 결과 반환)
        search_results = tmdb_service.search_movies(query, lang, limit=10)
        
        # 검색 결과가 없으면 빈 배열 반환
        if not search_results:
            return jsonify({"results": []})
        
        # 결과 형식 변환
        results = [
            {
                "id": movie.get("id"),
                "title": movie.get("title") or movie.get("original_title"),
                "original_title": movie.get("original_title"),
                "release_date": movie.get("release_date"),
                "year": (movie.get("release_date") or "")[:4],
                "poster_path": movie.get("poster_path"),
                "overview": movie.get("overview")
            }
            for movie in search_results
        ]
        
        return jsonify({"results": results})
    
    except Exception as e:
        return jsonify({"error": f"검색 실패: {str(e)}"}), 500


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
