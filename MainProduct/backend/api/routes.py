"""
Flask API 라우트
"""
from typing import List
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import desc

from config import Config
from services.tmdb_service import tmdb_service
from services.omdb_service import omdb_service
from services.recommendation import recommendation_service
from database import get_db, SessionLocal
from models.review import Review

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
            "streaming_bulk": "/api/streaming/bulk",
            "reviews": "/api/reviews/<movie_id>"
        },
        "config": {
            "tmdb_configured": bool(Config.TMDB_API_KEY),
            "omdb_configured": bool(Config.OMDB_API_KEY)
        }
    })


@api_bp.route('/api/analyze', methods=['POST'])
def analyze():
    """영화 취향 분석 및 추천 API"""
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
        
        # 4. 후보 영화 풀 생성
        candidate_ids = []
        for profile in favorite_profiles:
            candidate_ids.extend(profile.get("candidate_ids") or [])
        
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
        
        # 6. 상위 N개 선택
        top_movies = scored_movies[:Config.TOP_N]
        recommendations = []
        
        for idx, (score, profile) in enumerate(top_movies, start=1):
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
    """특정 영화의 스트리밍 제공 정보 조회 API"""
    try:
        region = request.args.get('region', 'KR').upper()
        
        streaming_info = tmdb_service.get_streaming_providers(movie_id, region)
        
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
    """여러 영화의 스트리밍 제공 정보를 한 번에 조회하는 API"""
    try:
        data = request.get_json(force=True)
        movie_ids = data.get('movie_ids', [])
        region = data.get('region', 'KR').upper()
        
        if not movie_ids:
            return jsonify({"error": "movie_ids는 필수 필드입니다."}), 400
        
        if not isinstance(movie_ids, list):
            return jsonify({"error": "movie_ids는 리스트여야 합니다."}), 400
        
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
    """영화 제목으로 검색하는 API (자동완성용)"""
    try:
        query = request.args.get('q', '').strip()
        lang = request.args.get('language', 'ko-KR')
        
        if not query:
            return jsonify({"results": []})
        
        if len(query) < 1:
            return jsonify({"results": []})
        
        search_results = tmdb_service.search_movies(query, lang, limit=10)
        
        if not search_results:
            return jsonify({"results": []})
        
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
    """장르, 테마 기반 영화 발견 API"""
    try:
        data = request.get_json(force=True)
        genres = data.get("genres", [])
        themes = data.get("themes", [])
        lang = data.get("language", "ko-KR")
        page = data.get("page", 1)
        
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


@api_bp.route('/api/reviews/<int:movie_id>', methods=['GET'])
def get_reviews(movie_id: int):
    """특정 영화의 리뷰 목록 조회 API"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        db = SessionLocal()
        try:
            reviews = db.query(Review).filter(
                Review.movie_id == movie_id
            ).order_by(
                desc(Review.created_at)
            ).limit(limit).offset(offset).all()
            
            total = db.query(Review).filter(
                Review.movie_id == movie_id
            ).count()
            
            print(f"[DEBUG] 리뷰 조회 - movie_id: {movie_id}, total: {total}")
            
            return jsonify({
                "reviews": [review.to_dict() for review in reviews],
                "total": total,
                "movie_id": movie_id
            })
        finally:
            db.close()
    except Exception as e:
        print(f"[ERROR] 리뷰 조회 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"리뷰 조회 실패: {str(e)}"}), 500


@api_bp.route('/api/reviews', methods=['POST'])
def create_review():
    """리뷰 작성 API"""
    try:
        data = request.get_json(force=True)
        print(f"[DEBUG] 리뷰 작성 요청: {data}")
        
        movie_id = data.get('movie_id')
        author_name = data.get('author_name', '').strip()
        content = data.get('content', '').strip()
        rating = data.get('rating')
        
        if not movie_id:
            return jsonify({"error": "movie_id는 필수입니다."}), 400
        
        if not author_name or len(author_name) > 50:
            return jsonify({"error": "이름은 1-50자여야 합니다."}), 400
        
        if not content or len(content) > 1000:
            return jsonify({"error": "내용은 1-1000자여야 합니다."}), 400
        
        if rating is None or not (0.0 <= rating <= 5.0):
            return jsonify({"error": "별점은 0.0-5.0 사이여야 합니다."}), 400
        
        db = SessionLocal()
        try:
            review = Review(
                movie_id=movie_id,
                author_name=author_name,
                content=content,
                rating=rating
            )
            
            db.add(review)
            db.commit()
            db.refresh(review)
            
            print(f"[SUCCESS] 리뷰 작성 완료: ID={review.id}")
            
            return jsonify({
                "review": review.to_dict(),
                "message": "리뷰가 성공적으로 작성되었습니다."
            }), 201
        finally:
            db.close()
    except Exception as e:
        print(f"[ERROR] 리뷰 작성 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"리뷰 작성 실패: {str(e)}"}), 500


@api_bp.route('/api/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id: int):
    """리뷰 삭제 API"""
    try:
        db = SessionLocal()
        try:
            review = db.query(Review).filter(Review.id == review_id).first()
            
            if not review:
                return jsonify({"error": "리뷰를 찾을 수 없습니다."}), 404
            
            db.delete(review)
            db.commit()
            
            return jsonify({"message": "리뷰가 삭제되었습니다."})
        finally:
            db.close()
    except Exception as e:
        print(f"[ERROR] 리뷰 삭제 실패: {str(e)}")
        return jsonify({"error": f"리뷰 삭제 실패: {str(e)}"}), 500


@api_bp.route('/api/reviews/stats/<int:movie_id>', methods=['GET'])
def get_review_stats(movie_id: int):
    """영화의 리뷰 통계 조회 API"""
    try:
        db = SessionLocal()
        try:
            reviews = db.query(Review).filter(Review.movie_id == movie_id).all()
            
            total = len(reviews)
            avg_rating = sum(r.rating for r in reviews) / total if total > 0 else 0.0
            
            return jsonify({
                "total_reviews": total,
                "average_rating": round(avg_rating, 2),
                "movie_id": movie_id
            })
        finally:
            db.close()
    except Exception as e:
        print(f"[ERROR] 통계 조회 실패: {str(e)}")
        return jsonify({"error": f"통계 조회 실패: {str(e)}"}), 500
