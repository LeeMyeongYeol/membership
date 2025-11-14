# LongestMovie Backend - 영화 추천 시스템

## 📁 프로젝트 구조

```
backend/
├── app.py                    # Flask 앱 진입점 (간소화됨)
├── app_old.py                # 이전 버전 백업
├── config.py                 # 환경 변수 및 설정
│
├── api/                      # API 엔드포인트
│   ├── __init__.py
│   └── routes.py             # Flask 라우트 정의
│
├── services/                 # 비즈니스 로직
│   ├── __init__.py
│   ├── tmdb_service.py       # TMDb API 서비스 (스트리밍 정보 포함)
│   ├── omdb_service.py       # OMDb API 서비스
│   └── recommendation.py     # 추천 알고리즘 (TF-IDF)
│
├── templates/                # HTML 템플릿
│   └── index.html
│
├── utils/                    # 공통 유틸리티 (확장 가능)
│   └── __init__.py
│
├── requirements.txt          # Python 의존성
├── Dockerfile
├── STREAMING_API_EXAMPLES.md # 스트리밍 API 사용 가이드
└── test_streaming_api.py     # 스트리밍 API 테스트 스크립트
```

## 🔧 주요 기능

### 1. **영화 취향 분석 및 추천 (TF-IDF)**
- 좋아하는 영화 제목 입력 → TF-IDF 기반 맞춤 추천
- 장르, 감독, 배우, 키워드 패턴 분석
- TMDb + OMDb 데이터 결합

### 2. **영화 발견 (Discover)**
- 장르, 테마, 국가별 영화 필터링
- 인기순, 평점순, 최신작, 고전 명작 등

### 3. **영화 검색**
- TMDb + OMDb 통합 검색
- 다국어 지원

### 4. **스트리밍 정보 조회 ⭐ NEW**
- 영화 ID로 OTT 플랫폼 정보 조회
- Netflix, Disney+, Watcha 등 구독형 서비스
- 대여/구매 가능 플랫폼 정보
- 국가별 스트리밍 정보 제공 (KR, US, JP 등)
- 단일/대량 조회 지원

## 🚀 API 엔드포인트

### 헬스 체크
```
GET /
```

### 영화 분석 및 추천
```
POST /api/analyze
Body: {
  "titles": ["기생충", "인셉션", "인터스텔라"],
  "language": "ko-KR"
}
```

### 영화 발견
```
POST /api/discover
Body: {
  "genres": ["Action", "Sci-Fi"],
  "themes": ["Popular"],
  "language": "ko-KR",
  "page": 1
}
```

### 영화 검색
```
GET /api/search?q=기생충&source=both&page=1
```

### 인기 영화
```
GET /api/popular?page=1
```

### 스트리밍 정보 조회 (단일)
```
GET /api/streaming/{movie_id}?region=KR
```

### 스트리밍 정보 조회 (대량)
```
POST /api/streaming/bulk
Body: {
  "movie_ids": [550, 680, 155],
  "region": "KR"
}
```

자세한 스트리밍 API 사용법은 [STREAMING_API_EXAMPLES.md](./STREAMING_API_EXAMPLES.md) 참고

## 🔧 주요 변경사항

### 1. **모듈화**
- 단일 파일(500줄)에서 역할별로 분리
- 각 모듈이 명확한 책임을 가짐

### 2. **서비스 레이어**
- `TMDbService`: TMDb API 호출 전담 (스트리밍 정보 포함)
- `OMDbService`: OMDb API 호출 전담
- `RecommendationService`: TF-IDF 추천 알고리즘 전담

### 3. **설정 관리**
- `config.py`에서 모든 환경 변수와 설정을 중앙 관리
- 하드코딩된 값 제거

### 4. **API 라우트 분리**
- `api/routes.py`에서 Flask 엔드포인트만 관리
- 비즈니스 로직과 라우팅 로직 분리

### 5. **캐싱 최적화**
- LRU 캐시를 통한 중복 API 호출 방지
- 스트리밍 정보 캐시 (최대 2048개)
- 영화 상세 정보 캐시 (최대 8192개)

## 🏃 실행 방법

### 로컬 개발 환경
```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일 설정 (필수!)
cp .env.example .env
# TMDB_API_KEY와 OMDB_API_KEY 입력

# 서버 실행
python app.py
```

### Docker 사용
```bash
# 개발 환경
docker-compose -f docker-compose.dev.yml up

# 프로덕션 환경
docker-compose up
```

### 스트리밍 API 테스트
```bash
# 서버 실행 후
python test_streaming_api.py
```

## ⚙️ 환경 변수

`.env` 파일에 다음 설정 필요:

```env
# 필수 API 키
TMDB_API_KEY=your_tmdb_key_here
OMDB_API_KEY=your_omdb_key_here

# 선택사항 (기본값이 있음)
CANDIDATE_LIMIT=150
TOPN=20
ENRICH_TOP=10
MAX_WORKERS=8
PORT=8000
DEBUG=True
```

### API 키 발급 방법

1. **TMDb API Key**
   - https://www.themoviedb.org/ 회원가입
   - 설정 → API → API 키 신청
   - 무료 / 즉시 발급

2. **OMDb API Key** (선택)
   - https://www.omdbapi.com/apikey.aspx
   - 이메일 인증 후 발급
   - 무료 버전: 1일 1000회 제한

## 📊 성능 최적화

### 병렬 처리
- `ThreadPoolExecutor`를 사용한 병렬 API 호출
- 영화 상세 정보 대량 조회 시 최대 8개 워커 동시 실행
- 스트리밍 정보 대량 조회 시 병렬 처리

### 캐싱
- `functools.lru_cache`를 통한 메모리 캐싱
- 동일한 요청 시 API 호출 없이 즉시 응답
- 캐시 크기 제한으로 메모리 관리

### 요청 타임아웃
- 모든 외부 API 호출에 6초 타임아웃 설정
- 무한 대기 방지

## 🧪 테스트

```bash
# 스트리밍 API 테스트
python test_streaming_api.py

# API 헬스 체크
curl http://localhost:8000/

# 영화 검색 테스트
curl http://localhost:8000/api/search?q=기생충

# 스트리밍 정보 테스트
curl http://localhost:8000/api/streaming/496243?region=KR
```

## 📚 의존성

주요 라이브러리:
- **Flask**: 웹 프레임워크
- **Flask-CORS**: CORS 처리
- **requests**: HTTP 클라이언트
- **scikit-learn**: TF-IDF 벡터화
- **numpy**: 수치 연산
- **python-dotenv**: 환경 변수 관리
- **gunicorn**: WSGI 서버 (프로덕션)

전체 목록은 `requirements.txt` 참고

## 🎯 다음 개선 사항

- [ ] API 문서화 (Swagger/OpenAPI)
- [x] 스트리밍 정보 API 추가 ✅
- [ ] 영화 리뷰 감성 분석
- [ ] 사용자 평점 기반 추천

## 💡 기여 가이드

### 새로운 API 엔드포인트 추가
1. `api/routes.py`에 새 라우트 함수 추가
2. 필요 시 `services/`에 새 서비스 로직 추가
3. `README.md` 업데이트

### 새로운 서비스 로직 추가
1. `services/` 디렉토리에 새 파일 생성
2. 클래스 또는 함수로 구현
3. 싱글톤 패턴 권장

### 설정 값 추가
1. `config.py`의 `Config` 클래스에 추가
2. `.env.example` 업데이트
3. `README.md`에 문서화

### 공통 함수 추가
1. `utils/` 디렉토리에 헬퍼 함수 추가
2. 재사용 가능한 유틸리티 함수만

## 📖 참고 문서

- [TMDb API 문서](https://developers.themoviedb.org/3)
- [OMDb API 문서](https://www.omdbapi.com/)
- [스트리밍 API 사용 가이드](./STREAMING_API_EXAMPLES.md)
- [Flask 문서](https://flask.palletsprojects.com/)

## 📄 라이센스

MIT License

---

