import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import './PopularMovies.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TMDB_API_KEY_FRONT = 'ddd654eb8622a67e04f93f613653426d'
const POSTER_BASE = 'https://image.tmdb.org/t/p/w500'

const GENRES = ["Action (액션)", "Adventure (모험)", "Animation (애니메이션)", "Comedy (코미디)", "Crime (범죄)", "Drama (드라마)", "Fantasy (판타지)", "Historical (사극/역사)", "Horror (공포)", "Musical (뮤지컬)", "Mystery (미스터리)", "Romance (로맨스)", "Sci-Fi (SF / 공상과학)", "Thriller (스릴러)", "War (전쟁)", "Western (서부극)", "Documentary (다큐멘터리)", "Family (가족)", "Biography (전기)", "Sport (스포츠)"]
const REGIONS = ["한국영화", "해외영화", "일본영화", "중국영화", "프랑스영화", "OTT 전용 영화"]
const THEMES = ["Now Playing (현재 상영작)", "Upcoming (개봉 예정작)", "Top Rated (평점 높은 순)", "Popular (인기순)", "Classic (고전 명작)", "Indie (독립영화)", "Short Film (단편영화)", "LGBTQ+", "Noir / Neo-noir", "Superhero (히어로)", "Time Travel / Space / Cyberpunk", "Zombie / Monster / Disaster"]

const REGION_LANG = { "한국영화": "ko", "해외영화": "en", "일본영화": "ja", "중국영화": "zh", "프랑스영화": "fr" }

function PopularMovies() {
  const [tokens, setTokens] = useState([])
  const [query, setQuery] = useState('')
  const [panelOpen, setPanelOpen] = useState(false)
  const [currentItems, setCurrentItems] = useState([])
  const [selected, setSelected] = useState([])
  const [loading, setLoading] = useState(false)
  const [noMore, setNoMore] = useState(false)
  const [status, setStatus] = useState('')
  const [mode, setMode] = useState('popular') // 'popular' | 'discover' | 'search'
  const [queryState, setQueryState] = useState({ q: '', lang: '', page: 1 })

  const sentinelRef = useRef(null)
  const queryInputRef = useRef(null)

  // 키 생성
  const keyOf = (item) => {
    if (item.source === 'TMDb' && item.id) return `tmdb:${item.id}`
    const t = (item.title || '').toLowerCase()
    return `title:${t}|${item.year || ''}`
  }

  const isSelected = (item) => selected.some(s => keyOf(s) === keyOf(item))

  const posterUrl = (path) => path ? `${POSTER_BASE}${path}` : ''

  // API 호출
  const apiGet = async (path, params = {}) => {
    try {
      const response = await axios.get(`${API_BASE}${path}`, { params })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.error || error.message)
    }
  }

  const fetchPopularBackend = async (pageNum = 1) => {
    const { items } = await apiGet('/api/popular', { page: pageNum })
    return items || []
  }

  const fetchPopularFront = async (pageNum = 1) => {
    if (!TMDB_API_KEY_FRONT) throw new Error('No TMDb front key')
    const url = `https://api.themoviedb.org/3/movie/popular?api_key=${encodeURIComponent(TMDB_API_KEY_FRONT)}&language=ko-KR&region=KR&page=${pageNum}`
    const response = await axios.get(url)
    return (response.data.results || []).map(n => ({
      title: n.title || n.name || '',
      year: (n.release_date || n.first_air_date || '').slice(0, 4),
      poster: posterUrl(n.poster_path),
      source: 'TMDb',
      id: n.id
    }))
  }

  const fetchByMode = async (page) => {
    if (mode === 'popular') {
      try {
        return await fetchPopularBackend(page)
      } catch {
        return await fetchPopularFront(page)
      }
    } else if (mode === 'discover') {
      const { items } = await apiGet('/api/discover/lang', { lang: queryState.lang, page })
      return items || []
    } else { // 'search'
      const { items } = await apiGet('/api/search', { q: queryState.q, source: 'both', page })
      return items || []
    }
  }

  const filterDiscover = (list, extrasLower, textLower) => {
    if (!extrasLower.length && !textLower) return list
    return list.filter(m => {
      const title = (m.title || '').toLowerCase()
      const okExtra = extrasLower.every(k => title.includes(k.split(' ')[0]))
      const okText = textLower ? title.includes(textLower) : true
      return okExtra && okText
    })
  }

  const fetchAtLeastFour = async () => {
    let acc = []
    let guard = 0
    let currentPage = queryState.page

    while (acc.length < 4 && guard < 6 && !noMore) {
      const batch = await fetchByMode(currentPage)
      if (!batch.length) {
        setNoMore(true)
        break
      }

      let list = batch
      if (mode === 'discover') {
        const extras = tokens.filter(t => !REGION_LANG[t]).map(s => s.toLowerCase())
        const text = query.trim().toLowerCase()
        list = filterDiscover(batch, extras, text)
      }

      acc.push(...list)
      currentPage += 1
      guard += 1
    }

    setQueryState(prev => ({ ...prev, page: currentPage }))
    return acc
  }

  // 선택 토글
  const toggleSelection = (item) => {
    const k = keyOf(item)
    const exists = isSelected(item)

    if (!exists) {
      if (selected.length >= 10) {
        alert('최대 10개까지 선택할 수 있어요.')
        return
      }
      setSelected(prev => [...prev, item])
    } else {
      setSelected(prev => prev.filter(s => keyOf(s) !== k))
    }
  }

  // 토큰 추가
  const appendToken = (text) => {
    const t = (text || '').trim()
    if (!t || tokens.includes(t)) return
    setTokens(prev => [...prev, t])
    if (queryInputRef.current) {
      queryInputRef.current.focus()
    }
  }

  // 검색 수행
  const performSearch = async (closeAfter = false) => {
    const regionToken = tokens.find(t => REGION_LANG[t]) || null
    const text = query.trim()
    let out = []

    try {
      if (regionToken) {
        setMode('discover')
        const newQueryState = { q: '', lang: REGION_LANG[regionToken], page: 1 }
        setQueryState(newQueryState)
        setStatus(`${regionToken} 불러오는 중…`)

        const { items: first } = await apiGet('/api/discover/lang', { lang: newQueryState.lang, page: 1 })
        out = first || []

        const extras = tokens.filter(t => !REGION_LANG[t]).map(s => s.toLowerCase())
        const tLower = text.toLowerCase()
        out = filterDiscover(out, extras, tLower)

        setQueryState(prev => ({ ...prev, page: 2 }))

        if (out.length < 4) {
          const more = await fetchAtLeastFour()
          out = [...out, ...more]
        }
      } else {
        const combined = [...tokens, text].filter(Boolean).join(' ').trim()
        if (combined) {
          setMode('search')
          setQueryState({ q: combined, lang: '', page: 1 })
          setStatus(`"${combined}" 검색 중…`)

          const { items: first } = await apiGet('/api/search', { q: combined, source: 'both', page: 1 })
          out = first || []
          setQueryState(prev => ({ ...prev, page: 2 }))

          if (out.length < 4) {
            const more = await fetchAtLeastFour()
            out = [...out, ...more]
          }
        } else {
          setMode('popular')
          setQueryState({ q: '', lang: '', page: 1 })
          out = await fetchAtLeastFour()
        }
      }

      setCurrentItems(out)
      setStatus(`${out.length}개 결과`)
      setNoMore(false)
      if (closeAfter) setPanelOpen(false)
    } catch (e) {
      console.error(e)
      setStatus('검색 중 오류가 발생했습니다.')
    }
  }

  // 추천(유사작)
  const tmdbSimilarIds = async (tmdbId) => {
    const url = `https://api.themoviedb.org/3/movie/${tmdbId}/similar?api_key=${encodeURIComponent(TMDB_API_KEY_FRONT)}&language=ko-KR&page=1`
    const response = await axios.get(url)
    return (response.data.results || []).map(n => ({
      title: n.title || n.name || '',
      year: (n.release_date || n.first_air_date || '').slice(0, 4),
      poster: n.poster_path ? (POSTER_BASE + n.poster_path) : '',
      source: 'TMDb',
      id: n.id,
      tmdbId: n.id,
      popularity: n.popularity || 0
    }))
  }

  const dedup = (items) => {
    const seen = new Set()
    const out = []
    for (const m of items) {
      const k = m.tmdbId ? `tmdb:${m.tmdbId}` : keyOf(m)
      if (seen.has(k)) continue
      seen.add(k)
      out.push(m)
    }
    return out
  }

  const recommendSimilar = async () => {
    if (selected.length === 0) return
    setStatus('비슷한 영화 불러오는 중…')

    const bag = []
    for (const base of selected) {
      try {
        const tid = base.id
        if (!tid) continue
        const sims = await tmdbSimilarIds(tid)
        bag.push(...sims)
      } catch (e) {
        console.warn('similar fail', e)
      }
    }

    const exclude = new Set(selected.map(keyOf))
    let cands = bag.filter(m => !exclude.has(keyOf(m)))

    const score = new Map()
    for (const m of cands) {
      const k = `tmdb:${m.tmdbId || m.id || m.title}`
      const prev = score.get(k) || { item: m, count: 0, pop: 0 }
      prev.count += 1
      prev.pop = Math.max(prev.pop, m.popularity || 0)
      score.set(k, prev)
    }

    const ranked = [...score.values()].sort((a, b) => (b.count - a.count) || (b.pop - a.pop)).map(x => x.item)
    const result = dedup(ranked).slice(0, 40)

    setCurrentItems(result)
    setStatus(`추천 결과 ${result.length}개`)
  }

  // 초기 로드
  useEffect(() => {
    setMode('popular')
    setQueryState({ q: '', lang: '', page: 1 })
    setNoMore(false)

    fetchAtLeastFour().then(list => {
      setCurrentItems(list)
      setStatus(`${list.length}개 결과`)
    })
  }, [])

  // 무한 스크롤
  useEffect(() => {
    if (!sentinelRef.current) return

    const observer = new IntersectionObserver(
      async (entries) => {
        const entry = entries[0]
        if (!entry.isIntersecting || loading || noMore) return

        setLoading(true)
        try {
          const chunk = await fetchAtLeastFour()
          if (chunk.length === 0) {
            setNoMore(true)
          } else {
            setCurrentItems(prev => [...prev, ...chunk])
            setStatus(`${currentItems.length + chunk.length}개 결과`)
          }
        } catch (e) {
          console.error(e)
          setNoMore(true)
        } finally {
          setLoading(false)
        }
      },
      { threshold: 0.1 }
    )

    observer.observe(sentinelRef.current)

    return () => observer.disconnect()
  }, [loading, noMore, currentItems.length])

  // 토큰 변경 시 검색
  useEffect(() => {
    if (tokens.length > 0 || query) {
      performSearch(false)
    }
  }, [tokens])

  return (
    <div className="popular-movies">
      <header className="movie-header">
        <div className="hwrap">
          <div className="brand">
            <div className="logo">🎬</div>
            <strong>Movie Finder</strong>
          </div>
          <div className="head-actions">
            <button
              className="icon-btn"
              title="검색 열기"
              onClick={() => setPanelOpen(!panelOpen)}
            >
              <svg className="icon-img" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="24" height="24">
                <circle cx="11" cy="11" r="7"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </button>
          </div>
        </div>

        {panelOpen && (
          <div className="panel">
            <div className="row">
              <div className="token-input">
                <div className="token-list">
                  {tokens.map((t, i) => (
                    <span key={i} className="token-chip">
                      <span>{t}</span>
                      <button onClick={() => setTokens(prev => prev.filter((_, idx) => idx !== i))}>✕</button>
                    </span>
                  ))}
                </div>
                <input
                  ref={queryInputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Backspace' && !query && tokens.length) {
                      setTokens(prev => prev.slice(0, -1))
                    }
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      performSearch(true)
                    }
                  }}
                  placeholder="검색어 입력 후 Enter를 누르면 패널이 닫혀요"
                />
              </div>
              <button className="icon-btn" onClick={() => setPanelOpen(false)}>✕</button>
            </div>

            <button className="clear-all" onClick={() => setTokens([])}>카테고리 전부 지우기</button>

            <div className="grid">
              <div className="col">
                <div className="section"><strong>장르 (Genre)</strong></div>
                <div className="chips">
                  {GENRES.map(name => (
                    <button key={name} className="chip" onClick={() => appendToken(name)}>{name}</button>
                  ))}
                </div>
              </div>
              <div className="col">
                <div className="section"><strong>국가 / 지역</strong></div>
                <div className="chips">
                  {REGIONS.map(name => (
                    <button key={name} className="chip" onClick={() => appendToken(name)}>{name}</button>
                  ))}
                </div>
              </div>
              <div className="col">
                <div className="section"><strong>테마 (Theme)</strong></div>
                <div className="chips">
                  {THEMES.map(name => (
                    <button key={name} className="chip" onClick={() => appendToken(name)}>{name}</button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </header>

      <main>
        <section className="selected-names">
          <div className="sel-names-head">
            <strong>선택한 영화</strong>
            <span className="muted">{selected.length}/10</span>
            <div className="spacer"></div>
            <button className="ghost small" onClick={() => setSelected([])}>모두 해제</button>
          </div>
          <div className="name-chips">
            {selected.map((s, idx) => (
              <span key={idx} className="name-chip">
                <span className="nm">{s.title || '(제목 없음)'}</span>
                <button className="x" onClick={() => setSelected(prev => prev.filter((_, i) => i !== idx))}>✕</button>
              </span>
            ))}
          </div>
        </section>

        <div className="status">{status}</div>

        <div className="movie-grid">
          {currentItems.map((m, idx) => (
            <div
              key={`${keyOf(m)}-${idx}`}
              className={`card ${isSelected(m) ? 'selected' : ''}`}
              onClick={() => toggleSelection(m)}
            >
              <img className="thumb" src={m.poster || ''} alt={m.title} />
              <div className="meta">
                <div className="title">
                  {m.title || '(제목 없음)'}
                  <span className="badge">{m.source || ''}</span>
                </div>
                <div className="sub">{m.year || ''}</div>
              </div>
            </div>
          ))}
        </div>
        <div ref={sentinelRef} className="sentinel"></div>
      </main>

      <div className="pickerbar">
        <div className="sel-info"><strong>{selected.length}</strong>/10 선택됨</div>
        <div className="sel-actions">
          <button className="ghost" onClick={() => setSelected([])}>모두 해제</button>
          <button className="primary" disabled={selected.length === 0} onClick={recommendSimilar}>추천</button>
        </div>
      </div>
    </div>
  )
}

export default PopularMovies
