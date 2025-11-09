-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 영화 메타데이터 테이블
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,  -- TMDb movie ID
    title VARCHAR(500) NOT NULL,
    original_title VARCHAR(500),
    release_date DATE,
    overview TEXT,  -- 영화 줄거리
    original_language VARCHAR(10),
    popularity FLOAT,
    vote_average FLOAT,
    vote_count INTEGER,
    poster_path VARCHAR(200),
    backdrop_path VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 장르 테이블
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,  -- TMDb genre ID
    name VARCHAR(100) NOT NULL
);

-- 영화-장르 매핑 테이블 (다대다 관계)
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,
    genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- 키워드 테이블
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY,  -- TMDb keyword ID
    name VARCHAR(200) NOT NULL UNIQUE
);

-- 영화-키워드 매핑 테이블 (다대다 관계)
CREATE TABLE IF NOT EXISTS movie_keywords (
    movie_id INTEGER REFERENCES movies(id) ON DELETE CASCADE,
    keyword_id INTEGER REFERENCES keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, keyword_id)
);

-- TF-IDF 벡터 저장 테이블
CREATE TABLE IF NOT EXISTS movie_vectors (
    movie_id INTEGER PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
    tfidf_vector vector(512),  -- TF-IDF 벡터 (차원은 필요에 따라 조정 가능)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 성능 향상을 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);
CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date);
CREATE INDEX IF NOT EXISTS idx_movies_popularity ON movies(popularity DESC);
CREATE INDEX IF NOT EXISTS idx_keywords_name ON keywords(name);

-- pgvector를 활용한 유사도 검색을 위한 인덱스
-- HNSW (Hierarchical Navigable Small World) 알고리즘 사용
-- 코사인 유사도를 위해 vector_cosine_ops 사용
CREATE INDEX IF NOT EXISTS idx_movie_vectors_cosine
ON movie_vectors USING hnsw (tfidf_vector vector_cosine_ops);

-- 장르 초기 데이터 삽입 (TMDb 표준 장르)
INSERT INTO genres (id, name) VALUES
    (28, 'Action'),
    (12, 'Adventure'),
    (16, 'Animation'),
    (35, 'Comedy'),
    (80, 'Crime'),
    (99, 'Documentary'),
    (18, 'Drama'),
    (10751, 'Family'),
    (14, 'Fantasy'),
    (36, 'History'),
    (27, 'Horror'),
    (10402, 'Music'),
    (9648, 'Mystery'),
    (10749, 'Romance'),
    (878, 'Science Fiction'),
    (10770, 'TV Movie'),
    (53, 'Thriller'),
    (10752, 'War'),
    (37, 'Western')
ON CONFLICT (id) DO NOTHING;

-- updated_at 자동 업데이트를 위한 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- movies 테이블에 트리거 추가
DROP TRIGGER IF EXISTS update_movies_updated_at ON movies;
CREATE TRIGGER update_movies_updated_at
    BEFORE UPDATE ON movies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- movie_vectors 테이블에 트리거 추가
DROP TRIGGER IF EXISTS update_movie_vectors_updated_at ON movie_vectors;
CREATE TRIGGER update_movie_vectors_updated_at
    BEFORE UPDATE ON movie_vectors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
