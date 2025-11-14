"""
OMDb API 호출 서비스
"""
from typing import Dict, Any

import requests
from config import Config


class OMDbService:
    """OMDb API 서비스 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.base_url = Config.OMDB_BASE_URL
        self.api_key = Config.OMDB_API_KEY
    
    def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """OMDb API GET 요청"""
        params = {"apikey": self.api_key, **params}
        response = self.session.get(
            self.base_url,
            params=params,
            timeout=Config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    
    def get_movie_by_imdb_id(self, imdb_id: str) -> Dict[str, Any]:
        """
        IMDb ID로 영화 정보 조회
        
        Args:
            imdb_id: IMDb ID (예: tt1234567)
            
        Returns:
            영화 정보 딕셔너리
        """
        if not self.api_key or not imdb_id:
            return {}
        
        try:
            data = self._get({"i": imdb_id})
            if data.get("Response") == "True":
                return {
                    "rated": data.get("Rated"),
                    "imdbRating": data.get("imdbRating"),
                    "metascore": data.get("Metascore"),
                    "boxOffice": data.get("BoxOffice"),
                }
        except Exception:
            pass
        
        return {}
    
    def enrich_movie_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        영화 프로필에 OMDb 정보 추가
        
        Args:
            profile: TMDb 영화 프로필
            
        Returns:
            OMDb 정보가 추가된 프로필
        """
        imdb_id = (profile.get("external_ids") or {}).get("imdb_id")
        omdb_data = self.get_movie_by_imdb_id(imdb_id)
        
        if omdb_data:
            profile["omdb"] = omdb_data
        
        return profile


# 싱글톤 인스턴스
omdb_service = OMDbService()
