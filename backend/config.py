"""
애플리케이션 설정 및 환경 변수 관리
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """애플리케이션 설정 클래스"""
    
    # API Keys
    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
    OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
    
    # API Base URLs
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"
    OMDB_BASE_URL = "https://www.omdbapi.com/"
    
    # 추천 알고리즘 파라미터
    CANDIDATE_LIMIT = int(os.getenv("CANDIDATE_LIMIT", "150"))
    TOP_N = int(os.getenv("TOPN", "20"))
    ENRICH_TOP = int(os.getenv("ENRICH_TOP", "10"))
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
    
    # Flask 설정
    HOST = "0.0.0.0"
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # 요청 타임아웃 (초)
    REQUEST_TIMEOUT = 6
