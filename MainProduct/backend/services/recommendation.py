"""
영화 추천 알고리즘 서비스 (TF-IDF 기반)
"""
import math
from typing import List, Dict, Any, Tuple
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class RecommendationService:
    """TF-IDF 기반 영화 추천 서비스"""
    
    @staticmethod
    def build_document(profile: Dict[str, Any]) -> str:
        """
        영화 프로필을 TF-IDF용 문서로 변환
        
        장르와 키워드를 반복하여 가중치 부여
        
        Args:
            profile: 영화 프로필 딕셔너리
            
        Returns:
            TF-IDF 분석용 문서 문자열
        """
        genres = " ".join(profile.get("genres") or [])
        keywords = " ".join(profile.get("keywords") or [])
        cast = " ".join(profile.get("cast") or [])
        directors = " ".join(profile.get("directors") or [])
        writers = " ".join(profile.get("writers") or [])
        
        # 장르/키워드는 3번 반복, 감독은 2번 반복하여 가중치 부여
        document = " ".join([
            profile.get("overview", ""),
            (genres + " ") * 3,
            (keywords + " ") * 3,
            (cast + " ") * 1,
            (directors + " ") * 2,
            (writers + " ") * 1,
        ])
        
        return document
    
    @staticmethod
    def create_tfidf_profile(
        favorite_profiles: List[Dict[str, Any]]
    ) -> Tuple[TfidfVectorizer, np.ndarray, List[Tuple[str, float]]]:
        """
        좋아하는 영화들로부터 TF-IDF 프로필 생성
        
        Args:
            favorite_profiles: 좋아하는 영화 프로필 리스트
            
        Returns:
            (vectorizer, user_vector, top_features) 튜플
            - vectorizer: 학습된 TfidfVectorizer
            - user_vector: 사용자 선호 벡터
            - top_features: 상위 10개 특징 [(특징명, 점수), ...]
        """
        if not favorite_profiles:
            raise ValueError("최소 1개 이상의 영화 프로필이 필요합니다.")
        
        # 각 영화를 문서로 변환
        documents = [
            RecommendationService.build_document(profile)
            for profile in favorite_profiles
        ]
        
        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=10000,
            stop_words=None
        )
        tfidf_matrix = vectorizer.fit_transform(documents)
        
        # 사용자 선호 벡터 = 좋아하는 영화들의 평균 벡터
        user_vector_1d = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
        user_vector = user_vector_1d.reshape(1, -1)
        
        # 상위 특징 추출
        feature_names = vectorizer.get_feature_names_out()
        top_indices = user_vector_1d.argsort()[::-1][:10]
        top_features = [
            (feature_names[i], float(user_vector_1d[i]))
            for i in top_indices
        ]
        
        return vectorizer, user_vector, top_features
    
    @staticmethod
    def score_candidates(
        vectorizer: TfidfVectorizer,
        user_vector: np.ndarray,
        candidates: List[Dict[str, Any]],
        exclude_ids: set
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        후보 영화들에 점수를 매겨 정렬
        
        Args:
            vectorizer: 학습된 TfidfVectorizer
            user_vector: 사용자 선호 벡터
            candidates: 후보 영화 프로필 리스트
            exclude_ids: 제외할 영화 ID 집합
            
        Returns:
            [(점수, 프로필), ...] 리스트 (점수 내림차순 정렬)
        """
        candidate_docs = []
        kept_profiles = []
        
        # 이미 입력한 영화는 제외
        for profile in candidates:
            if profile.get("id") in exclude_ids:
                continue
            
            doc = RecommendationService.build_document(profile)
            candidate_docs.append(doc)
            kept_profiles.append(profile)
        
        if not candidate_docs:
            return []
        
        # 후보 영화들을 벡터화
        candidate_matrix = vectorizer.transform(candidate_docs)
        
        # 코사인 유사도 계산
        similarities = cosine_similarity(user_vector, candidate_matrix).ravel()
        
        # 점수 계산 (유사도 + 인기도 보너스)
        scored_movies = []
        for profile, similarity in zip(kept_profiles, similarities):
            vote_count = profile.get("vote_count") or 0
            # 투표 수가 많을수록 보너스 (최대 0.3)
            popularity_bonus = min(math.log1p(vote_count) / 10.0, 0.3)
            final_score = float(similarity + popularity_bonus)
            
            scored_movies.append((final_score, profile))
        
        # 점수 내림차순 정렬
        scored_movies.sort(key=lambda x: x[0], reverse=True)
        
        return scored_movies
    
    @staticmethod
    def analyze_patterns(
        favorite_profiles: List[Dict[str, Any]]
    ) -> Dict[str, List[Tuple[str, int]]]:
        """
        좋아하는 영화들의 공통 패턴 분석
        
        Args:
            favorite_profiles: 좋아하는 영화 프로필 리스트
            
        Returns:
            {
                "top_genres": [(장르명, 빈도), ...],
                "top_directors": [(감독명, 빈도), ...],
                "top_actors": [(배우명, 빈도), ...]
            }
        """
        genre_counter = Counter()
        director_counter = Counter()
        actor_counter = Counter()
        
        for profile in favorite_profiles:
            # 장르 카운트
            for genre in profile.get("genres") or []:
                genre_counter[genre] += 1
            
            # 감독 카운트
            for director in profile.get("directors") or []:
                director_counter[director] += 1
            
            # 배우 카운트
            for actor in profile.get("cast") or []:
                actor_counter[actor] += 1
        
        return {
            "top_genres": genre_counter.most_common(5),
            "top_directors": director_counter.most_common(5),
            "top_actors": actor_counter.most_common(5),
        }


# 싱글톤 인스턴스
recommendation_service = RecommendationService()
