🎬 영화 취향 분석 및 추천 시스템

사용자가 좋아하는 영화를 입력하면, 해당 영화들의 줄거리와 키워드를 TF-IDF 알고리즘으로 분석하여 사용자의 취향 프로필을 생성합니다. 이 프로필을 기반으로 데이터베이스 내의 다른 영화들과 유사도를 비교하여 맞춤형 영화를 추천해주는 웹 애플리케이션입니다.

모든 서비스는 Docker Compose를 통해 컨테이너 환경에서 실행됩니다.

## ✨ 주요 기능

### ✅ 구현 완료

1. **영화 검색 및 자동완성**
   - TMDb API와 연동하여 실시간 영화 검색
   - 0.5초 디바운싱 적용으로 최적화된 API 호출
   - 한국어 우선 검색 결과 제공
   - 포스터 이미지, 제목, 개봉연도 표시

2. **영화 저장 기능**
   - 사용자가 선택한 영화를 PostgreSQL DB에 저장
   - TMDb API에서 영화 상세 정보 자동 수집 (줄거리, 키워드, 장르)
   - 관계형 데이터 구조로 효율적 저장 (movies, genres, keywords 테이블)
   - 중복 저장 방지 기능

3. **저장된 영화 관리**
   - 저장된 영화 목록을 카드 형태로 시각화
   - 영화별 평점, 장르, 개봉연도 표시
   - 우상단 X 버튼으로 영화 삭제 기능
   - 삭제 전 확인 대화상자

4. **데이터베이스 스키마**
   - PostgreSQL + pgvector 확장 활성화
   - 5개 테이블 구조 (movies, genres, keywords, movie_genres, movie_keywords, movie_vectors)
   - CASCADE 설정으로 관계 데이터 자동 관리
   - HNSW 인덱스로 벡터 검색 최적화 준비

### 🚧 구현 예정

- **취향 분석**: 사용자가 선택한 영화 목록을 기반으로 TF-IDF 벡터 생성
- **영화 추천**: 생성된 취향 벡터와 pgvector에 저장된 영화 벡터 간의 코사인 유사도 계산하여 맞춤형 영화 추천
- **TF-IDF 벡터 생성**: 영화 줄거리와 키워드 기반 벡터화
- **추천 알고리즘**: pgvector의 코사인 유사도 기반 추천 시스템

## 🛠️ 기술 스택 (Tech Stack)

**Frontend**
- React 18 (Vite)
- JavaScript (ES6+)
- CSS3 (Grid, Flexbox, Animations)

**Backend**
- FastAPI (Python 3.10)
- SQLAlchemy (ORM)
- httpx (Async HTTP client)
- psycopg2-binary (PostgreSQL driver)
- pgvector (Vector similarity search)

**Database**
- PostgreSQL 15
- pgvector extension v0.5.1

**External API**
- TMDb (The Movie Database) API v3

**DevOps**
- Docker
- Docker Compose

## 🏛️ 시스템 아키텍처

이 프로젝트는 Docker Compose에 의해 관리되는 3개의 컨테이너로 구성됩니다.

```
┌─────────────────────────────────────────────────────────┐
│                   User Browser                          │
│                 (http://localhost:5173)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Frontend Container (movie_web)                         │
│  - React 18 + Vite                                      │
│  - Port: 5173                                           │
│  - Hot Reloading 지원                                   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP Requests
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Backend Container (movie_api)                          │
│  - FastAPI + Uvicorn                                    │
│  - Port: 8000                                           │
│  - API Endpoints:                                       │
│    • GET  /search?query=...     (영화 검색)            │
│    • POST /movies/{id}          (영화 저장)            │
│    • GET  /movies               (영화 목록)            │
│    • GET  /movies/{id}          (영화 조회)            │
│    • DELETE /movies/{id}        (영화 삭제)            │
└────────────────────┬────────────────────────────────────┘
                     │ SQL Queries
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Database Container (movie_db)                          │
│  - PostgreSQL 15 + pgvector                             │
│  - Port: 5432 (internal) / 8888 (external)             │
│  - Tables:                                              │
│    • movies (영화 메타데이터)                           │
│    • genres (장르)                                      │
│    • keywords (키워드)                                  │
│    • movie_genres (영화-장르 매핑)                      │
│    • movie_keywords (영화-키워드 매핑)                  │
│    • movie_vectors (TF-IDF 벡터)                        │
└─────────────────────────────────────────────────────────┘
```

### 데이터 흐름

1. **영화 검색**: User → Frontend → Backend → TMDb API → Backend → Frontend
2. **영화 저장**: User → Frontend → Backend → TMDb API → Backend → Database
3. **저장 목록 조회**: User → Frontend → Backend → Database → Backend → Frontend
4. **영화 삭제**: User → Frontend → Backend → Database (CASCADE) → Backend → Frontend

## 🚀 로컬 환경에서 실행하기

### 1. 사전 요구 사항

- **Docker Desktop** 설치 ([다운로드](https://www.docker.com/products/docker-desktop/))
- **TMDb API Key** 발급 (발급 방법은 `.env.example` 참조)

### 2. 프로젝트 클론

```bash
git clone https://github.com/[Your-Username]/[Your-Repo-Name].git
cd [Your-Repo-Name]
```


### 3. 환경 변수 설정 (매우 중요!)

루트 디렉토리에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
```

생성된 `.env` 파일을 열어, 발급받은 본인의 TMDb API 키를 입력합니다.

```bash
# .env 파일 예시
TMDB_API_KEY=여러분의_TMDb_API_키를_여기에_붙여넣으세요

# 데이터베이스 설정 (기본값 사용 가능)
DB_USER=admin
DB_PASSWORD=admin
DB_NAME=movie_db
DB_HOST=db
DB_PORT=5432
```

### 4. Docker Compose 실행

터미널에서 아래 명령어를 입력하여 모든 서비스를 빌드하고 실행합니다.

```bash
docker-compose up --build
```

최초 실행 시 다음 작업이 자동으로 진행됩니다:
- Docker 이미지 다운로드
- 의존성 패키지 설치
- PostgreSQL 데이터베이스 초기화
- pgvector 확장 활성화
- 테이블 생성 및 초기 장르 데이터 삽입

### 5. 서비스 접속

빌드가 완료되고 모든 컨테이너가 실행되면, 아래 주소로 접속하여 확인할 수 있습니다.

- **React 웹페이지**: http://localhost:5173
- **FastAPI 서버 (루트)**: http://localhost:8000
- **FastAPI 문서 (Swagger)**: http://localhost:8000/docs
- **FastAPI 검색 테스트**: http://localhost:8000/search?query=인셉션
- **PostgreSQL DB (외부 접속)**:
  - Host: `localhost`
  - Port: `8888`
  - Database: `movie_db`
  - User: `admin`
  - Password: `admin`

## ⚙️ Docker Compose 명령어

```bash
# 서비스 시작
docker-compose up

# 백그라운드 실행
docker-compose up -d

# 서비스 중지
docker-compose down

# 특정 서비스 로그 확인
docker-compose logs -f api

# 특정 서비스 재시작
docker-compose restart api

# 강제 재빌드
docker-compose up --build

# 볼륨까지 완전히 삭제 (데이터베이스 초기화)
docker-compose down -v
```

## 📁 프로젝트 구조

```
movie-recommender/
├── backend/
│   ├── main.py                 # FastAPI 메인 애플리케이션
│   ├── database.py             # DB 연결 설정
│   ├── models.py               # SQLAlchemy ORM 모델
│   ├── tmdb_service.py         # TMDb API 서비스
│   ├── movie_service.py        # 영화 CRUD 서비스
│   ├── init_db.sql             # DB 스키마 정의
│   ├── init_database.py        # DB 초기화 스크립트
│   ├── startup.sh              # 컨테이너 시작 스크립트
│   ├── requirements.txt        # Python 의존성
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # React 메인 컴포넌트
│   │   ├── App.css             # 스타일시트
│   │   └── main.jsx            # React 진입점
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml          # Docker Compose 설정
├── .env                        # 환경 변수 (Git에 포함 안 됨)
├── .env.example                # 환경 변수 템플릿
├── .gitignore
├── README.md
└── LICENSE
```

## 🎯 사용 방법

1. **영화 검색**: 검색창에 영화 제목 입력 (예: "인셉션", "기생충")
2. **영화 선택**: 드롭다운에서 원하는 영화 클릭
3. **영화 저장**: "이 영화 저장하기" 버튼 클릭
4. **저장 확인**: 하단에 저장된 영화 카드 표시
5. **영화 삭제**: 영화 카드 우상단의 X 버튼 클릭

## 🔧 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | 서버 상태 확인 |
| GET | `/search?query={query}` | 영화 검색 (TMDb) |
| POST | `/movies/{movie_id}` | 영화 저장 |
| GET | `/movies/{movie_id}` | 영화 조회 |
| GET | `/movies?skip={skip}&limit={limit}` | 영화 목록 조회 |
| DELETE | `/movies/{movie_id}` | 영화 삭제 |

## 📊 데이터베이스 ERD

```
movies (영화 메타데이터)
├─ id (PK, TMDb ID)
├─ title
├─ original_title
├─ release_date
├─ overview (줄거리)
├─ popularity
├─ vote_average
├─ vote_count
├─ poster_path
├─ backdrop_path
└─ timestamps

genres (장르)                    movie_genres (매핑)
├─ id (PK, TMDb ID)              ├─ movie_id (FK)
└─ name                          └─ genre_id (FK)

keywords (키워드)                movie_keywords (매핑)
├─ id (PK, TMDb ID)              ├─ movie_id (FK)
└─ name                          └─ keyword_id (FK)

movie_vectors (TF-IDF)
├─ movie_id (PK, FK)
├─ tfidf_vector (vector(512))
└─ timestamps
```

## 📄 라이센스

이 프로젝트는 MIT License를 따릅니다.

---

## 🤝 기여하기

Pull Request는 언제나 환영합니다! 주요 변경사항이 있다면 먼저 Issue를 열어주세요.

## 📞 문의

프로젝트에 대한 질문이나 제안이 있으시면 Issue를 통해 알려주세요.