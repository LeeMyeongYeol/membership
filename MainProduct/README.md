# 🎬 LongestMovie - 영화 취향 분석 추천 시스템

TMDb + OMDb + TF-IDF 기반의 개인화된 영화 추천 서비스

## 🏗️ 프로젝트 구조

```
LongestMovie/
├── backend/                  # Flask API 서버
│   ├── api/                 # API 엔드포인트
│   ├── services/            # 비즈니스 로직
│   │   ├── tmdb_service.py
│   │   ├── omdb_service.py
│   │   └── recommendation.py
│   ├── templates/           # (사용 안 함 - React로 대체)
│   ├── app.py              # Flask 앱 진입점
│   ├── config.py           # 환경 설정
│   └── Dockerfile
│
├── frontend/                # React 프론트엔드
│   ├── src/
│   │   ├── App.jsx         # 메인 컴포넌트
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── index.css
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── nginx.conf          # Nginx 설정 (프로덕션)
│   └── Dockerfile
│
├── .env                     # 환경 변수 (API 키)
├── docker-compose.yml       # 프로덕션 배포
└── docker-compose.dev.yml   # 개발 환경
```

## 🚀 실행 방법

### 1️⃣ 환경 변수 설정

`.env` 파일에 API 키 설정:

```env
TMDB_API_KEY=your_tmdb_api_key
OMDB_API_KEY=your_omdb_api_key
```

### 2️⃣ 프로덕션(배포) 모드 (권장)

```bash
# Docker Compose로 빌드 및 실행
docker compose -f docker-compose.prod.yml up -d --build

# 백그라운드 실행
docker compose up -d

# 중지
docker compose down
```

**접속:**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### 3️⃣ 개발 모드 (Hot Reload)

```bash
# 개발 모드로 실행 (코드 변경 시 자동 새로고침)
docker compose -f docker compose.dev.yml up

# 백그라운드 실행
docker compose -f docker compose.dev.yml up -d

# 중지
docker compose -f docker compose.dev.yml down
```

**접속:**

- Frontend (Dev): http://localhost:3000
- Backend API (Dev): http://localhost:8000

### 4️⃣ 로컬 개발 (Docker 없이)

#### Backend:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

#### Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 📡 API 엔드포인트

### `GET /`

헬스 체크 및 API 정보

### `POST /api/analyze`

영화 취향 분석 및 추천

**Request:**

```json
{
  "titles": ["기생충", "인셉션", "라라랜드"],
  "language": "ko-KR"
}
```

**Response:**

```json
{
  "favorites": [...],
  "top_features": [...],
  "top_genres": [...],
  "top_directors": [...],
  "top_actors": [...],
  "recommendations": [...]
}
```

## 🛠️ 기술 스택

### Backend

- Python 3.10
- Flask 3.0
- scikit-learn (TF-IDF)
- Gunicorn
- Docker

### Frontend

- React 18
- Vite
- Axios
- Nginx (프로덕션)
- Docker

### APIs

- TMDb API (영화 데이터)
- OMDb API (IMDb 평점)

## 📦 주요 기능

1. **영화 검색 및 매칭**

   - TMDb API를 통한 정확한 영화 검색
   - 다국어 지원 (한국어, 영어, 일본어)

2. **TF-IDF 기반 추천**

   - 장르, 키워드, 감독, 배우 등을 종합 분석
   - 코사인 유사도 기반 스코어링
   - 인기도 보너스 적용

3. **패턴 분석**

   - 선호 장르 분석
   - 자주 등장하는 감독/배우
   - TF-IDF 상위 특징 추출

4. **추가 정보**
   - IMDb 평점 (OMDb API)
   - Metascore
   - 박스오피스 정보

## 🔧 환경 변수

| 변수           | 설명                       | 기본값              |
| -------------- | -------------------------- | ------------------- | --- |
| `TMDB_API_KEY` | TMDb API 키 (필수)         | -                   |
| `OMDB_API_KEY` | OMDb API 키 (선택)         | -                   |
| <!--           | `CANDIDATE_LIMIT`          | 후보 영화 최대 개수 | 150 |
| `TOPN`         | 추천 영화 개수             | 20                  |
| `ENRICH_TOP`   | OMDb 정보 추가할 영화 개수 | 10                  |
| `MAX_WORKERS`  | 병렬 처리 워커 수          | 8                   |
| `PORT`         | 백엔드 포트                | 8000                |
| `DEBUG`        | 디버그 모드                | True                | --> |

## 📝 라이센스

MIT License

## 👥 기여

이슈와 PR은 언제나 환영합니다!
