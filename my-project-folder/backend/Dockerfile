# 1. 베이스 이미지 (Python 3.10)
FROM python:3.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 시스템 패키지 업데이트 및 Java 설치 (konlpy를 위한 Java 필요)
RUN apt-get update && apt-get install -y \
    default-jdk \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. JAVA_HOME 환경 변수 설정
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH=$PATH:$JAVA_HOME/bin

# 5. requirements.txt 먼저 복사 (캐시 활용)
COPY requirements.txt .

# 6. 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 7. 데이터 디렉토리 생성 (vectorizer 저장용)
RUN mkdir -p /app/data

# 8. 나머지 소스 코드 복사
COPY . .

# 9. 서버 실행 (컨테이너 외부에서 접근 가능하도록 0.0.0.0으로 호스트)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]