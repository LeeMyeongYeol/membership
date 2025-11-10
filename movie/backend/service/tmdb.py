from typing import List, Dict, Any
import httpx
from ..settings import settings
from .util import year_of

async def _get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    params = {"api_key": settings.TMDB_API_KEY, "language": settings.DEFAULT_LANG, "region": settings.DEFAULT_REGION, **params}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{settings.TMDB_BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()

def map_items(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for m in results or []:
        out.append({
            "source": "TMDB",
            "title": m.get("title") or m.get("name") or "",
            "year": year_of(m.get("release_date", "")),
            "poster": f"{settings.TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else "",
            "imdbID": None,
            "tmdb_id": m.get("id"),
        })
    return out

async def popular() -> List[Dict[str, Any]]:
    data = await _get("/movie/popular", {"page": 1})
    return map_items(data.get("results"))

async def upcoming() -> List[Dict[str, Any]]:
    data = await _get("/movie/upcoming", {"page": 1})
    return map_items(data.get("results"))

async def discover_by_lang(lang: str) -> List[Dict[str, Any]]:
    data = await _get("/discover/movie", {"with_original_language": lang, "sort_by": "popularity.desc", "include_adult": "false"})
    return map_items(data.get("results"))

async def search(q: str) -> List[Dict[str, Any]]:
    data = await _get("/search/movie", {"query": q, "include_adult": "false"})
    return map_items(data.get("results"))

async def genres() -> List[Dict[str, Any]]:
    data = await _get("/genre/movie/list", {})
    return data.get("genres", [])
