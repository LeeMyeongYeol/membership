import { useState, useEffect } from 'react';
import './App.css';

// FastAPI 서버 주소 (docker-compose.yml에서 설정한 'api' 서비스)
// React는 브라우저에서 실행되므로, 'localhost:8000'으로 접근합니다.
const API_URL = 'http://localhost:8000';

function App() {
  // 1. 사용자가 입력 중인 검색어
  const [searchTerm, setSearchTerm] = useState('');

  // 2. API로부터 받은 검색 결과 (영화 목록)
  const [searchResults, setSearchResults] = useState([]);

  // 3. 사용자가 최종 선택한 영화
  const [selectedMovie, setSelectedMovie] = useState(null);

  // 4. 사용자가 추가한 영화 목록 (추천 대상)
  const [myMovies, setMyMovies] = useState([]);

  // 5. 추가 중 상태
  const [isAdding, setIsAdding] = useState(false);

  // 6. 추천 시스템 관련 상태
  const [recommendations, setRecommendations] = useState([]);
  const [recommendationLimit, setRecommendationLimit] = useState(20);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);

  // useEffect: searchTerm이 변경될 때마다 실행됩니다.
  useEffect(() => {
    // 사용자가 타이핑을 멈출 때까지 기다리기 (디바운싱)
    const delayDebounceFn = setTimeout(() => {
      // 검색어가 비어있지 않다면 API 호출
      if (searchTerm) {
        fetch(`${API_URL}/search?query=${searchTerm}`)
          .then(response => response.json())
          .then(data => {
            if (data && !data.error) {
              setSearchResults(data);
            } else {
              setSearchResults([]);
            }
          })
          .catch(error => console.error("Search API Error:", error));
      } else {
        // 검색어가 비어있으면 결과 목록도 비움
        setSearchResults([]);
      }
    }, 500); // 500ms (0.5초) 동안 타이핑이 없으면 검색 실행

    // cleanup 함수:
    // 0.5초가 지나기 전에 사용자가 다시 타이핑하면, 
    // 이전에 예약된 API 호출(setTimeout)을 취소합니다.
    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm]); // searchTerm이 바뀔 때만 이 hook을 다시 실행

  // 초기 로딩 제거 (사용자가 직접 추가하는 방식으로 변경)

  // 검색 결과에서 영화를 클릭했을 때
  const handleMovieSelect = (movie) => {
    // 1. 선택한 영화를 state에 저장
    setSelectedMovie(movie);
    // 2. 검색창에 선택한 영화 제목을 표시
    setSearchTerm(movie.title);
    // 3. 검색 결과(드롭다운)를 닫음
    setSearchResults([]);
  };

  // 영화를 내 목록에 추가 (DB에 자동 저장)
  const handleAddMovie = async () => {
    if (!selectedMovie) return;

    // 이미 추가된 영화인지 확인
    if (myMovies.some(m => m.id === selectedMovie.id)) {
      alert('이미 추가된 영화입니다.');
      return;
    }

    setIsAdding(true);
    try {
      // DB에 저장 (없으면 자동 등록)
      const response = await fetch(`${API_URL}/movies/${selectedMovie.id}`, {
        method: 'POST',
      });

      const data = await response.json();

      if (data.status === 'success') {
        // 내 목록에 추가
        setMyMovies([...myMovies, data.movie]);
        // 검색창 초기화
        setSelectedMovie(null);
        setSearchTerm('');
      } else {
        alert('영화 추가에 실패했습니다.');
      }
    } catch (error) {
      console.error("Error adding movie:", error);
      alert('영화 추가 중 오류가 발생했습니다.');
    } finally {
      setIsAdding(false);
    }
  };

  // 내 목록에서 영화 제거
  const handleRemoveMovie = (movieId) => {
    setMyMovies(myMovies.filter(m => m.id !== movieId));
  };

  // 포스터 이미지 URL을 완성해주는 헬퍼 함수
  const getPosterUrl = (posterPath) => {
    return posterPath
      ? `https://image.tmdb.org/t/p/w200${posterPath}`
      : 'https://placehold.co/200x300?text=No+Image'; // 포스터 없을 시
  };

  // 영화 추천 받기 (내 목록의 모든 영화 기반)
  const handleGetRecommendations = async () => {
    if (myMovies.length === 0) {
      alert('추천을 받으려면 최소 1개 이상의 영화를 추가해주세요.');
      return;
    }

    setIsLoadingRecommendations(true);
    try {
      const movieIds = myMovies.map(m => m.id);

      const response = await fetch(`${API_URL}/recommend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          movie_ids: movieIds,
          limit: recommendationLimit,
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        setRecommendations(data.recommendations);

        // 벡터 생성 결과 표시
        if (data.vector_generation?.newly_created > 0) {
          alert(`✓ ${data.vector_generation.newly_created}개 영화의 분석 데이터를 생성했습니다.`);
        }

        // 스크롤을 추천 결과로 이동
        setTimeout(() => {
          document.getElementById('recommendations-section')?.scrollIntoView({
            behavior: 'smooth'
          });
        }, 100);
      } else {
        alert('추천을 받는데 실패했습니다.');
      }
    } catch (error) {
      console.error("Error getting recommendations:", error);
      alert('추천 요청 중 오류가 발생했습니다.');
    } finally {
      setIsLoadingRecommendations(false);
    }
  };

  return (
    <div className="container">
      <h1>🎬 영화 취향 분석기</h1>
      <p>가장 좋아하는 영화를 검색해 보세요.</p>
      
      <div className="search-container">
        <input
          type="text"
          className="search-input"
          placeholder="예: 인셉션, 기생충..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        
        {/* 검색 결과 드롭다운 */}
        {searchResults.length > 0 && (
          <ul className="search-results">
            {searchResults.map(movie => (
              <li 
                key={movie.id} 
                className="result-item"
                onClick={() => handleMovieSelect(movie)}
              >
                <img 
                  src={getPosterUrl(movie.poster_path)}
                  alt={movie.title} 
                  className="result-poster"
                />
                <div className="result-info">
                  <strong>{movie.title}</strong>
                  <span>({movie.release_date ? movie.release_date.split('-')[0] : 'N/A'})</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 사용자가 영화를 선택하면 표시됨 */}
      {selectedMovie && (
        <div className="selected-movie">
          <h2>선택한 영화: {selectedMovie.title}</h2>
          <img
            src={getPosterUrl(selectedMovie.poster_path)}
            alt={selectedMovie.title}
          />
          <p>({selectedMovie.release_date ? selectedMovie.release_date.split('-')[0] : 'N/A'})</p>
          <button
            onClick={handleAddMovie}
            disabled={isAdding}
            className="save-button"
          >
            {isAdding ? '추가 중...' : '내 목록에 추가하기'}
          </button>
        </div>
      )}

      {/* 내가 선택한 영화 목록 */}
      <div className="my-movies-section">
        <h2>내가 좋아하는 영화 {myMovies.length > 0 && `(${myMovies.length}개)`}</h2>

        {myMovies.length === 0 ? (
          <div className="empty-state">
            <p>아직 추가된 영화가 없습니다.</p>
            <p>위에서 영화를 검색하여 추가해보세요!</p>
          </div>
        ) : (
          <>
            <div className="movie-grid">
              {myMovies.map(movie => (
                <div key={movie.id} className="movie-card">
                  <button
                    className="delete-button"
                    onClick={() => handleRemoveMovie(movie.id)}
                    aria-label="영화 제거"
                  >
                    ×
                  </button>
                  <img
                    src={getPosterUrl(movie.poster_path)}
                    alt={movie.title}
                  />
                  <h3>{movie.title}</h3>
                  <p className="movie-year">
                    {movie.release_date ? movie.release_date.split('-')[0] : 'N/A'}
                  </p>
                  <p className="movie-rating">⭐ {movie.vote_average?.toFixed(1)}</p>
                  <div className="movie-genres">
                    {movie.genres?.slice(0, 2).map(genre => (
                      <span key={genre.id} className="genre-tag">{genre.name}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* 추천 받기 컨트롤 */}
            <div className="recommendation-controls">
              <h3>이 영화들을 기반으로 추천받기</h3>
              <div className="slider-container">
                <label>추천 받을 영화 개수: {recommendationLimit}개</label>
                <input
                  type="range"
                  min="10"
                  max="50"
                  value={recommendationLimit}
                  onChange={(e) => setRecommendationLimit(parseInt(e.target.value))}
                  className="recommendation-slider"
                />
              </div>
              <button
                onClick={handleGetRecommendations}
                disabled={isLoadingRecommendations}
                className="recommend-button"
              >
                {isLoadingRecommendations ? '분석 중...' : '🎯 영화 추천 받기'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* 추천 결과 */}
      {recommendations.length > 0 && (
        <div id="recommendations-section" className="recommendations-section">
          <h2>🎬 추천 영화 ({recommendations.length}개)</h2>
          <p className="recommendation-subtitle">
            선택하신 영화를 분석하여 취향에 맞는 영화를 찾았습니다!
          </p>
          <div className="movie-grid">
            {recommendations.map((movie, index) => (
              <div key={movie.id} className="movie-card recommendation-card">
                <div className="recommendation-rank">#{index + 1}</div>
                <div className="similarity-badge">
                  {movie.similarity_percent}% 유사
                </div>
                <img
                  src={getPosterUrl(movie.poster_path)}
                  alt={movie.title}
                />
                <h3>{movie.title}</h3>
                <p className="movie-year">
                  {movie.release_date ? movie.release_date.split('-')[0] : 'N/A'}
                </p>
                <p className="movie-rating">⭐ {movie.vote_average?.toFixed(1)}</p>
                <div className="movie-genres">
                  {movie.genres?.slice(0, 2).map(genre => (
                    <span key={genre.id} className="genre-tag">{genre.name}</span>
                  ))}
                </div>
                {movie.overview && (
                  <p className="movie-overview">
                    {movie.overview.length > 100
                      ? movie.overview.substring(0, 100) + '...'
                      : movie.overview}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;