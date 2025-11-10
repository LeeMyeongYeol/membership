from typing import List, Dict, Any
import httpx
from ..settings import settings

async def search(q: str) -> List[Dict[str, Any]]:
    params = {"apikey": settings.OMDB_API_KEY, "s": q, "type": "movie"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(settings.OMDB_BASE, params=params)
        data = r.json()
    arr = data.get("Search") or []
    out = []
    for o in arr:
        out.append({
            "source": "OMDb",
            "title": o.get("Title") or "",
            "year": o.get("Year") or "",
            "poster": (o.get("Poster") if o.get("Poster") and o["Poster"] != "N/A" else ""),
            "imdbID": o.get("imdbID"),
        })
    return out
