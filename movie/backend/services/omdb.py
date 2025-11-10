# services/omdb.py
import httpx
from typing import List, Dict
from settings import OMDB_API_KEY, HTTP_TIMEOUT

BASE = "https://www.omdbapi.com/"

def _norm(item: Dict) -> Dict:
    title = item.get("Title") or ""
    year = item.get("Year") or ""
    poster = item.get("Poster") if item.get("Poster") and item.get("Poster") != "N/A" else ""
    return {
        "title": title,
        "year": year,
        "poster": poster,
        "source": "OMDb",
        "id": item.get("imdbID"),
    }

async def search(q: str) -> List[Dict]:
    # OMDb는 s= 로 검색 (영화만)
    params = {"apikey": OMDB_API_KEY, "type": "movie", "s": q}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(BASE, params=params)
        r.raise_for_status()
        data = r.json()
    results = data.get("Search") or []
    return [_norm(m) for m in results]
