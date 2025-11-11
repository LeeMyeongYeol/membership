# 📦 프로젝트 구조 (단일 파일 실행 가능)
# ├─ app.py                ← Flask 서버 (백엔드 + 프론트엔드 템플릿 내장)
# ├─ requirements.txt      ← 필요한 패키지 목록
# ├─ .env                  ← API 키 저장 (TMDB_API_KEY, OMDB_API_KEY)
# 
# 아래에 app.py, requirements.txt, .env 예시를 한 번에 제공합니다.
# 파일을 각각 저장 후 실행하세요.

########################################
# app.py
########################################

import os
import math
import json
import textwrap
from collections import Counter, defaultdict
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from flask import Flask, request, jsonify, render_template_string
import requests
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")

# Tuning knobs (can be overridden via .env)
CANDIDATE_LIMIT = int(os.getenv("CANDIDATE_LIMIT", "150"))
TOPN = int(os.getenv("TOPN", "20"))
ENRICH_TOP = int(os.getenv("ENRICH_TOP", "10"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))

app = Flask(__name__)

# Reuse HTTP session for connection pooling
SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

# ------------------------------
# TMDb / OMDb helpers
# ------------------------------
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w342"


def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    params = {"api_key": TMDB_API_KEY, **params}
    r = SESSION.get(f"{TMDB_BASE}{path}", params=params, timeout=6)
    r.raise_for_status()
    return r.json()


def omdb_get(params: Dict[str, Any]) -> Dict[str, Any]:
    params = {"apikey": OMDB_API_KEY, **params}
    r = SESSION.get("https://www.omdbapi.com/", params=params, timeout=6)
    r.raise_for_status()
    return r.json()


@lru_cache(maxsize=4096)
def pick_best_tmdb_match(title: str, lang: str = "ko-KR") -> Dict[str, Any]:
    """Search TMDb by title and return the best match movie JSON (or {})."""
    if not title.strip():
        return {}
    data = tmdb_get("/search/movie", {"query": title, "language": lang, "include_adult": False})
    results = data.get("results", [])
    if not results:
        # try en-US fallback
        data = tmdb_get("/search/movie", {"query": title, "language": "en-US", "include_adult": False})
        results = data.get("results", [])
        if not results:
            return {}
    # sort by popularity and exact-ish title match boost
    title_low = title.lower()
    for m in results:
        m["_pop"] = m.get("popularity", 0)
        name = (m.get("title") or m.get("original_title") or "").lower()
        m["_pop"] += 100 if title_low in name else 0
    best = sorted(results, key=lambda x: x["_pop"], reverse=True)[0]
    return best


@lru_cache(maxsize=8192)
def tmdb_movie_profile(movie_id: int, lang: str = "ko-KR") -> Dict[str, Any]:
    """Fetch a rich movie profile including keywords, credits, recommendations, external IDs."""
    detail = tmdb_get(f"/movie/{movie_id}", {"language": lang, "append_to_response": "keywords,credits,recommendations,external_ids,similar"})

    # Normalize fields
    genres = [g.get("name") for g in (detail.get("genres") or [])]
    keywords = [k.get("name") for k in ((detail.get("keywords") or {}).get("keywords") or [])]
    cast = [c.get("name") for c in ((detail.get("credits") or {}).get("cast") or [])[:10]]
    crew = (detail.get("credits") or {}).get("crew") or []
    directors = [c.get("name") for c in crew if c.get("job") == "Director"]
    writers = [c.get("name") for c in crew if c.get("job") in ("Writer", "Screenplay")] 
    recs = ((detail.get("recommendations") or {}).get("results") or [])
    similars = ((detail.get("similar") or {}).get("results") or [])

    profile = {
        "id": detail.get("id"),
        "title": detail.get("title") or detail.get("original_title"),
        "overview": detail.get("overview") or "",
        "genres": genres,
        "keywords": keywords,
        "cast": cast,
        "directors": directors,
        "writers": writers,
        "poster": (TMDB_IMG + detail.get("poster_path")) if detail.get("poster_path") else None,
        "vote_average": detail.get("vote_average"),
        "vote_count": detail.get("vote_count"),
        "release_date": detail.get("release_date"),
        "runtime": detail.get("runtime"),
        "lang": lang,
        "external_ids": detail.get("external_ids") or {},
        "candidate_ids": [m.get("id") for m in recs[:30] + similars[:30] if m.get("id")],
    }
    return profile


def tmdb_bulk_profiles(ids: List[int], lang: str = "ko-KR") -> List[Dict[str, Any]]:
    # Deduplicate while preserving order
    seen, order = set(), []
    for mid in ids:
        if mid not in seen:
            seen.add(mid); order.append(mid)

    out: List[Dict[str, Any]] = []
    def fetch(mid: int):
        try:
            return tmdb_movie_profile(mid, lang)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for p in ex.map(fetch, order):
            if p:
                out.append(p)
    return out

# ------------------------------
# Content → Corpus helpers
# ------------------------------

def build_doc(p: Dict[str, Any]) -> str:
    # We weight genres/keywords a bit by repeating them (cheap weighting)
    g = " ".join((p.get("genres") or []))
    k = " ".join((p.get("keywords") or []))
    cast = " ".join((p.get("cast") or []))
    directors = " ".join((p.get("directors") or []))
    writers = " ".join((p.get("writers") or []))
    # Repeat genres/keywords to emphasize them
    bag = " ".join([
        p.get("overview", ""),
        (g + " ") * 3,
        (k + " ") * 3,
        (cast + " ") * 1,
        (directors + " ") * 2,
        (writers + " ") * 1,
    ])
    return bag


def tfidf_and_profile(favorite_profiles: List[Dict[str, Any]]):
    docs = [build_doc(p) for p in favorite_profiles]
    if not docs:
        raise ValueError("No documents for TF-IDF")
    vec = TfidfVectorizer(ngram_range=(1,2), max_features=10000, stop_words=None)
    X = vec.fit_transform(docs)

    # user preference vector = mean of favorite vectors
    user_vec_1d = np.asarray(X.mean(axis=0)).ravel()

    # Top features (common patterns)
    feature_names = vec.get_feature_names_out()
    # Convert to flat array
    arr = user_vec_1d
    top_idx = arr.argsort()[::-1][:10]
    top_features = [(feature_names[i], float(arr[i])) for i in top_idx]

    return vec, user_vec_1d.reshape(1, -1), top_features


# ------------------------------
# Recommendation logic
# ------------------------------

def recommend_from_candidates(vec: TfidfVectorizer, user_vec, candidates: List[Dict[str, Any]], exclude_ids: set):
    cand_docs, kept = [], []
    for p in candidates:
        if p.get("id") in exclude_ids:
            continue
        doc = build_doc(p)
        cand_docs.append(doc)
        kept.append(p)
    if not cand_docs:
        return []

    Y = vec.transform(cand_docs)
    sim = cosine_similarity(user_vec, Y).ravel()

    scored = []
    for p, s in zip(kept, sim):
        # confidence tweaks: favor higher vote_count and recency a little
        vc = p.get("vote_count") or 0
        bonus = min(math.log1p(vc)/10.0, 0.3)
        score = float(s + bonus)
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def enrich_with_omdb(p: Dict[str, Any]) -> Dict[str, Any]:
    imdb_id = (p.get("external_ids") or {}).get("imdb_id")
    if not (OMDB_API_KEY and imdb_id):
        return p
    try:
        od = omdb_get({"i": imdb_id})
        if od.get("Response") == "True":
            p["omdb"] = {
                "rated": od.get("Rated"),
                "imdbRating": od.get("imdbRating"),
                "metascore": od.get("Metascore"),
                "boxOffice": od.get("BoxOffice"),
            }
    except Exception:
        pass
    return p


# ------------------------------
# API routes
# ------------------------------

@app.get("/")
def index():
    return render_template_string(INDEX_HTML,
        has_tmdb=bool(TMDB_API_KEY),
        has_omdb=bool(OMDB_API_KEY)
    )


@app.post("/api/analyze")
def api_analyze():
    data = request.get_json(force=True)
    titles: List[str] = data.get("titles", [])
    lang: str = data.get("language", "ko-KR")

    # 1) Resolve titles → TMDb IDs
    resolved: List[int] = []
    for t in titles:
        try:
            m = pick_best_tmdb_match(t, lang)
            if m:
                mid = m.get("id")
                if mid:
                    resolved.append(mid)
        except Exception:
            continue

    if not resolved:
        return jsonify({"error": "입력한 제목으로 TMDb에서 영화를 찾을 수 없습니다."}), 400

    # 2) Build favorite profiles
    fav_profiles = tmdb_bulk_profiles(resolved, lang)

    # 3) TF-IDF profile
    try:
        vec, user_vec, top_features = tfidf_and_profile(fav_profiles)
    except Exception as e:
        return jsonify({"error": f"TF-IDF 분석 실패: {e}"}), 500

    # 4) Candidate pool: union of recommendations/similars
    cand_ids: List[int] = []
    for p in fav_profiles:
        cand_ids.extend(p.get("candidate_ids") or [])
    cand_ids = list(dict.fromkeys(cand_ids))[:CANDIDATE_LIMIT]

    candidates = tmdb_bulk_profiles(cand_ids, lang)

    # 5) Score
    exclude = {p.get("id") for p in fav_profiles}
    scored = recommend_from_candidates(vec, user_vec, candidates, exclude)

    # 6) Select top N (+ selective OMDb enrich)
    top_raw = scored[:TOPN]
    enriched: List[Dict[str, Any]] = []
    for idx, (s, p) in enumerate(top_raw, start=1):
        if idx <= ENRICH_TOP:
            p = enrich_with_omdb(p)
        enriched.append({"score": float(s), **{
            "id": p.get("id"),
            "title": p.get("title"),
            "overview": p.get("overview"),
            "poster": p.get("poster"),
            "genres": p.get("genres"),
            "vote_average": p.get("vote_average"),
            "vote_count": p.get("vote_count"),
            "release_date": p.get("release_date"),
            "runtime": p.get("runtime"),
            "omdb": p.get("omdb"),
        }})

    # 7) Aggregate pattern stats
    genre_counter = Counter(g for p in fav_profiles for g in (p.get("genres") or []))
    director_counter = Counter(d for p in fav_profiles for d in (p.get("directors") or []))
    actor_counter = Counter(a for p in fav_profiles for a in (p.get("cast") or []))

    resp = {
        "favorites": [{"id": p.get("id"), "title": p.get("title"), "poster": p.get("poster")} for p in fav_profiles],
        "top_features": top_features,
        "top_genres": genre_counter.most_common(5),
        "top_directors": director_counter.most_common(5),
        "top_actors": actor_counter.most_common(5),
        "recommendations": enriched,
    }
    return jsonify(resp)


# ------------------------------
# Minimal inline UI (Tailwind-less vanilla CSS)
# ------------------------------
INDEX_HTML = r"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>영화 취향 분석 추천 | TMDb + OMDb + TF‑IDF</title>
  <style>
    :root { --bg:#0b1020; --card:#121a33; --ink:#e7ecff; --muted:#9fb0ff; --accent:#6ea8ff; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Apple SD Gothic Neo, 'Malgun Gothic', sans-serif; background: var(--bg); color: var(--ink); }
    header { padding: 24px; border-bottom: 1px solid #22305b; }
    .container { max-width: 1100px; margin: 0 auto; padding: 24px; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .card { background: var(--card); border:1px solid #22305b; border-radius:16px; padding: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.25);}    
    textarea, select, input[type=text] { width:100%; background:#0c1730; color: var(--ink); border:1px solid #243356; border-radius: 12px; padding:12px; }
    button { background: linear-gradient(135deg, #3b82f6, #2563eb); border:none; color:white; padding:12px 16px; border-radius:12px; font-weight:700; cursor:pointer; }
    button:disabled { opacity:.5; cursor:not-allowed; }
    .hint { color: var(--muted); font-size: 13px; }
    .pill { background:#0b1430; border:1px solid #243356; padding:6px 10px; border-radius:999px; margin-right:6px; display:inline-block; color:#cfe0ff; }
    .poster { width:100%; border-radius:12px; }
    .rec-grid { display:grid; grid-template-columns: repeat(5, 1fr); gap:14px; }
    .rec { background:#0d1530; border:1px solid #22305b; border-radius:14px; overflow:hidden; display:flex; flex-direction:column; }
    .rec .info { padding:10px; font-size: 14px; line-height:1.35; }
    .badge { font-size: 12px; color:#bcd2ff; border:1px solid #2a3d6f; padding:4px 6px; border-radius:8px; display:inline-block; margin-right:6px; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap: wrap; }
    .features span { background:#101b3d; border:1px dashed #2a3d6f; border-radius:10px; padding:6px 8px; margin:4px; font-size:13px;}
    footer { text-align:center; padding:24px; color:#5d79b9; }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <h1 style="margin:0 0 6px 0;">🎬 영화 취향 분석 추천</h1>
      <div class="hint">TMDb + OMDb + Python TF‑IDF로 내가 좋아할 영화를 찾아줍니다.</div>
      <div class="hint">TMDb 키: <b>{{ 'OK' if has_tmdb else '미설정' }}</b> · OMDb 키: <b>{{ 'OK' if has_omdb else '미설정' }}</b></div>
    </div>
  </header>

  <div class="container">
    <div class="grid">
      <div class="card">
        <h3>1) 좋아하는 영화 제목 (한 줄에 1개)</h3>
        <textarea id="titles" rows="10" placeholder="예) 기생충\n인셉션\n라라랜드\n어바웃 타임\n인터스텔라\n암살\n헤어질 결심"></textarea>
        <div class="row" style="margin-top:10px;">
          <div style="flex:1;">
            <label class="hint">언어 (TMDb 응답 언어)</label>
            <select id="lang">
              <option value="ko-KR" selected>한국어 (ko-KR)</option>
              <option value="en-US">영어 (en-US)</option>
              <option value="ja-JP">일본어 (ja-JP)</option>
            </select>
          </div>
          <div>
            <button id="run">분석 & 추천 실행</button>
          </div>
        </div>
        <p class="hint" style="margin-top:10px;">* 서버의 .env에 TMDB_API_KEY, OMDB_API_KEY를 넣어두면 자동 사용합니다.</p>
      </div>

      <div class="card">
        <h3>2) 감지된 공통 패턴 (Top 10 TF‑IDF 특징)</h3>
        <div id="features" class="features"></div>
        <div style="height:8px;"></div>
        <div class="row">
          <div id="genres"></div>
        </div>
        <div style="height:8px;"></div>
        <div class="row">
          <div id="directors"></div>
        </div>
        <div style="height:8px;"></div>
        <div class="row">
          <div id="actors"></div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:20px;">
      <h3>3) 맞춤 추천</h3>
      <div id="recs" class="rec-grid"></div>
      <div id="error" class="hint" style="color:#ff9c9c;"></div>
    </div>
  </div>

  <footer>© TF‑IDF Recommender • TMDb/OMDb 데이터를 사용합니다.</footer>

  <script>
    const $ = (sel) => document.querySelector(sel);

    function chipList(el, title, arr) {
      if (!arr || !arr.length) { el.innerHTML = ''; return; }
      el.innerHTML = `<div class="pill">${title}</div>` + arr.map(([k,v]) => `<span class="pill">${k} × ${v}</span>`).join('');
    }

    function featureList(el, arr) {
      if (!arr || !arr.length) { el.innerHTML = '<div class="hint">(패턴이 아직 없습니다)</div>'; return; }
      el.innerHTML = arr.map(([k,score]) => `<span>${k} <small style="opacity:.6">${score.toFixed(3)}</small></span>`).join('');
    }

    function recCard(item) {
      const poster = item.poster ? `<img class="poster" loading="lazy" src="${item.poster}" alt="${item.title}">` : `<div style="height:180px; background:#0b1430"></div>`;
      const genres = (item.genres||[]).map(g=>`<span class="badge">${g}</span>`).join('');
      const extra = [
        item.release_date ? `개봉 ${item.release_date}` : null,
        item.runtime ? `${item.runtime}분` : null,
        item.vote_average ? `TMDb ★${item.vote_average.toFixed(1)} (${item.vote_count||0})` : null,
        item.omdb?.imdbRating ? `IMDb ★${item.omdb.imdbRating}` : null,
        item.omdb?.metascore ? `Metascore ${item.omdb.metascore}` : null,
      ].filter(Boolean).join(' · ');
      return `
        <div class="rec">
          ${poster}
          <div class="info">
            <div style="font-weight:700; margin-bottom:6px;">${item.title}</div>
            <div class="row" style="margin-bottom:6px;">${genres}</div>
            <div class="hint" style="margin-bottom:6px;">${extra}</div>
            <div style="font-size:13px; opacity:.9;">${(item.overview||'').slice(0,180)}${(item.overview||'').length>180?'…':''}</div>
          </div>
        </div>`;
    }

    async function runAnalyze() {
      $('#error').textContent = '';
      $('#recs').innerHTML = '';
      $('#features').innerHTML = '';
      $('#genres').innerHTML = '';
      $('#directors').innerHTML = '';
      $('#actors').innerHTML = '';

      const titles = $('#titles').value.split('\n').map(s=>s.trim()).filter(Boolean);
      if (!titles.length) {
        $('#error').textContent = '영화 제목을 한 개 이상 입력하세요.';
        return;
      }

      $('#run').disabled = true; $('#run').textContent = '분석 중…';
      try {
        const resp = await fetch('/api/analyze', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ titles, language: $('#lang').value })
        });
        const data = await resp.json();
        if (!resp.ok) { throw new Error(data.error || '요청 실패'); }

        featureList($('#features'), data.top_features);
        chipList($('#genres'), 'Top 장르', data.top_genres);
        chipList($('#directors'), 'Top 감독', data.top_directors);
        chipList($('#actors'), 'Top 배우', data.top_actors);

        $('#recs').innerHTML = data.recommendations.map(recCard).join('');
      } catch (e) {
        $('#error').textContent = e.message || String(e);
      } finally {
        $('#run').disabled = false; $('#run').textContent = '분석 & 추천 실행';
      }
    }

    $('#run').addEventListener('click', runAnalyze);
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    if not TMDB_API_KEY:
        print("[경고] TMDB_API_KEY가 .env에 없습니다. TMDb 요청이 실패할 수 있습니다.")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)




