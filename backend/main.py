import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os  # 환경 변수를 사용하기 위해 추가

# 로컬 모듈 import
from database import get_db
from movie_service import save_movie_to_db, get_movie_by_id, get_all_movies, delete_movie, movie_to_dict

# --- FastAPI 앱 생성 ---
app = FastAPI()

# --- 설정 (TMDb API 키) ---
# docker-compose.yml의 env_file을 통해 .env 파일에서 주입됩니다.
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"

# --- CORS 미들웨어 설정 ---
# React 앱이 실행될 주소
origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite 기본 포트
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API 엔드포인트 ---

@app.get("/")
def read_root():
    """ 서버가 살아있는지 확인하는 루트 엔드포인트 """
    # .env 파일에서 TMDB_API_KEY를 읽었는지 확인
    if not TMDB_API_KEY:
        return {"status": "error", "message": "TMDB_API_KEY is not set in .env file."}
    
    return {"status": "success", "message": "Movie recommendation API server is running"}


@app.get("/search")
async def search_movies(query: str):
    """
    영화 제목 자동완성을 위한 검색 엔드포인트
    React에서 /search?query=... 로 호출합니다.
    """
    if not query:
        return []
    
    # API 키가 설정되지 않았다면 에러 반환
    if not TMDB_API_KEY:
        return {"error": "TMDb API key is missing or not set up on the server."}

    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "ko-KR",  # 한국어 결과 우선
        "page": 1
    }

    # TMDb API에 비동기로 요청
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(TMDB_SEARCH_URL, params=params)
            response.raise_for_status()  # 200 OK가 아니면 예외 발생
        
        except httpx.HTTPStatusError as e:
            # API 키가 잘못되었거나(401) 요청이 잘못된 경우(404 등)
            if e.response.status_code == 401:
                return {"error": "Invalid TMDb API key. Please check your .env file."}
            return {"error": f"TMDb API error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}

    # 결과 처리 (try 블록 밖으로 이동)
    search_results = response.json().get("results", [])
    
    # React에 필요한 최소한의 정보만 가공하여 반환
    simplified_results = [
        {
            "id": movie.get("id"),
            "title": movie.get("title"),
            "release_date": movie.get("release_date", "N/A"),
            "poster_path": movie.get("poster_path")
        }
        for movie in search_results[:10]  # 상위 10개 결과만 반환
    ]
    return simplified_results


@app.post("/movies/{movie_id}")
async def save_movie(movie_id: int, db: Session = Depends(get_db)):
    """
    사용자가 선택한 영화를 DB에 저장합니다.
    TMDb에서 상세 정보(줄거리, 키워드, 장르)를 가져와 저장합니다.

    Args:
        movie_id: TMDb 영화 ID
        db: DB 세션 (의존성 주입)

    Returns:
        저장된 영화 정보
    """
    movie = await save_movie_to_db(movie_id, db)

    if not movie:
        raise HTTPException(status_code=500, detail="Failed to save movie")

    return {
        "status": "success",
        "message": f"Movie '{movie.title}' saved successfully",
        "movie": movie_to_dict(movie)
    }


@app.get("/movies/{movie_id}")
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    """
    DB에서 영화 정보를 조회합니다.

    Args:
        movie_id: 영화 ID
        db: DB 세션 (의존성 주입)

    Returns:
        영화 정보
    """
    movie = get_movie_by_id(movie_id, db)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return movie_to_dict(movie)


@app.get("/movies")
def list_movies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    DB에 저장된 모든 영화 목록을 조회합니다.

    Args:
        skip: 건너뛸 개수 (페이지네이션)
        limit: 가져올 최대 개수
        db: DB 세션 (의존성 주입)

    Returns:
        영화 목록
    """
    movies = get_all_movies(db, skip, limit)

    return {
        "total": len(movies),
        "movies": [movie_to_dict(movie) for movie in movies]
    }


@app.delete("/movies/{movie_id}")
def remove_movie(movie_id: int, db: Session = Depends(get_db)):
    """
    DB에서 영화를 삭제합니다.

    Args:
        movie_id: 영화 ID
        db: DB 세션 (의존성 주입)

    Returns:
        삭제 결과
    """
    success = delete_movie(movie_id, db)

    if not success:
        raise HTTPException(status_code=404, detail="Movie not found or could not be deleted")

    return {
        "status": "success",
        "message": f"Movie ID {movie_id} deleted successfully"
    }