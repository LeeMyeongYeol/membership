# Dockerfile

# 1. Python 3.10-slim 버전을 기반으로 시작
FROM python:3.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. requirements.txt를 먼저 복사하여 종속성 캐싱 활용
COPY requirements.txt .

# 4. 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. 나머지 소스 코드(.env 파일 제외) 복사
COPY . .

# 6. .env 파일은 Docker 이미지에 포함시키지 않습니다. (보안)
#    대신 docker-compose.yml의 'env_file'을 통해 런타임에 주입합니다.

# 7. 앱이 사용할 포트 (기본 8000)
#    (app.py의 PORT 환경 변수와 일치시킴)
EXPOSE 8000

# 8. Gunicorn을 사용하여 앱 실행
#    -b 0.0.0.0:8000 : 모든 인터페이스의 8000번 포트로 바인딩
#    -w 4 : 워커 프로세스 4개 (CPU 코어 수에 따라 조절)
#    app:app : app.py 파일의 app 객체를 실행
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "4", "app:app"]