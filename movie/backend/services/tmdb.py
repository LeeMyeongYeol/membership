# services/tmdb.py
import httpx
from typing import List, Dict
from settings import TMDB_API_KEY, DEFAULT_LANG, DEFAULT_REGION, POSTER_BASE, HTTP_TIMEOUT

BASE = "https://api.themoviedb.org/3"

def _norm(item: Dict) -> Dict:
    title = item.get("title") or item.get("name") or ""
    year = (item.get("release_date") or item.get("first_air_date") or "")[:4]
    poster_path = item.get("poster_path") or ""
    return {
        "title": title,
        "year": year,
        "poster": f"{POSTER_BASE}{poster_path}" if poster_path else "",
        "source": "TMDb",
        "id": item.get("id"),
    }

async def popular() -> List[Dict]:
    params = {
        "api_key": TMDB_API_KEY,
        "language": DEFAULT_LANG,
        "region": DEFAULT_REGION,
        "page": 1,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(f"{BASE}/movie/popular", params=params)
        r.raise_for_status()
        data = r.json()
    return [_norm(m) for m in data.get("results", [])]

async def search(q: str) -> List[Dict]:
    params = {
        "api_key": TMDB_API_KEY,
        "query": q,
        "language": DEFAULT_LANG,
        "include_adult": False,
        "page": 1,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(f"{BASE}/search/movie", params=params)
        r.raise_for_status()
        data = r.json()
    return [_norm(m) for m in data.get("results", [])]

_LANG_CODE = {
    "ko": "ko-KR",
    "en": "en-US",
    "ja": "ja-JP",
    "zh": "zh-CN",
    "fr": "fr-FR",
}

async def discover_by_lang(lang_short: str) -> List[Dict]:
    lang = _LANG_CODE.get(lang_short, DEFAULT_LANG)
    params = {
        "api_key": TMDB_API_KEY,
        "with_original_language": lang_short,
        "language": lang,
        "sort_by": "popularity.desc",
        "page": 1,
        "include_adult": False,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(f"{BASE}/discover/movie", params=params)
        r.raise_for_status()
        data = r.json()
    return [_norm(m) for m in data.get("results", [])]
