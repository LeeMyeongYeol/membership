import { useState, useEffect } from 'react'
import './MovieDetailModal.css'

function MovieDetailModal({ movie, isOpen, onClose }) {
  const [streaming, setStreaming] = useState(null)
  const [loadingStreaming, setLoadingStreaming] = useState(false)
  const [reviews, setReviews] = useState([
    // 임시 더미 데이터 (추후 DB 연동)
    { id: 1, author: '익명1', rating: 4.5, text: '정말 재미있게 봤습니다!', date: '2024-11-10' },
    { id: 2, author: '익명2', rating: 5.0, text: '최고의 영화입니다. 강추!', date: '2024-11-09' }
  ])
  const [newReview, setNewReview] = useState({ author: '', rating: 5, text: '' })

  useEffect(() => {
    if (isOpen && movie?.id) {
      fetchStreaming()
      // 모달 열릴 때 body 스크롤 잠금
      document.body.style.overflow = 'hidden'
    } else {
      // 모달 닫힐 때 body 스크롤 복원
      document.body.style.overflow = 'unset'
    }
    
    // 컴포넌트 언마운트 시 복원
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, movie])

  const fetchStreaming = async () => {
    setLoadingStreaming(true)
    try {
      const response = await fetch(`/api/streaming/${movie.id}?region=KR`)
      const data = await response.json()
      setStreaming(data)
    } catch (error) {
      console.error('스트리밍 정보 로드 실패:', error)
    } finally {
      setLoadingStreaming(false)
    }
  }

  const handleSubmitReview = (e) => {
    e.preventDefault()
    if (!newReview.text.trim()) {
      alert('리뷰 내용을 입력해주세요.')
      return
    }

    // TODO: 추후 API 연동
    const review = {
      id: Date.now(),
      author: newReview.author || '익명',
      rating: newReview.rating,
      text: newReview.text,
      date: new Date().toISOString().split('T')[0]
    }
    
    setReviews([review, ...reviews])
    setNewReview({ author: '', rating: 5, text: '' })
    alert('리뷰가 등록되었습니다! (임시 - DB 연동 전)')
  }

  if (!isOpen || !movie) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        
        <div className="modal-body">
          {/* 좌측: 포스터 + 장르 + 스트리밍 */}
          <div className="modal-left">
            <div className="poster-section">
              {movie.poster ? (
                <img src={movie.poster} alt={movie.title} className="modal-poster" />
              ) : (
                <div className="modal-poster-placeholder">포스터 없음</div>
              )}
            </div>

            <div className="info-section">
              <h2 className="movie-title">{movie.title}</h2>
              
              {movie.release_date && (
                <p className="movie-year">{movie.release_date.split('-')[0]}</p>
              )}

              {movie.vote_average && (
                <div className="rating-section">
                  <span className="rating-star">★</span>
                  <span className="rating-value">{movie.vote_average.toFixed(1)}</span>
                  <span className="rating-count">({movie.vote_count || 0})</span>
                </div>
              )}

              {movie.runtime && (
                <p className="runtime">{movie.runtime}분</p>
              )}

              {movie.genres && movie.genres.length > 0 && (
                <div className="genres-section">
                  <h3>장르</h3>
                  <div className="genre-tags">
                    {movie.genres.map((genre, idx) => (
                      <span key={idx} className="genre-tag">{genre}</span>
                    ))}
                  </div>
                </div>
              )}

              {movie.overview && (
                <div className="overview-section">
                  <h3>줄거리</h3>
                  <p>{movie.overview}</p>
                </div>
              )}

              {/* 스트리밍 정보 */}
              <div className="streaming-section">
                <h3>어디서 볼 수 있나요?</h3>
                {loadingStreaming ? (
                  <p className="loading-text">로딩 중...</p>
                ) : streaming ? (
                  <>
                    {streaming.flatrate && streaming.flatrate.length > 0 && (
                      <div className="streaming-category">
                        <h4>구독형 스트리밍</h4>
                        <div className="provider-list">
                          {streaming.flatrate.map((provider) => (
                            <div key={provider.provider_id} className="provider-item">
                              {provider.logo_path && (
                                <img 
                                  src={provider.logo_path} 
                                  alt={provider.provider_name}
                                  className="provider-logo"
                                />
                              )}
                              <span>{provider.provider_name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {streaming.rent && streaming.rent.length > 0 && (
                      <div className="streaming-category">
                        <h4>대여</h4>
                        <div className="provider-list">
                          {streaming.rent.map((provider) => (
                            <div key={provider.provider_id} className="provider-item">
                              {provider.logo_path && (
                                <img 
                                  src={provider.logo_path} 
                                  alt={provider.provider_name}
                                  className="provider-logo"
                                />
                              )}
                              <span>{provider.provider_name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {streaming.buy && streaming.buy.length > 0 && (
                      <div className="streaming-category">
                        <h4>구매</h4>
                        <div className="provider-list">
                          {streaming.buy.map((provider) => (
                            <div key={provider.provider_id} className="provider-item">
                              {provider.logo_path && (
                                <img 
                                  src={provider.logo_path} 
                                  alt={provider.provider_name}
                                  className="provider-logo"
                                />
                              )}
                              <span>{provider.provider_name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {!streaming.flatrate?.length && !streaming.rent?.length && !streaming.buy?.length && (
                      <p className="no-streaming">한국에서 스트리밍 정보를 찾을 수 없습니다.</p>
                    )}

                    {streaming.link && (
                      <a href={streaming.link} target="_blank" rel="noopener noreferrer" className="more-link">
                        더 많은 옵션 보기 →
                      </a>
                    )}
                  </>
                ) : (
                  <p className="no-streaming">스트리밍 정보를 불러올 수 없습니다.</p>
                )}
              </div>
            </div>
          </div>

          {/* 우측: 리뷰 섹션 */}
          <div className="modal-right">
            <div className="reviews-section">
              <h3>사용자 리뷰</h3>
              
              {/* 리뷰 작성 폼 */}
              <form className="review-form" onSubmit={handleSubmitReview}>
                <input
                  type="text"
                  placeholder="닉네임 (선택사항)"
                  value={newReview.author}
                  onChange={(e) => setNewReview({ ...newReview, author: e.target.value })}
                  className="review-input"
                  maxLength={20}
                />
                
                <div className="rating-input">
                  <label>평점: </label>
                  <select
                    value={newReview.rating}
                    onChange={(e) => setNewReview({ ...newReview, rating: parseFloat(e.target.value) })}
                    className="rating-select"
                  >
                    <option value={5}>⭐⭐⭐⭐⭐ (5.0)</option>
                    <option value={4.5}>⭐⭐⭐⭐☆ (4.5)</option>
                    <option value={4}>⭐⭐⭐⭐ (4.0)</option>
                    <option value={3.5}>⭐⭐⭐☆ (3.5)</option>
                    <option value={3}>⭐⭐⭐ (3.0)</option>
                    <option value={2.5}>⭐⭐☆ (2.5)</option>
                    <option value={2}>⭐⭐ (2.0)</option>
                    <option value={1.5}>⭐☆ (1.5)</option>
                    <option value={1}>⭐ (1.0)</option>
                  </select>
                </div>

                <textarea
                  placeholder="이 영화에 대한 감상을 남겨주세요... (DB 연동 전 임시)"
                  value={newReview.text}
                  onChange={(e) => setNewReview({ ...newReview, text: e.target.value })}
                  className="review-textarea"
                  rows={4}
                  maxLength={500}
                />
                
                <button type="submit" className="review-submit">리뷰 작성</button>
              </form>

              {/* 리뷰 목록 */}
              <div className="reviews-list">
                {reviews.length === 0 ? (
                  <p className="no-reviews">아직 리뷰가 없습니다. 첫 리뷰를 작성해보세요!</p>
                ) : (
                  reviews.map((review) => (
                    <div key={review.id} className="review-item">
                      <div className="review-header">
                        <span className="review-author">{review.author}</span>
                        <span className="review-rating">★ {review.rating.toFixed(1)}</span>
                      </div>
                      <p className="review-text">{review.text}</p>
                      <span className="review-date">{review.date}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MovieDetailModal
