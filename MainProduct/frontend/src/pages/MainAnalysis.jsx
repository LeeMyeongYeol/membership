import { useState } from 'react'
import axios from 'axios'
import MovieDetailModal from '../components/MovieDetailModal'
import './MainAnalysis.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function MainAnalysis() {
  const [titles, setTitles] = useState('')
  const [language, setLanguage] = useState('ko-KR')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [selectedMovie, setSelectedMovie] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleAnalyze = async () => {
    setError('')
    setResult(null)

    const titleList = titles
      .split('\n')
      .map(t => t.trim())
      .filter(Boolean)

    if (titleList.length === 0) {
      setError('영화 제목을 한 개 이상 입력하세요.')
      return
    }

    setLoading(true)

    try {
      const response = await axios.post(`${API_URL}/api/analyze`, {
        titles: titleList,
        language: language
      })
      setResult(response.data)
    } catch (err) {
      setError(err.response?.data?.error || err.message || '요청 실패')
    } finally {
      setLoading(false)
    }
  }

  const renderChipList = (title, items) => {
    if (!items || items.length === 0) return null
    return (
      <div className="row">
        <div className="pill">{title}</div>
        {items.map(([name, count], idx) => (
          <span key={idx} className="pill">{name} × {count}</span>
        ))}
      </div>
    )
  }

  const renderFeatureList = (items) => {
    if (!items || items.length === 0) {
      return <div className="hint">(패턴이 아직 없습니다)</div>
    }
    return (
      <div className="features">
        {items.map(([name, score], idx) => (
          <span key={idx}>
            {name} <small style={{ opacity: 0.6 }}>{score.toFixed(3)}</small>
          </span>
        ))}
      </div>
    )
  }

  const handleMovieClick = (item) => {
    setSelectedMovie(item)
    setIsModalOpen(true)
  }

  const renderMovieCard = (item) => {
    const poster = item.poster
      ? <img className="poster" loading="lazy" src={item.poster} alt={item.title} onClick={() => handleMovieClick(item)} style={{ cursor: 'pointer' }} />
      : <div onClick={() => handleMovieClick(item)} style={{ height: '180px', background: '#0b1430', cursor: 'pointer' }}></div>

    const genres = (item.genres || []).map((g, idx) => (
      <span key={idx} className="badge">{g}</span>
    ))

    const extra = [
      item.release_date ? `개봉 ${item.release_date}` : null,
      item.runtime ? `${item.runtime}분` : null,
      item.vote_average ? `TMDb ★${item.vote_average.toFixed(1)} (${item.vote_count || 0})` : null,
      item.omdb?.imdbRating ? `IMDb ★${item.omdb.imdbRating}` : null,
      item.omdb?.metascore ? `Metascore ${item.omdb.metascore}` : null,
    ].filter(Boolean).join(' · ')

    const overview = item.overview || ''
    const shortOverview = overview.length > 180 ? overview.slice(0, 180) + '…' : overview

    return (
      <div className="rec" key={item.id}>
        {poster}
        <div className="info">
          <div style={{ fontWeight: 700, marginBottom: '6px' }}>{item.title}</div>
          <div className="row" style={{ marginBottom: '6px' }}>{genres}</div>
          <div className="hint" style={{ marginBottom: '6px' }}>{extra}</div>
          <div style={{ fontSize: '13px', opacity: 0.9 }}>{shortOverview}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="main-analysis">
      <header className="page-header">
        <div className="container">
          <h1> 영화 취향 분석 추천 </h1>
          <div className="hint">TMDb + OMDb + Python TF‑IDF로 내가 좋아할 영화를 찾아줍니다.</div>
        </div>
      </header>

      <div className="container">
        <div className="grid">
          <div className="card">
            <h3>1) 좋아하는 영화 제목 (한 줄에 1개)</h3>
            <textarea
              rows="10"
              value={titles}
              onChange={(e) => setTitles(e.target.value)}
              placeholder="예) 기생충&#10;인셉션&#10;라라랜드&#10;어바웃 타임&#10;인터스텔라&#10;암살&#10;헤어질 결심"
            />
            <div className="row" style={{ marginTop: '10px' }}>
              <div style={{ flex: 1 }}>
                <label className="hint">언어 (TMDb 응답 언어)</label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                  <option value="ko-KR">한국어 (ko-KR)</option>
                  <option value="en-US">영어 (en-US)</option>
                  <option value="ja-JP">일본어 (ja-JP)</option>
                </select>
              </div>
              <div>
                <button onClick={handleAnalyze} disabled={loading}>
                  {loading ? '분석 중…' : '분석 & 추천 실행'}
                </button>
              </div>
            </div>
            <p className="hint" style={{ marginTop: '10px' }}>
              * 서버의 .env에 TMDB_API_KEY, OMDB_API_KEY를 넣어두면 자동 사용합니다.
            </p>
          </div>

          <div className="card">
            <h3>2) 감지된 공통 패턴 (Top 10 TF‑IDF 특징)</h3>
            {result && (
              <>
                {renderFeatureList(result.top_features)}
                <div style={{ height: '8px' }}></div>
                {renderChipList('Top 장르', result.top_genres)}
                <div style={{ height: '8px' }}></div>
                {renderChipList('Top 감독', result.top_directors)}
                <div style={{ height: '8px' }}></div>
                {renderChipList('Top 배우', result.top_actors)}
              </>
            )}
          </div>
        </div>

        <div className="card" style={{ marginTop: '20px' }}>
          <h3>3) 맞춤 추천</h3>
          {error && <div className="hint" style={{ color: '#ff9c9c' }}>{error}</div>}
          {result && (
            <div className="rec-grid">
              {result.recommendations.map(renderMovieCard)}
            </div>
          )}
        </div>
      </div>

      <footer className="page-footer">© TF‑IDF Recommender • TMDb/OMDb 데이터를 사용합니다.</footer>

      <MovieDetailModal 
        movie={selectedMovie}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  )
}

export default MainAnalysis
