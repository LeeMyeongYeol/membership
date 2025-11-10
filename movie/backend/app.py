# app.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Literal
from services import tmdb, omdb

app = FastAPI(title="Movie Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중엔 * ; 배포 시 프론트 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/api/popular")
async def api_popular():
    items = await tmdb.popular()
    return {"items": items}

@app.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1),
    source: Literal["tmdb", "omdb", "both"] = "both"
):
    items: List[Dict] = []
    if source in ("tmdb", "both"):
        try:
            items.extend(await tmdb.search(q))
        except Exception:
            pass
    if source in ("omdb", "both"):
        try:
            items.extend(await omdb.search(q))
        except Exception:
            pass
    # 중복 제거(제목+연도로 단순 병합)
    seen = set()
    dedup = []
    for m in items:
        k = (m.get("title","").lower(), m.get("year",""))
        if k in seen: 
            continue
        seen.add(k)
        dedup.append(m)
    return {"items": dedup}

@app.get("/api/discover/lang")
async def api_discover_by_lang(lang: str = Query("ko")):
    items = await tmdb.discover_by_lang(lang)
    return {"items": items}
