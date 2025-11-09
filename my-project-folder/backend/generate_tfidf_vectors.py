#!/usr/bin/env python3
"""
TF-IDF 벡터 배치 생성 스크립트

모든 영화 데이터를 기반으로 TF-IDF vectorizer를 학습하고,
각 영화의 벡터를 생성하여 데이터베이스에 저장합니다.

Usage:
    python generate_tfidf_vectors.py
"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Movie, MovieVector
from tfidf_service import (
    create_and_train_vectorizer,
    save_vectorizer,
    generate_tfidf_vector,
    save_movie_vector
)


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("TF-IDF Vector Generation Script")
    print("=" * 60)

    db: Session = SessionLocal()

    try:
        # 1. 모든 영화 데이터 로드
        print("\n[Step 1] Loading all movies from database...")
        movies = db.query(Movie).all()

        if not movies:
            print("No movies found in database. Please add movies first.")
            return

        print(f"Found {len(movies)} movies")

        # 2. TfidfVectorizer 학습
        print("\n[Step 2] Training TF-IDF vectorizer...")
        vectorizer = create_and_train_vectorizer(movies)

        # 3. Vectorizer 저장
        print("\n[Step 3] Saving vectorizer...")
        save_vectorizer(vectorizer)

        # 4. 각 영화의 벡터 생성 및 저장
        print("\n[Step 4] Generating and saving vectors for each movie...")
        success_count = 0
        error_count = 0

        for i, movie in enumerate(movies, 1):
            print(f"\n[{i}/{len(movies)}] Processing: {movie.title} (ID: {movie.id})")

            try:
                # 벡터 생성
                vector = generate_tfidf_vector(movie, vectorizer)

                # 저장
                if save_movie_vector(movie.id, vector, db):
                    success_count += 1
                    print(f"  ✓ Vector saved successfully")
                else:
                    error_count += 1
                    print(f"  ✗ Failed to save vector")

            except Exception as e:
                error_count += 1
                print(f"  ✗ Error: {e}")

        # 5. 결과 요약
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total movies:     {len(movies)}")
        print(f"Successful:       {success_count}")
        print(f"Failed:           {error_count}")
        print("=" * 60)

        if success_count == len(movies):
            print("\n✓ All vectors generated successfully!")
        elif success_count > 0:
            print(f"\n⚠ Partially completed: {success_count}/{len(movies)} vectors generated")
        else:
            print("\n✗ No vectors were generated. Please check errors above.")

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
