import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import MovieDetailModal from '../components/MovieDetailModal';
import './PopularMovies.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TMDB_API_KEY_FRONT = 'ddd654eb8622a67e04f93f613653426d';
const POSTER_BASE = 'https://image.tmdb.org/t/p/w500';

const GENRES = [
  'Action (액션)',
  'Adventure (모험)',
  'Animation (애니메이션)',
  'Comedy (코미디)',
  'Crime (범죄)',
  'Drama (드라마)',
  'Fantasy (판타지)',
  'Historical (사극/역사)',
  'Horror (공포)',
  'Musical (뮤지컬)',
  'Mystery (미스터리)',
  'Romance (로맨스)',
  'Sci-Fi (SF / 공상과학)',
  'Thriller (스릴러)',
  'War (전쟁)',
  'Western (서부극)',
  'Documentary (다큐멘터리)',
  'Family (가족)',
  'Biography (전기)',
  'Sport (스포츠)',
];
const REGIONS = ['한국영화', '해외영화', '일본영화', '중국영화', '프랑스영화'];
const THEMES = [
  'Now Playing (현재 상영작)',
  'Upcoming (개봉 예정작)',
  'Top Rated (평점 높은 순)',
  'Popular (인기순)',
  'Classic (고전 명작)',
];

const REGION_LANG = {
  한국영화: 'ko',
  해외영화: 'en',
  일본영화: 'ja',
  중국영화: 'zh',
  프랑스영화: 'fr',
};

function PopularMovies() {
  const [tokens, setTokens] = useState([]);
  const [query, setQuery] = useState('');
  const [panelOpen, setPanelOpen] = useState(false);
  const [currentItems, setCurrentItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [noMore, setNoMore] = useState(false);
  const [status, setStatus] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const sentinelRef = useRef(null);
  const queryInputRef = useRef(null);

  const posterUrl = (path) => (path ? `${POSTER_BASE}${path}` : '');

  // 토큰 분류
  const categorizeTokens = () => {
    const genreTokens = tokens.filter((t) =>
      GENRES.some((g) => g.includes(t) || t.includes(g.split('(')[0].trim()))
    );
    const themeTokens = tokens.filter((t) =>
      THEMES.some((th) => th.includes(t) || t.includes(th.split('(')[0].trim()))
    );
    const regionToken = tokens.find((t) => REGION_LANG[t]) || null;

    return { genreTokens, themeTokens, regionToken };
  };

  // API 호출
  const apiGet = async (path, params = {}) => {
    try {
      const response = await axios.get(`${API_BASE}${path}`, { params });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || error.message);
    }
  };

  const apiPost = async (path, data = {}) => {
    try {
      const response = await axios.post(`${API_BASE}${path}`, data);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || error.message);
    }
  };

  const fetchPopularBackend = async (pageNum = 1) => {
    const { items } = await apiGet('/api/popular', { page: pageNum });
    return items || [];
  };

  const fetchPopularFront = async (pageNum = 1) => {
    if (!TMDB_API_KEY_FRONT) throw new Error('No TMDb front key');
    const url = `https://api.themoviedb.org/3/movie/popular?api_key=${encodeURIComponent(
      TMDB_API_KEY_FRONT
    )}&language=ko-KR&region=KR&page=${pageNum}`;
    const response = await axios.get(url);
    return (response.data.results || []).map((n) => ({
      title: n.title || n.name || '',
      year: (n.release_date || n.first_air_date || '').slice(0, 4),
      poster: posterUrl(n.poster_path),
      source: 'TMDb',
      id: n.id,
    }));
  };

  // 새로운 discover API 호출
  const fetchDiscover = async (pageNum = 1) => {
    const { genreTokens, themeTokens, regionToken } = categorizeTokens();

    const lang = regionToken ? REGION_LANG[regionToken] : 'ko-KR';

    const response = await apiPost('/api/discover', {
      genres: genreTokens,
      themes: themeTokens,
      language: lang,
      page: pageNum,
    });

    return response.items || [];
  };

  // 검색 API 호출
  const fetchSearch = async (searchQuery, pageNum = 1) => {
    const { items } = await apiGet('/api/search', {
      q: searchQuery,
      source: 'both',
      page: pageNum,
    });
    return items || [];
  };

  // 토큰 추가
  const appendToken = (text) => {
    const t = (text || '').trim();
    if (!t || tokens.includes(t)) return;
    setTokens((prev) => [...prev, t]);
    if (queryInputRef.current) {
      queryInputRef.current.focus();
    }
  };

  // 영화 불러오기
  const loadMovies = async (page = 1, append = false) => {
    setLoading(true);
    try {
      let movies = [];

      // 토큰이나 검색어가 있으면
      if (tokens.length > 0 || query.trim()) {
        const { genreTokens, themeTokens } = categorizeTokens();

        // 검색어가 있으면 검색 우선
        if (query.trim()) {
          const searchQuery = [...tokens, query.trim()].join(' ');
          setStatus(`"${searchQuery}" 검색 중...`);
          movies = await fetchSearch(searchQuery, page);
        }
        // 장르나 테마 토큰이 있으면 discover
        else if (genreTokens.length > 0 || themeTokens.length > 0) {
          setStatus('영화 필터링 중...');
          movies = await fetchDiscover(page);
        }
        // 국가 토큰만 있으면 인기영화 (해당 언어)
        else {
          setStatus('인기 영화 불러오는 중...');
          try {
            movies = await fetchPopularBackend(page);
          } catch {
            movies = await fetchPopularFront(page);
          }
        }
      }
      // 아무것도 없으면 인기영화
      else {
        setStatus('인기 영화 불러오는 중...');
        try {
          movies = await fetchPopularBackend(page);
        } catch {
          movies = await fetchPopularFront(page);
        }
      }

      if (movies.length === 0) {
        setNoMore(true);
        setStatus(
          append ? `총 ${currentItems.length}개 결과` : '결과가 없습니다'
        );
      } else {
        if (append) {
          setCurrentItems((prev) => [...prev, ...movies]);
          setStatus(`${currentItems.length + movies.length}개 결과`);
        } else {
          setCurrentItems(movies);
          setStatus(`${movies.length}개 결과`);
        }
        setCurrentPage(page);
      }
    } catch (e) {
      console.error(e);
      setStatus('오류가 발생했습니다: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  // 검색 수행
  const performSearch = async (closeAfter = false) => {
    setNoMore(false);
    await loadMovies(1, false);
    if (closeAfter) setPanelOpen(false);
  };

  // 영화 클릭 핸들러
  const handleMovieClick = async (movie) => {
    // 필요한 데이터 보강
    const enrichedMovie = {
      ...movie,
      id: movie.id,
      title: movie.title,
      poster: movie.poster,
      year: movie.year,
      // MainAnalysis와 호환성을 위해 release_date 추가
      release_date: movie.year ? `${movie.year}-01-01` : null,
      // 기본값 설정
      genres: movie.genres || [],
      overview: movie.overview || '',
      vote_average: movie.vote_average || 0,
      vote_count: movie.vote_count || 0,
      runtime: movie.runtime || null,
    };
    setSelectedMovie(enrichedMovie);
    setIsModalOpen(true);
  };

  // 초기 로드
  useEffect(() => {
    loadMovies(1, false);
  }, []);

  // 토큰 변경 시 검색
  useEffect(() => {
    if (tokens.length > 0) {
      loadMovies(1, false);
    }
  }, [tokens]);

  // 무한 스크롤
  useEffect(() => {
    if (!sentinelRef.current) return;

    const observer = new IntersectionObserver(
      async (entries) => {
        const entry = entries[0];
        if (!entry.isIntersecting || loading || noMore) return;

        await loadMovies(currentPage + 1, true);
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinelRef.current);

    return () => observer.disconnect();
  }, [loading, noMore, currentPage]);

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
              <svg
                className="icon-img"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                width="24"
                height="24"
              >
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
                      <button
                        onClick={() => {
                          setTokens((prev) =>
                            prev.filter((_, idx) => idx !== i)
                          );
                        }}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
                <input
                  ref={queryInputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Backspace' && !query && tokens.length) {
                      setTokens((prev) => prev.slice(0, -1));
                    }
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      performSearch(true);
                    }
                  }}
                  placeholder="검색어 입력 후 Enter를 누르면 패널이 닫혀요"
                />
              </div>
              <button className="icon-btn" onClick={() => setPanelOpen(false)}>
                ✕
              </button>
            </div>

            <button
              className="clear-all"
              onClick={() => {
                setTokens([]);
                setQuery('');
              }}
            >
              카테고리 전부 지우기
            </button>

            <div className="grid">
              <div className="col">
                <div className="section">
                  <strong>장르 (Genre)</strong>
                </div>
                <div className="chips">
                  {GENRES.map((name) => (
                    <button
                      key={name}
                      className="chip"
                      onClick={() => appendToken(name)}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
              <div className="col">
                <div className="section">
                  <strong>국가 / 지역</strong>
                </div>
                <div className="chips">
                  {REGIONS.map((name) => (
                    <button
                      key={name}
                      className="chip"
                      onClick={() => appendToken(name)}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
              <div className="col">
                <div className="section">
                  <strong>테마 (Theme)</strong>
                </div>
                <div className="chips">
                  {THEMES.map((name) => (
                    <button
                      key={name}
                      className="chip"
                      onClick={() => appendToken(name)}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </header>

      <main>
        <div className="status">{status}</div>

        <div className="movie-grid">
          {currentItems.map((m, idx) => (
            <div
              key={`${m.id}-${idx}`}
              className="card"
              onClick={() => handleMovieClick(m)}
              style={{ cursor: 'pointer' }}
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

      <MovieDetailModal
        movie={selectedMovie}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}

export default PopularMovies;
