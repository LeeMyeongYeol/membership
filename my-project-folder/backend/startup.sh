#!/bin/bash

echo "Starting backend services..."

# 1. DB 초기화 (최초 실행 시에만 테이블 생성)
echo "Initializing database..."
python init_database.py

# 2. FastAPI 서버 실행
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
