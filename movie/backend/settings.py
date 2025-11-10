# settings.py
from dotenv import load_dotenv
import os

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ko-KR")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "KR")

POSTER_BASE = "https://image.tmdb.org/t/p/w500"
HTTP_TIMEOUT = 12.0
