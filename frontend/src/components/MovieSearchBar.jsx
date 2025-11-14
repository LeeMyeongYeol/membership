import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './MovieSearchBar.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function MovieSearchBar({ onSelectMovie, language }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const searchRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    const delayTimer = setTimeout(() => {
      if (searchQuery.trim().length > 0) {
        searchMovies(searchQuery)
      } else {
        setSuggestions([])
        setShowSuggestions(false)
      }
    }, 300)

    return () => clearTimeout(delayTimer)
  }, [searchQuery, language])

  const searchMovies = async (query) => {
    setLoading(true)
    try {
      const response = await axios.get(`${API_URL}/api/search`, {
        params: {
          q: query,
          language: language
        }
      })
      setSuggestions((response.data.results || []).slice(0, 5))
      setShowSuggestions(true)
    } catch (err) {
      console.error('검색 오류:', err)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectMovie = (movie) => {
    onSelectMovie(movie.title)
    setSearchQuery('')
    setSuggestions([])
    setShowSuggestions(false)
  }

  return (
    <div className="movie-search-bar" ref={searchRef}>
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
        placeholder="영화 제목을 검색하세요..."
        className="search-input"
      />
      {loading && <div className="search-loading">검색 중...</div>}
      {showSuggestions && suggestions.length > 0 && (
        <div className="suggestions-dropdown">
          {suggestions.map((movie) => (
            <div
              key={movie.id}
              className="suggestion-item"
              onClick={() => handleSelectMovie(movie)}
            >
              <div className="suggestion-title">
                {movie.title}
                {movie.year && <span className="suggestion-year"> ({movie.year})</span>}
              </div>
              {movie.original_title && movie.original_title !== movie.title && (
                <div className="suggestion-original">{movie.original_title}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default MovieSearchBar
