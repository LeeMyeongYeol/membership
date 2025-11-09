# 1. 베이스 이미지 (Node 18)
FROM node:20

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. package.json과 package-lock.json 먼저 복사
COPY package.json .
COPY package-lock.json .

# 4. 의존성 설치
RUN npm install

# 5. 나머지 소스 코드 복사
COPY . .

# 6. Vite의 기본 포트 5173번을 노출
EXPOSE 5173

# 7. React 개발 서버 실행 (Vite 방식)
# --host 옵션: 컨테이너 외부(PC)에서 접속을 허용하기 위해 필수
CMD ["npm", "run", "dev", "--", "--host"]