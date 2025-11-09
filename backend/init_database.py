"""
데이터베이스 초기화 스크립트

이 스크립트는 다음 작업을 수행합니다:
1. PostgreSQL 연결 확인
2. init_db.sql 스크립트 실행 (pgvector 확장, 테이블 생성)
3. 초기 장르 데이터 삽입
"""

import os
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 환경 변수에서 DB 연결 정보 가져오기
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "movie_db")

DB_CONFIG = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
    "database": DB_NAME
}


def wait_for_db(max_retries=30, delay=2):
    """데이터베이스 연결 대기"""
    print(f"Waiting for database at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            print("✓ Database is ready!")
            return True
        except psycopg2.OperationalError as e:
            if i < max_retries - 1:
                print(f"  Attempt {i+1}/{max_retries}: Database not ready yet, retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"✗ Failed to connect to database after {max_retries} attempts")
                print(f"  Error: {e}")
                return False
    return False


def init_db():
    """데이터베이스 초기화"""
    print("\n=== Database Initialization ===\n")

    # 1. DB 연결 대기
    if not wait_for_db():
        return False

    # 2. SQL 스크립트 읽기
    sql_file_path = os.path.join(os.path.dirname(__file__), "init_db.sql")

    if not os.path.exists(sql_file_path):
        print(f"✗ SQL file not found: {sql_file_path}")
        return False

    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # 3. SQL 실행
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("Executing init_db.sql...")
        cursor.execute(sql_script)

        print("✓ Database schema created successfully!")
        print("✓ pgvector extension enabled")
        print("✓ Tables created: movies, genres, keywords, movie_genres, movie_keywords, movie_vectors")
        print("✓ Indexes created for performance optimization")
        print("✓ Initial genre data inserted")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"✗ Error during database initialization: {e}")
        return False


def verify_db():
    """데이터베이스 상태 확인"""
    print("\n=== Database Verification ===\n")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # pgvector 확장 확인
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        if result:
            print(f"✓ pgvector extension: {result[0]} v{result[1]}")
        else:
            print("✗ pgvector extension not found")

        # 테이블 목록 확인
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\n✓ Tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")

        # 장르 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM genres;")
        genre_count = cursor.fetchone()[0]
        print(f"\n✓ Genres: {genre_count} records")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"✗ Error during verification: {e}")
        return False


if __name__ == "__main__":
    success = init_db()

    if success:
        verify_db()
        print("\n=== Initialization Complete ===")
        print("\nYou can now:")
        print("1. Import movie data using TMDb API")
        print("2. Generate TF-IDF vectors for movies")
        print("3. Start using the recommendation system")
    else:
        print("\n=== Initialization Failed ===")
        exit(1)
